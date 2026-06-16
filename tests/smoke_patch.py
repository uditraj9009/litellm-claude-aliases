"""End-to-end smoke test for the patch layer.

Runs without pytest-asyncio: just plain asyncio.run. Verifies the wrappers
delegate and translate as expected against mock endpoint functions.

Usage (from the repo root):

    pip install -e ".[test]"
    python tests/smoke_patch.py

This requires ``litellm[proxy]`` to be importable in the active Python env
(so the patches can be installed). It's a plain script, not a pytest test,
because pytest-asyncio complicates the bootstrap path and we want this to
work in any environment where LiteLLM is installed.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure src/ is on path so this script can be run directly.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

import litellm.proxy.proxy_server as ps  # noqa: E402
import litellm.proxy.anthropic_endpoints.endpoints as ae  # noqa: E402

from litellm_claude_aliases import aliases  # noqa: E402
from litellm_claude_aliases.patch import bootstrap  # noqa: E402


def _make_fake_model_list(return_value):
    async def fake(*args, **kwargs):
        return return_value

    fake.__name__ = "model_list"
    return fake


def _make_fake_chat(captured):
    async def fake(*args, **kwargs):
        captured.append(kwargs.get("data"))
        return {"ok": True}

    fake.__name__ = "chat_completion"
    return fake


def _make_fake_anthropic(captured):
    async def fake(*args, **kwargs):
        captured.append(kwargs.get("data"))
        return {"ok": True}

    fake.__name__ = "anthropic_response"
    return fake


def _unwrap(wrapped):
    while hasattr(wrapped, "__wrapped__"):
        wrapped = wrapped.__wrapped__
    return wrapped


def main() -> int:
    failures = []

    # --- Test 1: model_list remap ---
    aliases.configure({
        "enabled": True,
        "response_mappings": {"claude-3-5-sonnet": "claude-sonnet-4-6-20251120"},
    })
    original = _make_fake_model_list(
        {"data": [{"id": "claude-3-5-sonnet", "object": "model"}], "object": "list"}
    )
    ps.model_list = original
    bootstrap()
    result = asyncio.run(ps.model_list())
    if result["data"][0]["id"] != "claude-sonnet-4-6-20251120":
        failures.append(f"model_list remap: got {result['data'][0]['id']}")
    ps.model_list = _unwrap(ps.model_list)
    print("PASS  model_list remap")

    # --- Test 2: chat_completion translate ---
    aliases.configure({
        "enabled": True,
        "request_mappings": {"claude-sonnet-4-6-20251120": "claude-3-5-sonnet"},
    })
    captured_cc = []
    ps.chat_completion = _make_fake_chat(captured_cc)
    bootstrap()
    asyncio.run(ps.chat_completion(data={"model": "claude-sonnet-4-6-20251120"}))
    if captured_cc[0]["model"] != "claude-3-5-sonnet":
        failures.append(f"chat_completion translate: got {captured_cc[0]['model']}")
    ps.chat_completion = _unwrap(ps.chat_completion)
    print("PASS  chat_completion translate")

    # --- Test 3: anthropic_response translate ---
    captured_ar = []
    ae.anthropic_response = _make_fake_anthropic(captured_ar)
    bootstrap()
    asyncio.run(ae.anthropic_response(data={"model": "claude-opus-4-8-20251120"}))
    if captured_ar[0]["model"] != "claude-3-5-opus":
        failures.append(
            f"anthropic_response translate: got {captured_ar[0]['model']}"
        )
    ae.anthropic_response = _unwrap(ae.anthropic_response)
    print("PASS  anthropic_response translate")

    # --- Test 4: idempotency ---
    ps.model_list = _make_fake_model_list({"data": [], "object": "list"})
    ps.chat_completion = _make_fake_chat([])
    ae.anthropic_response = _make_fake_anthropic([])
    bootstrap()
    first = ps.model_list
    bootstrap()
    if ps.model_list is not first:
        failures.append("bootstrap is not idempotent")
    print("PASS  bootstrap idempotent")
    ps.model_list = _unwrap(ps.model_list)
    ps.chat_completion = _unwrap(ps.chat_completion)
    ae.anthropic_response = _unwrap(ae.anthropic_response)

    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nAll smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
