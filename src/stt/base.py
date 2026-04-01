from abc import ABC, abstractmethod


class STTError(Exception):
    pass


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_data: bytes, language: str = "es") -> str:
        """Transcribe WAV audio bytes to text."""
