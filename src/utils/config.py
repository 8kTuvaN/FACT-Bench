"""Configuration loader for FACT-Bench.

Loads API keys from environment variables / .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_api_key(provider: str) -> str:
    """Get API key for a provider. Raises ValueError if not set."""
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "together": "TOGETHER_API_KEY",
    }
    env_var = key_map.get(provider)
    if env_var is None:
        raise ValueError(f"Unknown provider: {provider}")
    key = os.getenv(env_var, "")
    if not key or "xxx" in key:
        raise ValueError(
            f"{env_var} is not set. Copy .env.example to .env and add your API key."
        )
    return key


def get_base_url(provider: str) -> str | None:
    """Get base URL override for a provider."""
    url_map = {
        "openai": "OPENAI_BASE_URL",
        "deepseek": "DEEPSEEK_BASE_URL",
        "together": "TOGETHER_BASE_URL",
    }
    env_var = url_map.get(provider)
    if env_var is None:
        return None
    return os.getenv(env_var) or None


def get_project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT
