from __future__ import annotations

from .tts import TTSSettings

# Opinionated presets to make the tool feel like a real product.
PRESETS: dict[str, TTSSettings] = {
    "study": TTSSettings(rate=175, volume=1.0),
    "podcast": TTSSettings(rate=190, volume=1.0),
    "relax": TTSSettings(rate=155, volume=0.9),
    "custom": TTSSettings(rate=175, volume=1.0),
}
