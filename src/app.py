import queue
import threading
import tkinter as tk
from tkinter import messagebox

from .config.manager import ConfigManager, HistoryManager
from .audio.recorder import AudioRecorder
from .stt import get_provider, get_api_key, STTError
from .ui.widget import FloatingWidget
from .ui.tray import TrayIcon
from .ui.config_window import ConfigWindow, HistoryWindow
from .hotkey.listener import HotkeyListener
from .output.inserter import insert_text

VERSION = "0.9.1"


class GliFlowApp:
    def __init__(self):
        self.config_manager = ConfigManager()
        self._queue: queue.Queue = queue.Queue()

        self.root = tk.Tk()
        self.root.withdraw()  # hidden main window; only widget/toplevel shown

        self.widget = FloatingWidget(self.root, self.config_manager)
        self.tray = TrayIcon(self)
        self.recorder = AudioRecorder()
        self.provider = get_provider(self.config_manager.config)

        self.history: HistoryManager | None = None
        if self.config_manager.get("general.history_enabled", False):
            self.history = HistoryManager()

        self.hotkey = self._build_hotkey_listener()

        self._config_win = ConfigWindow(self)
        self._history_win = HistoryWindow(self) if self.history else None

        self._running = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        self._running = True
        self.tray.start()
        self.hotkey.start()
        self.root.after(50, self._process_queue)
        try:
            self.root.mainloop()
        finally:
            self._running = False

    def quit(self) -> None:
        self.hotkey.stop()
        self.tray.stop()
        self.root.after(0, self.root.destroy)

    def _build_hotkey_listener(self) -> HotkeyListener:
        cfg = self.config_manager
        return HotkeyListener(
            callback_start=self._on_start,
            callback_stop=self._on_stop,
            mode=cfg.get("hotkey.mode", "combo"),
            combo_keys=cfg.get("hotkey.combo_keys", "ctrl+shift+1"),
            double_tap_key=cfg.get("hotkey.double_tap_key", "ctrl_l"),
            double_tap_ms=cfg.get("hotkey.double_tap_ms", 400),
        )

    def reload_hotkey(self) -> None:
        self.hotkey.stop()
        self.hotkey = self._build_hotkey_listener()
        self.hotkey.start()

    # ── Queue bridge (thread-safe UI updates) ────────────────────────────────

    def _process_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                self._dispatch(msg)
        except queue.Empty:
            pass
        if self._running:
            self.root.after(50, self._process_queue)

    def _dispatch(self, msg: tuple) -> None:
        action = msg[0]
        if action == "start":
            self._handle_start()
        elif action == "stop":
            self._handle_stop()
        elif action == "stop_delayed":
            self._handle_stop(delayed=True)
        elif action == "done":
            self._handle_done(msg[1])
        elif action == "done_delayed":
            self._handle_done_delayed(msg[1], msg[2])
        elif action == "error":
            self._handle_error(msg[1])
        elif action == "open_config":
            self._config_win.show()
        elif action == "open_history":
            if self._history_win:
                self._history_win.show()
        elif action == "show_about":
            self._show_about_window()

    # ── Hotkey callbacks (called from listener thread) ────────────────────────

    def _on_start(self) -> None:
        self._queue.put(("start",))

    def _on_stop(self) -> None:
        self._queue.put(("stop",))

    # ── Recording flow (main thread) ──────────────────────────────────────────

    def _handle_start(self) -> None:
        if self.recorder.is_recording:
            return
        active = self.config_manager.get("provider.active", "groq")
        api_key = get_api_key(active, self.config_manager.config)  # checks .env first
        if not api_key:
            self.tray.notify("GliFlow", "Configura tu API key primero (clic derecho → Configuración)")
            return
        self.recorder.start()
        self.widget.show_listening()
        self.tray.rebuild_menu()

    def _handle_stop(self, delayed: bool = False) -> None:
        if not self.recorder.is_recording:
            return
        audio_data = self.recorder.stop()
        self.tray.rebuild_menu()
        if not audio_data:
            self.widget.hide()
            return
        self.widget.show_transcribing()
        threading.Thread(target=self._transcribe, args=(audio_data, delayed), daemon=True).start()

    def _transcribe(self, audio_data: bytes, delayed: bool = False) -> None:
        language = self.config_manager.get("general.language", "es")
        try:
            text = self.provider.transcribe(audio_data, language=language)
            if text:
                if delayed:
                    self._queue.put(("done_delayed", text, 3))
                else:
                    self._queue.put(("done", text))
            else:
                self._queue.put(("error", "No se detectó texto"))
        except STTError as e:
            self._queue.put(("error", str(e)))

    def _handle_done(self, text: str) -> None:
        insert_text(text)
        self.widget.show_done()
        self._save_history(text)

    def _handle_done_delayed(self, text: str, countdown: int) -> None:
        """Show countdown, then insert text — gives user time to switch focus."""
        def do_insert():
            insert_text(text)
            self.widget.show_done()
            self._save_history(text)

        self.widget.show_countdown(countdown, on_done=do_insert)

    def _save_history(self, text: str) -> None:
        if self.history:
            active = self.config_manager.get("provider.active", "groq")
            language = self.config_manager.get("general.language", "es")
            self.history.add(text, provider=active, language=language)

    def _handle_error(self, msg: str) -> None:
        self.widget.show_error(msg)
        self.tray.notify("GliFlow — Error", msg)

    # ── Tray menu actions ─────────────────────────────────────────────────────

    def toggle_recording(self) -> None:
        if self.recorder.is_recording:
            self._queue.put(("stop_delayed",))
        else:
            self._queue.put(("start",))

    def open_config(self) -> None:
        self._queue.put(("open_config",))

    def open_history(self) -> None:
        self._queue.put(("open_history",))

    def show_about(self) -> None:
        self._queue.put(("show_about",))

    def _show_about_window(self) -> None:
        import tkinter as tk
        win = tk.Toplevel(self.root)
        win.title("Acerca de GliFlow")
        win.resizable(False, False)

        # Icon
        try:
            from .ui.tray import _make_icon_image
            from PIL import ImageTk
            img = _make_icon_image().resize((48, 48))
            photo = ImageTk.PhotoImage(img)
            win._photo = photo  # keep reference
            win.iconphoto(False, ImageTk.PhotoImage(_make_icon_image().resize((32, 32))))
            tk.Label(win, image=photo, bg="white").pack(pady=(20, 6))
        except Exception:
            pass

        tk.Label(win, text="GliFlow", font=("Segoe UI", 16, "bold"), bg="white").pack()
        tk.Label(win, text=f"v{VERSION}  —  Speech-to-Text Desktop App",
                 font=("Segoe UI", 9), fg="#555", bg="white").pack(pady=(2, 12))
        tk.Frame(win, height=1, bg="#ddd").pack(fill="x", padx=20)
        tk.Label(win, text="Developed by virapa",
                 font=("Segoe UI", 9, "italic"), fg="#444", bg="white").pack(pady=(10, 4))
        tk.Label(win, text="Powered by Groq · OpenAI · Google Gemini",
                 font=("Segoe UI", 8), fg="#888", bg="white").pack()
        tk.Button(win, text="Cerrar", command=win.destroy, width=10).pack(pady=(16, 20))

        win.configure(bg="white")
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        w, h = win.winfo_width(), win.winfo_height()
        win.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def reload_provider(self) -> None:
        """Recreate STT provider after config change."""
        self.provider = get_provider(self.config_manager.config)
        # Reload history manager if setting changed
        if self.config_manager.get("general.history_enabled", False):
            if self.history is None:
                self.history = HistoryManager()
                self._history_win = HistoryWindow(self)
        else:
            self.history = None
            self._history_win = None
