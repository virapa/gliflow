import io
import wave
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from src.audio.recorder import AudioRecorder, SAMPLE_RATE, CHANNELS


def _make_frames(seconds: float = 0.5) -> list[np.ndarray]:
    n = int(SAMPLE_RATE * seconds)
    return [np.zeros((n, CHANNELS), dtype=np.int16)]


def test_to_wav_format():
    rec = AudioRecorder()
    frames = _make_frames(0.1)
    audio = np.concatenate(frames, axis=0)
    wav_bytes = rec._to_wav(audio)

    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        assert wf.getnchannels() == CHANNELS
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == SAMPLE_RATE
        assert wf.getnframes() > 0


def test_stop_without_start_returns_empty():
    rec = AudioRecorder()
    result = rec.stop()
    assert result == b""


def test_is_recording_flag():
    rec = AudioRecorder()
    assert rec.is_recording is False

    with patch("sounddevice.InputStream") as mock_stream_cls:
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream
        rec.start()
        assert rec.is_recording is True
        # Simulate stop
        rec._frames = _make_frames(0.1)
        wav = rec.stop()
        assert rec.is_recording is False
        assert len(wav) > 0


def test_wav_output_is_valid_for_whisper():
    """WAV must be 16kHz mono 16-bit — Whisper requirements."""
    rec = AudioRecorder()
    frames = _make_frames(1.0)
    audio = np.concatenate(frames, axis=0)
    wav_bytes = rec._to_wav(audio)

    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        assert wf.getframerate() == 16000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
