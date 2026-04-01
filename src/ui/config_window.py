import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# ── KeyRecorder widget ────────────────────────────────────────────────────────

# keysym → display label for modifier keys
_MOD_KEYSYMS = {"Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R",
                 "Control_R", "Shift", "Control"}
_MOD_DISPLAY = {
    "Control_L": "Ctrl", "Control_R": "Ctrl", "Control": "Ctrl",
    "Shift_L": "Shift", "Shift_R": "Shift", "Shift": "Shift",
    "Alt_L": "Alt", "Alt_R": "Alt", "Alt": "Alt",
}
# keysym → pynput key name (for double_tap mode)
_MOD_TO_PYNPUT = {
    "Control_L": "ctrl_l", "Control_R": "ctrl_r", "Control": "ctrl",
    "Shift_L": "shift_l", "Shift_R": "shift_r", "Shift": "shift",
    "Alt_L": "alt_l", "Alt_R": "alt_r", "Alt": "alt",
}
_MOD_ORDER = ["Ctrl", "Alt", "Shift"]
_MOD_TO_COMBO = {"Ctrl": "ctrl", "Shift": "shift", "Alt": "alt"}

# Windows VK keycode → (display, combo_key_name)  — physical key, locale-independent
_VK_MAP: dict[int, tuple[str, str]] = {
    **{48 + i: (str(i), str(i)) for i in range(10)},           # 0-9
    **{65 + i: (chr(65 + i), chr(97 + i)) for i in range(26)}, # A-Z / a-z
    32: ("Space", "space"), 13: ("Enter", "enter"), 9: ("Tab", "tab"),
    27: ("Esc", "esc"), 8: ("Backspace", "backspace"), 46: ("Del", "delete"),
    45: ("Ins", "insert"), 36: ("Home", "home"), 35: ("End", "end"),
    33: ("PgUp", "pageup"), 34: ("PgDn", "pagedown"),
    37: ("←", "left"), 38: ("↑", "up"), 39: ("→", "right"), 40: ("↓", "down"),
    **{112 + i: (f"F{i + 1}", f"f{i + 1}") for i in range(12)},  # F1-F12
    186: (";", ";"), 187: ("=", "="), 188: (",", ","), 189: ("-", "-"),
    190: (".", "."), 191: ("/", "/"), 192: ("`", "`"),
    219: ("[", "["), 220: ("\\", "\\"), 221: ("]", "]"), 222: ("'", "'"),
}


