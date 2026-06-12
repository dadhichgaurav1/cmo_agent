"""Multi-model router over LangChain chat models. Best model per task; model surfaced in the trace."""
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
    if provider == "openai" and not config.has(config.OPENAI_API_KEY):
        return DEFAULT
    return provider, model


def get_model(task: str, temperature: float = 0.3, max_tokens: int = 4096):
    provider, model = route(task)
    key = (provider, model, temperature, max_tokens)
    if key not in _cache:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            _cache[key] = ChatAnthropic(
                model=model,
                api_key=config.ANTHROPIC_API_KEY,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=120,
            )
        else:
            from langchain_openai import ChatOpenAI
            _cache[key] = ChatOpenAI(
                model=model,
                api_key=config.OPENAI_API_KEY,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=120,
            )
    return _cache[key], model


async def run_structured(task, system, human, schema, temperature: float = 0.3, max_tokens: int = 4096):
    """Returns (pydantic_instance, model_name)."""
    model, name = get_model(task, temperature, max_tokens)
    structured = model.with_structured_output(schema)
    result = await structured.ainvoke([("system", system), ("human", human)])
    return result, name


async def run_text(task, system, human, temperature: float = 0.4, max_tokens: int = 1500):
    """Returns (text, model_name)."""
    model, name = get_model(task, temperature, max_tokens)
    resp = await model.ainvoke([("system", system), ("human", human)])
    content = resp.content
    if isinstance(content, list):  # some providers return content blocks
        content = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return content, name
