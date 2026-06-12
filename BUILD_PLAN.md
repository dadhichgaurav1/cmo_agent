# CMO Cofounder — Build Plan

> A hackathon build. ~3h total; most brainstorm spent — **~135 min of build left.** This plan is the execution contract. Flex items marked ⚑. Cut items in §10.

---

## 0. Product thesis — a CMO *cofounder*, not a tracker

Point it at a company URL. The agent behaves like a world-class CMO cofounder **for that specific company**:

1. **Picks the right objective for the stage.** Pre-seed = narrative + design partners; seed = ICP + founder-led demand; Series A = repeatable channels + category. It does *not* assume "drive traffic."
2. **Hunts adjacencies & non-obvious wedges** — adjacent communities, channel arbitrage, positioning shifts, partnership/integration angles, emerging segments — the intelligent, lateral stuff. **Not** "you were mentioned 3x on HN."
3. **Knows where the customers actually are.** A **source-strategy skill** maps the company *type* to the right sources (dev → HN/Reddit/dev.to; DTC → TikTok/review-sites/niche subs; B2B-services → LinkedIn/G2/communities) — so it generalizes far beyond tech.
4. **Delivers stage-appropriate moves**, prioritized, laddering up to the objective — plus an **engagement radar** (specific threads to act on today) with **ready-to-send drafts** that fit each channel's culture (operator; the founder approves & sends — no AI-slop autopilot).
5. **Remembers & compounds** across runs (Synap) and **runs fully remote** (cloud, not the laptop).

**Inspectable by design:** every step / finding / draft shows a **summary + open-in-new-tab deep link** (sources → their URL; artifacts & reasoning → their own addressable route). No black box.

**Demo company:** **Resend** (email API; competitors Postmark / SendGrid / Loops / Mailgun / SES; dense HN + Reddit chatter → rich radar).

**The demo "wow":** one genuinely non-obvious, stage-right insight about Resend that makes the room nod.

---

## 1. Sponsor-prize alignment (grand prize = 3 sponsor tools, prerequisite — not AWS-dependent)

| Tool | Role | Load-bearing? |
|---|---|---|
| **Composio** | Unified tool gateway: EXA search (toolkit) + Hacker News (no-auth) + Reddit (read) + ship-it connector (Gmail/Slack/Notion) | ✅ core |
| **OpenUI** | Dashboard UI generated **at build-time** (harvested into React) + ⚑ runtime artifact panel | ✅ core (build-time) |
| **Render** (sponsor) | Cloud deploy — Docker web service, binds `$PORT` | ✅ core |

**Used but not prizes:** EXA (search quality; via Composio), Browserbase (freshness fallback), **Maximem Synap** (memory = the differentiator + dogfood), **LangGraph** (agent framework), multi-model (Anthropic + OpenAI).

---

## 2. Architecture

```
                    ┌──────────────────────────── Render (Docker, $PORT) ────────────────────────────┐
  Browser ──HTTP──► │  FastAPI                                                                        │
   (React,          │   ├─ GET /api/analyze/stream?url=&mode=  → SSE trace (objective→…→drafts)       │
    OpenUI-built)   │   ├─ POST /api/chat        (Synap conversation-scoped)                          │
                    │   ├─ POST /api/research     (custom triggered research)                         │
                    │   ├─ GET  /a/{artifact_id}  → standalone artifact page (open-in-new-tab)        │
                    │   ├─ GET  /step/{run}/{i}   → standalone reasoning page (open-in-new-tab)       │
                    │   └─ /  (static React build)                                                    │
                    │                                                                                 │
                    │  Agent — LangGraph StateGraph                                                   │
                    │   recall → objective → source_strategy → plan → act(≤6) ⇄ reflect →             │
                    │            synthesize → draft → remember                                        │
                    │      │                         │                                                │
                    │      │                    Tool layer (act node executes directly)               │
                    │      │                     ├─ Composio: exa_search · hackernews · reddit · gmail/slack │
                    │      │                     ├─ Browserbase: fresh_fetch (remote headless; recency)│
                    │      │                     └─ direct EXA / Algolia-HN  (fallbacks)               │
                    │      └─ Models (router): Sonnet 4.6 / Haiku 4.5 / GPT-4o                         │
                    │                                                                                 │
                    │  Memory: Maximem Synap  (customer_id = analyzed company)                        │
                    └─────────────────────────────────────────────────────────────────────────────────┘
  Modes: cached (deterministic seed for Resend, stage-safe) · live (try-your-own). Toggle in UI.
```

