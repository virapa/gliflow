# GliFlow - Speech-to-Text Desktop Application

## Context

GliFlow is a desktop speech-to-text (STT) application for Windows (with future macOS/Linux support). The user needs a lightweight, always-ready tool to transcribe voice to text via a global hotkey, inserting the result wherever the cursor is. The primary use case is quick dictation in any application without switching context.

## Requirements

### Functional
- **Global hotkey**: Double-tap Ctrl to start/stop recording
- **Floating widget**: Transparent, draggable overlay showing recording status
- **Widget position persistence**: Position saved to config; resets to default (bottom-center) if out of screen bounds
- **Transcription output**: Text copied to clipboard AND auto-pasted at cursor position
- **Multi-provider STT**: Abstracted engine supporting Groq (Whisper large-v3), OpenAI Whisper, Google Gemini
- **System tray**: Runs in background with tray icon, context menu for config/history/exit
- **GUI configuration**: Tkinter settings window with tabs for general, provider, hotkey, widget
- **History**: Optional SQLite-backed transcription log (configurable on/off)
- **Primary language**: Spanish (with Whisper auto-detection available)

### Non-Functional
- Lightweight: ~20MB packaged
- Cross-platform ready (Python + Tkinter)
- Modular architecture for easy provider addition

## Technology Stack

| Component       | Library          | Purpose                              |
|-----------------|------------------|--------------------------------------|
| Language        | Python 3.11+     | Core runtime                         |
| GUI/Widget      | Tkinter          | Transparent overlay + config window  |
| Audio capture   | sounddevice      | Cross-platform audio recording       |
| Global hotkeys  | pynput           | Double-tap Ctrl detection            |
| System tray     | pystray + Pillow | Tray icon and context menu           |
| Clipboard       | pyperclip        | Cross-platform clipboard access      |
| HTTP client     | httpx            | Async API calls to STT providers     |
| Database        | sqlite3 (stdlib) | Optional transcription history       |
| Config          | json (stdlib)    | Configuration persistence            |
| Packaging       | PyInstaller      | Distributable executable             |

## Architecture

```
+-----------------------------------------------------+
|                    GliFlow App                       |
+----------+----------+-----------+-------------------+
|  Hotkey  |  Audio   |  Widget   |  System Tray      |
| Listener | Recorder | (Tkinter) |  (pystray)        |
| (pynput) |(sounddev)|           |                   |
+----------+----------+-----------+-------------------+
|              STT Engine Abstraction                  |
|  +---------+  +----------+  +---------+             |
|  |  Groq   |  |  OpenAI  |  | Gemini  |  ...       |
|  | Whisper |  | Whisper  |  |  STT    |             |
|  +---------+  +----------+  +---------+             |
+-----------------------------------------------------+
|  Config Manager  |  Clipboard  |  History (SQLite)  |
+-----------------------------------------------------+
```

### Main Flow

1. App starts -> registers in system tray -> listens for hotkey (double-tap Ctrl)
2. Double-tap Ctrl -> starts audio recording -> shows transparent widget
3. Double-tap Ctrl again -> stops recording -> sends audio to STT API
4. Receives text -> copies to clipboard + simulates Ctrl+V to paste -> hides widget
5. (Optional) saves transcription to SQLite history

## Component Details

### 1. Hotkey Listener (`src/hotkey/listener.py`)

- Uses `pynput.keyboard.Listener` in a background thread
- Detects double-tap of Ctrl key (left or right)
- Configurable sensitivity (time window between taps, default 400ms)
- Fires callback: `on_recording_start()` or `on_recording_stop()`
- Must not interfere with normal Ctrl usage (single press, Ctrl+C, etc.)

### 2. Audio Recorder (`src/audio/recorder.py`)

- Uses `sounddevice.InputStream` for real-time capture
- Settings: 16kHz sample rate, mono, 16-bit PCM
- Buffers audio frames in memory (list of numpy arrays)
- On stop: concatenates frames and converts to WAV bytes using `wave` stdlib
- No temporary files needed (WAV built in memory)

### 3. Transparent Widget (`src/ui/widget.py`)

- `Tk()` window with `overrideredirect(True)` (no title bar)
- `wm_attributes('-alpha', 0.85)` for transparency
- `wm_attributes('-topmost', True)` to stay on top
- Size: ~200x60 px
- Content: Microphone icon label + "Escuchando..." with animated dots
- Draggable via `<Button-1>` and `<B1-Motion>` event bindings
- On drag end: saves new position to config
- States: "Escuchando..." -> "Transcribiendo..." -> "Texto copiado" -> hide

**Position persistence:**
- Stored as `{"widget_x": int, "widget_y": int}` in config.json
- On show: validate position is within `winfo_screenwidth()` x `winfo_screenheight()`
- If out of bounds: reset to bottom-center (screen_width/2 - widget_width/2, screen_height - 100)

### 4. STT Engine (`src/stt/`)

**Base interface** (`base.py`):
```python
class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_data: bytes, language: str = "es") -> str:
        """Transcribe WAV audio bytes to text."""
        pass
```

**Groq Provider** (`groq_provider.py`):
- Endpoint: `https://api.groq.com/openai/v1/audio/transcriptions`
- Model: `whisper-large-v3`
- Sends multipart form: file (WAV), model, language
- Returns JSON with `text` field

**OpenAI Provider** (`openai_provider.py`):
- Endpoint: `https://api.openai.com/v1/audio/transcriptions`
- Model: `whisper-1`
- Same multipart format as Groq (compatible API)

