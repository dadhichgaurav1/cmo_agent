"""Addendum 2 — per-channel writing skills with runtime discovery.

Because we can't predict what kind of company the agent will be pointed at, we can't know which
publishing channels it will need to write for. So skills resolve at runtime:

    local pack (app/skills/*.json)  ->  remote catalogue (SKILLS_CATALOG_URL)  ->  generate-and-cache

The humanizer skill is always applied. A per-channel skill (reddit_reply, hn_comment, linkedin_post,
or anything generated on the fly like tiktok_caption / g2_review_response) is layered on top so each
draft reads native to its platform. Skills are cached in the shared capability registry.
"""
import json
import os
import re
from typing import List, Optional

import httpx

from app import capabilities, config, models, prompts
from app.schemas import Capability, SkillSpec

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills")
_CACHE: dict[str, SkillSpec] = {}


def _slug(channel: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", (channel or "").lower()).strip("_") or "outreach"


def _load_local(name: str) -> Optional[SkillSpec]:
    path = os.path.join(SKILLS_DIR, name + ".json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return SkillSpec(**json.load(f))
    except Exception:
        return None


def _save_local(spec: SkillSpec) -> None:
    try:
        os.makedirs(SKILLS_DIR, exist_ok=True)
        with open(os.path.join(SKILLS_DIR, spec.name + ".json"), "w") as f:
            json.dump(spec.model_dump(), f, indent=2)
    except Exception:
        pass


async def _from_catalog(name: str) -> Optional[SkillSpec]:
    base = config.SKILLS_CATALOG_URL
    if not base:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(base.rstrip("/") + f"/{name}.json")
            r.raise_for_status()
            return SkillSpec(**r.json())
    except Exception:
        return None


async def _generate(name: str, channel: str) -> Optional[SkillSpec]:
    try:
        spec, _ = await models.run_structured(
            "extract", prompts.SKILLGEN_SYS, prompts.skillgen_human(channel), SkillSpec,
            temperature=0.3, max_tokens=700,
        )
    except Exception:
        return None
    spec.name = name
    if not spec.applies_to:
        spec.applies_to = channel
    if not spec.rules:
        return None
    _save_local(spec)  # cache so we never regenerate the same channel
    return spec


async def resolve_skill(channel: str, emit=None) -> Optional[SkillSpec]:
    """Resolve a writing skill for a channel: local -> remote -> generate. Caches + registers it."""
    name = _slug(channel)
    if name in _CACHE:
        return _CACHE[name]

    source = "local"
    spec = _load_local(name)
    if spec is None:
        spec = await _from_catalog(name)
        source = "catalog" if spec else source
    generated = False
    if spec is None:
        spec = await _generate(name, channel)
        source, generated = ("generated", True) if spec else (source, False)
    if spec is None:
        return None

    _CACHE[name] = spec
    capabilities.remember_capability(Capability(
        name="skill:" + name, kind="skill", source=source,
        bound_at="runtime" if generated else "plan", why=spec.voice,
        spec=spec.model_dump(),
    ))
    if emit and generated:
        await emit({"type": "skill_bound", "label": f"Generated writing skill: {name}",
                    "model": "skillgen", "data": spec.model_dump()})
    elif emit:
        await emit({"type": "skill_bound", "label": f"Applied writing skill: {name}",
                    "model": source, "data": spec.model_dump()})
    return spec


def render(specs: List[Optional[SkillSpec]]) -> str:
    """Render resolved skills into a prompt augmentation block."""
    blocks = []
    for s in specs:
        if not s:
            continue
        rules = "\n".join(f"- {r}" for r in s.rules)
        blocks.append(f"WRITING SKILL ({s.name}) — voice: {s.voice}\n{rules}")
    if not blocks:
        return ""
    return "\n\nApply these writing skills strictly:\n\n" + "\n\n".join(blocks)
