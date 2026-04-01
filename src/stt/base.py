# Security note: Full certificate pinning (hash-based) was considered but not implemented
# due to pin rotation maintenance overhead — when provider certificates rotate, pinned
# hashes must be updated manually or connections break. As a pragmatic alternative for a
# desktop app, strict hostname verification is enforced via _make_client(): ssl.CERT_REQUIRED
# + check_hostname=True using the system's default CA store. This eliminates the main
# MITM risk from misconfigured clients while avoiding pin maintenance burden.

import ssl
import time
import threading
import httpx
from abc import ABC, abstractmethod


class STTError(Exception):
    pass


def _make_client(timeout: int = 30) -> httpx.Client:
    """Build a pre-configured httpx.Client with strict SSL hostname verification.

    Creates an SSLContext with CERT_REQUIRED and check_hostname enabled,
    loaded against the system default CA certificates.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    ctx.load_default_certs()
    return httpx.Client(verify=ctx, timeout=timeout)


class STTProvider(ABC):
    _MIN_INTERVAL: float = 2.0

    def __init__(self) -> None:
        self._last_call: float = 0.0
        self._lock: threading.Lock = threading.Lock()

    def _enforce_rate_limit(self) -> None:
        """Block until the minimum interval since the last call has elapsed."""
        with self._lock:
            elapsed = time.time() - self._last_call
            if elapsed < self._MIN_INTERVAL:
                time.sleep(self._MIN_INTERVAL - elapsed)
            self._last_call = time.time()

    def transcribe(self, audio_data: bytes, language: str = "es") -> str:
        """Transcribe WAV audio bytes to text.

        Enforces a minimum interval between successive API calls before
        delegating to the provider-specific _do_transcribe() implementation.
        """
        self._enforce_rate_limit()
        return self._do_transcribe(audio_data, language)

    @abstractmethod
    def _do_transcribe(self, audio_data: bytes, language: str = "es") -> str:
        """Provider-specific transcription logic. Subclasses must implement this."""
