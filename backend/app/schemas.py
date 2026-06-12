from typing import List

from pydantic import BaseModel, Field


class CompanyProfile(BaseModel):
    url: str
    name: str = ""
    one_liner: str = ""
    stage: str = ""        # pre-seed | seed | series A | growth | unknown
    category: str = ""     # market category
    domain: str = ""       # business domain
    icp: str = ""          # ideal customer profile
    competitors: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class ResearchFinding(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = "exa"


class ActionItem(BaseModel):
    id: str = ""
    title: str
    why: str = ""
    priority: str = "P1"          # P0 | P1 | P2
    impact: str = "medium"        # high | medium | low
    effort: str = "medium"        # high | medium | low
    category: str = ""            # positioning | content | GTM | growth | product-marketing
    steps: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    model_used: str = ""


class Skill(BaseModel):
    name: str
    when_to_use: str = ""
    prompt: str = ""
    generated: bool = True