---

## 3. Repo structure

```
cmo_agent/
  backend/
    app/
      main.py            # FastAPI: SSE, chat, research, /a/{id}, /step routes, static
      config.py          # env keys
      schemas.py         # Objective, SourceStrategy, Opportunity, Artifact, Finding, AgentEvent, CompanyProfile
      models.py          # multi-model router → LangChain chat models (ChatAnthropic / ChatOpenAI)
      memory.py          # Synap wrapper (real SDK; local JSON fallback)
      agent/
        graph.py         # LangGraph StateGraph: recall→objective→source_strategy→plan→act⇄reflect→synthesize→draft→remember
        tools.py         # tool registry → Composio actions (EXA/HN/Reddit) + Browserbase + EXA/Algolia fallbacks
        skills.py        # source-strategy skill (company-type→ranked sources) + per-channel engagement templates
        prompts.py       # CMO-cofounder prompts: objective + source-strategy + adjacency + critique + draft
      cache/
        resend.json      # seeded cached transcript for demo mode
    requirements.txt
  frontend/              # React + Vite (components generated with OpenUI)
  Dockerfile             # multi-stage: build FE → serve via FastAPI on $PORT
  render.yaml            # Render blueprint
  .env.example
  BUILD_PLAN.md
```

> Reuse from the throwaway scaffold already on disk: `config.py`, `schemas.py` (extend), FastAPI/SSE shell, `memory.py` fallback structure. Replace: fixed pipeline → `agent/graph.py`; raw model calls → LangChain chat models; App Runner → Render.

---

## 4. Env vars (`backend/.env` — fill all at once; mirror in Render dashboard)

```
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
EXA_API_KEY=
COMPOSIO_API_KEY=
SYNAP_API_KEY=
BROWSERBASE_API_KEY=
BROWSERBASE_PROJECT_ID=
```

---

## 5. Verified integration notes (use these exact APIs)

**Synap** (`pip install maximem-synap`)
```python
from maximem_synap import MaximemSynapSDK
sdk = MaximemSynapSDK(api_key=SYNAP_API_KEY); await sdk.initialize()
CID = "resend"          # customer_id = analyzed company
# recall at run start (accurate = vector+graph+rerank)
ctx = await sdk.customer.context.fetch(customer_id=CID,
        search_query=[company, "adjacencies", "positioning", "channels"], mode="accurate")
#   → ctx.formatted_context / ctx.facts / ctx.episodes / ctx.temporal_events
# ingest findings/objective/drafts (non-blocking; preserve time for recency)
await sdk.memories.create(document=text, document_type="document",
        customer_id=CID, user_id="founder",
        document_created_at=iso_now, metadata={"kind":"adjacency","source_url":url,"run_id":rid})
# chat memory: record_message(...) per turn + conversation.context.fetch(conversation_id=uuid, ...)
```

**LangGraph** (`pip install langgraph langchain-anthropic langchain-openai`)
- Agent as a `StateGraph`. State (`TypedDict`) accumulates `profile / objective / sources / observations / opportunities / artifacts / trace`.
- Nodes call `ChatAnthropic(model="claude-sonnet-4-6")` / `ChatOpenAI(model="gpt-4o")`; use `.with_structured_output(Schema)` for objective / source-strategy / opportunities.
- Bounded loop = conditional edge `reflect → {act, synthesize}` with an iteration cap (≤6).
- Stream with `app.astream(state, stream_mode="updates")` → map each node's new `trace` items to SSE `AgentEvent`s.
- Tools executed **directly inside the act node** (deterministic, fully traceable) — not autonomous tool-binding.

