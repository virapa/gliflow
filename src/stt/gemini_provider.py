import base64
from .base import STTProvider, STTError, _make_client


class GeminiProvider(STTProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        super().__init__()
        self._api_key = api_key
        self._model = model

    def _do_transcribe(self, audio_data: bytes, language: str = "es") -> str:
        if not self._api_key:
            raise STTError("Gemini API key not configured")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent"
        )
        audio_b64 = base64.b64encode(audio_data).decode()
        lang_hint = "en español" if language == "es" else f"in {language}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "audio/wav",
                                "data": audio_b64,
                            }
                        },
                        {
                            "text": f"Transcribe the audio {lang_hint}. Return only the transcribed text, no explanations."
                        },
                    ]
                }
            ]
        }
        try:
            with _make_client() as client:
                response = client.post(url, json=payload, headers={"x-goog-api-key": self._api_key})
            response.raise_for_status()
            candidates = response.json().get("candidates", [])
            if not candidates:
                raise STTError("Gemini returned no candidates")
            return candidates[0]["content"]["parts"][0]["text"].strip()
        except httpx.TimeoutException as e:
            raise STTError("Gemini API timeout") from e
        except httpx.HTTPStatusError as e:
            raise STTError(f"API error {e.response.status_code} — check your API key and try again") from e
        except httpx.RequestError as e:
            raise STTError(f"Network error — {type(e).__name__}") from e
        except STTError:
            raise
        except Exception as e:
            raise STTError(f"Gemini transcription failed: {type(e).__name__}") from e
