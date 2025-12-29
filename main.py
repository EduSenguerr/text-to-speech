from __future__ import annotations

from datetime import datetime
from pathlib import Path

from speaknotes.presets import PRESETS
from speaknotes.tts import TTSSettings, list_voices, synthesize_to_file, speak_now


def safe_filename(base: str) -> str:
    """
    Converts a string into a short, filesystem-safe filename.
    """
    base = base.strip().lower()
    base = "".join(ch for ch in base if ch.isalnum() or ch in (" ", "-", "_"))
    base = base.replace(" ", "-")
    return base[:40] or "note"


def main() -> None:
    print("\nSpeakNotes — quick TTS tool\n")

    user_text = input("Paste your text: ").strip()
    if not user_text:
        print("No text provided. Exiting.")
        return

    print("\nChoose a preset:")
    for key in PRESETS:
        print(f" - {key}")

    preset = input("Preset (study/podcast/relax) [study]: ").strip().lower() or "study"
    settings = PRESETS.get(preset, PRESETS["study"])

    pick_voice = input("\nDo you want to pick a specific voice? (y/n) [n]: ").strip().lower()
    if pick_voice == "y":
        voices = list_voices()
        for idx, (_, name) in enumerate(voices):
            print(f"{idx}: {name}")

        choice = input("Voice number: ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 0 <= idx < len(voices):
                settings = TTSSettings(rate=settings.rate, volume=settings.volume, voice_id=voices[idx][0])

    mode = input("\nMode: preview / export / both [export]: ").strip().lower() or "export"

    if mode in ("preview", "both"):
        print("\n🔊 Previewing speech...")
        speak_now(text=user_text, settings=settings)

    if mode in ("export", "both"):
        out_dir = Path("outputs")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}-{safe_filename(user_text[:60])}.aiff"
        out_path = out_dir / filename

        print("\n💾 Exporting audio file...")
        synthesize_to_file(text=user_text, output_path=out_path, settings=settings)
        print(f"\n✅ Audio saved: {out_path}\n")


    

if __name__ == "__main__":
    main()
