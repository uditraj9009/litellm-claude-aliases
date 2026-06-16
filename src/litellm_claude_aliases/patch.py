"""Monkey-patches LiteLLM proxy functions to call the alias helpers.

This module is the *only* piece that touches upstream LiteLLM. It wraps three
FastAPI endpoint functions:

- ``proxy_server.model_list`` — rewrites the ``id`` of each entry in the
  ``/v1/models`` response so clients see the alias name.
- ``proxy_server.chat_completion`` — translates the ``model`` field of the
  request body from alias name to internal name before processing.
- ``_read_request_body`` — translates model names in request body for
  the Anthropic-format ``/v1/messages`` endpoint.

Wrapping is done with ``functools.wraps`` so that FastAPI's route table,
OpenAPI metadata, and signature inspection all keep working.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict

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


def _wrap_read_request_body(original: Callable) -> Callable:
    """Wrap _read_request_body to translate model names in request body."""
    @functools.wraps(original)
    async def wrapper(request: Any) -> Dict:
        result = await original(request)
        if isinstance(result, dict) and aliases.is_enabled():
            model = result.get("model")
            if isinstance(model, str) and model in aliases._REQUEST_MAPPINGS:
                print(f"[DEBUG _read_request_body] Translating model: {model} -> {aliases._REQUEST_MAPPINGS[model]}")
                result["model"] = aliases._REQUEST_MAPPINGS[model]
        return result

    return wrapper


def bootstrap() -> None:
    """Install the alias patches into LiteLLM proxy.

    Idempotent — safe to call multiple times. Loads the helper from
    ``litellm.proxy.anthropic_endpoints.model_aliases`` if available so we
    keep one source of truth if a user has the in-tree variant installed.
    """
    from litellm.proxy import proxy_server
    from litellm.proxy.common_utils.http_parsing_utils import _read_request_body
    from litellm.proxy.anthropic_endpoints import endpoints as anthropic_endpoints

    if getattr(proxy_server.model_list, "_lca_wrapped", False):
        return

    # Save original function references
    original_model_list = proxy_server.model_list
    original_chat_completion = proxy_server.chat_completion
    original_read_request_body = _read_request_body

    proxy_server.model_list = _wrap_model_list(proxy_server.model_list)
    proxy_server.model_list._lca_wrapped = True  # type: ignore[attr-defined]
    proxy_server.model_list.__wrapped__ = original_model_list  # type: ignore[attr-defined]

    proxy_server.chat_completion = _wrap_chat_completion(proxy_server.chat_completion)
    proxy_server.chat_completion._lca_wrapped = True  # type: ignore[attr-defined]
    proxy_server.chat_completion.__wrapped__ = original_chat_completion  # type: ignore[attr-defined]

    wrapped_read_request_body = _wrap_read_request_body(_read_request_body)
    import litellm.proxy.common_utils.http_parsing_utils as http_parsing
    http_parsing._read_request_body = wrapped_read_request_body
    anthropic_endpoints._read_request_body = wrapped_read_request_body

    wrapped_model_list = proxy_server.model_list
    wrapped_chat_completion = proxy_server.chat_completion

    for route in proxy_server.router.routes:
        if hasattr(route, 'endpoint'):
            if route.endpoint is original_model_list:
                route.endpoint = wrapped_model_list
            elif route.endpoint is original_chat_completion:
                route.endpoint = wrapped_chat_completion

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
