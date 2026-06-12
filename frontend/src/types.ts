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
