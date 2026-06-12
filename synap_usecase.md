# Use-Case Description — CMO Cofounder

This describes our agent's use case so Synap can generate an optimal memory architecture.

## Agent Objective

Our agent is an autonomous **CMO cofounder for startup founders** — not a metrics tracker. Pointed at a company's URL, it:

1. **Determines the right marketing objective for the company's stage** (pre-seed = narrative + design partners; seed = ICP + founder-led demand; Series A = repeatable channels + category ownership). It never assumes "drive traffic."
2. **Hunts adjacencies and non-obvious wedges** a great CMO cofounder would find — adjacent communities, channel arbitrage, positioning shifts, partnership/integration angles, emerging segments — across the web and relevant communities.
3. **Figures out where the company's customers actually are** (a "source-strategy" skill that maps company *type* to the right sources/communities — dev tools → Hacker News/Reddit/dev.to; DTC → TikTok/review sites/niche subreddits; B2B services → LinkedIn/G2/communities).
4. **Produces prioritized, stage-appropriate moves** plus an **engagement radar**: specific threads/posts to act on now, each with a ready-to-send draft that fits that channel's culture (the founder approves and sends — the agent never auto-posts).
5. **Compounds intelligence over time.** Each run recalls everything learned about the company before, so recommendations get sharper week over week, and fresh/time-sensitive signal (competitor moves, trending threads) is surfaced first.

The problem it solves: founders manually scan many sources to stay on top of their space, competitors, and adjacencies, and struggle to turn that into prioritized action. This agent does that continuously, remembers it, and hands back concrete, channel-ready moves.

## Target Users

**Startup founders and early operators/marketers.** Mostly non-marketing-specialist founders (technical or business) who need senior CMO judgment they don't have in-house. Technical level varies widely. Usage is **recurring, not one-off**: a founder returns over days/weeks expecting the agent to remember their company, the objective it set, the competitors and adjacencies it found, which channels matter, and the founder's preferences about tone and tactics. The value grows the more it remembers.

## Task Examples

- **User**: "Analyze resend.com and tell me what to focus on."
  **Agent**: Infers stage (Series A) and the *right* objective (category ownership over raw traffic), maps the relevant sources/communities, surfaces non-obvious adjacencies and wedges, and returns a prioritized board plus an engagement radar with channel-fit drafts. **Remembers** the company profile, the objective, the source strategy, and the findings under the company's memory.

- **User**: "Anything new in our space this week?"
  **Agent**: **Recalls** prior competitor/adjacency context, runs fresh research, and returns only what *changed* since the last run plus new engagement opportunities. Stores the deltas as time-anchored events so recency is preserved.

- **User**: "Draft a reply for that r/SaaS thread — but make it less salesy."
  **Agent**: Drafts a channel-appropriate reply using the source template; **remembers** the founder's tone preference ("less salesy") and applies it to all future drafts.

- **User**: "We just closed a Series B."
  **Agent**: Updates the company's **stage**, shifts the recommended objective accordingly, and records the change as a fact/temporal event that reframes all future recommendations.

- **User**: "Who are our real competitors, and where are our customers hanging out?"
  **Agent**: **Recalls** the accumulated competitor map and source strategy, supplements with fresh research, and returns the competitive + community map. Persists any refinements.

## Behavioral Guidelines

**Do's**:
- Always determine the stage-appropriate objective before recommending tactics.
- Remember, per company: profile, stage, objective history, competitor/adjacency intelligence, source strategy, surfaced opportunities and their outcomes, and the founder's tone/channel preferences — across sessions.
- Prioritize recent, time-anchored signal (competitor moves, trending threads); recency matters daily.
- Produce drafts that fit each channel's norms, and treat every draft as a proposal for human approval.
- Keep every step inspectable and cite sources.

**Don'ts**:
- Never auto-post, send, or publish on the founder's behalf without explicit approval (drafts only).
- Never let one company's intelligence appear in another company's context (strict multi-tenant isolation).
- Never store third-party personal data beyond what's publicly relevant to market intelligence; never store payment or credential data.
- Don't recommend generic "drive more traffic" tactics divorced from the company's stage and objective.
- Don't present stale data as current — always flag the as-of time.

## Role Descriptions

- **Client** (us, the company operating the agent): **the CMO Cofounder product.** Client/world-scope memory holds cross-company marketing knowledge that applies to every tenant — channel norms (what a good Reddit reply vs. LinkedIn post looks like), stage→objective playbooks, general CMO heuristics.
- **Customer** (the tenant): **the specific startup being analyzed** — e.g., `customer_id = "resend"`. This is the compounding "market brain": everything specific to that company (profile, stage, objective history, competitors, adjacencies, source strategy, opportunities, drafts, outcomes) lives at customer scope. **One Synap customer per company we run the CMO Cofounder for.**
- **User**: **the founder or operator** chatting with the agent for that company. User-scope memory holds that individual's preferences — preferred channels, tone/voice, draft styles they approved or rejected, objectives they endorse.

(This maps directly onto Synap's USER → CUSTOMER → CLIENT scope chain.)

## Compliance & Data Sensitivity

- Data is primarily **public web and community/market data**; minimal PII.
- **Strict multi-tenant isolation** — one customer's memory must never be retrievable in another customer's context.
- **PII**: avoid storing third parties' personal data beyond public professional context; **never** store payment-card or credential data.
- **GDPR-aware**: memories must be deletable and exportable per customer on request.
- **Retention**: market intelligence is retained so it compounds, but must be purgeable per company on request.

## Memory Priorities

Mapped to Synap's extracted memory types:

- **Fact (high)**: company profile, stage, category, ICP, positioning, named competitors, confirmed adjacencies, which sources/communities are relevant, channel norms.
- **Preference (high)**: the founder's preferred channels, tone/voice, approved vs. rejected draft styles, endorsed objectives, do-not-touch areas.
- **Episode (high)**: each analysis run, each engagement opportunity surfaced and whether it was acted on, each draft and its outcome/edits.
- **Temporal Event (high — recency is core)**: competitor launches/moves, market shifts, trending threads, and when an objective was set or changed. Time-anchored; critical for "what's fresh now."
- **Emotion (disable / low)**: founder affective state is not central to this B2B market-intelligence use case.

## Additional Context

- **Memory access pattern**: at the start of every run the agent recalls **customer-scoped** context (`mode="accurate"`) to make each run sharper; it ingests profile/objective/findings/opportunities/drafts via `memories.create` with `document_created_at` set to preserve recency and `metadata` tagging (`kind`, `source_url`, `run_id`). The founder chat uses **conversation scope** (`record_message` + `conversation.context.fetch`).
- **Document types ingested**: mostly `document` (profile, competitive/adjacency intel, drafts) and `ai-chat-conversation` (founder chat).
- **Cadence**: triggered on demand plus periodic (e.g., weekly) market sweeps — so temporal ordering and "what changed since last time" retrieval are important.
- **Goal**: each run visibly smarter than the last; the company's market brain compounds over weeks, with fresh/time-sensitive signal surfaced first.
- **Tech context**: LangGraph agent; tools via Composio (EXA search, Hacker News, Reddit) + Browserbase for fresh fetches; multi-model (Claude Sonnet 4.6 / Haiku 4.5 + GPT-4o); deployed on Render; UI generated with OpenUI.
