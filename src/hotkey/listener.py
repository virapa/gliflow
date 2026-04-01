import sys
import threading
from typing import Callable

# ── Key mappings ──────────────────────────────────────────────────────────────

# Windows Virtual Key codes for common keys
_VK_MAP: dict[str, int] = {
    **{str(i): 0x30 + i for i in range(10)},          # 0-9
    **{chr(c): 0x41 + (c - ord("a")) for c in range(ord("a"), ord("z") + 1)},  # a-z
    "space": 0x20, "enter": 0x0D, "tab": 0x09, "esc": 0x1B,
    "backspace": 0x08, "delete": 0x2E, "insert": 0x2D,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    **{f"f{i}": 0x6F + i for i in range(1, 13)},       # f1-f12
}

_WIN_MOD_MAP: dict[str, int] = {
    "ctrl": 0x0002, "shift": 0x0004, "alt": 0x0001, "win": 0x0008,
}

# pynput key names for double-tap mode
_PYNPUT_KEY_MAP: dict[str, str] = {
    "ctrl_l": "ctrl_l", "ctrl_r": "ctrl_r", "ctrl": "ctrl",
    "shift_l": "shift_l", "shift_r": "shift_r", "shift": "shift",
    "alt_l": "alt_l", "alt_r": "alt_r", "alt": "alt",
}


def parse_combo(combo_keys: str) -> tuple[int, int]:
    """Parse 'ctrl+shift+1' → (win_modifiers, vk_code). Returns (0,0) on failure."""
    parts = [p.strip().lower() for p in combo_keys.split("+")]
    mods = 0
    vk = 0
    for part in parts:
        if part in _WIN_MOD_MAP:
            mods |= _WIN_MOD_MAP[part]
        elif part in _VK_MAP:
            vk = _VK_MAP[part]
        elif len(part) == 1:
            vk = ord(part.upper())
    return mods, vk


class HotkeyListener:
    """Global hotkey listener supporting combo (Ctrl+Shift+1) and double-tap modes."""

    def __init__(
        self,
        callback_start: Callable,
        callback_stop: Callable,
        mode: str = "combo",
        combo_keys: str = "ctrl+shift+1",
        double_tap_key: str = "ctrl_l",
        double_tap_ms: int = 400,
    ):
        self._callback_start = callback_start
        self._callback_stop = callback_stop
        self._mode = mode
        self._combo_keys = combo_keys
        self._double_tap_key = double_tap_key
        self._double_tap_ms = double_tap_ms

        self._recording = False
        self._paused = False
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._win_thread_id: int = 0

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def start(self) -> None:
        self._stop_event.clear()
        if self._mode == "combo" and sys.platform == "win32":
            self._thread = threading.Thread(target=self._run_windows_combo, daemon=True)
        else:
            self._thread = threading.Thread(target=self._run_pynput, daemon=True)
        self._thread.start()

    def stop(self, wait: bool = True) -> None:
        self._stop_event.set()
        if sys.platform == "win32" and self._win_thread_id:
            try:
                import ctypes
                ctypes.windll.user32.PostThreadMessageW(self._win_thread_id, 0x0012, 0, 0)
            except Exception:
                pass
        if wait and self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _toggle(self) -> None:
        if self._paused:
            return
        with self._lock:
            if not self._recording:
                self._recording = True
                threading.Thread(target=self._callback_start, daemon=True).start()
            else:
                self._recording = False
                threading.Thread(target=self._callback_stop, daemon=True).start()

    # ── Windows RegisterHotKey (combo mode) ───────────────────────────────────

    def _run_windows_combo(self) -> None:
        import ctypes
        import ctypes.wintypes as wintypes

        MOD_NOREPEAT = 0x4000
        WM_HOTKEY = 0x0312
        HOTKEY_ID = 1

        mods, vk = parse_combo(self._combo_keys)
        if not vk:
            return  # invalid combo, nothing to register

        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, HOTKEY_ID, mods | MOD_NOREPEAT, vk):
            return

        self._win_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        msg = wintypes.MSG()
        while not self._stop_event.is_set():
            ret = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)
            if ret:
                if msg.message == 0x0012:  # WM_QUIT
                    break
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self._toggle()
            else:
                self._stop_event.wait(timeout=0.05)

        user32.UnregisterHotKey(None, HOTKEY_ID)

    # ── pynput (double-tap mode or non-Windows) ───────────────────────────────

    def _run_pynput(self) -> None:
        from pynput import keyboard
        import time

        if self._mode == "double_tap":
            self._run_pynput_double_tap(keyboard, time)
        else:
            self._run_pynput_combo(keyboard)

    def _run_pynput_double_tap(self, keyboard, time) -> None:
        double_tap_sec = self._double_tap_ms / 1000.0
        last_time: list[float] = [0.0]

        target_key = self._resolve_pynput_key(keyboard, self._double_tap_key)

        def on_press(key):
            if self._stop_event.is_set():
                return False
            if key == target_key or (hasattr(key, "name") and key.name == self._double_tap_key):
                now = time.time()
                elapsed = now - last_time[0]
                if elapsed < double_tap_sec:
                    last_time[0] = 0.0
                    self._toggle()
                else:
                    last_time[0] = now

        with keyboard.Listener(on_press=on_press) as lst:
            self._stop_event.wait()
            lst.stop()

    def _run_pynput_combo(self, keyboard) -> None:
        """Fallback combo detection via pynput (non-Windows)."""
        parts = [p.strip().lower() for p in self._combo_keys.split("+")]
        mods = {p for p in parts if p in ("ctrl", "shift", "alt", "cmd")}
        main_keys = [p for p in parts if p not in mods]
        main_key = main_keys[0] if main_keys else None
        pressed: set = set()

        _mod_aliases = {
            "ctrl": {keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.ctrl},
            "shift": {keyboard.Key.shift_l, keyboard.Key.shift_r, keyboard.Key.shift},
            "alt": {keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt},
        }

        def _held(mod: str) -> bool:
            return bool(pressed & _mod_aliases.get(mod, set()))

        def on_press(key):
            if self._stop_event.is_set():
                return False
            pressed.add(key)
            if main_key and all(_held(m) for m in mods):
                vk = getattr(key, "vk", None)
                char = getattr(key, "char", None)
                if (char and char.lower() == main_key) or (vk and vk == _VK_MAP.get(main_key, -1)):
                    self._toggle()
                    pressed.clear()

        def on_release(key):
            pressed.discard(key)

        with keyboard.Listener(on_press=on_press, on_release=on_release) as lst:
            self._stop_event.wait()
            lst.stop()

    @staticmethod
    def _resolve_pynput_key(keyboard, key_name: str):
        """Convert a key name string to a pynput Key enum value."""
        try:
            return getattr(keyboard.Key, key_name)
        except AttributeError:
            return keyboard.KeyCode(char=key_name)