**Gemini Provider** (`gemini_provider.py`):
- Uses Google Generative AI API
- Sends audio with transcription prompt
- Parses text from response

### 5. Text Inserter (`src/output/inserter.py`)

- Step 1: Copy text to clipboard via `pyperclip.copy(text)`
- Step 2: Wait 100ms
- Step 3: Simulate `Ctrl+V` using `pynput.keyboard.Controller`
- Fallback: if paste fails, text remains in clipboard for manual paste
- Visual feedback on widget before hiding: "Texto copiado"

### 6. System Tray (`src/ui/tray.py`)

- Uses `pystray.Icon` with a microphone PNG icon
- Context menu items:
  - "Configuracion" -> opens config window
  - "Historial" -> opens history viewer (if enabled)
  - "Acerca de" -> version info dialog
  - Separator
  - "Salir" -> graceful shutdown
- Runs in its own thread (pystray requirement)

### 7. Configuration (`src/config/manager.py`)

**Config file**: `~/.gliflow/config.json`

**Default config:**
```json
{
  "general": {
    "language": "es",
    "auto_start": false,
    "history_enabled": false
  },
  "provider": {
    "active": "groq",
    "groq": {
      "api_key": "",
      "model": "whisper-large-v3"
    },
    "openai": {
      "api_key": "",
      "model": "whisper-1"
    },
    "gemini": {
      "api_key": "",
      "model": "gemini-2.0-flash"
    }
  },
  "hotkey": {
    "type": "double_tap_ctrl",
    "double_tap_ms": 400
  },
  "widget": {
    "alpha": 0.85,
    "x": null,
    "y": null,
    "default_position": "bottom-center"
  }
}
```

**Config GUI** (`src/ui/config_window.py`):
- Tkinter `Toplevel` with `ttk.Notebook` (tabs)
- Tab 1 - General: Language dropdown, auto-start checkbox, history toggle
- Tab 2 - Provider: Provider selector, API key entry (masked), model selector
- Tab 3 - Hotkey: Double-tap sensitivity slider (200-800ms)
- Tab 4 - Widget: Transparency slider, reset position button

### 8. History (`src/config/manager.py` or `src/history/`)

**SQLite schema:**
```sql
CREATE TABLE transcriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    provider TEXT NOT NULL,
    language TEXT NOT NULL,
    audio_duration_ms INTEGER
);
```

- Database file: `~/.gliflow/history.db`
- Only active when `history_enabled: true`
- Simple viewer accessible from tray menu (Tkinter listbox with search)

## Project Structure

```
gliflow/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── app.py               # GliFlow orchestrator class
│   ├── audio/
│   │   ├── __init__.py
│   │   └── recorder.py      # Audio capture with sounddevice
│   ├── stt/
│   │   ├── __init__.py
│   │   ├── base.py          # STTProvider abstract base
│   │   ├── groq_provider.py
│   │   ├── openai_provider.py
│   │   └── gemini_provider.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── widget.py        # Transparent floating widget
│   │   ├── tray.py          # System tray integration
│   │   └── config_window.py # Settings GUI
│   ├── hotkey/
│   │   ├── __init__.py
│   │   └── listener.py      # Double-tap Ctrl detection
│   ├── output/
│   │   ├── __init__.py
│   │   └── inserter.py      # Clipboard + auto-paste
│   └── config/
│       ├── __init__.py
│       └── manager.py       # Config read/write
├── assets/
│   └── icon.png             # Tray icon
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Dependencies

```
sounddevice>=0.4.6
numpy>=1.24.0
pynput>=1.7.6
pystray>=0.19.5
Pillow>=10.0.0
pyperclip>=1.8.2
httpx>=0.25.0
```

## Threading Model

- **Main thread**: Tkinter event loop (widget + config window)
- **Thread 1**: pystray (system tray) - runs its own event loop
- **Thread 2**: pynput listener (hotkey detection)
- **Thread 3**: Audio recording (when active)
- **Thread 4**: API call (when transcribing, short-lived)

Communication between threads via `queue.Queue` and Tkinter's `after()` method for thread-safe UI updates.

## Error Handling

- **No API key configured**: Show notification from tray "Configure your API key first"
- **API call fails**: Show error in widget, keep text in clipboard if partial
- **Audio device not found**: Notify user via tray, suggest checking microphone
- **Network timeout**: Retry once, then show error

## Future Considerations

- OS keyring integration for secure API key storage
- Local STT model (whisper.cpp) for offline transcription
- Streaming transcription (real-time partial results)
- Multiple hotkey configurations
- macOS/Linux support (test pynput, pystray, Tkinter on those platforms)
- English translation for token optimisation
- Speech optimisation
- Optimisation of the spoken text if requested at the end of the speech

## Verification Plan

1. **Unit tests**: Test config manager, audio recorder (mock), STT providers (mock API)
2. **Integration test**: Record short audio -> transcribe via Groq -> verify text output
3. **Manual testing**:
   - Launch app, verify tray icon appears
   - Double-tap Ctrl, verify widget shows
   - Speak, double-tap Ctrl again, verify text appears in clipboard and at cursor
   - Drag widget, close app, reopen, verify widget position persists
   - Move widget off-screen, reopen, verify it resets to bottom-center
   - Open config, change provider, verify new provider is used
   - Enable history, transcribe, verify entry in history viewer
