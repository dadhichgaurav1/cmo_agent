import os

from dotenv import load_dotenv

load_dotenv()


def _get(key: str) -> str:
    return os.getenv(key, "").strip()


ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")
EXA_API_KEY = _get("EXA_API_KEY")
COMPOSIO_API_KEY = _get("COMPOSIO_API_KEY")
SYNAP_API_KEY = _get("SYNAP_API_KEY")
SYNAP_BASE_URL = _get("SYNAP_BASE_URL")
BROWSERBASE_API_KEY = _get("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = _get("BROWSERBASE_PROJECT_ID")


def has(value: str) -> bool:
    return bool(value and value.strip())
