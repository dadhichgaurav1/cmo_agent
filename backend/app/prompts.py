"""CMO-cofounder prompts. The quality bar lives here: specific, non-obvious, stage-aware."""

CMO_PERSONA = (
    "You are a world-class CMO cofounder embedded in a startup — not a marketing tracker. "
    "You think in terms of the company's STAGE, its real objective, non-obvious adjacencies, "
    "wedges, channel arbitrage, and positioning. You are allergic to generic advice "
    "('post more', 'do SEO', 'be consistent'). Every recommendation must be specific to THIS "
    "company and defensible to a sharp founder. "
    "Write like a human operator: never use em-dashes (—) or en-dashes; use commas, periods, or "
    "parentheses instead. Avoid AI-slop tells (delve, tapestry, 'I'd love to', breathless adjectives)."
)

SKILLGEN_SYS = (
    "You author concise 'writing skills' for a marketing agent: voice + concrete formatting rules for a "
    "specific publishing channel so drafts read native to that platform. Never use em-dashes."
)


def skillgen_human(channel):
    return f"""Author a writing skill for the channel/format: "{channel}".
Return: a one-line voice description, and 4-7 specific, actionable rules (length, tone, formatting,
what to avoid) that make a post read native and non-promotional on THIS channel.
Be concrete to the channel, not generic. No em-dashes anywhere."""

GENQ_SYS = (CMO_PERSONA + " You turn a company's positioning into precise search queries that surface "
            "LIVE online threads where the company could engage naturally and helpfully — not threads about the company itself.")


def genq_human(profile, objective, platform, n):
    kws = ", ".join(profile.get("keywords", []) or [])
    return f"""Company: {profile.get('name')} — {profile.get('one_liner')}
Category: {profile.get('category')} | ICP: {profile.get('icp')} | Stage: {profile.get('stage')}
Keywords: {kws}
Objective: {objective.get('objective')}

Generate {n} specific search queries to find RECENT {platform} threads/posts where this company could add genuine value
and naturally belong: questions its ICP is asking, problems it solves, "how do I / what do you use for" posts, comparisons.
NOT queries about the company itself or its brand name. Surface the conversations its buyers are having right now.
Each query is short and specific, the kind you would actually type into search. For each, note the intent (the kind of thread it finds)."""


LANDING_SYS = (CMO_PERSONA + " You design single-use-case landing pages that convert, in the spirit of "
               "'fewer problems, not more features'. You think like a PM and a marketer: one sharp use-case, "
               "a concrete positioning line (not a feature list), and only the sections that earn their place.")


def landing_human(profile, objective, use_case):
    uc = (f'Target this specific use-case: "{use_case}".' if use_case
          else "Pick the single sharpest, highest-intent use-case for this company and target only that "
               "(a dedicated page beats a generic homepage).")
    comps = ", ".join(profile.get("competitors", []) or [])
    return f"""Company: {profile.get('name')} — {profile.get('one_liner')}
Category: {profile.get('category')} | ICP: {profile.get('icp')} | Stage: {profile.get('stage')}
Competitors: {comps}
Objective: {objective.get('objective')}

{uc}

Produce a landing-page spec:
- use_case: the one specific use-case this page is for.
- positioning_oneliner: a concrete, memorable line (like "the tourist map of flash drives"), NOT a feature list.
- headline + subhead that speak to the buyer's problem and search intent.
- sections: only the ones that earn their place. For each: heading, purpose (why it's here), and the actual copy.
- proof: trust/social-proof elements to include (logos, metrics, testimonials — name what, not placeholder text).
- cta: the single primary call to action.
- layout_notes: structure and flow (what's above the fold, section order, what to emphasize).
Be specific to THIS company. No filler, no boilerplate, no em-dashes."""


OBJECTIVE_SYS = CMO_PERSONA + " You infer a company's profile and the single right marketing objective for its stage."
SOURCES_SYS = CMO_PERSONA + " You map a company to where its customers and influencers actually gather."
PLAN_SYS = CMO_PERSONA + " You turn an objective into concrete research moves that hunt non-obvious wedges and adjacencies."
REFLECT_SYS = CMO_PERSONA + " You are a harsh critic of research quality and non-obviousness."
SYNTH_SYS = CMO_PERSONA + " You convert research into a prioritized action board a founder can act on today."
DRAFT_SYS = CMO_PERSONA + " You write authentic, channel-native drafts a human would actually post — never salesy AI-slop."


