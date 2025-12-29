from __future__ import annotations

from pathlib import Path


def read_text_file(file_path: Path) -> str:
    """
    Reads a UTF-8 text file and returns its content.
    Raises FileNotFoundError if the file doesn't exist.
    """
    return file_path.read_text(encoding="utf-8").strip()


def get_user_text() -> str:
    """
    Prompts the user to either paste text or load it from a .txt file.
    Always returns the final text as a single string.
    """
    print("\nChoose input method:")
    print("  1) Paste text")
    print("  2) Load from .txt file")

    choice = input("Select 1 or 2 [1]: ").strip() or "1"

    if choice == "2":
        path_str = input("Enter the path to your .txt file (e.g., samples/example.txt): ").strip()
        file_path = Path(path_str)

        try:
            text = read_text_file(file_path)
            if text:
                return text
            print("File was empty.")
        except FileNotFoundError:
            print("File not found.")

    # fallback to paste mode
    text = input("Paste your text: ").strip()
    return text