import tkinter as tk
from tkinter import font as tkfont

WIDGET_W = 220
WIDGET_H = 65
BG_COLOR = "#1a1a2e"
FG_COLOR = "#e0e0ff"
ACCENT_COLOR = "#7c7cff"


class FloatingWidget:
    """Transparent, draggable floating widget shown during recording."""

    def __init__(self, root: tk.Tk, config_manager):
        self._cfg = config_manager
        self._root = root

        self._win = tk.Toplevel(root)
        self._win.withdraw()
        self._win.overrideredirect(True)
        self._win.wm_attributes("-topmost", True)
        self._win.configure(bg=BG_COLOR)
        self._win.resizable(False, False)

        # Transparency (Windows supports -alpha; other OS may vary)
        try:
            self._win.wm_attributes("-alpha", self._cfg.get("widget.alpha", 0.85))
        except tk.TclError:
            pass

        self._build_ui()

        # Drag state
        self._drag_x = 0
        self._drag_y = 0
        self._win.bind("<Button-1>", self._on_drag_start)
        self._win.bind("<B1-Motion>", self._on_drag_motion)
        self._win.bind("<ButtonRelease-1>", self._on_drag_end)
        for child in self._win.winfo_children():
            child.bind("<Button-1>", self._on_drag_start)
            child.bind("<B1-Motion>", self._on_drag_motion)
            child.bind("<ButtonRelease-1>", self._on_drag_end)

        self._anim_job = None
        self._dot_state = 0

    def _build_ui(self) -> None:
        frame = tk.Frame(self._win, bg=BG_COLOR, padx=10, pady=8)
        frame.pack(fill="both", expand=True)

        self._icon_label = tk.Label(
            frame, text="🎤", font=("Segoe UI Emoji", 20), bg=BG_COLOR, fg=FG_COLOR
        )
        self._icon_label.pack(side="left", padx=(0, 8))

        right = tk.Frame(frame, bg=BG_COLOR)
        right.pack(side="left", fill="both", expand=True)

        self._title_label = tk.Label(
            right, text="GliFlow", font=("Segoe UI", 8, "bold"),
            bg=BG_COLOR, fg=ACCENT_COLOR
        )
        self._title_label.pack(anchor="w")

        self._status_label = tk.Label(
            right, text="Escuchando...", font=("Segoe UI", 10),
            bg=BG_COLOR, fg=FG_COLOR
        )
        self._status_label.pack(anchor="w")

    # ── Drag ────────────────────────────────────────────────────────────────

    def _on_drag_start(self, event) -> None:
        self._drag_x = event.x_root - self._win.winfo_x()
        self._drag_y = event.y_root - self._win.winfo_y()

    def _on_drag_motion(self, event) -> None:
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self._win.geometry(f"+{x}+{y}")

    def _on_drag_end(self, event) -> None:
        x = self._win.winfo_x()
        y = self._win.winfo_y()
        self._cfg.set("widget.x", x)
        self._cfg.set("widget.y", y)

    # ── Position ─────────────────────────────────────────────────────────────

    def _safe_position(self) -> tuple[int, int]:
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        x = self._cfg.get("widget.x")
        y = self._cfg.get("widget.y")
        if x is None or y is None or x < 0 or y < 0 or x > sw - WIDGET_W or y > sh - WIDGET_H:
            x = (sw - WIDGET_W) // 2
            y = sh - 100
        return int(x), int(y)

    # ── Animation ────────────────────────────────────────────────────────────

    def _animate_dots(self) -> None:
        dots = ["●○○", "○●○", "○○●"]
        self._dot_state = (self._dot_state + 1) % 3
        self._status_label.config(text=f"Escuchando {dots[self._dot_state]}")
        self._anim_job = self._win.after(400, self._animate_dots)

    def _stop_animation(self) -> None:
        if self._anim_job:
            self._win.after_cancel(self._anim_job)
            self._anim_job = None

    def show_countdown(self, seconds: int, on_done: callable) -> None:
        """Show a countdown before pasting, giving user time to switch focus."""
        self._stop_animation()
        self._icon_label.config(text="⏱")
        self._show_win()

        def tick(remaining: int) -> None:
            if remaining <= 0:
                on_done()
                return
            self._status_label.config(text=f"Pegando en {remaining}...")
            self._anim_job = self._win.after(1000, tick, remaining - 1)

        tick(seconds)

    def _show_win(self) -> None:
        x, y = self._safe_position()
        self._win.geometry(f"{WIDGET_W}x{WIDGET_H}+{x}+{y}")
        self._win.deiconify()
        self._win.lift()

    # ── Public API ───────────────────────────────────────────────────────────

    def show_listening(self) -> None:
        self._stop_animation()
        self._status_label.config(text="Escuchando ●○○", fg=FG_COLOR)
        self._icon_label.config(text="🎤")
        self._show_win()
        self._dot_state = 0
        self._anim_job = self._win.after(400, self._animate_dots)

    def show_transcribing(self) -> None:
        self._stop_animation()
        self._status_label.config(text="Transcribiendo...", fg=ACCENT_COLOR)
        self._icon_label.config(text="⏳")

    def show_done(self) -> None:
        self._stop_animation()
        self._status_label.config(text="Texto copiado ✓", fg="#66ff66")
        self._icon_label.config(text="✓")
        self._win.after(1200, self.hide)

    def show_error(self, msg: str) -> None:
        self._stop_animation()
        short = msg[:40] + ("…" if len(msg) > 40 else "")
        self._status_label.config(text=f"Error: {short}", fg="#ff6666")
        self._icon_label.config(text="✗")
        self._win.after(2500, self.hide)

    def hide(self) -> None:
        self._stop_animation()
        self._win.withdraw()

    def update_alpha(self, alpha: float) -> None:
        try:
            self._win.wm_attributes("-alpha", alpha)
        except tk.TclError:
            pass
