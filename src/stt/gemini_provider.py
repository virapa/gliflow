import base64
import httpx
from .base import STTProvider, STTError


class GeminiProvider(STTProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self._api_key = api_key
        self._model = model

    def transcribe(self, audio_data: bytes, language: str = "es") -> str:
        if not self._api_key:
            raise STTError("Gemini API key not configured")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
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
            with httpx.Client(timeout=30) as client:
                response = client.post(url, json=payload)
            response.raise_for_status()
            candidates = response.json().get("candidates", [])
            if not candidates:
                raise STTError("Gemini returned no candidates")
            return candidates[0]["content"]["parts"][0]["text"].strip()
        except httpx.TimeoutException as e:
            raise STTError("Gemini API timeout") from e
        except httpx.HTTPStatusError as e:
            raise STTError(f"Gemini API error {e.response.status_code}: {e.response.text}") from e
        except STTError:
            raise
        except Exception as e:
            raise STTError(f"Gemini transcription failed: {e}") from e
