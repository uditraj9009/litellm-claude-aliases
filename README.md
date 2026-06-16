# litellm-claude-aliases

Drop-in model name aliasing for [LiteLLM](https://github.com/BerriAI/litellm) proxy.

Designed for clients that need Anthropic-style model names (e.g. **Claude Desktop**) when talking to a LiteLLM proxy that uses different internal model names. Lets you advertise `claude-sonnet-4-6-20251120` to clients while your proxy routes to whatever internal `model_name` you want.

## Install

### From PyPI (once published)
```bash
pip install litellm-claude-aliases
```

### From GitHub (latest version)
```bash
pip install git+https://github.com/uditraj9009/litellm-claude-aliases.git
```

## Configure

Create a `config.yaml` file with your model aliases:

```yaml
general_settings:
  master_key: "your-master-key"
  model_aliases:
    enabled: true
    request_mappings:    # client-name -> internal-name (what your litellm config uses)
      "claude-sonnet-4-6-20251120": "claude-3-5-sonnet"
      "claude-opus-4-8-20251120":   "claude-3-5-opus"
    response_mappings:   # internal-name -> advertised-name (what clients see in /v1/models)
      "claude-3-5-sonnet": "claude-sonnet-4-6-20251120"
      "claude-3-5-opus":   "claude-opus-4-8-20251120"

model_list:
  - model_name: claude-3-5-sonnet
    litellm_params:
      model: your-provider/model-name    # internal model name
      api_key: os.environ/YOUR_API_KEY
      api_base: https://api.your-provider.com

  - model_name: claude-3-5-opus
    litellm_params:
      model: your-provider/another-model
      api_key: os.environ/YOUR_API_KEY
      api_base: https://api.your-provider.com
```

### Key configuration points:

- **`request_mappings`**: Translates model names from client requests to your internal model names. E.g., when Claude Desktop sends `claude-sonnet-4-6-20251120`, it gets translated to `claude-3-5-sonnet` before LiteLLM processes it.

- **`response_mappings`**: Translates model names in the `/v1/models` response so clients see the aliased names instead of your internal names.

- **`model_list`**: Your actual LiteLLM model configuration with internal names.

## Run

Use the `litellm-with-aliases` wrapper instead of `litellm`:

```bash
litellm-with-aliases --config config.yaml --port 4000
```

All other `litellm` flags pass through unchanged. For example:

```bash
litellm-with-aliases --config config.yaml --port 4000 --drop_params
```

## Complete Setup Example

1. Install the package:
```bash
pip install git+https://github.com/uditraj9009/litellm-claude-aliases.git
```

2. Create a config file at `~/litellm_config.yaml`:
```bash
cat > ~/litellm_config.yaml << 'EOF'
general_settings:
  master_key: "your-master-key"
  model_aliases:
    enabled: true
    request_mappings:
      "claude-sonnet-4-6-20251120": "claude-3-5-sonnet"
      "claude-opus-4-8-20251120": "claude-3-5-opus"
    response_mappings:
      "claude-3-5-sonnet": "claude-sonnet-4-6-20251120"
      "claude-3-5-opus": "claude-opus-4-8-20251120"

model_list:
  - model_name: claude-3-5-sonnet
    litellm_params:
      model: minimax/Minimax-M2.7-highspeed
      api_key: your-api-key
      api_base: https://api.minimax.io/anthropic

  - model_name: claude-3-5-opus
    litellm_params:
      model: minimax/Minimax-M3
      api_key: your-api-key
      api_base: https://api.minimax.io/anthropic
EOF
```

3. Start the proxy:
```bash
litellm-with-aliases --config ~/litellm_config.yaml --port 4000
```

4. Configure Claude Desktop to use `http://localhost:4000` with your master key as the API key.

## How it works

| Endpoint | Without Plugin | With Plugin |
|---|---|---|
| `GET /v1/models` | returns internal model IDs | returns aliased IDs |
| `POST /v1/messages` with alias model | `400 — model not found` | translates to internal, routes correctly |
| `POST /v1/chat/completions` with alias model | `400 — model not found` | translates to internal, routes correctly |

If `model_aliases.enabled` is `false` (or the block is missing), the wrapper is a no-op and `litellm` runs as if the package weren't installed.

## Note on API Keys

LiteLLM's `os.environ/FOO` syntax for resolving env vars is **only** applied to the `api_key` field of a `litellm_params` block. If your provider requires a custom header (like `X-Api-Key`), put the actual key value directly in your config or ensure your environment variable is set before running.

## License

MIT
