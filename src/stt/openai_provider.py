from .base import STTProvider, STTError, _make_client

ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"


class OpenAIProvider(STTProvider):
    def __init__(self, api_key: str, model: str = "whisper-1"):
        super().__init__()
        self._api_key = api_key
        self._model = model

    def _do_transcribe(self, audio_data: bytes, language: str = "es") -> str:
        if not self._api_key:
            raise STTError("OpenAI API key not configured")
        try:
            with _make_client() as client:
                response = client.post(
                    ENDPOINT,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    files={"file": ("audio.wav", audio_data, "audio/wav")},
                    data={"model": self._model, "language": language},
                )
            response.raise_for_status()
            return response.json()["text"].strip()
        except httpx.TimeoutException as e:
            raise STTError("OpenAI API timeout") from e
        except httpx.HTTPStatusError as e:
            raise STTError(f"API error {e.response.status_code} — check your API key and try again") from e
        except httpx.RequestError as e:
            raise STTError(f"Network error — {type(e).__name__}") from e
        except Exception as e:
            raise STTError(f"OpenAI transcription failed: {type(e).__name__}") from e
