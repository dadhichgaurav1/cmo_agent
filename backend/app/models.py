"""Multi-model router: picks the best model per task and dispatches the call.

The whole point of the demo's "mix of models" story lives here: each task type
maps to a provider+model, and we surface the chosen model in the agent trace.
"""
import json
import re
from typing import Optional, Tuple

from app import config

# task -> (provider, model)
ROUTING = {
    "detect":     ("anthropic", "claude-sonnet-4-6"),
    "plan":       ("anthropic", "claude-sonnet-4-6"),
    "synthesize": ("anthropic", "claude-sonnet-4-6"),
    "skill_gen":  ("anthropic", "claude-sonnet-4-6"),
    "extract":    ("anthropic", "claude-haiku-4-5-20251001"),
    "summarize":  ("anthropic", "claude-haiku-4-5-20251001"),
    "chat":       ("openai",    "gpt-4o"),
}
DEFAULT = ("anthropic", "claude-sonnet-4-6")

_anthropic = None
_openai = None


def _get_anthropic():
    global _anthropic
    if _anthropic is None:
        from anthropic import AsyncAnthropic
        _anthropic = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _anthropic


def _get_openai():
    global _openai
    if _openai is None:
        from openai import AsyncOpenAI
        _openai = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _openai


def route(task: str) -> Tuple[str, str]:
    provider, model = ROUTING.get(task, DEFAULT)
    # fall back to Anthropic if OpenAI key isn't present
    if provider == "openai" and not config.has(config.OPENAI_API_KEY):
        return DEFAULT
    return provider, model


async def complete(
    task: str,
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 1500,
) -> Tuple[str, str]:
    """Returns (text, model_used)."""
    provider, model = route(task)
    if provider == "anthropic":
        client = _get_anthropic()
        msg = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system or "You are a precise, concise assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            b.text for b in msg.content if getattr(b, "type", "") == "text"
        )
    else:
        client = _get_openai()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = await client.chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens
        )
        text = resp.choices[0].message.content or ""
    return text, model


def parse_json(text: str):
    """Tolerant JSON extraction from a model response."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    for open_c, close_c in (("[", "]"), ("{", "}")):
        i, j = text.find(open_c), text.rfind(close_c)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(text[i:j + 1])
            except Exception:
                continue
    return None
