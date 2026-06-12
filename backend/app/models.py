"""Multi-model router over LangChain chat models. Best model per task; model surfaced in the trace.

Inference is served through Pioneer (sponsor gateway) when PIONEER_API_KEY is set, with the
native Anthropic/OpenAI providers used as fallback if a Pioneer call fails. The trace label is
prefixed ``pioneer/`` when Pioneer served the request so it is visible in the demo.
"""
from typing import Tuple

from app import config

# task -> (provider, model)
ROUTING = {
    "objective":       ("anthropic", "claude-sonnet-4-6"),
    "source_strategy": ("anthropic", "claude-sonnet-4-6"),
    "plan":            ("anthropic", "claude-sonnet-4-6"),
    "reflect":         ("anthropic", "claude-sonnet-4-6"),
    "synthesize":      ("anthropic", "claude-sonnet-4-6"),
    "draft":           ("anthropic", "claude-haiku-4-5-20251001"),
    "extract":         ("anthropic", "claude-haiku-4-5-20251001"),
    "chat":            ("openai",    "gpt-4o"),
}
DEFAULT = ("anthropic", "claude-sonnet-4-6")

_cache = {}


def route(task: str) -> Tuple[str, str]:
    provider, model = ROUTING.get(task, DEFAULT)
    # If we can reach OpenAI models neither via Pioneer nor a native key, use the Anthropic default.
    if provider == "openai" and not (config.has(config.PIONEER_API_KEY) or config.has(config.OPENAI_API_KEY)):
        return DEFAULT
    return provider, model


def _build(provider: str, model: str, temperature: float, max_tokens: int, pioneer: bool):
    """Construct a LangChain chat client for the given provider, pointed at Pioneer or native."""
    common = dict(model=model, temperature=temperature, max_tokens=max_tokens, timeout=120)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        if pioneer:  # Pioneer exposes an Anthropic-compatible surface
            return ChatAnthropic(api_key=config.PIONEER_API_KEY, base_url=config.PIONEER_BASE_URL, **common)
        return ChatAnthropic(api_key=config.ANTHROPIC_API_KEY, **common)
    from langchain_openai import ChatOpenAI
    if pioneer:  # ...and an OpenAI-compatible /v1 surface
        return ChatOpenAI(api_key=config.PIONEER_API_KEY, base_url=config.PIONEER_BASE_URL.rstrip("/") + "/v1", **common)
    return ChatOpenAI(api_key=config.OPENAI_API_KEY, **common)


def get_model(task: str, temperature: float = 0.3, max_tokens: int = 4096, pioneer: bool = False):
    provider, model = route(task)
    key = (provider, model, temperature, max_tokens, pioneer)
    if key not in _cache:
        _cache[key] = _build(provider, model, temperature, max_tokens, pioneer)
    return _cache[key], model


def _attempts() -> Tuple[bool, ...]:
    """Try Pioneer first when configured, then fall back to the native provider."""
    return (True, False) if config.has(config.PIONEER_API_KEY) else (False,)


def _label(name: str, pioneer: bool) -> str:
    return f"pioneer/{name}" if pioneer else name


async def run_structured(task, system, human, schema, temperature: float = 0.3, max_tokens: int = 4096):
    """Returns (pydantic_instance, model_name). Pioneer primary, native fallback."""
    last = None
    for pioneer in _attempts():
        try:
            model, name = get_model(task, temperature, max_tokens, pioneer)
            structured = model.with_structured_output(schema)
            result = await structured.ainvoke([("system", system), ("human", human)])
            return result, _label(name, pioneer)
        except Exception as exc:  # noqa: BLE001 - fall through to native provider
            last = exc
    raise last


async def run_text(task, system, human, temperature: float = 0.4, max_tokens: int = 1500):
    """Returns (text, model_name). Pioneer primary, native fallback."""
    last = None
    for pioneer in _attempts():
        try:
            model, name = get_model(task, temperature, max_tokens, pioneer)
            resp = await model.ainvoke([("system", system), ("human", human)])
            content = resp.content
            if isinstance(content, list):  # some providers return content blocks
                content = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            return content, _label(name, pioneer)
        except Exception as exc:  # noqa: BLE001 - fall through to native provider
            last = exc
    raise last