class KeyRecorder(tk.Frame):
    """Entry that records a key combination when focused.
    Uses event.keycode (physical VK) for non-modifier keys to be locale-independent."""

    def __init__(self, parent, mode_var: tk.StringVar, on_captured=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._mode_var = mode_var
        self._on_captured = on_captured
        self._mods_held: set[str] = set()

        self._entry = tk.Entry(self, width=26, cursor="hand2", font=("Segoe UI", 9))
        self._entry.pack(side="left")
        tk.Label(self, text="← clic para capturar", fg="#888",
                 font=("Segoe UI", 8)).pack(side="left", padx=4)

        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<KeyPress>", self._on_key_press)
        self._entry.bind("<KeyRelease>", self._on_key_release)

    def set_display(self, text: str) -> None:
        self._entry.config(state="normal", fg="#222")
        self._entry.delete(0, "end")
        self._entry.insert(0, text)

    def _on_focus_in(self, _event) -> None:
        self._mods_held.clear()
        self._entry.config(fg="#888")
        self._entry.delete(0, "end")
        if self._mode_var.get() == "combo":
            self._entry.insert(0, "Mantén Ctrl/Alt/Shift y pulsa una tecla...")
        else:
            self._entry.insert(0, "Pulsa la tecla para el doble toque...")

    def _on_focus_out(self, _event) -> None:
        self._mods_held.clear()

    def _on_key_press(self, event) -> str:
        keysym = event.keysym
        keycode = event.keycode
        mode = self._mode_var.get()

        is_mod = keysym in _MOD_KEYSYMS

        if mode == "combo":
            if is_mod:
                self._mods_held.add(_MOD_DISPLAY.get(keysym, keysym))
                held = " + ".join(m for m in _MOD_ORDER if m in self._mods_held)
                self._entry.delete(0, "end")
                self._entry.insert(0, f"{held} + ...")
            else:
                # Use VK keycode for locale-independent physical key name
                key_disp, key_id = _VK_MAP.get(keycode, (keysym.upper(), keysym.lower()))
                mods_disp = [m for m in _MOD_ORDER if m in self._mods_held]
                display = " + ".join(mods_disp + [key_disp])
                combo = "+".join([_MOD_TO_COMBO[m] for m in mods_disp] + [key_id])
                self._entry.config(fg="#222")
                self._entry.delete(0, "end")
                self._entry.insert(0, display)
                if self._on_captured:
                    self._on_captured(display, combo)
                self.after(50, lambda: self.master.focus_set())
        else:  # double_tap
            if is_mod:
                key_id = _MOD_TO_PYNPUT.get(keysym, keysym.lower())
                disp = _MOD_DISPLAY.get(keysym, keysym)
            else:
                key_disp, key_id = _VK_MAP.get(keycode, (keysym.upper(), keysym.lower()))
                disp = key_disp
            self._entry.config(fg="#222")
            self._entry.delete(0, "end")
            self._entry.insert(0, disp)
            if self._on_captured:
                self._on_captured(disp, key_id)
            self.after(50, lambda: self.master.focus_set())

        return "break"

    def _on_key_release(self, event) -> str:
        self._mods_held.discard(_MOD_DISPLAY.get(event.keysym, ""))
        return "break"


class ConfigWindow:
    """Settings GUI with tabbed interface."""

    def __init__(self, app):
        self._app = app
        self._win: tk.Toplevel | None = None

    def show(self) -> None:
        if self._win and self._win.winfo_exists():
            self._win.lift()
            self._win.focus_force()
            return
        self._app.hotkey.pause()
        self._build()

    def _on_close(self) -> None:
        self._app.hotkey.resume()
        self._win.destroy()

    def _build(self) -> None:
        root = self._app.root
        self._win = tk.Toplevel(root)
        self._win.title("GliFlow — Configuración")
        self._win.resizable(False, False)

        # Center on screen
        self._win.update_idletasks()
        w, h = 460, 420
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        self._win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        # Window icon — same as system tray
        try:
            from .tray import _make_icon_image
            from PIL import ImageTk
            img = _make_icon_image().resize((32, 32))
            self._win._icon_photo = ImageTk.PhotoImage(img)
            self._win.iconphoto(False, self._win._icon_photo)
        except Exception:
            pass

        nb = ttk.Notebook(self._win)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self._vars: dict[str, tk.Variable] = {}

        nb.add(self._tab_test(nb), text="  🎤 Test  ")
        nb.add(self._tab_general(nb), text="  General  ")
        nb.add(self._tab_provider(nb), text="  Provider  ")
        nb.add(self._tab_hotkey(nb), text="  Hotkey  ")
        nb.add(self._tab_widget(nb), text="  Widget  ")
        nb.add(self._tab_about(nb), text="  Acerca de  ")

        self._win.protocol("WM_DELETE_WINDOW", self._on_close)

        btn_frame = tk.Frame(self._win)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(btn_frame, text="Guardar", command=self._save, width=12).pack(side="right")
        tk.Button(btn_frame, text="Cancelar", command=self._on_close, width=12).pack(side="right", padx=4)

    # ── Tabs ─────────────────────────────────────────────────────────────────

    def _tab_test(self, parent) -> tk.Frame:
        f = tk.Frame(parent, padx=20, pady=20)

        tk.Label(f, text="Prueba de transcripción", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(f, text="Pulsa Iniciar, habla, luego Detener.", fg="#555").pack(anchor="w", pady=(2, 16))

        self._rec_status = tk.StringVar(value="⏹ Listo")
        status_lbl = tk.Label(f, textvariable=self._rec_status, font=("Segoe UI", 10), fg="#333")
        status_lbl.pack(anchor="w", pady=(0, 12))

        btn_frame = tk.Frame(f)
        btn_frame.pack(anchor="w")

        self._btn_start = tk.Button(
            btn_frame, text="▶  Iniciar grabación",
            width=20, bg="#4a9", fg="white", activebackground="#3a8",
            command=self._test_start,
        )
        self._btn_start.pack(side="left", padx=(0, 8))

        self._btn_stop = tk.Button(
            btn_frame, text="⏹  Detener y transcribir",
            width=22, bg="#c55", fg="white", activebackground="#b44",
            command=self._test_stop, state="disabled",
        )
        self._btn_stop.pack(side="left")

        tk.Label(f, text="Resultado:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(16, 2))
        result_frame = tk.Frame(f, relief="sunken", bd=1)
        result_frame.pack(fill="x")
        self._result_text = tk.Text(result_frame, height=3, wrap="word", font=("Segoe UI", 9),
                                    state="disabled", bg="#f9f9f9")
        self._result_text.pack(fill="x", padx=4, pady=4)

        return f

    def _test_start(self) -> None:
        self._app._handle_start()
        if not self._app.recorder.is_recording:
            self._rec_status.set("⚠ Sin API key o error al iniciar")
            return
        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal")
        self._rec_status.set("🔴 Grabando...")

    def _test_stop(self) -> None:
        if not self._app.recorder.is_recording:
            self._rec_status.set("⏹ Listo")
            return
        self._btn_stop.config(state="disabled")
        self._rec_status.set("⏳ Transcribiendo...")

        orig_done_delayed = self._app._handle_done_delayed
        orig_error = self._app._handle_error

        def on_done_delayed(text, countdown):
            self._show_result(text)
            self._reset_test_buttons()
            orig_done_delayed(text, countdown)  # shows countdown + inserts

        def on_error(msg):
            orig_error(msg)
            self._show_result(f"Error: {msg}")
            self._reset_test_buttons()

        self._app._handle_done_delayed = on_done_delayed
        self._app._handle_error = on_error
        self._app._handle_stop(delayed=True)

    def _show_result(self, text: str) -> None:
        self._rec_status.set("✅ Listo")
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.insert("end", text)
        self._result_text.config(state="disabled")
        # Restore original handlers
        app = self._app
        app._handle_done_delayed = app.__class__._handle_done_delayed.__get__(app)
        app._handle_error = app.__class__._handle_error.__get__(app)

    def _reset_test_buttons(self) -> None:
        self._btn_start.config(state="normal")
        self._btn_stop.config(state="disabled")

    def _tab_general(self, parent) -> tk.Frame:
        cfg = self._app.config_manager
        f = tk.Frame(parent, padx=15, pady=15)

        tk.Label(f, text="Idioma de transcripción:").grid(row=0, column=0, sticky="w", pady=4)
        lang_var = tk.StringVar(value=cfg.get("general.language", "es"))
        self._vars["general.language"] = lang_var
        ttk.Combobox(f, textvariable=lang_var, values=["es", "en", "auto"], width=10, state="readonly").grid(
            row=0, column=1, sticky="w", padx=8
        )

        auto_var = tk.BooleanVar(value=cfg.get("general.auto_start", False))
        self._vars["general.auto_start"] = auto_var
        tk.Checkbutton(f, text="Iniciar con Windows", variable=auto_var).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=4
        )

        hist_var = tk.BooleanVar(value=cfg.get("general.history_enabled", False))
        self._vars["general.history_enabled"] = hist_var
        tk.Checkbutton(f, text="Guardar historial de transcripciones", variable=hist_var).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=4
        )

        return f

    def _tab_provider(self, parent) -> tk.Frame:
        cfg = self._app.config_manager
        f = tk.Frame(parent, padx=15, pady=15)

        _models = {
            "groq": [
                "whisper-large-v3",
                "whisper-large-v3-turbo",
            ],
            "openai": [
                "whisper-1",
                "gpt-4o-transcribe",
                "gpt-4o-mini-transcribe",
            ],
            "gemini": [
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
            ],
        }
        _env_keys = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}

        from ..stt import get_api_key_source, save_api_key_to_keyring

        tk.Label(f, text="Active provider:").grid(row=0, column=0, sticky="w", pady=4)
        prov_var = tk.StringVar(value=cfg.get("provider.active", "groq"))
        self._vars["provider.active"] = prov_var
        ttk.Combobox(f, textvariable=prov_var, values=["groq", "openai", "gemini"],
                     width=12, state="readonly").grid(row=0, column=1, sticky="w", padx=8)

        # Source badge colours
        _source_style = {
            "env":     ("● .env",     "#4a9", "#f0fff0"),
            "keyring": ("● keyring",  "#47a", "#f0f0ff"),
            "config":  ("● config",   "#888", "#f9f9f9"),
            "none":    ("○ no key",   "#c55", "#fff0f0"),
        }

        row = 1
        for prov, label in [("groq", "Groq"), ("openai", "OpenAI"), ("gemini", "Gemini")]:
            # Section header
            tk.Label(f, text=label, font=("Segoe UI", 9, "bold"), fg="#444").grid(
                row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))
            row += 1

            # API Key
            tk.Label(f, text="API Key:").grid(row=row, column=0, sticky="w", pady=2)
            source = get_api_key_source(prov, cfg.config)
            badge_text, badge_fg, badge_bg = _source_style.get(source, _source_style["none"])

            if source == "env":
                key_var = tk.StringVar(value="not editable here")
                tk.Entry(f, textvariable=key_var, width=24, state="disabled",
                         disabledforeground=badge_fg, disabledbackground=badge_bg).grid(
                    row=row, column=1, sticky="w", padx=8)
                tk.Label(f, text=badge_text, fg=badge_fg, bg=badge_bg,
                         font=("Segoe UI", 8), relief="flat", padx=4).grid(row=row, column=2, sticky="w")
            else:
                # Show current keyring value masked, or empty
                current_key = ""
                if source == "keyring":
                    try:
                        import keyring as _kr
                        current_key = _kr.get_password("gliflow", prov) or ""
                    except Exception:
                        pass
                elif source == "config":
                    current_key = cfg.get(f"provider.{prov}.api_key", "")

                key_var = tk.StringVar(value=current_key)
                entry = tk.Entry(f, textvariable=key_var, show="•", width=24)
                entry.grid(row=row, column=1, sticky="w", padx=8)

                source_lbl = tk.Label(f, text=badge_text, fg=badge_fg, bg=badge_bg,
                                      font=("Segoe UI", 8), relief="flat", padx=4)
                source_lbl.grid(row=row, column=2, sticky="w")

                def _make_save(p, kv, slbl):
                    def save_to_keyring():
                        val = kv.get().strip()
                        try:
                            save_api_key_to_keyring(p, val)
                            # clear from config.json if saved to keyring
                            if val:
                                cfg.set(f"provider.{p}.api_key", "")
                                bt, bf, bb = _source_style["keyring"]
                            else:
                                bt, bf, bb = _source_style["none"]
                            slbl.config(text=bt, fg=bf, bg=bb)
                            messagebox.showinfo(
                                "GliFlow",
                                f"Key {'saved to' if val else 'removed from'} OS keyring.",
                                parent=self._win,
                            )
                        except Exception as e:
                            messagebox.showerror("Keyring error", str(e), parent=self._win)
                    return save_to_keyring

                tk.Button(f, text="Save to keyring", font=("Segoe UI", 8),
                          command=_make_save(prov, key_var, source_lbl)).grid(
                    row=row + 1, column=1, sticky="w", padx=8, pady=(0, 2))

                # Still allow saving to config.json via _vars when keyring not chosen
                self._vars[f"provider.{prov}.api_key"] = key_var

            row += 2 if source != "env" else 1

            # Model
            tk.Label(f, text="Model:").grid(row=row, column=0, sticky="w", pady=2)
            current_model = cfg.get(f"provider.{prov}.model", _models[prov][0])
            model_var = tk.StringVar(value=current_model)
            self._vars[f"provider.{prov}.model"] = model_var
            ttk.Combobox(f, textvariable=model_var, values=_models[prov],
                         width=28, state="readonly").grid(row=row, column=1, sticky="w", padx=8)
            row += 1

        tk.Button(f, text="Test connection", command=self._test_connection).grid(
            row=row, column=0, columnspan=3, pady=(12, 0))

        return f

    def _tab_hotkey(self, parent) -> tk.Frame:
        cfg = self._app.config_manager
        f = tk.Frame(parent, padx=15, pady=15)

        # ── Mode selector ──────────────────────────────────────────────────
        row0 = tk.Frame(f)
        row0.pack(fill="x", pady=(0, 10))
        tk.Label(row0, text="Modo de activación:").pack(side="left")

        mode_var = tk.StringVar(value=cfg.get("hotkey.mode", "combo"))
        self._vars["hotkey.mode"] = mode_var
        mode_combo = ttk.Combobox(
            row0, textvariable=mode_var,
            values=["combo", "double_tap"],
            width=14, state="readonly",
        )
        mode_combo.pack(side="left", padx=8)

        mode_labels = {"combo": "Combinación de teclas", "double_tap": "Doble pulsación"}
        mode_desc = tk.Label(f, text=mode_labels.get(mode_var.get(), ""), fg="#555",
                             font=("Segoe UI", 8))
        mode_desc.pack(anchor="w", pady=(0, 8))

        def on_mode_change(*_):
            mode_desc.config(text=mode_labels.get(mode_var.get(), ""))
            sensitivity_frame.pack_forget()
            if mode_var.get() == "double_tap":
                sensitivity_frame.pack(fill="x", pady=(8, 0))

        mode_var.trace_add("write", on_mode_change)

        # ── Key recorder ───────────────────────────────────────────────────
        tk.Label(f, text="Tecla(s):").pack(anchor="w")

        # Internal storage for captured keys
        _captured: dict = {
            "combo_display": cfg.get("hotkey.combo_display", "Ctrl + Shift + 1"),
            "combo_keys": cfg.get("hotkey.combo_keys", "ctrl+shift+1"),
            "double_tap_key": cfg.get("hotkey.double_tap_key", "ctrl_l"),
            "double_tap_display": cfg.get("hotkey.double_tap_key", "ctrl_l"),
        }

        def on_captured(display: str, keys: str) -> None:
            if mode_var.get() == "combo":
                _captured["combo_display"] = display
                _captured["combo_keys"] = keys
            else:
                _captured["double_tap_key"] = keys
                _captured["double_tap_display"] = display

        recorder = KeyRecorder(f, mode_var=mode_var, on_captured=on_captured)
        recorder.pack(anchor="w", pady=4)

        # Show current value
        if mode_var.get() == "combo":
            recorder.set_display(_captured["combo_display"])
        else:
            recorder.set_display(_captured["double_tap_display"])

        # Update recorder display when mode changes
        def refresh_recorder(*_):
            if mode_var.get() == "combo":
                recorder.set_display(_captured["combo_display"])
            else:
                recorder.set_display(_captured["double_tap_display"])

        mode_var.trace_add("write", refresh_recorder)

        # Store reference to captured dict for _save
        self._hotkey_captured = _captured

        # ── Sensitivity (double_tap only) ──────────────────────────────────
        sensitivity_frame = tk.Frame(f)

        tk.Label(sensitivity_frame, text="Sensibilidad (ms entre taps):").pack(anchor="w", pady=(4, 2))
        ms_var = tk.IntVar(value=cfg.get("hotkey.double_tap_ms", 400))
        self._vars["hotkey.double_tap_ms"] = ms_var

        sl_row = tk.Frame(sensitivity_frame)
        sl_row.pack(fill="x")
        tk.Label(sl_row, text="200ms").pack(side="left")
        tk.Scale(sl_row, from_=200, to=800, orient="horizontal",
                 variable=ms_var, resolution=50, length=200, showvalue=True).pack(side="left", padx=6)
        tk.Label(sl_row, text="800ms").pack(side="left")

        if mode_var.get() == "double_tap":
            sensitivity_frame.pack(fill="x", pady=(8, 0))

        return f

    def _tab_widget(self, parent) -> tk.Frame:
        cfg = self._app.config_manager
        f = tk.Frame(parent, padx=15, pady=15)

        tk.Label(f, text="Transparencia del widget:").pack(anchor="w")

        alpha_var = tk.DoubleVar(value=cfg.get("widget.alpha", 0.85))
        self._vars["widget.alpha"] = alpha_var

        slider_frame = tk.Frame(f)
        slider_frame.pack(fill="x", pady=6)
        tk.Label(slider_frame, text="40%").pack(side="left")
        tk.Scale(slider_frame, from_=0.4, to=1.0, orient="horizontal",
                 variable=alpha_var, resolution=0.05, length=220, showvalue=True).pack(side="left", padx=6)
        tk.Label(slider_frame, text="100%").pack(side="left")

        tk.Button(f, text="Resetear posición (centro inferior)", command=self._reset_position).pack(
            anchor="w", pady=(16, 0)
        )

        return f

    def _tab_about(self, parent) -> tk.Frame:
        try:
            from ..app import VERSION
        except Exception:
            VERSION = "0.1.0"
        f = tk.Frame(parent, bg="white", padx=20, pady=20)

        try:
            from .tray import _make_icon_image
            from PIL import ImageTk
            img = _make_icon_image().resize((48, 48))
            photo = ImageTk.PhotoImage(img)
            f._photo = photo  # keep reference
            tk.Label(f, image=photo, bg="white").pack(pady=(10, 6))
        except Exception:
            pass

        tk.Label(f, text="GliFlow", font=("Segoe UI", 16, "bold"), bg="white").pack()
        tk.Label(f, text=f"v{VERSION}  —  Speech-to-Text Desktop App",
                 font=("Segoe UI", 9), fg="#555", bg="white").pack(pady=(2, 12))
        tk.Frame(f, height=1, bg="#ddd").pack(fill="x", padx=20)
        tk.Label(f, text="Developed by virapa",
                 font=("Segoe UI", 9, "italic"), fg="#444", bg="white").pack(pady=(10, 4))
        tk.Label(f, text="Powered by Groq · OpenAI · Google Gemini",
                 font=("Segoe UI", 8), fg="#888", bg="white").pack()

        return f

    # ── Actions ───────────────────────────────────────────────────────────────

    def _save(self) -> None:
        cfg = self._app.config_manager
        for key, var in self._vars.items():
            cfg.set(key, var.get())

        # Save captured hotkey values
        if hasattr(self, "_hotkey_captured"):
            c = self._hotkey_captured
            cfg.set("hotkey.combo_display", c["combo_display"])
            cfg.set("hotkey.combo_keys", c["combo_keys"])
            cfg.set("hotkey.double_tap_key", c["double_tap_key"])

        # Apply alpha immediately
        alpha = self._vars.get("widget.alpha")
        if alpha:
            self._app.widget.update_alpha(alpha.get())

        # Auto-start registry
        self._apply_auto_start(self._vars.get("general.auto_start", tk.BooleanVar()).get())

        # Rebuild tray menu in case history setting changed
        self._app.tray.rebuild_menu()

        # Recreate STT provider with new config
        self._app.reload_provider()

        # Restart hotkey listener with new config
        self._app.reload_hotkey()

        messagebox.showinfo("GliFlow", "Configuración guardada.", parent=self._win)
        self._on_close()

    def _reset_position(self) -> None:
        cfg = self._app.config_manager
        cfg.set("widget.x", None)
        cfg.set("widget.y", None)
        messagebox.showinfo("GliFlow", "Posición reseteada. Efecto en la próxima grabación.", parent=self._win)

    def _test_connection(self) -> None:
        import io, wave
        import numpy as np
        # 1-second silence WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(np.zeros(16000, dtype=np.int16).tobytes())
        audio = buf.getvalue()

        try:
            text = self._app.provider.transcribe(audio, language="es")
            messagebox.showinfo("Conexión OK", f"Respuesta: {text!r}", parent=self._win)
        except Exception as e:
            messagebox.showerror("Error de conexión", str(e), parent=self._win)

    def _apply_auto_start(self, enabled: bool) -> None:
        if sys.platform != "win32":
            return
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "GliFlow"
            import sys as _sys
            exe = _sys.executable
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe}" -m src.main')
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
        except Exception:
            pass


