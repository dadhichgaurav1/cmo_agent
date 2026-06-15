# Sub-agents in the cmo_agent harness — exploration notes

> Captured 2026-06-15. Parking-lot doc, not a committed plan. Revisit after launch/distribution
> settles. The goal here is to preserve the reasoning so we don't re-derive it later.

## The need

Can the **agent built inside cmo_agent** (the LangGraph `StateGraph` in
[backend/app/graph.py](backend/app/graph.py)) spawn **sub-agents when it deems fit**, the way the
Claude Code harness delegates to child agents? If not, what would it take?

Two different things hide under "sub-agents" — keep them separate (see Options A vs B), because
they have very different cost and risk.

## Where we are today

The agent is a **fixed, hand-wired DAG**, not an autonomous loop:

```
recall -> objective -> source_strategy -> plan -> act <-> reflect -> synthesize -> draft -> monitor_plan -> remember
```

Three structural facts mean it **cannot** spawn sub-agents on its own today:

1. **No model-driven tool loop.** Every node makes a *single-shot* LLM call —
   [models.py](backend/app/models.py) `run_structured` / `run_text` do one `.ainvoke([system, human])`
   and return. The model never gets a tool list and never decides what to call next. No
   `bind_tools`, no `ToolNode`, no `create_react_agent` anywhere. The LLM is a structured slot-filler.

2. **No delegation / fan-out.** Exactly one `GRAPH.ainvoke` ([graph.py:326](backend/app/graph.py#L326)).
   No subgraphs, no `asyncio.gather`, no child runs. `act` processes research moves **one at a time**
   by index (`plan_items[i]`), and the only branch is the `act <-> reflect` loop capped at `CAP=5`.
   The model controls flow in exactly one place: the binary `sufficient / needs-more` decision in
   `route_after_reflect` ([graph.py:170](backend/app/graph.py#L170)).

3. **The one agentic flourish is runtime tool *binding*, not a sub-agent.**
   [capabilities.py](backend/app/capabilities.py): when a plan names an unknown source, a model picks
   a Composio tool and binds it (always falling back to EXA). That's dynamic *capability acquisition*.
   The docstring even calls it "the deliberate, **bounded** reversal of the build plan's
   'no autonomous tool-binding'." So the constrained design is a **stated principle**, not an oversight.

**Summary:** Claude Code = open-ended, model-driven loop with a delegation tool it invokes at will.
cmo_agent = closed, deterministic pipeline where the LLM fills predetermined slots. We're at the far
opposite end of the spectrum, on purpose.

## The two options

### Option A — Orchestration fan-out (code decides, spawns parallel workers)

*We* decide where to parallelize; the model still doesn't control flow. Independent units that run
serially today and could run as parallel sub-tasks:

- **`act`** — research moves run serially through the act/reflect loop. LangGraph's `Send` API
  (map-reduce) fans all plan items into parallel workers, then reduces `findings`.
- **`draft`** ([graph.py:216](backend/app/graph.py#L216)) — the `for o in targets` loop is trivially
  `asyncio.gather`-able.
- **`generate_cards`** ([graph.py:420](backend/app/graph.py#L420)) — the per-platform loop is fully
  independent; one worker per platform.

**Pros**
- High practical payoff: roughly N× latency cut on research and drafting.
- Low risk, reversible, no change to the control philosophy.
- Doesn't touch the determinism / cost predictability the design relies on.

**Cons**
- Not "intelligent" delegation — the model gains no new authority; it's just parallelism.
- Still needs trace + cost plumbing (see cross-cutting concerns) before fan-out is safe.

### Option B — Model-decided delegation (true Claude-Code-like sub-agents)

Let the model decide at runtime: "spin up a sub-agent to go deep on X." Requires:

- A **real tool-use loop** in at least one node — swap `with_structured_output` for `bind_tools` +
  iterate-until-no-tool-calls, or `create_react_agent`.
- Factor the research portion (`act`/`reflect`) into a **reusable subgraph**, exposed via a
  `spawn_research(subquestion)` tool whose handler invokes that subgraph as a child run.
- Grant the orchestrator authority over control flow and recursion (it has essentially none today).

**Pros**
- Genuine flexibility: handles hard, open-ended sub-questions the fixed pipeline can't anticipate.
- The "wow" behavior — the agent visibly reasoning about when to go deeper.

**Cons**
- Real philosophy shift away from the deterministic design, not just a feature.
- Unpredictable token spend; harder to reason about and to bound.
- More surface area for failure loops; needs strict recursion/iteration budgets.

## Recommended sequence

1. **Distribution first.** (Current focus — do not start either option yet.)
2. **Then Option A.** Parallelize `act` / `draft` / `generate_cards` with `Send` / `asyncio.gather`.
   Captures most of the practical value (speed, depth), reversible, keeps cost predictable.
3. **Only then, narrowly, Option B** — and only where it pays off (deep research on a hard
   sub-question), as a single subgraph the planner can route to. Do **not** rearchitect the whole
   pipeline into an open loop; that throws away the determinism and cost control the design was
   built around.

## Cross-cutting concerns (apply to BOTH options)

- **Billing / usage.** Fan-out and delegation multiply token spend. The entitlement gates
  (`usage.can`, [capabilities.py](backend/app/capabilities.py), free=manual loop / Pro=engine) assume
  roughly-linear cost per run. Sub-agents must meter against quotas, or a free user triggers N× cost.
- **Tracing.** `emit` is a single event stream. Concurrent sub-agents need `run_id` / `parent_id`
  tagging or the frontend trace interleaves incoherently.
- **Determinism / cost tradeoff.** Today's design is cheap and predictable on purpose (Haiku for
  drafts, `CAP=5`, `recursion_limit=60`). Any model-driven spawning trades that away — go in
  knowing the tradeoff.

## Key file references

- Graph / control flow: [backend/app/graph.py](backend/app/graph.py)
- LLM calls (single-shot, no tool loop): [backend/app/models.py](backend/app/models.py)
- Runtime tool binding (the only agentic step today): [backend/app/capabilities.py](backend/app/capabilities.py)
- Per-channel writing skills (also runtime-resolved): [backend/app/skills.py](backend/app/skills.py)
- Entitlement / quota gates to respect: [backend/app/usage.py](backend/app/usage.py), [backend/app/capabilities.py](backend/app/capabilities.py)
