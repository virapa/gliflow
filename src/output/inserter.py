import time
import pyperclip
from pynput import keyboard

_ctrl = keyboard.Key.ctrl


def insert_text(text: str) -> None:
    """Copy text to clipboard and simulate Ctrl+V to paste at cursor."""
    pyperclip.copy(text)
    time.sleep(0.1)  # give clipboard time to update
    try:
        ctrl = keyboard.Controller()
        ctrl.press(_ctrl)
        ctrl.tap("v")
        ctrl.release(_ctrl)
    except Exception:
        # Paste failed — text still in clipboard for manual paste
        pass
