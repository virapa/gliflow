import threading
from pathlib import Path
from PIL import Image, ImageDraw
import pystray

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"


def _make_icon_image() -> Image.Image:
    icon_path = ASSETS_DIR / "icon.png"
    if icon_path.exists():
        return Image.open(icon_path).convert("RGBA")
    # Generate fallback icon
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 2, size - 2], fill=(45, 45, 80, 220))
    draw.rounded_rectangle([22, 10, 42, 36], radius=10, fill=(255, 255, 255, 240))
    draw.arc([14, 24, 50, 50], start=0, end=180, fill=(255, 255, 255, 240), width=3)
    draw.line([32, 49, 32, 56], fill=(255, 255, 255, 240), width=3)
    draw.line([24, 56, 40, 56], fill=(255, 255, 255, 240), width=3)
    return img


class TrayIcon:
    def __init__(self, app):
        self._app = app
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def _hotkey_label(self) -> str:
        cfg = self._app.config_manager
        mode = cfg.get("hotkey.mode", "combo")
        if mode == "double_tap":
            key = cfg.get("hotkey.double_tap_key", "ctrl_l")
            display = key.replace("_l", " L").replace("_r", " R").title()
            return f"({display} [x2])"
        else:
            display = cfg.get("hotkey.combo_display", "Ctrl + Shift + 1")
            return f"({display})"

    def _build_menu(self) -> pystray.Menu:
        history_enabled = self._app.config_manager.get("general.history_enabled", False)
        is_recording = self._app.recorder.is_recording
        hotkey = self._hotkey_label()

        items = [
            pystray.MenuItem("GliFlow", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                f"⏹  Detener grabación {hotkey}" if is_recording else f"🎤  Iniciar grabación {hotkey}",
                lambda icon, item: self._app.toggle_recording(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Configuración", lambda icon, item: self._app.open_config()),
        ]
        if history_enabled:
            items.append(
                pystray.MenuItem("Historial", lambda icon, item: self._app.open_history())
            )
        items += [
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", lambda icon, item: self._app.quit()),
        ]
        return pystray.Menu(*items)

    def start(self) -> None:
        image = _make_icon_image()
        self._icon = pystray.Icon(
            name="gliflow",
            icon=image,
            title="GliFlow STT",
            menu=self._build_menu(),
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()

    def notify(self, title: str, message: str) -> None:
        if self._icon:
            self._icon.notify(message, title)

    def rebuild_menu(self) -> None:
        if self._icon:
            self._icon.menu = self._build_menu()
            self._icon.update_menu()
