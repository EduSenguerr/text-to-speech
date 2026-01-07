from __future__ import annotations

import tkinter as tk
import subprocess
import sys
import threading



from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from datetime import datetime

from speaknotes.presets import PRESETS
from speaknotes.tts import TTSSettings, list_voices, speak_now, synthesize_to_file
from speaknotes.history_utils import append_history, create_entry, load_history
from speaknotes.config_utils import load_config, save_config
from speaknotes.text_utils import split_into_paragraphs
from speaknotes.macos_say import say_to_file





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
        self.last_export_path: Path | None = None

        # ---- UI Variables (Tkinter StringVars) ----
        config = load_config()

        self.preset_var = tk.StringVar(value=config.get("preset", "study"))
        self.voice_var = tk.StringVar(value=config.get("voice", "Default (system)"))
        self.mode_var = tk.StringVar(value=config.get("mode", "export"))
        self.rate_var = tk.IntVar(value=int(config.get("rate", 175)))
        self.volume_var = tk.DoubleVar(value=float(config.get("volume", 1.0)))
     
        self.status_var = tk.StringVar(value="Ready.")
        
        # Flag to prevent preset/slider feedback loops
        self._is_applying_preset = False

        # ---- Build UI ----
        self._build_layout()

        # Apply preset defaults on startup ONLY if preset is not custom
        if self.preset_var.get() != "custom":
            self.apply_preset_to_sliders()
        
        # Trace listeners (run after UI is ready and initial values are set)
        self.preset_var.trace_add("write", lambda *_: (self.apply_preset_to_sliders(), self.save_current_config()))
        self.voice_var.trace_add("write", lambda *_: self.save_current_config())
        self.mode_var.trace_add("write", lambda *_: self.save_current_config())
        self.rate_var.trace_add("write", lambda *_: (self.on_slider_changed(), self.save_current_config()))
        self.volume_var.trace_add("write", lambda *_: (self.on_slider_changed(), self.save_current_config()))

        # Track where the current text came from
        self.text_source = "manual"      
        self.text_source_path = ""       

        self.load_draft()
        self._schedule_draft_autosave()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        
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
        tk.Label(top_frame, text="Mode:").pack(side="left", padx=(16, 0))
        mode_menu = tk.OptionMenu(top_frame, self.mode_var, "preview", "export", "both")
        mode_menu.pack(side="left", padx=8)


        # Text box + scrollbar
        text_frame = tk.Frame(self.root)
        text_frame.pack(fill="both", expand=True, padx=12)

        self.text_box = tk.Text(text_frame, wrap="word")
        self.text_box.pack(side="left", fill="both", expand=True)
        # If the user edits the text manually, mark source as manual
        self.text_box.bind("<Key>", self._on_text_edited)


        scrollbar = tk.Scrollbar(text_frame, command=self.text_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_box.config(yscrollcommand=scrollbar.set)

        # Sliders row: rate + volume
        sliders_frame = tk.Frame(self.root)
        sliders_frame.pack(fill="x", padx=12, pady=(0, 10))
        
        tk.Label(sliders_frame, text="Rate:").pack(side="left")
        rate_scale = tk.Scale(
            sliders_frame,
            from_=120,
            to=260,
            orient="horizontal",
            variable=self.rate_var,
            length=220,
        )
        rate_scale.pack(side="left", padx=8)
        
        tk.Label(sliders_frame, text="Volume:").pack(side="left", padx=(16, 0))
        volume_scale = tk.Scale(
            sliders_frame,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient="horizontal",
            variable=self.volume_var,
            length=220,
        )
        volume_scale.pack(side="left", padx=8)


        # Buttons row
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=12, pady=10)

        tk.Button(btn_frame, text="Load .txt", command=self.load_txt).pack(side="left")
        tk.Button(btn_frame, text="History", command=self.open_history_window).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Open Outputs", command=self.open_outputs_folder).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Reveal Last", command=self.reveal_last_export).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Open Last", command=self.open_last_export).pack(side="left", padx=8)

        self.run_btn = tk.Button(btn_frame, text="Run", command=self.run_mode)
        self.run_btn.pack(side="right", padx=6)
        
        self.both_btn = tk.Button(btn_frame, text="Both", command=self.both)
        self.both_btn.pack(side="right", padx=6)
        
        self.export_btn = tk.Button(btn_frame, text="Export", command=self.export)
        self.export_btn.pack(side="right", padx=6)
        
        self.preview_btn = tk.Button(btn_frame, text="Preview", command=self.preview)
        self.preview_btn.pack(side="right", padx=6)

        tk.Button(btn_frame, text="Play Latest", command=self.play_latest).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Bulk Export", command=self.bulk_export).pack(side="left", padx=8)



        # Status line
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(status_frame, textvariable=self.status_var, anchor="w").pack(fill="x")

    def set_status(self, message: str) -> None:
        """
        Updates the status line and flushes UI redraw tasks.
        """
        self.status_var.set(message)
        self.root.update_idletasks()

    def set_status_async(self, message: str) -> None:
        """
        Thread-safe status update (scheduled on the Tk main loop).
        """
        self.root.after(0, lambda: self.set_status(message))



    # ---- Helpers ----

    def get_user_text(self) -> str:
        """
        Reads the current text box content and returns it as a clean string.
        """
        user_text = self.text_box.get("1.0", "end").strip()
        return user_text
    
    def _on_text_edited(self, event: tk.Event) -> None:
        """
        Marks the text source as manual when the user edits the text box.
        """
        # If the user types anything, we consider it manual input.
        self.text_source = "manual"
        self.text_source_path = ""


    def get_settings(self) -> TTSSettings:
        """
        Builds TTSSettings from the selected preset, voice, and slider overrides.
        """
        preset_key = self.preset_var.get().strip().lower()
        preset_settings = PRESETS.get(preset_key, PRESETS["study"])
    
        # Slider overrides (these are the "personal" settings)
        rate = int(self.rate_var.get())
        volume = float(self.volume_var.get())
    
        voice_name = self.voice_var.get()
        if voice_name != "Default (system)":
            voice_id = self.voice_name_to_id.get(voice_name)
            if voice_id:
                return TTSSettings(rate=rate, volume=volume, voice_id=voice_id)
    
        return TTSSettings(rate=rate, volume=volume, voice_id=None)

    def apply_preset_to_sliders(self) -> None:
        """
        Applies the selected preset defaults to the rate/volume sliders.
        """
        preset_key = self.preset_var.get().strip().lower()
        preset_settings = PRESETS.get(preset_key, PRESETS["study"])
    
        self._is_applying_preset = True
        try:
            self.rate_var.set(int(preset_settings.rate))
            self.volume_var.set(float(preset_settings.volume))
        finally:
            self._is_applying_preset = False
    
    def on_slider_changed(self) -> None:
        """
        Marks the preset as 'custom' when the user manually changes sliders.
        """
        if self._is_applying_preset:
            return
    
        if self.preset_var.get() != "custom":
            self.preset_var.set("custom")


    def make_output_path(self, user_text: str) -> Path:
        """
        Creates a timestamped filename for exporting audio.
        Uses .aiff for macOS compatibility with pyttsx3.
        """
        safe = "".join(ch for ch in user_text.lower() if ch.isalnum() or ch in (" ", "-", "_")).strip()
        safe = safe.replace(" ", "-")[:40] or "note"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return Path("outputs") / f"{timestamp}-{safe}.aiff"
    
    def make_output_path_part(self, user_text: str, part_index: int, total_parts: int) -> Path:
        """
        Creates a timestamped filename for a chunked export (part-XXX).
        """
        safe = "".join(ch for ch in user_text.lower() if ch.isalnum() or ch in (" ", "-", "_")).strip()
        safe = safe.replace(" ", "-")[:30] or "note"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        part = f"part-{part_index:03d}-of-{total_parts:03d}"
        return Path("outputs") / f"{timestamp}-{part}-{safe}.aiff"

    
    def _set_controls_enabled(self, enabled: bool) -> None:
        """
        Enables or disables main action buttons to prevent concurrent runs.
        """
        state = "normal" if enabled else "disabled"
        for btn in (self.preview_btn, self.export_btn, self.both_btn, self.run_btn):
            btn.config(state=state)


    def _run_job(self, status_start: str, job_fn, status_done: str | None = None) -> None:
        """
        Runs a blocking job on the Tkinter main thread (macOS-safe) and keeps UI state consistent.
        The job is scheduled with 'after' so the start status is visible before work begins.
        """
        self._set_controls_enabled(False)
        self.set_status(status_start)
    
        def run_job() -> None:
            try:
                job_fn()
                if status_done:
                    self.set_status(status_done)
            except Exception as e:
                messagebox.showerror("Error", str(e))
                self.set_status("Error.")
            finally:
                self._set_controls_enabled(True)
    

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

        self.text_source = "txt"
        self.text_source_path = str(Path(file_path))

        self.status_var.set(f"Loaded: {Path(file_path).name}")

    def preview(self) -> None:
        user_text = self.get_user_text()
        if not user_text:
            messagebox.showwarning("Missing text", "Please enter or load text first.")
            return
    
        settings = self.get_settings()
    
        def job():
            speak_now(text=user_text, settings=settings)
    
        self._run_job("Previewing speech...", job, "Preview finished.")


    def export(self) -> None:
        user_text = self.get_user_text()
        if not user_text:
            messagebox.showwarning("Missing text", "Please enter or load text first.")
            return
    
        settings = self.get_settings()
        out_path = self.make_output_path(user_text)
    
        def job():
            synthesize_to_file(text=user_text, output_path=out_path, settings=settings)
            self.last_export_path = out_path
            append_history(create_entry(out_path, settings, "export", user_text, self.text_source, self.text_source_path))
    
        self._run_job("Exporting audio file...", job, f"Saved: {out_path}")

    def bulk_export(self) -> None:
        user_text = self.get_user_text()
        if not user_text:
            messagebox.showwarning("Missing text", "Please enter or load text first.")
            return
    
        if self.text_source != "txt":
            messagebox.showwarning("Bulk export", "Bulk export is designed for .txt input. Load a .txt file first.")
            return
    
        parts = split_into_paragraphs(user_text)
        if len(parts) < 2:
            messagebox.showinfo("Bulk export", "Only one paragraph found. Use Export instead.")
            return
    
        if sys.platform != "darwin":
            messagebox.showinfo("Bulk export", "Bulk export is currently implemented for macOS only.")
            return
    
        settings = self.get_settings()
        voice_name = self.voice_var.get()
        rate_wpm = int(self.rate_var.get())
    
        self._set_controls_enabled(False)
        self.set_status("Starting bulk export...")
    
        def worker() -> None:
            try:
                total = len(parts)
                for i, chunk in enumerate(parts, start=1):
                    self.set_status_async(f"Exporting {i}/{total}...")
    
                    out_path = self.make_output_path_part(chunk, i, total)
    
                    say_to_file(
                        text=chunk,
                        output_path=out_path,
                        voice_name=voice_name,
                        rate_wpm=rate_wpm,
                    )
    
                    self.last_export_path = out_path
                    append_history(
                        create_entry(
                            out_path,
                            settings,
                            "export",
                            chunk,
                            self.text_source,
                            self.text_source_path,
                        )
                    )
    
                self.set_status_async(f"Bulk export finished: {total} files")
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.set_status_async("Error.")
            finally:
                self.root.after(0, lambda: self._set_controls_enabled(True))
    
        threading.Thread(target=worker, daemon=True).start()


    def reveal_last_export(self) -> None:
        """
        Reveals the most recently exported audio file in the system file browser.
        """
        if not self.last_export_path or not self.last_export_path.exists():
            messagebox.showinfo("No export yet", "No exported file found yet.")
            return
    
        import subprocess
        import sys
    
        path_str = str(self.last_export_path)
    
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path_str])
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", "/select,", path_str])
        else:
            subprocess.run(["xdg-open", str(self.last_export_path.parent)])


    def open_last_export(self) -> None:
        """
        Opens the most recently exported audio file with the default system app.
        """
        if not self.last_export_path or not self.last_export_path.exists():
            messagebox.showinfo("No export yet", "No exported file found yet.")
            return
    
        import subprocess
        import sys
    
        path_str = str(self.last_export_path)
    
        if sys.platform == "darwin":
            subprocess.run(["open", path_str])
        elif sys.platform.startswith("win"):
            subprocess.run(["start", "", path_str], shell=True)
        else:
            subprocess.run(["xdg-open", path_str])

    def both(self) -> None:
        user_text = self.get_user_text()
        if not user_text:
            messagebox.showwarning("Missing text", "Please enter or load text first.")
            return
    
        settings = self.get_settings()
    
        def job() -> None:
            self.set_status("Previewing speech...")
            speak_now(text=user_text, settings=settings)
    
            self.set_status("Exporting audio file...")
            out_path = self.make_output_path(user_text)
            synthesize_to_file(text=user_text, output_path=out_path, settings=settings)
    
            self.last_export_path = out_path
            append_history(
                create_entry(
                    out_path,
                    settings,
                    "both",
                    user_text,
                    self.text_source,
                    self.text_source_path,
                )
            )
    
            self.set_status(f"Preview + saved: {out_path}")
    
        self._run_job("Starting both...", job)


    def open_history_window(self) -> None:
        """
        Opens a separate window that displays history.json entries in a table (Treeview).
        """
        window = tk.Toplevel(self.root)
        window.title("SpeakNotes — History")
        window.geometry("900x420")
    
        # Top controls (Refresh + Play Selected)
        controls = tk.Frame(window)
        controls.pack(fill="x", padx=12, pady=10)
    
        tk.Button(controls, text="Refresh", command=lambda: self._populate_history(tree)).pack(side="left")
    
        tk.Button(controls, text="Play Selected", command=lambda: self._play_selected_history(tree)).pack(side="left", padx=8)
    
        # Treeview (table)
        columns = ("date", "mode", "source", "file", "voice", "rate", "volume", "text_preview")
    
        tree = ttk.Treeview(window, columns=columns, show="headings", height=14)
        tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    
        # Define column headings
        tree.heading("date", text="Date")
        tree.heading("mode", text="Mode")
        tree.heading("source", text="Source")
        tree.heading("file", text="File")
        tree.heading("voice", text="Voice")
        tree.heading("rate", text="Rate")
        tree.heading("volume", text="Volume")
        tree.heading("text_preview", text="Text Preview")
    
        # Define column widths (reasonable defaults)
        tree.column("date", width=140, anchor="w")
        tree.column("mode", width=70, anchor="w")
        tree.column("source", width=80, anchor="w")
        tree.column("file", width=240, anchor="w")
        tree.column("voice", width=140, anchor="w")
        tree.column("rate", width=60, anchor="center")
        tree.column("volume", width=70, anchor="center")
        tree.column("text_preview", width=260, anchor="w")
    
        # Populate initial data
        self._populate_history(tree)


    def _populate_history(self, tree: ttk.Treeview) -> None:
        """
        Loads history entries from history.json and fills the Treeview.
        """
        # Clear existing rows
        for item_id in tree.get_children():
            tree.delete(item_id)
    
        entries = load_history()
        if not isinstance(entries, list):
            return
    
        # Insert newest first (optional but practical)
        for entry in reversed(entries):
            date = entry.get("date", "")
            mode = entry.get("mode", "")
            source = entry.get("source", "")
            file_path = entry.get("file", "")
            voice = entry.get("voice", "")
            rate = entry.get("rate", "")
            volume = entry.get("volume", "")
            text_preview = entry.get("text_preview", "")
    
            tree.insert(
                "",
                "end",
                values=(date, mode, source, file_path, voice, rate, volume, text_preview),
            )
    
    
    def _play_selected_history(self, tree: ttk.Treeview) -> None:
        """
        Plays the audio file from the selected history row (macOS uses afplay).
        """
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Please select a row first.")
            return
    
        item_id = selection[0]
        values = tree.item(item_id, "values")
        if not values or len(values) < 3:
            messagebox.showerror("Error", "Invalid selection data.")
            return
    
        file_path = values[3]
        if not file_path:
            messagebox.showerror("Error", "No file path found for this entry.")
            return
    
        audio_path = Path(file_path)
        if not audio_path.exists():
            messagebox.showerror("File not found", f"Audio file not found:\n{audio_path}")
            return
    
        # Reuse the same playback logic as Play Latest (macOS only, for now)
        import subprocess
        import sys
    
        if sys.platform == "darwin":
            subprocess.run(["afplay", str(audio_path)])
        else:
            messagebox.showinfo("Unsupported", "Auto-play is currently implemented only for macOS.")

    
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

    def run_mode(self) -> None:
        """
        Runs the selected mode (preview/export/both) using the current text and settings.
        """
        mode = self.mode_var.get().strip().lower()
        if mode == "preview":
            self.preview()
        elif mode == "both":
            self.both()
        else:
            self.export()


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

    def save_current_config(self) -> None:
        """
        Persists the current GUI selections to config.json.
        """
        save_config({
            "preset": self.preset_var.get(),
            "voice": self.voice_var.get(),
            "mode": self.mode_var.get(),
            "rate": int(self.rate_var.get()),
            "volume": float(self.volume_var.get()),
        })

    def load_draft(self) -> None:
        """
        Loads draft.txt into the text box if it exists.
        """
        draft_path = Path("draft.txt")
        if not draft_path.exists():
            return
    
        try:
            content = draft_path.read_text(encoding="utf-8")
        except Exception:
            return
    
        if content.strip():
            self.text_box.delete("1.0", "end")
            self.text_box.insert("1.0", content)
            self.status_var.set("Draft restored.")


    def save_draft(self) -> None:
        """
        Saves the current text box content to draft.txt.
        """
        user_text = self.get_user_text()
        Path("draft.txt").write_text(user_text, encoding="utf-8")
    
    
    def _schedule_draft_autosave(self) -> None:
        """
        Autosaves the draft every few seconds without blocking the UI.
        """
        try:
            self.save_draft()
        except Exception:
            pass
    
        self.root.after(3000, self._schedule_draft_autosave)
    
    
    def _on_close(self) -> None:
        """
        Ensures draft is saved before closing the app.
        """
        try:
            self.save_draft()
        except Exception:
            pass
    
        self.root.destroy()
    
    



def main() -> None:
    root = tk.Tk()
    app = SpeakNotesApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
