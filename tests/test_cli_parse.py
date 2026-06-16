"""Tests for the CLI argument parser.

The space-separated form ``--config <path>`` was broken: the parser appended
the path to passthrough but never assigned it to config_path, so the alias
block was silently ignored and ``load_from_yaml(None)`` was a no-op. These
tests pin the fix in place.
"""

from __future__ import annotations

import pytest

from litellm_claude_aliases.cli import parse_args


def test_space_separated_long_flag():
    config_path, passthrough = parse_args(
        ["--config", "/tmp/some/config.yaml", "--port", "4000"]
    )
    assert config_path == "/tmp/some/config.yaml"
    assert passthrough == ["--config", "/tmp/some/config.yaml", "--port", "4000"]


def test_space_separated_short_flag():
    config_path, passthrough = parse_args(
        ["-c", "/tmp/cfg.yaml", "--port", "4000"]
    )
    assert config_path == "/tmp/cfg.yaml"
    assert passthrough == ["-c", "/tmp/cfg.yaml", "--port", "4000"]


def test_equals_separated_long_flag():
    config_path, passthrough = parse_args(
        ["--config=/tmp/cfg.yaml", "--port", "4000"]
    )
    assert config_path == "/tmp/cfg.yaml"
    assert passthrough == ["--config=/tmp/cfg.yaml", "--port", "4000"]


def test_equals_separated_short_flag():
    config_path, passthrough = parse_args(["-c=/tmp/cfg.yaml"])
    assert config_path == "/tmp/cfg.yaml"


def test_no_config_flag_returns_none():
    config_path, passthrough = parse_args(["--port", "4000"])
    assert config_path is None
    assert passthrough == ["--port", "4000"]


def test_empty_argv():
    config_path, passthrough = parse_args([])
    assert config_path is None
    assert passthrough == []


def test_config_at_end_with_nothing_after_uses_last_arg():
    """If --config is the last arg with no value, parse_args would return None
    for config_path and the lone --config would still be in passthrough.
    This is the existing behavior — the upstream CLI will error out, which is
    acceptable."""
    config_path, passthrough = parse_args(["--port", "4000", "--config"])
    assert config_path is None
    assert passthrough == ["--port", "4000", "--config"]
