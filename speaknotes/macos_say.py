from __future__ import annotations

import subprocess
from pathlib import Path


def say_to_file(text: str, output_path: Path, voice_name: str | None = None, rate_wpm: int | None = None) -> None:
    """
    Uses macOS 'say' to export speech audio to a file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["say", "-o", str(output_path)]

    if voice_name and voice_name != "Default (system)":
        cmd += ["-v", voice_name]

    if rate_wpm:
        cmd += ["-r", str(rate_wpm)]

    cmd.append(text)

    subprocess.run(cmd, check=True)

def say_now(text: str, voice_name: str | None = None, rate_wpm: int | None = None) -> None:
    """
    Uses macOS 'say' to speak text immediately.
    """
    cmd = ["say"]

    if voice_name and voice_name != "Default (system)":
        cmd += ["-v", voice_name]

    if rate_wpm:
        cmd += ["-r", str(rate_wpm)]

    cmd.append(text)

    subprocess.run(cmd, check=True)
