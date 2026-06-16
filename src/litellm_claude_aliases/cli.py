"""``litellm-with-aliases`` CLI — drop-in replacement for the ``litellm`` command.

Usage:

    litellm-with-aliases --config /path/to/config.yaml --port 4000

The wrapper reads the ``general_settings.model_aliases`` block from the same
config file LiteLLM will use, then delegates to the upstream ``litellm`` CLI.
"""

from __future__ import annotations

import sys
from typing import List, Optional, Tuple

from . import aliases
from .config import load_from_yaml
from .patch import bootstrap


def parse_args(argv: List[str]) -> Tuple[Optional[str], List[str]]:
    """Extract the ``--config``/``-c`` value and return ``(config_path, passthrough)``.

    Supports both ``--config <path>`` (space-separated) and ``--config=<path>``
    (equals form). Other flags are returned unchanged in ``passthrough`` so they
    can be forwarded to the upstream ``litellm`` CLI.
    """
    config_path: Optional[str] = None
    passthrough: List[str] = []
    skip_next = False
    for arg in argv:
        if skip_next:
            config_path = arg
            passthrough.append(arg)
            skip_next = False
            continue
        if arg in ("--config", "-c"):
            passthrough.append(arg)
            skip_next = True
            continue
        if arg.startswith("--config="):
            config_path = arg.split("=", 1)[1]
            passthrough.append(arg)
            continue
        if arg.startswith("-c="):
            config_path = arg.split("=", 1)[1]
            passthrough.append(arg)
            continue
        passthrough.append(arg)
    return config_path, passthrough


def main() -> int:
    config_path, passthrough = parse_args(sys.argv[1:])

    bootstrap()
    load_from_yaml(config_path)

    if aliases.is_enabled():
        print(
            f"litellm_claude_aliases: enabled with "
            f"{sum(1 for _ in _request_keys())} request mappings, "
            f"{sum(1 for _ in _response_keys())} response mappings"
        )
    else:
        print("litellm_claude_aliases: disabled (no model_aliases in config)")

    # Delegate to the upstream litellm CLI. We re-exec so the child process
    # inherits all of LiteLLM's signal handling and argument parsing.
    from litellm.proxy.proxy_cli import run_server

    sys.argv = ["litellm"] + passthrough
    run_server()
    return 0


def _request_keys():
    return (k for k in aliases._REQUEST_MAPPINGS)  # noqa: SLF001


def _response_keys():
    return (k for k in aliases._RESPONSE_MAPPINGS)  # noqa: SLF001


if __name__ == "__main__":
    raise SystemExit(main())
