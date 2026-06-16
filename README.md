# litellm-claude-aliases

Drop-in model name aliasing for [LiteLLM](https://github.com/BerriAI/litellm) proxy.

Designed for clients that need Anthropic-style model names (e.g. **Claude Desktop**)
when talking to a LiteLLM proxy that uses internal model names. Lets you advertise
`claude-sonnet-4-6-20251120` to clients while your proxy routes to whatever internal
`model_name` you want.

## Install

```bash
pip install litellm-claude-aliases
```

## Configure

Add a `model_aliases` block to your existing `config.yaml` under `general_settings`:

```yaml
general_settings:
  master_key: "sk-..."
  model_aliases:
    enabled: true
    request_mappings:    # client-name -> internal-name
      "claude-sonnet-4-6-20251120": "claude-3-5-sonnet"
      "claude-opus-4-8-20251120":   "claude-3-5-opus"
    response_mappings:   # internal-name -> advertised-name (in /v1/models)
      "claude-3-5-sonnet": "claude-sonnet-4-6-20251120"
      "claude-3-5-opus":   "claude-opus-4-8-20251120"

model_list:
  - model_name: claude-3-5-sonnet
    litellm_params:
      model: minimax/Minimax-M3
      ...
  - model_name: claude-3-5-opus
    litellm_params:
      model: minimax/Minimax-M2.7-highspeed
      ...
```

## Run

Use the `litellm-with-aliases` wrapper instead of `litellm`:

```bash
litellm-with-aliases --config config.yaml --port 4000
```

All other `litellm` flags pass through unchanged.

## What it does

| Endpoint | Before | After |
|---|---|---|
| `GET /v1/models` | returns internal model IDs | returns aliased IDs |
| `POST /v1/messages` with alias model | `401 — model not found` | translates to internal, routes correctly |
| `POST /v1/chat/completions` with alias model | `401 — model not found` | translates to internal, routes correctly |

If `model_aliases.enabled` is `false` (or the block is missing), the wrapper is a
no-op and `litellm` runs as if the package weren't installed.

## Notes on auth headers

LiteLLM's `os.environ/FOO` syntax for resolving env vars is **only** applied to
the `api_key` field of a `litellm_params` block. It is **not** applied to
`extra_headers` values. Putting a placeholder like
`X-Api-Key: "os.environ/FOO"` in `extra_headers` sends the literal string and
fails with `Header value must be str or bytes, not NoneType`.

For providers whose API takes the key in a non-standard header, configure that
provider's own key resolution (e.g. set `api_key: os.environ/MINIMAX_API_KEY`
on the model and let the provider's transformation inject the right header),
not `extra_headers`.

## License

MIT
