from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pyttsx3


@dataclass(frozen=True)
class TTSSettings:
    """
    Holds Text-to-Speech settings so we can reuse them consistently.
    """
    rate: int = 185           # Speaking speed (approx. words per minute)
    volume: float = 1.0       # Range: 0.0 to 1.0
    voice_id: Optional[str] = None  # If None, the system default voice is used


def list_voices() -> list[tuple[str, str]]:
    """
    Returns a list of available voices as (voice_id, human_readable_name).
    """
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")

    result: list[tuple[str, str]] = []
    for v in voices:
        name = getattr(v, "name", "Unknown")
        result.append((v.id, name))
    return result

def speak_now(text: str, settings: TTSSettings = TTSSettings()) -> None:
    """
    Speaks the given text immediately (no file output).
    """
    engine = pyttsx3.init()

    engine.setProperty("rate", settings.rate)
    engine.setProperty("volume", settings.volume)
    if settings.voice_id:
        engine.setProperty("voice", settings.voice_id)

    engine.say(text)
    engine.runAndWait()
    engine.stop()


def synthesize_to_file(
    text: str,
    output_path: Path,
    settings: TTSSettings = TTSSettings(),
) -> Path:
    """
    Converts the given text into speech and saves it to output_path.
    Returns the final output path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    engine = pyttsx3.init()

    # Apply settings
    engine.setProperty("rate", settings.rate)
    engine.setProperty("volume", settings.volume)
    if settings.voice_id:
        engine.setProperty("voice", settings.voice_id)

    print(f"[SpeakNotes] Saving audio to: {output_path}")
    engine.save_to_file(text, str(output_path))

    print("[SpeakNotes] Running engine (this should finish)...")
    engine.runAndWait()

    # Make sure the engine is stopped/cleaned up
    engine.stop()
    print("[SpeakNotes] Done.")

    return output_path
