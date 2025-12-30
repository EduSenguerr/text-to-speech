from __future__ import annotations

import tkinter as tk
import subprocess
import sys

from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

from speaknotes.presets import PRESETS
from speaknotes.tts import TTSSettings, list_voices, speak_now, synthesize_to_file
from speaknotes.history_utils import append_history, create_entry


class SpeakNotesApp:
    """
    A simple Tkinter GUI wrapper around the SpeakNotes TTS features.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SpeakNotes")
        self.root.geometry("720x520")

        # ---- Data we keep in the app (state) ----
        self.voice_items = list_voices()  # list of (voice_id, voice_name)
        self.voice_name_to_id = {name: vid for vid, name in self.voice_items}

        # ---- UI Variables (Tkinter StringVars) ----
        self.preset_var = tk.StringVar(value="study")
        self.voice_var = tk.StringVar(value="Default (system)")
        self.status_var = tk.StringVar(value="Ready.")

        # ---- Build UI ----
        self._build_layout()

    def _build_layout(self) -> None:
        # Top row: preset + voice
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=12, pady=10)

        tk.Label(top_frame, text="Preset:").pack(side="left")
        preset_menu = tk.OptionMenu(top_frame, self.preset_var, *PRESETS.keys())
        preset_menu.pack(side="left", padx=8)

        tk.Label(top_frame, text="Voice:").pack(side="left", padx=(16, 0))

        voice_options = ["Default (system)"] + [name for _, name in self.voice_items]
        voice_menu = tk.OptionMenu(top_frame, self.voice_var, *voice_options)
        voice_menu.pack(side="left", padx=8)

        # Text box + scrollbar
        text_frame = tk.Frame(self.root)
        text_frame.pack(fill="both", expand=True, padx=12)

        self.text_box = tk.Text(text_frame, wrap="word")
        self.text_box.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(text_frame, command=self.text_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_box.config(yscrollcommand=scrollbar.set)

        # Buttons row
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=12, pady=10)

        tk.Button(btn_frame, text="Load .txt", command=self.load_txt).pack(side="left")
        tk.Button(btn_frame, text="Open Outputs", command=self.open_outputs_folder).pack(side="left", padx=8)


        tk.Button(btn_frame, text="Preview", command=self.preview).pack(side="right", padx=6)
        tk.Button(btn_frame, text="Export", command=self.export).pack(side="right", padx=6)
        tk.Button(btn_frame, text="Both", command=self.both).pack(side="right", padx=6)
        tk.Button(btn_frame, text="Play Latest", command=self.play_latest).pack(side="left", padx=8)


        # Status line
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(status_frame, textvariable=self.status_var, anchor="w").pack(fill="x")

    # ---- Helpers ----

    def get_user_text(self) -> str:
        """
        Reads the current text box content and returns it as a clean string.
        """
        user_text = self.text_box.get("1.0", "end").strip()
        return user_text

    def get_settings(self) -> TTSSettings:
        """
        Builds TTSSettings from the selected preset and voice.
        """
        preset_key = self.preset_var.get().strip().lower()
        settings = PRESETS.get(preset_key, PRESETS["study"])

        voice_name = self.voice_var.get()
        if voice_name != "Default (system)":
            voice_id = self.voice_name_to_id.get(voice_name)
            if voice_id:
                return TTSSettings(rate=settings.rate, volume=settings.volume, voice_id=voice_id)

        return settings

    def make_output_path(self, user_text: str) -> Path:
        """
        Creates a timestamped filename for exporting audio.
        Uses .aiff for macOS compatibility with pyttsx3.
        """
        safe = "".join(ch for ch in user_text.lower() if ch.isalnum() or ch in (" ", "-", "_")).strip()
        safe = safe.replace(" ", "-")[:40] or "note"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return Path("outputs") / f"{timestamp}-{safe}.aiff"

    # ---- Actions ----

    def load_txt(self) -> None:
        """
        Opens a file picker and loads a .txt file into the text box.
        """
        file_path = filedialog.askopenfilename(
            title="Select a text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file:\n{e}")
            return

        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", content)
        self.status_var.set(f"Loaded: {Path(file_path).name}")

    def preview(self) -> None:
        user_text = self.get_user_text()
        if not user_text:
            messagebox.showwarning("Missing text", "Please enter or load text first.")
            return

        settings = self.get_settings()
        self.status_var.set("Previewing speech...")
        self.root.update_idletasks()

        speak_now(text=user_text, settings=settings)
        self.status_var.set("Preview finished.")

    def export(self) -> None:
        user_text = self.get_user_text()
        if not user_text:
            messagebox.showwarning("Missing text", "Please enter or load text first.")
            return

        settings = self.get_settings()
        out_path = self.make_output_path(user_text)

        self.status_var.set("Exporting audio file...")
        self.root.update_idletasks()

        synthesize_to_file(text=user_text, output_path=out_path, settings=settings)
        append_history(create_entry(out_path, settings, "export", user_text))

        self.status_var.set(f"Saved: {out_path}")

    def both(self) -> None:
        user_text = self.get_user_text()
        if not user_text:
            messagebox.showwarning("Missing text", "Please enter or load text first.")
            return

        settings = self.get_settings()

        self.status_var.set("Previewing speech...")
        self.root.update_idletasks()
        speak_now(text=user_text, settings=settings)

        out_path = self.make_output_path(user_text)
        self.status_var.set("Exporting audio file...")
        self.root.update_idletasks()

        synthesize_to_file(text=user_text, output_path=out_path, settings=settings)
        append_history(create_entry(out_path, settings, "both", user_text))

        self.status_var.set(f"Preview + saved: {out_path}")
    
    def open_outputs_folder(self) -> None:
        """
        Opens the outputs folder in the system file browser.
        """
        out_dir = Path("outputs")
        out_dir.mkdir(exist_ok=True)

        if sys.platform == "darwin":
            subprocess.run(["open", str(out_dir)])
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", str(out_dir)])
        else:
            subprocess.run(["xdg-open", str(out_dir)])

    def play_latest(self) -> None:
        """
        Plays the most recently modified audio file in outputs/ (macOS uses afplay).
        """
        out_dir = Path("outputs")
        if not out_dir.exists():
            messagebox.showinfo("No outputs", "No outputs folder found yet.")
            return

        audio_files = sorted(out_dir.glob("*.aiff"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not audio_files:
            messagebox.showinfo("No audio files", "No exported audio files found in outputs/.")
            return

        latest = audio_files[0]
        self.status_var.set(f"Playing: {latest.name}")
        self.root.update_idletasks()

        if sys.platform == "darwin":
            subprocess.run(["afplay", str(latest)])
        else:
            messagebox.showinfo("Unsupported", "Auto-play is currently implemented only for macOS.")


def main() -> None:
    root = tk.Tk()
    app = SpeakNotesApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
