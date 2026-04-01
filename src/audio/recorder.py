import io
import wave
import threading
import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"


class AudioRecorder:
    def __init__(self):
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._recording = False
        self._stop_event = threading.Event()

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        if self._recording:
            return
        self._frames = []
        self._stop_event.clear()
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()
        self._recording = True

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        if self._stop_event.is_set():
            return
        with self._lock:
            self._frames.append(indata.copy())

    def stop(self) -> bytes:
        if not self._recording:
            return b""
        self._stop_event.set()
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._recording = False

        with self._lock:
            frames = self._frames[:]

        if not frames:
            return b""

        audio = np.concatenate(frames, axis=0)
        return self._to_wav(audio)

    def _to_wav(self, audio: np.ndarray) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()
