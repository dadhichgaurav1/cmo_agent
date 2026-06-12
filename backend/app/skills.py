"""CMO skill library + live skill generation."""
from app import models
from app.schemas import CompanyProfile, Skill

# A small canned library; the agent also generates one custom skill per company.
CMO_SKILLS = {
    "positioning": "Craft sharp positioning vs named competitors using category, ICP and differentiation.",
    "competitive_teardown": "Tear down competitors' messaging, pricing and GTM; find gaps to exploit.",
    "content_engine": "Design a founder-led content engine matched to the company's stage and ICP.",
    "gtm_channel": "Pick the 1-2 highest-leverage GTM channels for this stage and category.",
}


async def generate_skill(profile: CompanyProfile) -> Skill:
    prompt = f"""You are designing ONE custom CMO skill tailored to this company.

Company: {profile.name} — {profile.one_liner}
Stage: {profile.stage} | Category: {profile.category} | ICP: {profile.icp}
Competitors: {', '.join(profile.competitors[:6])}

Return JSON only:
{{"name": "...", "when_to_use": "...", "prompt": "A reusable instruction the marketing agent can follow for THIS company"}}

Make it specific to the stage and category, not generic."""
    text, _ = await models.complete(
        "skill_gen",
        prompt,
        system="You generate concise, reusable marketing 'skills' as JSON.",
        max_tokens=800,
    )
    data = models.parse_json(text) or {}
    return Skill(
        name=data.get("name") or f"{profile.category or 'Growth'} play",
        when_to_use=data.get("when_to_use", ""),
        prompt=data.get("prompt", ""),
        generated=True,
    )
