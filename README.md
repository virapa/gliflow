# GliFlow

Windows desktop Speech-to-Text app. Trigger recording with a global hotkey, transcribe your voice, and automatically paste the text wherever your cursor is.

---

## Quick Start

```bash
# 1. Clone and create virtual environment
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 2. Set up your API key (copy .env.example and fill in your key)
copy .env.example .env

# 3. Run
.venv\Scripts\python -m src.main
```

The GliFlow icon will appear in the system tray. You're ready.

---

## Features

- **Global hotkey** — configurable key combo (`Ctrl+Shift+1` by default) or double-tap a single key
- **Floating widget** — semi-transparent, draggable indicator showing real-time status
- **Auto-paste** — transcribed text is copied to clipboard and pasted at the active focus via `Ctrl+V`
- **Multiple STT providers** — Groq (Whisper large-v3), OpenAI (Whisper / GPT-4o), and Google Gemini
- **System tray** — context menu with start/stop, settings, and history
- **History** — transcriptions stored in SQLite (`~/.gliflow/history.db`), optional
- **Settings GUI** — tabbed window: Test, General, Provider, Hotkey, Widget, About
- **OS keyring** — API keys stored securely in Windows Credential Manager (macOS Keychain / libsecret on Linux)

---

## Configuration

### API Keys

GliFlow resolves API keys in this priority order:

```
env var (.env)  →  OS keyring  →  config.json
```

**Option 1 — OS keyring (recommended):** open Settings → Provider, type the key in the entry field and click **Save to keyring**. The key is stored in Windows Credential Manager (macOS Keychain / libsecret on Linux) and never written to disk in plain text.

**Option 2 — `.env` file:** create a `.env` file in the project root (takes priority over keyring):

```env
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
```

**Option 3 — config.json:** enter the key directly in Settings → Provider and press Save. Stored at `~/.gliflow/config.json` in plain text.

You only need a key for the provider you intend to use. The Provider tab shows a colour-coded badge indicating the active source for each key: `● .env` (green), `● keyring` (blue), `● config` (grey), `○ no key` (red).

### Config file

Auto-generated at `~/.gliflow/config.json`:

| Key | Description | Default |
|-----|-------------|---------|
| `general.language` | Transcription language | `es` |
| `general.auto_start` | Start with Windows | `false` |
| `general.history_enabled` | Save transcription history | `false` |
| `provider.active` | Active STT provider | `groq` |
| `provider.groq.model` | Groq model | `whisper-large-v3` |
| `provider.openai.model` | OpenAI model | `whisper-1` |
| `provider.gemini.model` | Gemini model | `gemini-2.0-flash` |
| `hotkey.mode` | Activation mode (`combo` / `double_tap`) | `combo` |
| `hotkey.combo_keys` | Key combination | `ctrl+shift+1` |
| `hotkey.double_tap_key` | Key for double-tap mode | `ctrl_l` |
| `hotkey.double_tap_ms` | Double-tap window (ms) | `400` |
| `widget.alpha` | Widget transparency (0.4–1.0) | `0.85` |

---

## Usage

1. **Start recording** — press the hotkey (or use the tray menu)
2. **Speak** — the widget shows an animated dot indicator while recording
3. **Stop** — press the hotkey again; the widget switches to "Transcribing..."
4. **Result** — text is automatically inserted at the active cursor position

> When stopping from the tray or the GUI button, a 3-second countdown gives you time to switch focus before the text is pasted.

---

## STT Providers

| Provider | Available models | Environment variable |
|----------|-----------------|---------------------|
| **Groq** | `whisper-large-v3`, `whisper-large-v3-turbo` | `GROQ_API_KEY` |
| **OpenAI** | `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` | `OPENAI_API_KEY` |
| **Gemini** | `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-flash`, `gemini-1.5-pro` | `GEMINI_API_KEY` |

---

## Architecture

```
src/
├── main.py              # Entry point — loads .env and starts GliFlowApp
├── app.py               # Central orchestrator (queue.Queue for thread safety)
├── audio/
│   └── recorder.py      # Audio capture (sounddevice, 16kHz mono, WAV in-memory)
├── stt/
│   ├── base.py          # STTProvider ABC + STTError
│   ├── groq_provider.py
│   ├── openai_provider.py
│   └── gemini_provider.py
├── hotkey/
│   └── listener.py      # RegisterHotKey (Windows) or pynput (double-tap / fallback)
├── output/
│   └── inserter.py      # pyperclip.copy() + Ctrl+V simulation via pynput
├── config/
│   └── manager.py       # ConfigManager (JSON) + HistoryManager (SQLite)
└── ui/
    ├── widget.py         # Floating widget (Toplevel, overrideredirect, -topmost)
    ├── tray.py           # System tray icon (pystray)
    └── config_window.py  # Settings GUI (ttk.Notebook)
```

**Thread flow:**

```
Hotkey thread ──┐
                ├──► queue.Queue ──► main thread (Tkinter) ──► UI updates
Audio thread ───┘
```

Worker threads never touch Tkinter directly — they only call `queue.put()`. The main thread drains the queue every 50 ms via `root.after()`.

---

## Development

```bash
# Run test suite
.venv\Scripts\python -m pytest tests/ -v

# Debug key detection
.venv\Scripts\python debug_keys.py
```

### Custom icon

Replace `assets/icon.png` with your own 64×64 px RGBA PNG. If the file is missing, a default microphone icon is generated at runtime.

---

## Deployment

GliFlow uses GitHub Actions to build standalone executables for Windows, macOS, and Linux via PyInstaller. No Python installation is required to run the distributed binaries.

### Automated builds

Every push to a `v*` tag triggers the build pipeline:

```bash
# 1. Bump version in src/app.py
# 2. Commit and tag
git add src/app.py
git commit -m "chore: bump version to v0.9.0"
git tag v0.9.0
git push origin main --tags
```

GitHub Actions will:
1. Build three executables in parallel (Windows, macOS, Linux)
2. Create a GitHub Release with auto-generated release notes
3. Attach the binaries as release assets:
   - `GliFlow-windows.exe`
   - `GliFlow-macos.zip` (contains `GliFlow.app`)
   - `GliFlow-linux`

### Manual build trigger

You can also trigger a build without a release from the GitHub Actions tab → **Build** → **Run workflow**.

### Build locally

```bash
pip install pyinstaller==6.11.1
pyinstaller gliflow.spec --clean --noconfirm
# Output: dist/GliFlow  (or dist/GliFlow.exe on Windows)
```

### Platform notes

| Platform | Extra requirements |
|----------|--------------------|
| **Windows** | None — PortAudio DLL is bundled by `sounddevice` |
| **macOS** | `brew install portaudio` before building |
| **Linux** | `python3-tk`, `libayatana-appindicator3-dev`, `xvfb` (installed automatically in CI) |

> macOS builds produce a `.app` bundle with microphone permission description in `Info.plist` (`NSMicrophoneUsageDescription`). On first launch, macOS will prompt for microphone access.

---

## Requirements

- Python 3.11+
- Windows 10/11 (`combo` mode uses the native `RegisterHotKey` API)
- Working microphone
- API key for at least one supported provider

> **macOS / Linux:** supported in `double_tap` mode via pynput. `combo` mode requires Windows.

---

## License

MIT — developed by virapa
