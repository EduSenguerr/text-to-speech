from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import Any


HISTORY_FILE = Path("history.json")


def load_history() -> list[Any]:
    """
    Loads the current TTS history from the JSON file.
    If the file doesn't exist or is invalid, returns an empty list.
    """
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def append_history(entry: dict[str, Any]) -> None:
    """
    Appends a new history entry to the JSON file.
    """
    history = load_history()
    history.append(entry)
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")

def create_entry(file: Path, settings: Any, mode: str, text: str, source: str = "manual", source_path: str = "") -> dict[str, Any]:
    """
    Creates a new history entry object with a timestamp and relevant TTS data.
    'source' describes where the text came from (e.g., 'manual' or 'txt').
    'source_path' stores the originating file path/name when applicable.
    """
    preview_snippet = text[:60].replace("\n", " ")
    return {
        "date": datetime.now().isoformat(timespec="seconds"),
        "file": str(file.resolve()),
        "rate": settings.rate,
        "volume": settings.volume,
        "voice": settings.voice_id or "default",
        "mode": mode,
        "source": source,
        "source_path": source_path,
        "text_preview": preview_snippet,
    }

