"""Model name alias state — translation tables for the alias feature."""

from typing import Any, Dict, List, Optional

_ENABLED: bool = False
_REQUEST_MAPPINGS: Dict[str, str] = {}
_RESPONSE_MAPPINGS: Dict[str, str] = {}


def configure(cfg: Optional[Dict[str, Any]]) -> None:
    global _ENABLED, _REQUEST_MAPPINGS, _RESPONSE_MAPPINGS
    cfg = cfg or {}
    _ENABLED = bool(cfg.get("enabled", False))
    _REQUEST_MAPPINGS = dict(cfg.get("request_mappings") or {})
    _RESPONSE_MAPPINGS = dict(cfg.get("response_mappings") or {})


def is_enabled() -> bool:
    return _ENABLED


def translate_request_body(data: Dict[str, Any]) -> None:
    if not _ENABLED or not isinstance(data, dict):
        return
    model = data.get("model")
    if isinstance(model, str) and model in _REQUEST_MAPPINGS:
        data["model"] = _REQUEST_MAPPINGS[model]


def remap_model_list(model_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not _ENABLED or not _RESPONSE_MAPPINGS:
        return model_data
    remapped: List[Dict[str, Any]] = []
    for entry in model_data:
        if isinstance(entry, dict) and entry.get("id") in _RESPONSE_MAPPINGS:
            new_entry = dict(entry)
            new_entry["id"] = _RESPONSE_MAPPINGS[entry["id"]]
            remapped.append(new_entry)
        else:
            remapped.append(entry)
    return remapped
