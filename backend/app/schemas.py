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


class PlanOut(BaseModel):
    items: List[PlanItem] = Field(default_factory=list)


class ReflectOut(BaseModel):
    sufficient: bool = False
    critique: str = ""
    extra_query: Optional[str] = None
    extra_access: Optional[str] = None


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


class Artifact(BaseModel):
    id: str = ""
    opportunity_id: str = ""
    title: str = ""
    channel: str = ""
    body: str = ""
    model_used: str = ""


# --- Addendum 4: runtime tool discovery + binding ---
class ToolBinding(BaseModel):
    """The model's choice of which discovered tool to bind for a research need."""
    slug: str = ""               # the Composio tool slug to execute
    args_json: str = "{}"        # JSON object of arguments for that tool
    why: str = ""                # one line: why this tool fits the need
    confidence: float = 0.5      # 0-1; low confidence skips binding, falls back to EXA


class Capability(BaseModel):
    """A tool or skill known to the registry (builtin, discovered, or generated)."""
    name: str                    # the access key / channel this resolves
    kind: str = "tool"           # tool | skill
    source: str = "builtin"      # builtin | composio | catalog | generated
    bound_at: str = "plan"       # plan | runtime
    slug: str = ""               # tool: Composio slug
    why: str = ""
    spec: dict = Field(default_factory=dict)  # skill: prompt augmentation; tool: arg template
