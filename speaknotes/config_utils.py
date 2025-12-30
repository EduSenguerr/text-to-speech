from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONFIG_FILE = Path("config.json")


def load_config() -> dict[str, Any]:
    """
    Loads config.json. Returns an empty dict if missing or invalid.
    """
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(config: dict[str, Any]) -> None:
    """
    Saves the given config dict into config.json.
    """
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
