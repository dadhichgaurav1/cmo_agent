"""The autonomous CMO agent loop. Yields trace events as an async generator."""
import time
from typing import Any, AsyncGenerator, Dict, List

from app import models, site, web
from app.memory import memory
from app.schemas import ActionItem, CompanyProfile, ResearchFinding
from app.skills import generate_skill

DETECT_SYS = "You are a sharp startup analyst. You infer a company's profile from its website text."
SYNTH_SYS = (
    "You are a world-class fractional CMO. You turn market research into prioritized, "
    "concrete action items for a founder."
)


def _ev(type_: str, label: str = "", data: Any = None, model: str = "") -> Dict[str, Any]:
    return {"type": type_, "label": label, "data": data, "model": model, "ts": time.time()}


async def run(url: str) -> AsyncGenerator[Dict[str, Any], None]:
    yield _ev("step", "Starting CMO agent")

    prior = await memory.retrieve(url)
    if prior:
        yield _ev("step", "Recalled prior context from Synap memory")

    # 1. Read the founder's own website
    yield _ev("step", "Reading your website", model="claude-haiku-4-5")
    site_text = await site.fetch_site_text(url)
    if not site_text:
        yield _ev("step", "Could not read site; inferring from URL only")

    # 2. Detect stage / category / competitors
    yield _ev("step", "Inferring stage, category & competitors", model="claude-sonnet-4-6")
    detect_prompt = f"""Website URL: {url}
Website text (truncated):
\"\"\"{site_text[:4000]}\"\"\"

Return JSON only with keys:
name, one_liner, stage (pre-seed|seed|series A|growth|unknown), category, domain, icp,
competitors (array of 3-6 company names), keywords (array of 4-8 search keywords for market research).
If unsure, make your best inference."""
    text, model = await models.complete("detect", detect_prompt, system=DETECT_SYS, max_tokens=1200)
    pdata = models.parse_json(text) or {}
    profile = CompanyProfile(
        url=url,
        **{
            k: pdata.get(k)
            for k in ["name", "one_liner", "stage", "category", "domain", "icp", "competitors", "keywords"]
            if pdata.get(k) is not None
        },
    )
    yield _ev("profile", "Company profile", data=profile.model_dump(), model=model)
    await memory.store(url, "profile", profile.model_dump())

    # 3. Research the space with EXA
    yield _ev("step", "Scanning competitors & the space (EXA)", model="exa")
    queries: List[str] = []
    if profile.competitors:
        queries.append(f"{profile.competitors[0]} alternatives competitors {profile.category}")
    queries.append(f"{profile.category or profile.domain} market trends 2026")
    if profile.keywords:
        queries.append(" ".join(profile.keywords[:4]))

    findings: List[ResearchFinding] = []
    for q in queries[:3]:
        for f in await web.exa_search(q, num=4):
            findings.append(f)
            yield _ev("finding", f.title, data=f.model_dump(), model="exa")
    await memory.store(url, "findings", [f.model_dump() for f in findings])

    # 4. Generate a custom CMO skill for this company
    yield _ev("step", "Generating a custom CMO skill", model="claude-sonnet-4-6")
    skill = await generate_skill(profile)
    yield _ev("skill", skill.name, data=skill.model_dump(), model="claude-sonnet-4-6")

    # 5. Synthesize prioritized action items
    yield _ev("step", "Reasoning into prioritized actions", model="claude-sonnet-4-6")
    findings_block = "\n".join(
        f"- {f.title}: {f.snippet[:200]} ({f.url})" for f in findings[:10]
    )
    synth_prompt = f"""Company: {profile.name} — {profile.one_liner}
Stage: {profile.stage} | Category: {profile.category} | ICP: {profile.icp}
Competitors: {', '.join(profile.competitors)}

Apply this custom skill where relevant:
{skill.name}: {skill.prompt}

Market research findings:
{findings_block or '(limited findings)'}

Produce 5-7 prioritized CMO action items. Return JSON only: an array of objects with keys:
title, why (reasoning tied to findings/stage), priority (P0|P1|P2), impact (high|medium|low),
effort (high|medium|low), category (positioning|content|GTM|growth|product-marketing),
steps (array of 2-4 concrete steps), sources (array of urls from findings if relevant).
Order by priority then impact."""
    text, model = await models.complete("synthesize", synth_prompt, system=SYNTH_SYS, max_tokens=2500)
    raw = models.parse_json(text) or []
    items: List[ActionItem] = []
    if isinstance(raw, list):
        for i, d in enumerate(raw):
            if not isinstance(d, dict) or not d.get("title"):
                continue
            d["id"] = str(i + 1)
            d["model_used"] = model
            try:
                items.append(
                    ActionItem(**{k: d.get(k) for k in ActionItem.model_fields if d.get(k) is not None})
                )
            except Exception:
                continue
    yield _ev("action_items", "Prioritized action board", data=[it.model_dump() for it in items], model=model)
    await memory.store(url, "action_items", [it.model_dump() for it in items])

    yield _ev("done", "Done")
