export type Ev = {
  type: string
  label?: string
  data?: any
  model?: string
  detail?: string
}

export type Profile = {
  name: string
  one_liner: string
  stage: string
  category: string
  icp: string
  competitors: string[]
}

export type Objective = { objective: string; reasoning: string; not_this: string }

export type Source = { name: string; kind: string; why: string; access: string; template_id: string }

export type Opp = {
  id: string
  title: string
  type: string
  why: string
  priority: string
  impact: string
  effort: string
  category: string
  steps: string[]
  sources: string[]
  source_name?: string
  thread_url?: string
  template_id?: string
}

export type Artifact = {
  id: string
  opportunity_id: string
  title: string
  channel: string
  body: string
  model_used: string
}

export type Discarded = { idea: string; reason: string; stage: string }

export type Capability = {
  name: string; kind: string; source: string; bound_at: string
  slug?: string; why?: string; spec?: any
}

export type MonitorJob = { name: string; query: string; access: string; cadence: string; rationale: string }

export type ChangelogEntry = { monitor: string; summary: string; new: string[]; changed: string[]; at: string; run_id: string }

export type Platform = 'reddit' | 'hackernews' | 'x' | 'linkedin' | 'indiehackers' | 'other'
export type CardKind = 'post' | 'reply'
export type CardState = 'suggested' | 'drafted' | 'approved' | 'posted' | 'engaged' | 'dismissed'

export type ActionCard = {
  id: string
  org_id?: string
  run_id?: string | null
  company_slug?: string
  source?: string
  platform: Platform
  kind: CardKind
  target_url?: string | null
  target_title?: string
  title: string
  body: string
  voice?: string
  state: CardState
  posted_url?: string | null
  posted_at?: string | null
  position?: number
  metadata?: any
  // marks a card derived from the live run in-memory (no server row yet)
  _local?: boolean
}

export type MemoryView = {
  active: boolean
  formatted_context: string
  facts: any[]
  episodes: any[]
  temporal_events: any[]
  processing?: number
  conversation_id?: string
}
