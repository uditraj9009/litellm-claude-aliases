"""litellm-claude-aliases — opt-in model name aliasing for LiteLLM proxy.

Designed for clients that need Anthropic-style model names (e.g. Claude Desktop)
when talking to a LiteLLM proxy that uses internal model names.

Configure via ``general_settings.model_aliases`` in your config.yaml:

    general_settings:
      model_aliases:
        enabled: true
        request_mappings:    # client-name -> internal-name
          "claude-sonnet-4-6-20251120": "claude-3-5-sonnet"
        response_mappings:   # internal-name -> advertised-name
          "claude-3-5-sonnet": "claude-sonnet-4-6-20251120"

Then run the proxy with the ``litellm-with-aliases`` wrapper instead of
``litellm``:

    litellm-with-aliases --config config.yaml --port 4000
"""

from . import aliases
from .config import load_from_yaml
from .patch import bootstrap

__all__ = ["aliases", "bootstrap", "load_from_yaml"]
__version__ = "0.1.0"
