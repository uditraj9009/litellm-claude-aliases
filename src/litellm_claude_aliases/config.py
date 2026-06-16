"""Read the ``model_aliases`` block from a LiteLLM config.yaml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from . import aliases


def load_from_yaml(config_path: Optional[str]) -> None:
    """Load the alias config from a LiteLLM config.yaml.

    Reads the file, looks for ``general_settings.model_aliases``, and configures
    the in-process alias state. Safe to call with ``None`` (no-op).
    """
    if not config_path:
        return
    path = Path(config_path)
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        config: Dict[str, Any] = yaml.safe_load(fh) or {}
    general = config.get("general_settings") or {}
    aliases.configure(general.get("model_aliases"))


def load_from_env_or_default() -> Optional[str]:
    """Return a config path from the env, or None if not set.

    Resolves ``LITELLM_CLI_CONFIG`` first, then ``LITELLM_CONFIG``. Returns the
    path *string* (not loaded — call :func:`load_from_yaml` on it). The point
    of this function is to give the auto-bootstrap step in ``bootstrap()``
    something to read.
    """
    return os.environ.get("LITELLM_CLI_CONFIG") or os.environ.get("LITELLM_CONFIG")
