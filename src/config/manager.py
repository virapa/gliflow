import copy
import json
import sqlite3
from pathlib import Path
from datetime import datetime

APP_DIR = Path.home() / ".gliflow"

DEFAULT_CONFIG = {
    "general": {
        "language": "es",
        "auto_start": False,
        "history_enabled": False,
    },
    "provider": {
        "active": "groq",
        "groq": {
            "api_key": "",
            "model": "whisper-large-v3",
        },
        "openai": {
            "api_key": "",
            "model": "whisper-1",
        },
        "gemini": {
            "api_key": "",
            "model": "gemini-2.0-flash",
        },
    },
    "hotkey": {
        "mode": "combo",           # "combo" | "double_tap"
        "combo_display": "Ctrl + Shift + 1",
        "combo_keys": "ctrl+shift+1",
        "double_tap_key": "ctrl_l",
        "double_tap_ms": 400,
    },
    "widget": {
        "alpha": 0.85,
        "x": None,
        "y": None,
    },
}


class ConfigManager:
    def __init__(self, config_dir: Path = APP_DIR):
        self._path = config_dir / "config.json"
        config_dir.mkdir(parents=True, exist_ok=True)
        self._config = self._load()

    def _load(self) -> dict:
        if not self._path.exists():
            self._write(DEFAULT_CONFIG)
            return copy.deepcopy(DEFAULT_CONFIG)
        with open(self._path, encoding="utf-8") as f:
            data = json.load(f)
        return self._merge(copy.deepcopy(DEFAULT_CONFIG), data)

    def _merge(self, defaults: dict, overrides: dict) -> dict:
        """Deep merge: defaults filled in where keys are missing."""
        result = dict(defaults)
        for k, v in overrides.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge(result[k], v)
            else:
                result[k] = v
        return result

    def _write(self, data: dict) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save(self) -> None:
        self._write(self._config)

    def get(self, key_path: str, default=None):
        keys = key_path.split(".")
        node = self._config
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    def set(self, key_path: str, value) -> None:
        keys = key_path.split(".")
        node = self._config
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = value
        self.save()

    @property
    def config(self) -> dict:
        return self._config

    def reload(self) -> None:
        self._config = self._load()


class HistoryManager:
    def __init__(self, db_dir: Path = APP_DIR):
        self._db_path = db_dir / "history.db"
        db_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    provider TEXT NOT NULL,
                    language TEXT NOT NULL,
                    audio_duration_ms INTEGER
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, text: str, provider: str, language: str, duration_ms: int = 0) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO transcriptions (text, provider, language, audio_duration_ms) VALUES (?, ?, ?, ?)",
                (text, provider, language, duration_ms),
            )

    def get_all(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM transcriptions ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
