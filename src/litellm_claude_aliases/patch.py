"""Monkey-patches LiteLLM proxy functions to call the alias helpers.

This module is the *only* piece that touches upstream LiteLLM. It wraps three
FastAPI endpoint functions:

- ``proxy_server.model_list`` — rewrites the ``id`` of each entry in the
  ``/v1/models`` response so clients see the alias name.
- ``proxy_server.chat_completion`` — translates the ``model`` field of the
  request body from alias name to internal name before processing.
- ``anthropic_endpoints.endpoints.anthropic_response`` — same as above for
  the Anthropic-format ``/v1/messages`` endpoint.

Wrapping is done with ``functools.wraps`` so that FastAPI's route table,
OpenAPI metadata, and signature inspection all keep working.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from . import aliases

_LOGGER = logging.getLogger("litellm_claude_aliases")


def _wrap_model_list(original: Callable) -> Callable:
    @functools.wraps(original)
    async def model_list(*args: Any, **kwargs: Any):
        result = await original(*args, **kwargs)
        if isinstance(result, dict) and isinstance(result.get("data"), list):
            result["data"] = aliases.remap_model_list(result["data"])
        return result

    return model_list


def _wrap_chat_completion(original: Callable) -> Callable:
    @functools.wraps(original)
    async def chat_completion(*args: Any, **kwargs: Any):
        data = kwargs.get("data")
        if isinstance(data, dict):
            aliases.translate_request_body(data)
        return await original(*args, **kwargs)

    return chat_completion


def _wrap_anthropic_response(original: Callable) -> Callable:
    @functools.wraps(original)
    async def anthropic_response(*args: Any, **kwargs: Any):
        data = kwargs.get("data")
        if isinstance(data, dict):
            aliases.translate_request_body(data)
        return await original(*args, **kwargs)

    return anthropic_response


def bootstrap() -> None:
    """Install the alias patches into LiteLLM proxy.

    Idempotent — safe to call multiple times. Loads the helper from
    ``litellm.proxy.anthropic_endpoints.model_aliases`` if available so we
    keep one source of truth if a user has the in-tree variant installed.
    """
    from litellm.proxy import proxy_server
    from litellm.proxy.anthropic_endpoints import endpoints as anthropic_endpoints

    if getattr(proxy_server.model_list, "_lca_wrapped", False):
        return

    proxy_server.model_list = _wrap_model_list(proxy_server.model_list)
    proxy_server.model_list._lca_wrapped = True  # type: ignore[attr-defined]

    proxy_server.chat_completion = _wrap_chat_completion(proxy_server.chat_completion)
    proxy_server.chat_completion._lca_wrapped = True  # type: ignore[attr-defined]

    anthropic_endpoints.anthropic_response = _wrap_anthropic_response(
        anthropic_endpoints.anthropic_response
    )
    anthropic_endpoints.anthropic_response._lca_wrapped = True  # type: ignore[attr-defined]

    _LOGGER.info("litellm_claude_aliases: patches installed")


def auto_configure() -> None:
    """Bootstrap + read config from env. Used by the .pth auto-import path.

    Resolves the config path from ``LITELLM_CLI_CONFIG`` or ``LITELLM_CONFIG``
    env vars and applies it, then installs the patches. Intended to be called
    once at Python startup via a sitecustomize-style hook.
    """
    from .config import load_from_env_or_default, load_from_yaml

    config_path = load_from_env_or_default()
    if config_path:
        load_from_yaml(config_path)
    bootstrap()
