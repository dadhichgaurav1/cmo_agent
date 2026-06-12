"""Addendum 2 — the hard guarantee: no generated content ships with em-dashes.

Two layers:
  - humanize(text): deterministic scrub of a single string (dashes + spacing tidy).
  - scrub(obj): recursively humanize every string field of a model / dict / list, so
    structured outputs (objective.reasoning, opportunity.why, steps, drafts) are clean too.

Voice-level humanizing (operator tone, anti-slop) is the *humanizer skill*'s job (skills.py);
this module only enforces the mechanical, always-true rule.
"""
import re

try:
    from pydantic import BaseModel
except Exception:  # pragma: no cover
    BaseModel = ()  # type: ignore

# digit – digit  -> hyphenated range (e.g. "10–20" -> "10-20")
_RANGE = re.compile(r"(?<=\d)\s*[—–]\s*(?=\d)")
# any other em/en dash (or the typed "--") -> comma break, the safe universal replacement
_DASH = re.compile(r"\s*(?:—|–|--)\s*")
_DOUBLE_COMMA = re.compile(r",\s*,+")
_SPACE_COMMA = re.compile(r"\s+,")
_MULTISPACE = re.compile(r"[ \t]{2,}")


def humanize(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    if "—" not in text and "–" not in text and "--" not in text:
        # nothing to do beyond cheap whitespace tidy
        return _MULTISPACE.sub(" ", text)
    t = _RANGE.sub("-", text)
    t = _DASH.sub(", ", t)
    t = _DOUBLE_COMMA.sub(",", t)
    t = _SPACE_COMMA.sub(",", t)
    t = _MULTISPACE.sub(" ", t)
    return t


def scrub(obj):
    """Recursively humanize every string in a pydantic model / dict / list. Mutates pydantic
    models in place (v2 models are mutable) and returns the cleaned object."""
    if isinstance(obj, str):
        return humanize(obj)
    if isinstance(obj, BaseModel):
        for name in obj.__class__.model_fields:
            setattr(obj, name, scrub(getattr(obj, name)))
        return obj
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(scrub(v) for v in obj)
    return obj
