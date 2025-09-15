"""
Configuration management for AI Coaching Framework.
Loads settings from environment variables and provides defaults.
"""

import os
from typing import Dict, Any
from pathlib import Path

# Try to load environment variables, but don't fail if dotenv is not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, likely in Streamlit Cloud
    pass

# Try to get Streamlit secrets if available
def get_streamlit_secret(key: str, default: str = '') -> str:
    """Get secret from Streamlit secrets if available."""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return str(st.secrets[key])
    except (ImportError, Exception):
        pass
    return os.getenv(key, default)

def get_boolean_setting(key: str, default: bool = True) -> bool:
    """Get boolean setting from environment or Streamlit secrets."""
    value = get_streamlit_secret(key, str(default).lower())
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == 'true'
    return default

class Config:
    """Configuration settings for the coaching framework."""

    # API Configuration
    OPENAI_API_KEY: str = get_streamlit_secret('OPENAI_API_KEY', '')
    DEFAULT_MODEL: str = get_streamlit_secret('DEFAULT_MODEL', 'gpt-5')
    REASONING_EFFORT: str = get_streamlit_secret('REASONING_EFFORT', 'medium')
    VERBOSITY: str = get_streamlit_secret('VERBOSITY', 'medium')
    MAX_TOKENS: int = int(get_streamlit_secret('MAX_TOKENS', '4000'))
    # Note: GPT-5 does not support temperature parameter

    # Processing Settings
    DEFAULT_INTERVAL_MINUTES: float = float(get_streamlit_secret('DEFAULT_INTERVAL_MINUTES', '2'))
    MAX_CONTEXT_WINDOWS: int = int(get_streamlit_secret('MAX_CONTEXT_WINDOWS', '3'))
    RETRY_ATTEMPTS: int = int(get_streamlit_secret('RETRY_ATTEMPTS', '3'))
    TIMEOUT_MS: int = int(get_streamlit_secret('TIMEOUT_MS', '60000'))

    # Output Settings
    OUTPUT_DIR: str = get_streamlit_secret('OUTPUT_DIR', 'outputs')
    LOGS_DIR: str = get_streamlit_secret('LOGS_DIR', 'logs')
    ENABLE_LOGGING: bool = get_boolean_setting('ENABLE_LOGGING', True)
    AUTO_SUMMARY: bool = get_boolean_setting('AUTO_SUMMARY', True)

    # Streamlit Settings
    STREAMLIT_PORT: int = int(get_streamlit_secret('STREAMLIT_PORT', '8501'))
    DEBUG_MODE: bool = get_boolean_setting('DEBUG_MODE', False)

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        Path(cls.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(cls.LOGS_DIR).mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate_api_key(cls) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(cls.OPENAI_API_KEY and cls.OPENAI_API_KEY.strip())

    @classmethod
    def get_api_settings(cls) -> Dict[str, Any]:
        """Get API settings as dictionary."""
        return {
            'model_name': cls.DEFAULT_MODEL,
            'reasoning_effort': cls.REASONING_EFFORT,
            'verbosity': cls.VERBOSITY,
            'max_tokens': cls.MAX_TOKENS,
            # Note: temperature removed - not supported by GPT-5
        }

    @classmethod
    def update_setting(cls, key: str, value: Any) -> None:
        """Update a configuration setting."""
        if hasattr(cls, key.upper()):
            setattr(cls, key.upper(), value)
        else:
            raise ValueError(f"Unknown setting: {key}")

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Export all settings as dictionary."""
        return {
            'openai_api_key': '***CONFIGURED***' if cls.OPENAI_API_KEY else '',
            'default_model': cls.DEFAULT_MODEL,
            'reasoning_effort': cls.REASONING_EFFORT,
            'verbosity': cls.VERBOSITY,
            'max_tokens': cls.MAX_TOKENS,
            # Note: temperature removed - not supported by GPT-5
            'default_interval_minutes': cls.DEFAULT_INTERVAL_MINUTES,
            'max_context_windows': cls.MAX_CONTEXT_WINDOWS,
            'retry_attempts': cls.RETRY_ATTEMPTS,
            'timeout_ms': cls.TIMEOUT_MS,
            'output_dir': cls.OUTPUT_DIR,
            'enable_logging': cls.ENABLE_LOGGING,
            'auto_summary': cls.AUTO_SUMMARY,
        }

# Initialize directories on import
Config.ensure_directories()