import os
from .base import STTProvider, STTError
from .groq_provider import GroqProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider

_PROVIDERS = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}

# Env var names per provider (loaded from .env via python-dotenv)
_ENV_KEYS = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


_KEYRING_SERVICE = "gliflow"


def get_api_key(provider: str, config: dict) -> str:
    """Return API key. Priority: env var → OS keyring → config.json."""
    env_var = _ENV_KEYS.get(provider, "")
    if key := os.environ.get(env_var):
        return key
    try:
        import keyring
        if key := keyring.get_password(_KEYRING_SERVICE, provider):
            return key
    except Exception:
        pass
    return config["provider"].get(provider, {}).get("api_key", "")


def save_api_key_to_keyring(provider: str, api_key: str) -> None:
    """Save an API key to the OS keyring. Deletes entry if api_key is empty."""
    import keyring
    if api_key:
        keyring.set_password(_KEYRING_SERVICE, provider, api_key)
    else:
        try:
            keyring.delete_password(_KEYRING_SERVICE, provider)
        except keyring.errors.PasswordDeleteError:
            pass


def get_api_key_source(provider: str, config: dict) -> str:
    """Return where the key comes from: 'env', 'keyring', 'config', or 'none'."""
    env_var = _ENV_KEYS.get(provider, "")
    if os.environ.get(env_var):
        return "env"
    try:
        import keyring
        if keyring.get_password(_KEYRING_SERVICE, provider):
            return "keyring"
    except Exception:
        pass
    if config["provider"].get(provider, {}).get("api_key", ""):
        return "config"
    return "none"


def get_provider(config: dict) -> STTProvider:
    active = config["provider"]["active"]
    cfg = config["provider"].get(active, {})
    cls = _PROVIDERS.get(active)
    if cls is None:
        raise ValueError(f"Unknown STT provider: {active!r}")
    api_key = get_api_key(active, config)
    return cls(api_key=api_key, model=cfg.get("model", ""))


__all__ = [
    "STTProvider", "STTError",
    "GroqProvider", "OpenAIProvider", "GeminiProvider",
    "get_provider", "get_api_key", "get_api_key_source", "save_api_key_to_keyring",
]
