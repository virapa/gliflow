# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GliFlow is a Windows desktop Speech-to-Text application (Python 3.11+, Tkinter). It provides always-on voice transcription via a global hotkey, with automatic text insertion at the cursor position. UI text is in Spanish.

## Commands

```bash
# Setup
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt

# Run
.venv/Scripts/python -m src.main

# Test
.venv/Scripts/python -m pytest tests/ -v          # full suite
.venv/Scripts/python -m pytest tests/test_config.py -v  # single file

# Debug hotkeys
.venv/Scripts/python debug_keys.py
```

## Architecture

**Entry point**: `src/main.py` → loads `.env` → runs `GliFlowApp`.

**GliFlowApp** (`src/app.py`) is the central orchestrator. It owns all subsystems and coordinates them via a `queue.Queue` for thread-safe UI updates. The main thread runs the Tkinter mainloop and processes queued messages; worker threads (audio, hotkey) push events into the queue.

### Key modules

- **`src/stt/`** — STT provider abstraction. `base.py` defines the `STTProvider` ABC. Three implementations (Groq, OpenAI, Gemini) use `httpx`. Factory in `__init__.py:get_provider()` instantiates the active provider. API keys: env vars (`.env`) take priority over `config.json`.
- **`src/audio/recorder.py`** — Captures audio via `sounddevice` (16kHz mono). Streams into numpy arrays, exports WAV bytes in-memory (no temp files).
- **`src/hotkey/listener.py`** — Dual-mode: Windows `RegisterHotKey` API (combo mode) or `pynput` double-tap detection (400ms window).
- **`src/output/inserter.py`** — Copies transcription to clipboard via `pyperclip`, then simulates Ctrl+V with `pynput`.
- **`src/config/manager.py`** — `ConfigManager` reads/writes `~/.gliflow/config.json` with deep-merge defaults. `HistoryManager` stores transcription history in `~/.gliflow/history.db` (SQLite).
- **`src/ui/`** — `widget.py`: transparent, draggable, always-on-top floating widget. `tray.py`: system tray icon with context menu. `config_window.py`: multi-tab config GUI with VK-based key recorder.

### Thread safety pattern

Worker threads never touch Tkinter directly. They call `queue.put(callback)` and the main thread polls with `_process_queue()`. Audio frames and hotkey state are protected by locks.

## Configuration

- API keys: `.env` file (see `.env.example`) or `~/.gliflow/config.json`
- User config: `~/.gliflow/config.json` (JSON, auto-created with defaults)
- History DB: `~/.gliflow/history.db`
