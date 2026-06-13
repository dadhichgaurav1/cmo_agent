"""#4 — turn a landing-page spec into a single, copyable, stack-agnostic Claude Code prompt.

The handoff tenet: StratCMO supplies the PM+marketer thinking (the spec, via LLM); the founder's
OWN coding agent supplies the stack-specific code. So this is pure string assembly, not an LLM
call — deterministic, free, and instant when the founder clicks "generate prompt".
"""
from typing import Optional


def claude_prompt(spec: dict, company: str = "") -> str:
    spec = spec or {}
    name = company or "the product"
    sections = spec.get("sections", []) or []
    proof = spec.get("proof", []) or []

    lines = []
    lines.append(f"Build a single-use-case landing page for {name} in THIS repo.")
    lines.append("")
    lines.append("First, inspect the repo and adapt to whatever stack, framework, routing, styling system, "
                 "and component conventions you find. Make NO assumptions about React/Next/Tailwind/etc. "
                 "Match the code that is already here. If the repo has a design system or existing pages, reuse them.")
    lines.append("")
    lines.append("This is a conversion-focused page for ONE specific use-case, not a generic homepage. "
                 "Here is the page to build and why each part exists:")
    lines.append("")
    if spec.get("use_case"):
        lines.append(f"USE-CASE: {spec['use_case']}")
    if spec.get("positioning_oneliner"):
        lines.append(f"POSITIONING (the throughline, keep it concrete): {spec['positioning_oneliner']}")
    lines.append("")
    if spec.get("headline"):
        lines.append(f"HEADLINE: {spec['headline']}")
    if spec.get("subhead"):
        lines.append(f"SUBHEAD: {spec['subhead']}")
    if spec.get("cta"):
        lines.append(f"PRIMARY CTA: {spec['cta']}")
    lines.append("")

    if sections:
        lines.append("SECTIONS (in order; include only these, each earns its place):")
        for i, s in enumerate(sections, 1):
            head = s.get("heading", f"Section {i}")
            lines.append(f"{i}. {head}")
            if s.get("purpose"):
                lines.append(f"   - purpose: {s['purpose']}")
            if s.get("content"):
                lines.append(f"   - copy: {s['content']}")
        lines.append("")

    if proof:
        lines.append("PROOF / TRUST elements to include (use real assets where they exist, do not invent metrics):")
        for p in proof:
            lines.append(f"- {p}")
        lines.append("")

    if spec.get("layout_notes"):
        lines.append(f"LAYOUT & FLOW: {spec['layout_notes']}")
        lines.append("")

    lines.append("Requirements:")
    lines.append("- Use the exact copy above; tighten only for fit, do not pad with filler.")
    lines.append("- Responsive and accessible. Match the repo's existing visual language.")
    lines.append("- Wire the primary CTA to the existing signup/checkout/contact path if one exists; "
                 "otherwise leave a clearly-marked TODO.")
    lines.append("- Add the route/page and link it where new pages are normally linked. Do not touch unrelated code.")
    lines.append("- When done, tell me the file(s) you added and how to preview the page locally.")
    return "\n".join(lines)
