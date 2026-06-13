from typing import List, Optional

from pydantic import BaseModel, Field


class CompanyProfile(BaseModel):
    url: str = ""
    name: str = ""
    one_liner: str = ""
    stage: str = ""        # pre-seed | seed | series A | growth | unknown
    category: str = ""
    domain: str = ""
    icp: str = ""
    competitors: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class Objective(BaseModel):
    objective: str = ""        # the single stage-appropriate marketing objective
    reasoning: str = ""        # why this, for this stage
    not_this: str = ""         # what it is explicitly NOT (e.g. "raw traffic")


class ProfileObjective(BaseModel):
    profile: CompanyProfile
    objective: Objective


class Source(BaseModel):
    name: str
    kind: str = ""             # community | review | social | news | search
    why: str = ""
    access: str = "exa"        # exa | hackernews | reddit | browser
    template_id: str = "outreach"


class SourceStrategy(BaseModel):
    company_type: str = ""
    sources: List[Source] = Field(default_factory=list)


class PlanItem(BaseModel):
    goal: str = ""
    query: str = ""
    access: str = "exa"        # exa | hackernews | reddit | browser


class DiscardedIdea(BaseModel):
    """Addendum 3: an idea the agent considered and chose not to pursue, with why."""
    idea: str = ""
    reason: str = ""
    stage: str = ""            # plan | reflect | synthesize (set by the node)


class PlanOut(BaseModel):
    items: List[PlanItem] = Field(default_factory=list)
    discarded: List[DiscardedIdea] = Field(default_factory=list)


class ReflectOut(BaseModel):
    sufficient: bool = False
    critique: str = ""
    extra_query: Optional[str] = None
    extra_access: Optional[str] = None
    discarded: List[DiscardedIdea] = Field(default_factory=list)


class Finding(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = "exa"


class Opportunity(BaseModel):
    id: str = ""
    title: str = ""
    type: str = "strategic"    # strategic | engagement
    why: str = ""
    priority: str = "P1"       # P0 | P1 | P2
    impact: str = "medium"
    effort: str = "medium"
    category: str = ""
    steps: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    # engagement-specific
    source_name: str = ""
    thread_url: str = ""
    template_id: str = ""


class SynthesisOut(BaseModel):
    opportunities: List[Opportunity] = Field(default_factory=list)
    discarded: List[DiscardedIdea] = Field(default_factory=list)


class Artifact(BaseModel):
    id: str = ""
    opportunity_id: str = ""
    title: str = ""
    channel: str = ""
    body: str = ""
    model_used: str = ""


# --- Addendum 1: self-identified recurring monitors + Synap diff ---
class MonitorJob(BaseModel):
    name: str = ""
    query: str = ""
    access: str = "exa"          # builtin source or a platform the agent will bind at runtime
    cadence: str = "weekly"      # daily | weekly | monthly
    rationale: str = ""          # why this signal is worth watching for THIS company


class MonitorPlan(BaseModel):
    jobs: List[MonitorJob] = Field(default_factory=list)


class DiffOut(BaseModel):
    """The delta between a fresh monitor pull and what Synap already knows."""
    new: List[str] = Field(default_factory=list)        # genuinely new signal
    changed: List[str] = Field(default_factory=list)    # shifted since last time
    confirmed: List[str] = Field(default_factory=list)  # re-seen, no change
    stale: List[str] = Field(default_factory=list)      # prior intel that looks dated
    summary: str = ""


class ChangelogEntry(BaseModel):
    monitor: str = ""
    summary: str = ""
    new: List[str] = Field(default_factory=list)
    changed: List[str] = Field(default_factory=list)
    at: str = ""
    run_id: str = ""


# --- Addendum 4: runtime tool discovery + binding ---
class ToolBinding(BaseModel):
    """The model's choice of which discovered tool to bind for a research need."""
    slug: str = ""               # the Composio tool slug to execute
    args_json: str = "{}"        # JSON object of arguments for that tool
    why: str = ""                # one line: why this tool fits the need
    confidence: float = 0.5      # 0-1; low confidence skips binding, falls back to EXA


class SkillSpec(BaseModel):
    """A per-channel writing skill: voice + concrete rules to make a draft read native."""
    name: str = ""
    applies_to: str = ""         # channel/template this shapes
    voice: str = ""
    rules: List[str] = Field(default_factory=list)


class Capability(BaseModel):
    """A tool or skill known to the registry (builtin, discovered, or generated)."""
    name: str                    # the access key / channel this resolves
    kind: str = "tool"           # tool | skill
    source: str = "builtin"      # builtin | composio | catalog | generated
    bound_at: str = "plan"       # plan | runtime
    slug: str = ""               # tool: Composio slug
    why: str = ""
    spec: dict = Field(default_factory=dict)  # skill: prompt augmentation; tool: arg template


# --- Action Board: stateful marketing-action cards ---
class ActionCardCreate(BaseModel):
    """Payload to create a card — used by manual add and the CLI build-in-public skill."""
    company_slug: str = ""
    source: str = "manual"       # agent | cli | manual
    platform: str = "other"      # reddit | hackernews | x | linkedin | indiehackers | other
    kind: str = "reply"          # post | reply
    target_url: str = ""
    target_title: str = ""
    title: str = ""
    body: str = ""
    voice: str = ""
    state: str = "drafted"
    metadata: dict = Field(default_factory=dict)


class ActionCardPatch(BaseModel):
    """Partial update — move a card's state, edit the draft, record where it was posted."""
    state: Optional[str] = None
    body: Optional[str] = None
    title: Optional[str] = None
    position: Optional[int] = None
    posted_url: Optional[str] = None


class LessonOut(BaseModel):
    """The Daily Edge: one tailored marketing-psychology lesson tied to the founder's work."""
    title: str = ""              # punchy, specific to them — "Why your 12 likes hurt you"
    body: str = ""              # ~120-word plain-language read, ends with the one-line fix
    cta_label: str = ""         # send-language nudge toward the card on their board


class CardQuery(BaseModel):
    query: str = ""
    intent: str = ""             # the kind of thread this query is meant to surface


class CardQueries(BaseModel):
    """Search queries that find live threads where the company could naturally engage."""
    queries: List[CardQuery] = Field(default_factory=list)


# --- Landing page spec (#4): PM+marketer thinking handed to the founder's own coding agent ---
class LandingSection(BaseModel):
    heading: str = ""
    purpose: str = ""            # why this section exists, for the builder agent
    content: str = ""            # the actual copy to render


class LandingSpec(BaseModel):
    use_case: str = ""           # the single specific use-case this page targets
    positioning_oneliner: str = ""  # "the tourist map of flash drives" — concrete, not a feature list
    headline: str = ""
    subhead: str = ""
    sections: List[LandingSection] = Field(default_factory=list)
    proof: List[str] = Field(default_factory=list)  # trust/social-proof elements to include
    cta: str = ""
    layout_notes: str = ""       # structure/flow guidance (above-the-fold, order, emphasis)
