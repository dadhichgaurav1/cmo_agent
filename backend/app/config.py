import os

from dotenv import load_dotenv

load_dotenv()


def _get(key: str) -> str:
    return os.getenv(key, "").strip()


ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")
# Pioneer: sponsor inference gateway (Anthropic/OpenAI-compatible). Primary LLM backend
# when present; native Anthropic/OpenAI are used as fallback. Scoped to this process only.
PIONEER_API_KEY = _get("PIONEER_API_KEY")
PIONEER_BASE_URL = _get("PIONEER_BASE_URL") or "https://api.pioneer.ai"
EXA_API_KEY = _get("EXA_API_KEY")
COMPOSIO_API_KEY = _get("COMPOSIO_API_KEY")
SYNAP_API_KEY = _get("SYNAP_API_KEY")
SYNAP_BASE_URL = _get("SYNAP_BASE_URL")
BROWSERBASE_API_KEY = _get("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = _get("BROWSERBASE_PROJECT_ID")
# Optional remote catalogue of per-channel writing skills (Addendum 2). When unset, the agent
# falls back to generating-and-caching a skill for any unknown channel at runtime.
SKILLS_CATALOG_URL = _get("SKILLS_CATALOG_URL")


def has(value: str) -> bool:
    return bool(value and value.strip())
