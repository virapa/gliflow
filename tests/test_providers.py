import io
import wave
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from src.stt import get_provider, GroqProvider, OpenAIProvider, GeminiProvider
from src.stt.base import STTError


DUMMY_WAV = b"RIFF\x00\x00\x00\x00WAVEfmt "  # minimal header for testing


def _make_config(active: str, api_key: str = "test-key") -> dict:
    return {
        "provider": {
            "active": active,
            active: {"api_key": api_key, "model": "test-model"},
        }
    }


# ── Factory ───────────────────────────────────────────────────────────────────

def test_factory_groq():
    p = get_provider(_make_config("groq"))
    assert isinstance(p, GroqProvider)


def test_factory_openai():
    p = get_provider(_make_config("openai"))
    assert isinstance(p, OpenAIProvider)


def test_factory_gemini():
    p = get_provider(_make_config("gemini"))
    assert isinstance(p, GeminiProvider)


def test_factory_unknown_raises():
    with pytest.raises(ValueError, match="Unknown STT provider"):
        get_provider(_make_config("unknown"))


# ── Groq Provider ─────────────────────────────────────────────────────────────

def test_groq_no_api_key_raises():
    p = GroqProvider(api_key="", model="whisper-large-v3")
    with pytest.raises(STTError, match="API key"):
        p.transcribe(DUMMY_WAV)


def test_groq_request_structure():
    p = GroqProvider(api_key="test-key", model="whisper-large-v3")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"text": "hola mundo"}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        result = p.transcribe(DUMMY_WAV, language="es")

    assert result == "hola mundo"
    call_kwargs = mock_client.post.call_args
    assert "groq.com" in call_kwargs[0][0]
    assert call_kwargs[1]["headers"]["Authorization"] == "Bearer test-key"
    assert call_kwargs[1]["data"]["model"] == "whisper-large-v3"
    assert call_kwargs[1]["data"]["language"] == "es"


def test_groq_http_error_raises_stt_error():
    import httpx
    p = GroqProvider(api_key="bad-key", model="whisper-large-v3")

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_client.post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_resp
        )

        with pytest.raises(STTError, match="401"):
            p.transcribe(DUMMY_WAV)


# ── OpenAI Provider ───────────────────────────────────────────────────────────

def test_openai_request_uses_openai_endpoint():
    p = OpenAIProvider(api_key="test-key", model="whisper-1")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"text": "hello world"}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        result = p.transcribe(DUMMY_WAV, language="en")

    assert result == "hello world"
    url = mock_client.post.call_args[0][0]
    assert "openai.com" in url