**Source-strategy skill (generalizes beyond tech)** — structured model call: profile → `{company_type, sources:[{name, kind(community|review|social|news|search), why, access_method, template_id}]}`. `access_method ∈ {composio:hackernews, composio:reddit, exa_scoped, browserbase}`. Per-channel **engagement templates** (`reddit_reply / hn_comment / linkedin_post / review_response / twitter_reply / outreach`) drive the draft node so each draft fits the channel's norms (anti-slop). Resend → HN, r/webdev, r/SaaS, dev.to. DTC brand → r/SkincareAddiction, TikTok, review sites via `exa_scoped`. *This is the auto-generated, company-specific skill from the original spec.*

**Composio** (Python SDK) — gateway for: `EXA` (search), `HACKERNEWS` (no auth), `REDDIT` (read — **in scope**, 2-min OAuth connect), `GMAIL/SLACK` (ship-it ⚑).
> ⚠️ Composio's SDK surface churns — **confirm the exact tool-fetch/`execute` call at build** (`from composio import Composio`). Fallbacks if blocked: **direct EXA REST**, **Algolia HN API** (`http://hn.algolia.com/api/v1/search`, free/no-auth).

**Browserbase** (freshness fallback — remote headless, no local Chromium)
```python
# POST https://api.browserbase.com/v1/sessions  (X-BB-API-Key, {projectId}) → connectUrl
from playwright.async_api import async_playwright
async with async_playwright() as p:
    b = await p.chromium.connect_over_cdp(connect_url)
    pg = await b.new_page(); await pg.goto(url, wait_until="networkidle")
    text = await pg.inner_text("body"); await b.close()
```
`pip install playwright` only (no `playwright install` — browser is remote).