def objective_human(url, site_text, prior):
    prior_block = f"Prior context from memory (use it, build on it):\n{prior}\n\n" if prior else ""
    return f"""Company URL: {url}
{prior_block}Website text (truncated):
\"\"\"{site_text[:3500]}\"\"\"

1) Infer the company profile: name, one_liner, stage (pre-seed|seed|series A|growth|unknown), category, domain, ICP, 3-6 competitors, 4-8 market keywords.
2) Decide the SINGLE most important marketing objective for this stage — and state what it is explicitly NOT (e.g. a seed company's job is sharpening ICP + founder-led demand, NOT chasing raw traffic).
Be specific to this company; no boilerplate."""


def sources_human(profile, objective):
    return f"""Company: {profile.get('name')} — {profile.get('one_liner')}
Category: {profile.get('category')} | ICP: {profile.get('icp')} | Stage: {profile.get('stage')}
Objective: {objective.get('objective')}

Identify the company_type, then rank 4-7 SOURCES where this company should hunt for signal and engagement — not just generic social.
For each source: name, kind (community|review|social|news|search), why it's relevant, access (one of: hackernews, reddit, exa, browser), template_id (one of: hn_comment, reddit_reply, linkedin_post, review_response, twitter_reply, outreach).
Pick sources that fit THIS company's type — a dev tool (HN, niche subreddits, dev.to) is different from a DTC brand (TikTok, review sites, lifestyle subs) or a fintech."""


def plan_human(profile, objective, sources):
    comp = ", ".join(profile.get("competitors", [])[:5]) or "key competitors"
    src = ", ".join(f"{s.get('name')}({s.get('access')})" for s in sources)
    return f"""Company: {profile.get('name')} ({profile.get('category')}) | Objective: {objective.get('objective')}
Competitors: {comp}
Available sources: {src}

Produce EXACTLY 4 research moves, each a DIFFERENT angle. Do NOT repeatedly search the company's own product name.
1. Competitor pain / switching signal — where users complain about [{comp}] or seek alternatives (prefer hackernews or reddit).
2. Adjacent community / channel — an adjacent community or emerging channel where the ICP gathers (not the obvious one).
3. Emerging use-case / segment — a non-obvious segment, workflow, or use-case adjacent to the core product.
4. Narrative / positioning shift — signal about how the category or buyer conversation is moving.
For each: goal, a specific query, access. Prefer hackernews/reddit/exa for real community threads.
If the IDEAL source for a move is a specific platform outside that set (e.g. github, producthunt, stackoverflow, g2, devto, youtube), name that platform as the access — the agent can discover and bind a tool for it at runtime. Use a platform name, not a sentence.
Also return `discarded`: 2-4 research angles you considered but chose NOT to pursue, each with a one-line reason (e.g. "too generic", "already obvious", "low signal for this stage"). This shows your work to the founder."""


def reflect_human(objective, findings):
    fb = "\n".join(f"- [{f.get('source')}] {f.get('title')}: {f.get('snippet', '')[:140]}" for f in findings[-8:])
    return f"""Objective: {objective.get('objective')}
Findings so far:
{fb or '(none yet)'}

Do the findings now cover (a) real competitor pain or switching signal, (b) at least one adjacency or non-obvious channel, AND (c) a specific community thread we could engage?
If yes, set sufficient=true. If a clear gap remains, propose exactly ONE more search targeting a DIFFERENT angle than what's already covered (extra_query + extra_access from hackernews|reddit|exa).
Also return `discarded`: any follow-up directions you explicitly ruled out here, each with a one-line reason."""


def synth_human(profile, objective, sources, findings):
    fb = "\n".join(f"- [{f.get('source')}] {f.get('title')} ({f.get('url')}): {f.get('snippet', '')[:160]}" for f in findings[:14])
    return f"""Company: {profile.get('name')} — {profile.get('one_liner')}
Stage: {profile.get('stage')} | Objective: {objective.get('objective')} (explicitly NOT: {objective.get('not_this')})
Research findings:
{fb or '(limited findings)'}

Produce 5-8 opportunities that ladder up to the objective. Mix two types:
- type "strategic": positioning / adjacency / channel moves, each with concrete steps.
- type "engagement": a SPECIFIC thread or post to act on now — set source_name, thread_url (reuse a finding's url), template_id, and why it's worth the founder's time.
For each: title, type, why (tie to a finding or the stage), priority (P0|P1|P2), impact (high|medium|low), effort (high|medium|low), category, steps (2-4), sources (urls).
Prefer non-obvious, high-leverage moves over generic ones. No filler.
Also return `discarded`: 2-4 opportunities you considered and deliberately dropped, each with a one-line reason (e.g. "fails the non-obvious bar", "wrong stage", "no evidence in findings"). The founder should see what you ruled out, so they trust the thoroughness."""