class HistoryWindow:
    """Simple transcription history viewer."""

    def __init__(self, app):
        self._app = app
        self._win: tk.Toplevel | None = None

    def show(self) -> None:
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._build()

    def _build(self) -> None:
        root = self._app.root
        self._win = tk.Toplevel(root)
        self._win.title("GliFlow — Historial")
        w, h = 500, 400
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        self._win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        top = tk.Frame(self._win)
        top.pack(fill="x", padx=10, pady=8)
        tk.Label(top, text="Historial de transcripciones", font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Button(top, text="Copiar seleccionado", command=self._copy_selected).pack(side="right")

        frame = tk.Frame(self._win)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        self._listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Segoe UI", 9), selectmode="single")
        self._listbox.pack(fill="both", expand=True)
        scrollbar.config(command=self._listbox.yview)

        self._entries: list[dict] = []
        self._load_entries()

    def _load_entries(self) -> None:
        self._listbox.delete(0, "end")
        self._entries = self._app.history.get_all(limit=200)
        for e in self._entries:
            ts = e["timestamp"][:16]
            preview = e["text"][:60] + ("…" if len(e["text"]) > 60 else "")
            self._listbox.insert("end", f"[{ts}] {e['provider']} — {preview}")

    def _copy_selected(self) -> None:
        idx = self._listbox.curselection()
        if not idx:
            return
        import pyperclip
        pyperclip.copy(self._entries[idx[0]]["text"])