**Render** — bind `$PORT`; Dockerfile CMD shell form: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}`. Deploy: push to GitHub → Render → "New Web Service" → Docker auto-detected (or `render.yaml` blueprint). Set env vars in dashboard.

**OpenUI** — `docker run -p 7878:7878 -e ANTHROPIC_API_KEY=… ghcr.io/wandb/openui`. **Build-time:** generate dashboard components in the playground, harvest HTML/React into `frontend/`. **Runtime ⚑:** uses LiteLLM → likely an OpenAI-compatible internal route; if usable, call it for the dynamic artifact panel, else fall back to a model call returning HTML.

---

## 6. Phases

### Phase 0 — Scaffold + deploy skeleton to Render · ~15 min · *de-risk first*
- Evolve scaffold; add `render.yaml`, `$PORT` binding, `requirements.txt` (+ langgraph, langchain-anthropic, langchain-openai, composio, maximem-synap, playwright).
- Minimal `/api/health` + a placeholder React build served by FastAPI.
- Push to GitHub, create Render web service, set env vars, deploy.
- **Acceptance:** public Render URL returns `/api/health` ok and serves the page.

### Phase 1 — Agentic core (LangGraph) · ~55 min · *the brain*
`agent/graph.py`: `StateGraph` streaming `AgentEvent`s over SSE (`astream(stream_mode="updates")`):
1. **recall** — Synap `customer.context.fetch` (prior intel).
2. **objective** — Sonnet picks the stage-appropriate objective + why (site + profile). Banner event.
3. **source_strategy (skill)** — Sonnet maps company-type → ranked sources + access method + engagement template. Emitted, inspectable.
4. **plan** — Sonnet decomposes objective → sub-goals over the chosen sources, **biased to adjacencies/wedges**, not competitor mentions.
5. **act (≤6)** — model picks next `{tool, args}` over the chosen sources (`composio: exa / hackernews / reddit`, `fetch_site`, `browserbase`); execute; observe. Each step → summary + deep link.
6. **reflect** — Sonnet critiques *"specific & non-obvious, or generic? gaps?"* → conditional edge loops to **act** or proceeds. **Insight-quality gate.**
7. **synthesize** — prioritized Opportunities (objective-laddered) + engagement radar (specific threads).
8. **draft** — per top opportunity, drafts the channel-appropriate artifact **using the source's template** (reply / comparison / email / post).
9. **remember** — Synap `memories.create` for objective/findings/opportunities/drafts (with `document_created_at`).
- Model router live (Sonnet/Haiku/GPT-4o), surfaced per event. **Seed `cache/resend.json`** from one good live run → cached mode replays deterministically.
- **Acceptance:** `mode=live` and `mode=cached` on `resend.com` stream objective → source map → adjacencies → radar → drafts; sources adapt to company type; Synap write+recall confirmed (run twice → recall non-empty).

### Phase 2 — OpenUI-built dashboard · ~35 min · *the face*
- Generate components with OpenUI (record the session for the pitch), harvest into React/Vite:
  - **Objective banner** (the stage-right goal, expandable to reasoning).
  - **Source map** — where it's looking and why (the cofounder smarts, inspectable).
  - **Live trace** — streamed nodes, model badges, each with summary + **open-in-new-tab**.
  - **Opportunity board** — grouped by priority, laddered to objective; cards expand → why + steps + sources.
  - **Engagement radar** — specific threads + channel-fit draft; **"open draft in new tab"** (`/a/{id}`).
  - **Chat** — founder ↔ CMO (Synap conversation-scoped) + custom-research box.
  - **Mode toggle** — cached / live.
- `/a/{id}` and `/step/{run}/{i}` standalone pages for inspectability.
- **Acceptance:** full run renders end-to-end; every artifact/source opens in a new tab.

### Phase 3 — Flex (only if green) · ~20 min
- ⚑ **OpenUI runtime artifact panel** (dynamic UI per artifact; fallback = model-HTML).
- ⚑ **Composio ship-it** — "Send draft" → Gmail draft / Slack message.
- ⚑ **Reddit read** via Composio (uses the connected OAuth).
- ⚑ **Browserbase fresh-fetch** — wired behind `fetch(strategy="browser")` for a recency moment.
- ⚑ **Non-tech demo beat** — show the source map adapting for a DTC/B2B example.

### Phase 4 — Ship & rehearse · ~20 min
- Redeploy to Render; smoke-test the public URL in **cached** + **live**.
- Polish copy/spacing; ensure the non-obvious Resend insight is front-and-center.
- **Rehearse the 90s demo on cached mode**; keep live as the "try yours" encore.

---

## 7. Demo script (~90s)
1. "Founders don't need a dashboard — they need a CMO cofounder. Watch." Paste **resend.com**, hit Run (cached).
2. Trace streams: **"Stage: Series A → objective isn't traffic, it's *category ownership*"** — model badges visible.
3. **Source map** appears — "here's where Resend's buyers actually are" — then a **non-obvious adjacency/wedge** + an **engagement radar**: a specific HN/Reddit thread + a drafted, channel-fit reply. Click → opens in a new tab (inspectable).
4. "It remembers." Show Synap recall making run #2 sharper.
5. "Runs in the cloud on Render; tools via Composio; UI built with OpenUI." Encore: **live** run on a judge's company (shows the source map adapting).

---

## 8. Risks & fallbacks
| Risk | Fallback |
|---|---|
| Composio SDK API drift | Direct EXA REST + Algolia HN API (no auth) |
| LangGraph friction | Controlled act-node (no auto tool-binding); worst case, hand-rolled loop reusing the same node fns |
| Live APIs slow/flaky on stage | **Cached mode** is the primary demo path |
| OpenUI no runtime endpoint | Build-time generation (prize-safe) + model-HTML for runtime |
| Synap latency/SDK issue | Local JSON memory fallback (interface identical) |
| Browserbase setup eats time | It's Phase 3 flex; cut freely |
| Behind at end of Phase 2 | Ship cached-only, skip all of Phase 3 |

## 9. Models (router)
Sonnet 4.6 → objective / source-strategy / plan / reflect / synthesize · Haiku 4.5 → read / extract / summarize · GPT-4o → chat. Via LangChain chat models; surfaced in the trace as the "best model per task" story.

## 10. Cut list (explicitly not doing)
Repo-PR operator (roadmap line only) · auto-posting (drafts only) · multi-user/auth · multi-company persistence beyond Synap · agentic browsing beyond a single fresh-fetch · pixel-perfect design.

## 11. Need from you
- **Keys** → `backend/.env` (§4), all at once. For Composio **Reddit**, do the 2-min OAuth connect in the Composio dashboard (HN needs none).
- **Render**: connect the GitHub repo (or grant access) so I can deploy; set the §4 env vars in the Render dashboard.
- **Resolved:** cloud = Render (no AWS) · ADK = **LangGraph** · Reddit = in scope · source-strategy skill = in.
- **Go-ahead** → I start Phase 0 immediately.