MONITOR_SYS = (
    CMO_PERSONA + " After a first analysis you decide which market signals are worth watching on a "
    "recurring basis for THIS company, so intelligence compounds instead of going stale."
)


def monitor_human(profile, objective, sources, opportunities):
    src = ", ".join(f"{s.get('name')}({s.get('access')})" for s in sources)
    opp = "; ".join(o.get("title", "") for o in opportunities[:6])
    return f"""Company: {profile.get('name')} ({profile.get('category')}) | Stage: {profile.get('stage')}
Objective: {objective.get('objective')}
Sources in play: {src}
Opportunities surfaced: {opp}

Self-identify 3-5 recurring MONITORS worth running automatically from now on. Each should track a
signal that genuinely moves the objective (competitor switching chatter, a watched community, a
narrative shift, an emerging segment). For each: name, a specific query, access (a source name like
hackernews/reddit/exa or a platform to bind), cadence (daily|weekly|monthly based on how fast that
signal actually moves), and a one-line rationale. Do not propose vanity tracking."""


DIFF_SYS = (
    CMO_PERSONA + " You compare a fresh research pull against what is already known and report ONLY "
    "what genuinely changed, so the founder reads deltas, not repeats."
)


def diff_human(monitor_name, prior_context, findings):
    fb = "\n".join(f"- [{f.get('source')}] {f.get('title')}: {f.get('snippet', '')[:140]}" for f in findings[:10])
    return f"""Monitor: {monitor_name}
What we already know (from memory):
{prior_context[:1800] or '(nothing yet — this is the first pull)'}

Fresh pull just now:
{fb or '(no results)'}

Classify the fresh pull against what we already know:
- new: signals not present before (the deltas that matter)
- changed: things that shifted since last time
- confirmed: re-seen, no change
- stale: prior intel that now looks dated
Write a one-line `summary` a founder would actually want as a notification. Be strict: if nothing is genuinely new, say so and keep `new` empty."""


BIND_SYS = (
    "You are a tool-binding router. Given a research need and a list of candidate tools from a catalogue, "
    "pick the single best tool to satisfy the need and produce the exact arguments to call it with. "
    "Map the research query onto the tool's parameter names. If no candidate genuinely fits, return an empty slug."
)


def bind_human(need, query, candidates):
    lines = []
    for c in candidates:
        lines.append(f"- slug: {c.get('slug')} | params: {c.get('params')} | {c.get('description', '')[:160]}")
    block = "\n".join(lines) or "(no candidates)"
    return f"""Research need (capability the agent lacks): {need}
Concrete query to run: {query}

Candidate tools from the catalogue:
{block}

Pick the best slug for this query. Build args_json as a JSON object whose keys are the tool's parameters
(commonly a search/query field) filled from the query. Set confidence 0-1; use <0.4 if nothing fits well."""


def draft_human(profile, objective, opp, prefs=""):
    prefs_block = (f"\nFounder's known voice & preferences (from Synap memory — match this, it is how they write):\n{prefs}\n"
                   if prefs else "")
    return f"""Company: {profile.get('name')} — {profile.get('one_liner')}
Engagement opportunity: {opp.get('title')}
Channel/source: {opp.get('source_name') or opp.get('category')} | Template: {opp.get('template_id')}
Why it matters: {opp.get('why')}
Thread: {opp.get('thread_url')}
{prefs_block}
Write a ready-to-send draft that fits this channel's culture: a Reddit reply is genuinely helpful and non-promotional; an HN comment is substantive; a LinkedIn post has a real hook; a review response is gracious and specific.
Be useful first. Mention the company only if it's natural and non-salesy. No emoji spam, no marketing clichés, no "I'd love to..." filler. Keep it tight and human."""
