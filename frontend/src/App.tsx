import { useEffect, useRef, useState } from 'react'
import { analyze, chatApi, researchApi, uiRender, landingSpec, landingPrompt, memoryView, monitorsView, runMonitors, openInTab, openPrintable, escapeHtml, getMomentum, setOrgTimezone, getEdge } from './api'
import ActionBoard from './ActionBoard'
import Momentum from './Momentum'
import MomentumChip, { PERSONA_GLYPH } from './MomentumChip'
import type { Ev, Profile, Objective, Source, Opp, Artifact, Discarded, Capability, MonitorJob, ChangelogEntry, MemoryView, Momentum as Mom, MomentumAward, Lesson } from './types'

function modelColor(m?: string) {
  if (!m) return '#8a8378'
  if (m.includes('sonnet')) return '#c2603f'
  if (m.includes('haiku')) return '#3e7c74'
  if (m.includes('gpt')) return '#5e7f4f'
  if (m.includes('exa')) return '#b07d2e'
  if (m.includes('composio')) return '#7b6cb3'
  if (m.includes('hackernews')) return '#c8642e'
  if (m.includes('synap')) return '#a65a7e'
  if (m.includes('skill')) return '#6f8f3e'
  return '#8a8378'
}

function Badge({ model }: { model?: string }) {
  if (!model) return null
  const c = modelColor(model)
  return <span className="badge" style={{ color: c, borderColor: c + '40', background: c + '14' }}>{model}</span>
}

const PRIORITIES = ['P0', 'P1', 'P2']
const priClass = (p?: string) => 'pri ' + (p || 'P1').toLowerCase()

function OpportunityCard({ o }: { o: Opp }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="oppcard">
      <div className="opphead" onClick={() => setOpen(!open)}>
        <span className={priClass(o.priority)}>{o.priority}</span>
        <span className="opptitle">{o.title}</span>
        <span className="chev">{open ? '−' : '+'}</span>
      </div>
      <div className="oppmeta">{o.category} · impact {o.impact} · effort {o.effort}</div>
      {open && (
        <div className="oppbody">
          <p className="why">{o.why}</p>
          {o.steps?.length > 0 && <ol>{o.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>}
          {o.sources?.length > 0 && (
            <div className="srcs">{o.sources.map((s, i) => <a key={i} href={s} target="_blank" rel="noreferrer">source {i + 1} ↗</a>)}</div>
          )}
        </div>
      )}
    </div>
  )
}

function RadarCard({ o, art }: { o: Opp; art?: Artifact }) {
  const [copied, setCopied] = useState(false)
  const [open, setOpen] = useState(false)
  function copy() {
    if (!art) return
    navigator.clipboard?.writeText(art.body)
    setCopied(true); setTimeout(() => setCopied(false), 1200)
  }
  function openDraft() {
    if (!art) return
    openInTab(art.title,
      `<h1>${escapeHtml(art.title)}</h1><div class="meta">${escapeHtml(art.channel)} · ${escapeHtml(art.model_used)}</div>` +
      `<pre>${escapeHtml(art.body)}</pre>` +
      (o.thread_url ? `<p><a href="${o.thread_url}" target="_blank">Open the thread ↗</a></p>` : ''))
  }
  return (
    <div className="radarcard">
      <div className="radarhead" onClick={() => setOpen(!open)}>
        <span className="radardot" /><span className="opptitle">{o.title}</span>
        {art && <span className="chev">{open ? '−' : '+'}</span>}
      </div>
      <p className="why">{o.why}</p>
      <div className="radarmeta">
        {o.source_name && <span className="chip">{o.source_name}</span>}
        {o.template_id && <span className="chip ghost">{o.template_id}</span>}
        {o.thread_url && <a href={o.thread_url} target="_blank" rel="noreferrer" className="chip link">open thread ↗</a>}
        {art && !open && <button className="chip linkbtn" onClick={() => setOpen(true)}>show drafted reply ▾</button>}
      </div>
      {art && open && (
        <div className="draft">
          <div className="drafthead">Drafted reply <Badge model={art.model_used} /></div>
          <pre className="draftbody">{art.body}</pre>
          <div className="draftactions">
            <button onClick={copy}>{copied ? 'copied ✓' : 'copy'}</button>
            <button onClick={openDraft}>open in tab ↗</button>
          </div>
        </div>
      )}
    </div>
  )
}

// Assemble the run's key sections into a clean, print-ready document and hand it
// to the browser's print → "Save as PDF". Mirrors what the Brief tab shows.
function downloadBriefPdf(p: {
  url: string; objective: Objective | null; profile: Profile | null; companyType: string
  sources: Source[]; radar: Opp[]; strategic: Opp[]; artifacts: Record<string, Artifact>
  ledger: Discarded[]
}) {
  const e = escapeHtml
  const company = p.profile?.name || p.url || 'company'
  const today = new Date().toISOString().slice(0, 10)
  const parts: string[] = []

  parts.push(`<h1>${e(company)} — CMO brief</h1>`)
  parts.push(`<div class="meta">StratCMO · ${e(p.url)}${p.companyType ? ' · ' + e(p.companyType) : ''} · ${today}</div>`)

  if (p.objective) {
    parts.push('<h2>Objective</h2>')
    parts.push(`<div class="doc-objective">${e(p.objective.objective)}`)
    if (p.objective.reasoning) parts.push(`<div class="doc-why">${e(p.objective.reasoning)}</div>`)
    if (p.objective.not_this) parts.push(`<div class="doc-not">Not: ${e(p.objective.not_this)}</div>`)
    parts.push('</div>')
  }

  if (p.profile) {
    parts.push('<h2>Company</h2>')
    parts.push(`<p><b>${e(p.profile.name)}</b> — ${e(p.profile.one_liner)}</p>`)
    parts.push(`<div class="doc-sub">${e(p.profile.category || '')}${p.profile.icp ? ' · ICP: ' + e(p.profile.icp) : ''}</div>`)
    if (p.profile.competitors?.length) parts.push(`<div class="doc-sub">vs ${e(p.profile.competitors.join(', '))}</div>`)
  }

  if (p.sources.length) {
    parts.push(`<h2>Where your customers are${p.companyType ? ' <span class="doc-sub">' + e(p.companyType) + '</span>' : ''}</h2>`)
    for (const s of p.sources) {
      parts.push(`<div class="doc-item"><b>${e(s.name)}</b> <span class="doc-chip">${e(s.access)}</span>`)
      if (s.why) parts.push(`<div class="doc-why">${e(s.why)}</div>`)
      parts.push('</div>')
    }
  }

  if (p.radar.length) {
    parts.push('<h2>Engagement radar</h2>')
    for (const o of p.radar) {
      const art = p.artifacts[o.id]
      parts.push('<div class="doc-item">')
      parts.push(`<h3>${e(o.title)}</h3>`)
      if (o.why) parts.push(`<p class="doc-why">${e(o.why)}</p>`)
      if (o.source_name) parts.push(`<span class="doc-chip">${e(o.source_name)}</span>`)
      if (o.thread_url) parts.push(`<div><a href="${e(o.thread_url)}">${e(o.thread_url)}</a></div>`)
      if (art) {
        parts.push(`<div class="doc-sub">Drafted reply · ${e(art.model_used || '')}</div>`)
        parts.push(`<div class="doc-draft">${e(art.body)}</div>`)
      }
      parts.push('</div>')
    }
  }

  if (p.strategic.length) {
    parts.push('<h2>Prioritized moves</h2>')
    for (const pr of PRIORITIES) {
      const list = p.strategic.filter((o) => (o.priority || 'P1').toUpperCase().startsWith(pr))
      for (const o of list) {
        parts.push('<div class="doc-item">')
        parts.push(`<h3><span class="doc-pri">${e(o.priority || 'P1')}</span>${e(o.title)}</h3>`)
        parts.push(`<div class="doc-sub">${e(o.category || '')} · impact ${e(o.impact || '')} · effort ${e(o.effort || '')}</div>`)
        if (o.why) parts.push(`<p>${e(o.why)}</p>`)
        if (o.steps?.length) parts.push(`<ol>${o.steps.map((s) => `<li>${e(s)}</li>`).join('')}</ol>`)
        if (o.sources?.length) parts.push(`<div class="doc-sub">${o.sources.map((s, i) => `<a href="${e(s)}">source ${i + 1}</a>`).join(' · ')}</div>`)
        parts.push('</div>')
      }
    }
  }

  if (p.ledger?.length) {
    parts.push('<h2>Reasoning log <span class="doc-sub">ideas considered and discarded</span></h2>')
    for (const st of ['plan', 'reflect', 'synthesize']) {
      const items = p.ledger.filter((d) => d.stage === st)
      if (!items.length) continue
      parts.push(`<h3>Ruled out at ${e(st)}</h3>`)
      for (const d of items) {
        parts.push('<div class="doc-item">')
        parts.push(`<div><b>${e(d.idea)}</b></div>`)
        if (d.reason) parts.push(`<div class="doc-why">${e(d.reason)}</div>`)
        parts.push('</div>')
      }
    }
  }

  openPrintable(`${company} — CMO brief`, parts.join('\n'))
}

// Primary = what you act on; secondary = transparency/"behind the scenes" views,
// rendered muted and to the right of a divider. ids are unchanged (tab routing).
const TABS = [
  { id: 'brief', label: 'Brief', tier: 'primary' },
  { id: 'actions', label: 'Action Board', tier: 'primary' },
  { id: 'momentum', label: 'Momentum', tier: 'primary' },
  { id: 'reasoning', label: 'Reasoning', tier: 'primary' },
  { id: 'monitors', label: 'Monitors', tier: 'primary' },
  { id: 'synap', label: 'Memory', tier: 'secondary' },
  { id: 'capabilities', label: 'Toolkit', tier: 'secondary' },
]

export default function App() {
  const [url, setUrl] = useState('resend.com')
  const [mode, setMode] = useState<'cached' | 'live'>('cached')
  const [running, setRunning] = useState(false)
  const [tab, setTab] = useState('brief')
  const [trace, setTrace] = useState<Ev[]>([])
  const [profile, setProfile] = useState<Profile | null>(null)
  const [objective, setObjective] = useState<Objective | null>(null)
  const [companyType, setCompanyType] = useState('')
  const [sources, setSources] = useState<Source[]>([])
  const [strategic, setStrategic] = useState<Opp[]>([])
  const [radar, setRadar] = useState<Opp[]>([])
  const [artifacts, setArtifacts] = useState<Record<string, Artifact>>({})
  const [ledger, setLedger] = useState<Discarded[]>([])
  const [caps, setCaps] = useState<Capability[]>([])
  const [monitorJobs, setMonitorJobs] = useState<MonitorJob[]>([])
  const [momentum, setMomentum] = useState<Mom | null>(null)
  const [edge, setEdge] = useState<Lesson | null>(null)
  const [toast, setToast] = useState<MomentumAward | null>(null)
  const [levelUp, setLevelUp] = useState<MomentumAward['leveled_up'] | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const toastTimer = useRef<number | null>(null)

  // Capture the founder's timezone once (streak day-bucketing depends on it), then load momentum.
  useEffect(() => {
    try { setOrgTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone).catch(() => {}) } catch { /* ignore */ }
  }, [])
  useEffect(() => {
    getMomentum(url).then((r) => setMomentum(r.momentum ?? null)).catch(() => {})
    getEdge(url).then((r) => setEdge(r.lesson ?? null)).catch(() => {})
  }, [url])

  // An award came back from a card PATCH — refresh the chip, toast it, and catch level-ups.
  function onMomentum(a: MomentumAward) {
    setMomentum((prev) => prev ? {
      ...prev,
      total_points: a.total_points,
      current_streak: a.current_streak,
      persona_key: a.persona_key,
      shipped_today: a.streak_safe || prev.shipped_today,
    } : prev)
    getMomentum(url).then((r) => setMomentum(r.momentum ?? null)).catch(() => {})
    setToast(a)
    if (toastTimer.current) window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setToast(null), 5000)
    if (a.leveled_up) setLevelUp(a.leveled_up)
  }

  function run() {
    if (running || !url.trim()) return
    setRunning(true); setTrace([]); setProfile(null); setObjective(null); setSources([]); setCompanyType('')
    setStrategic([]); setRadar([]); setArtifacts({}); setLedger([]); setCaps([]); setMonitorJobs([]); setTab('brief')
    analyze(url.trim(), mode,
      (e) => {
        if (e.type === 'step' || e.type === 'memory' || e.type === 'finding' || e.type === 'reflect'
            || e.type === 'tool_bound' || e.type === 'skill_bound') setTrace((t) => [...t, e])
        else if (e.type === 'profile') setProfile(e.data)
        else if (e.type === 'objective') { setObjective(e.data); setTrace((t) => [...t, e]) }
        else if (e.type === 'sources') { setSources(e.data?.sources || []); setCompanyType(e.data?.company_type || ''); setTrace((t) => [...t, e]) }
        else if (e.type === 'plan') setTrace((t) => [...t, e])
        else if (e.type === 'opportunities') setStrategic(e.data || [])
        else if (e.type === 'radar') setRadar(e.data || [])
        else if (e.type === 'artifact') { const a = e.data as Artifact; setArtifacts((m) => ({ ...m, [a.opportunity_id || a.id]: a })) }
        else if (e.type === 'discarded') { setLedger((l) => [...l, ...(e.data || [])]); setTrace((t) => [...t, e]) }
        else if (e.type === 'capabilities') setCaps(e.data || [])
        else if (e.type === 'monitors') setMonitorJobs(e.data || [])
      },
      () => setRunning(false),
      () => setRunning(false),
    ).then((es) => { esRef.current = es })
  }

  function openTrace(e: Ev) {
    if (e.type === 'finding' && e.data?.url) { window.open(e.data.url, '_blank'); return }
    openInTab(e.label || e.type,
      `<h1>${escapeHtml(e.label || e.type)}</h1>${e.model ? `<div class="meta">${escapeHtml(e.model)}</div>` : ''}` +
      `<pre>${escapeHtml(JSON.stringify(e.data || e.detail || {}, null, 2))}</pre>`)
  }

  const started = trace.length > 0 || profile || objective

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <div className="wordmark"><span className="mark">◆</span> StratCMO</div>
          <div className="sub">market intelligence that acts like a cofounder, not a tracker</div>
        </div>
        {started && momentum && <MomentumChip m={momentum} onClick={() => setTab('momentum')} unreadEdge={!!edge && edge.state === 'unread'} />}
        <div className="controls">
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="company url e.g. resend.com" onKeyDown={(e) => e.key === 'Enter' && run()} />
          <div className="toggle">
            <button className={mode === 'cached' ? 'on' : ''} onClick={() => setMode('cached')}>cached</button>
            <button className={mode === 'live' ? 'on' : ''} onClick={() => setMode('live')}>live</button>
          </div>
          <button className="run" onClick={run} disabled={running}>{running ? 'running…' : 'Run agent'}</button>
        </div>
      </header>

      {!started && (
        <div className="empty">
          <h1>Point it at a company. Get a CMO cofounder's read.</h1>
          <p>Stage-right objective · where your customers actually are · non-obvious wedges · specific threads to engage, with drafts.</p>
        </div>
      )}

      {started && (
        <nav className="tabs">
          <div className="tabgroup">
            {TABS.filter((t) => t.tier === 'primary').map((t) => (
              <button key={t.id} className={'tab' + (tab === t.id ? ' on' : '')} onClick={() => setTab(t.id)}>
                {t.label}
                {t.id === 'monitors' && monitorJobs.length > 0 && <span className="tabcount">{monitorJobs.length}</span>}
                {t.id === 'reasoning' && ledger.length > 0 && <span className="tabcount">{ledger.length}</span>}
              </button>
            ))}
          </div>
          <span className="tabdivider" aria-hidden="true" />
          <div className="tabgroup secondary">
            {TABS.filter((t) => t.tier === 'secondary').map((t) => (
              <button key={t.id} className={'tab' + (tab === t.id ? ' on' : '')} onClick={() => setTab(t.id)}>
                {t.label}
                {t.id === 'monitors' && monitorJobs.length > 0 && <span className="tabcount">{monitorJobs.length}</span>}
                {t.id === 'reasoning' && ledger.length > 0 && <span className="tabcount">{ledger.length}</span>}
              </button>
            ))}
          </div>
        </nav>
      )}

      {started && tab === 'brief' && (
        <BriefTab {...{ objective, profile, companyType, sources, radar, strategic, artifacts, ledger, trace, running, openTrace, url }} />
      )}
      {started && tab === 'actions' && <ActionBoard url={url} radar={radar} artifacts={artifacts} onMomentum={onMomentum} />}
      {started && tab === 'momentum' && (
        <Momentum url={url} m={momentum} companyType={companyType} edge={edge}
          onMomentum={onMomentum} onGoToBoard={() => setTab('actions')}
          onEdgeRead={() => setEdge((e) => e ? { ...e, state: 'read' } : e)} />
      )}
      {tab === 'synap' && <SynapTab url={url} />}
      {tab === 'monitors' && <MonitorsTab url={url} jobs={monitorJobs} />}
      {tab === 'reasoning' && <ReasoningTab ledger={ledger} />}
      {tab === 'capabilities' && <CapabilitiesTab caps={caps} trace={trace} />}

      {toast && (
        <div className="toast" onClick={() => setToast(null)}>
          <div className="toast-head">✦ {toast.awarded > 0 ? `+${toast.awarded}` : ''} {toastTitle(toast)}</div>
          <div className="toast-breakdown">{toast.breakdown.join(' · ')}</div>
          {toast.streak_safe && <div className="toast-streak">🔥 streak safe for today — {toast.current_streak} days</div>}
        </div>
      )}

      {levelUp && (
        <div className="levelup-overlay" onClick={() => setLevelUp(null)}>
          <div className="levelup-card" onClick={(e) => e.stopPropagation()}>
            <div className="levelup-glyph">{PERSONA_GLYPH[levelUp.to] || '◆'}</div>
            <div className="levelup-kicker">New level</div>
            <h2>{levelUp.title}</h2>
            <p>{levelUp.blurb}</p>
            <button className="run" onClick={() => setLevelUp(null)}>Keep going</button>
          </div>
        </div>
      )}
    </div>
  )
}

function toastTitle(a: MomentumAward): string {
  if (a.kind === 'card_posted') {
    if (a.breakdown.some((b) => b.includes('first time'))) return 'Shipped — first time on a new platform. That took guts.'
    return 'Shipped. You hit send.'
  }
  if (a.kind === 'card_engaged') return 'Someone engaged — that’s real traction.'
  if (a.kind === 'card_approved') return 'Draft approved.'
  if (a.kind === 'card_reviewed') return 'Draft sharpened.'
  if (a.kind === 'lesson_read') return 'Edge read.'
  return 'Nice move.'
}

function ObjectiveBanner({ objective, profile }: { objective: Objective; profile: Profile | null }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="objbanner">
      <div className="objtop">
        <span className="objlabel">OBJECTIVE{profile?.stage ? ' · ' + profile.stage : ''}</span>
        {(objective.reasoning || objective.not_this) &&
          <button className="objtoggle" onClick={() => setOpen(!open)}>{open ? 'hide reasoning ▴' : 'why ▾'}</button>}
      </div>
      <div className="objtext">{objective.objective}</div>
      {open && (
        <div className="objdetail">
          {objective.reasoning && <div className="objwhy">{objective.reasoning}</div>}
          {objective.not_this && <div className="objnot">Not: {objective.not_this}</div>}
        </div>
      )}
    </div>
  )
}

function ProfileBar({ profile }: { profile: Profile }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="profilebar">
      <div className="profrow" onClick={() => setOpen(!open)}>
        <span><b>{profile.name}</b> — {profile.one_liner}</span>
        <span className="chev">{open ? '−' : '+'}</span>
      </div>
      {open && (
        <div className="profdetail muted">
          {profile.category} · ICP: {profile.icp}
          {profile.competitors?.length > 0 && <div>vs {profile.competitors.join(', ')}</div>}
        </div>
      )}
    </div>
  )
}

function BriefTab({ objective, profile, companyType, sources, radar, strategic, artifacts, ledger, trace, running, openTrace, url }: any) {
  const hasBrief = !running && (objective || sources.length || radar.length || strategic.length)
  return (
    <>
      {hasBrief && (
        <div className="briefactions">
          <button className="mini" onClick={() => downloadBriefPdf({ url, objective, profile, companyType, sources, radar, strategic, artifacts, ledger })}>
            ⬇ Save brief as PDF
          </button>
        </div>
      )}
      {objective && <ObjectiveBanner objective={objective} profile={profile} />}
      <div className="grid">
        <aside className="rail">
          <div className="railhead">Agent trace {running && <span className="spin" />}</div>
          <div className="tracelist">
            {trace.map((e: Ev, i: number) => (
              <div key={i} className={'titem t-' + e.type} onClick={() => openTrace(e)} title="open in tab ↗">
                <span className="tdot" style={{ background: modelColor(e.model) }} />
                <span className="tlabel">{e.label}</span>
                {e.model && <Badge model={e.model} />}
              </div>
            ))}
            {!trace.length && <div className="muted">run the agent to watch it think…</div>}
          </div>
        </aside>

        <main className="main">
          {profile && <ProfileBar profile={profile} />}

          {sources.length > 0 && (
            <section className="card">
              <h3>Where your customers actually are <span className="muted">{companyType}</span></h3>
              <div className="sourcemap">
                {sources.map((s: Source, i: number) => (
                  <div className="srcchip" key={i} title={s.why}><b>{s.name}</b><span className="srckind">{s.access}</span></div>
                ))}
              </div>
            </section>
          )}

          {radar.length > 0 && (
            <section className="card">
              <h3>Engagement radar <span className="muted">specific places to show up — with drafts</span></h3>
              {radar.map((o: Opp) => <RadarCard key={o.id} o={o} art={artifacts[o.id]} />)}
            </section>
          )}

          {strategic.length > 0 && (
            <section className="card">
              <h3>Prioritized moves</h3>
              {PRIORITIES.map((p) => {
                const list = strategic.filter((o: Opp) => (o.priority || 'P1').toUpperCase().startsWith(p))
                if (!list.length) return null
                return <div key={p} className="prigroup">{list.map((o: Opp) => <OpportunityCard key={o.id} o={o} />)}</div>
              })}
            </section>
          )}

          {(strategic.length > 0 || radar.length > 0) && (
            <OpenUIPanel profile={profile} objective={objective} strategic={strategic} radar={radar} />
          )}

          {(strategic.length > 0 || radar.length > 0) && profile && (
            <LandingPanel profile={profile} objective={objective} />
          )}

          <ChatDock url={url} />
        </main>
      </div>
    </>
  )
}

function SynapTab({ url }: { url: string }) {
  const [mem, setMem] = useState<MemoryView | null>(null)
  const [busy, setBusy] = useState(false)
  async function load() {
    setBusy(true)
    try { setMem(await memoryView(url)) } catch { /* ignore */ }
    setBusy(false)
  }
  useEffect(() => { load() }, [url])
  return (
    <div className="tabpanel">
      <div className="panelhead">
        <div>
          <h2>Maximem Synap <span className="muted">the company's durable market brain</span></h2>
          <p className="panellede">Every run recalls what's known, reasons, then writes back. This is the memory that makes run #2 sharper than run #1, and compounds across monitors.</p>
        </div>
        <button className="mini" onClick={load} disabled={busy}>{busy ? 'loading…' : 'refresh'}</button>
      </div>

      <div className="synaploop">
        <span className="loopnode">recall</span><span className="looparrow">→</span>
        <span className="loopnode">reason</span><span className="looparrow">→</span>
        <span className="loopnode write">write</span><span className="looparrow">↺</span>
      </div>

      {mem && (
        <div className="memstat">
          <span className={'memdot ' + (mem.active ? 'on' : '')} />
          {mem.active ? 'Synap connected' : 'local fallback brain'} · {mem.facts.length} facts · {mem.episodes.length} episodes
        </div>
      )}

      {mem?.formatted_context && (
        <section className="card">
          <h3>Recalled context</h3>
          <pre className="memctx">{mem.formatted_context.slice(0, 4000)}</pre>
        </section>
      )}

      {mem && mem.facts.length > 0 && (
        <section className="card">
          <h3>Stored facts <span className="muted">{mem.facts.length}</span></h3>
          <div className="memitems">
            {mem.facts.slice(0, 40).map((f: any, i: number) => (
              <div className="memitem" key={i}>
                {f.kind && <span className="memkind">{f.kind}</span>}
                <span>{f.text || f.fact || f.content || JSON.stringify(f).slice(0, 200)}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {mem && !mem.facts.length && !busy && (
        <div className="muted empty-inline">
          {mem.processing
            ? `Indexing ${mem.processing} ${mem.processing === 1 ? 'memory' : 'memories'} in Synap. Writes are queued; facts surface once Synap finishes processing. Hit refresh shortly.`
            : 'No memory yet for this company. Run the agent once, then come back, the brain fills in.'}
        </div>
      )}
    </div>
  )
}

function MonitorsTab({ url, jobs }: { url: string; jobs: MonitorJob[] }) {
  const [changelog, setChangelog] = useState<ChangelogEntry[]>([])
  const [stored, setStored] = useState<MonitorJob[]>([])
  const [busy, setBusy] = useState(false)
  const [ran, setRan] = useState(false)
  async function load() {
    try { const r = await monitorsView(url); setStored(r.jobs || []); setChangelog(r.changelog || []) } catch { /* ignore */ }
  }
  useEffect(() => { load() }, [url])
  async function runNow() {
    setBusy(true); setRan(false)
    try { const r = await runMonitors(url); setChangelog(r.changelog || []); setRan(true) } catch { /* ignore */ }
    setBusy(false)
  }
  const list = jobs.length ? jobs : stored
  return (
    <div className="tabpanel">
      <div className="panelhead">
        <div>
          <h2>Recurring monitors <span className="muted">the agent self-identified what to watch</span></h2>
          <p className="panellede">These run automatically on their cadence. Each run diffs against Synap and records only what's new, so you read deltas, not repeats.</p>
        </div>
        <button className="run" onClick={runNow} disabled={busy || !list.length}>{busy ? 'running…' : 'Run monitors now'}</button>
      </div>

      {!list.length && <div className="muted empty-inline">No monitors yet. Run an analysis, the agent decides what's worth watching.</div>}

      <div className="monitorgrid">
        {list.map((m, i) => (
          <div className="monitorcard" key={i}>
            <div className="monitorhead"><b>{m.name}</b><span className="cadence">{m.cadence}</span></div>
            <div className="muted monitorq">{m.query}</div>
            <div className="monitorwhy">{m.rationale}</div>
            <span className="srckind">{m.access}</span>
          </div>
        ))}
      </div>

      {(changelog.length > 0 || ran) && (
        <section className="card">
          <h3>What's new <span className="muted">delta feed</span></h3>
          {!changelog.length && <div className="muted">No deltas yet. The last run found nothing new.</div>}
          {changelog.map((c, i) => (
            <div className="changelog" key={i}>
              <div className="changehead"><b>{c.monitor}</b><span className="muted">{(c.at || '').slice(0, 16).replace('T', ' ')}</span></div>
              <div className="why">{c.summary}</div>
              {c.new?.length > 0 && <ul className="changenew">{c.new.map((n, j) => <li key={j}>{n}</li>)}</ul>}
            </div>
          ))}
        </section>
      )}
    </div>
  )
}

function ReasoningTab({ ledger }: { ledger: Discarded[] }) {
  const stages = ['plan', 'reflect', 'synthesize']
  return (
    <div className="tabpanel">
      <div className="panelhead">
        <div>
          <h2>Reasoning log <span className="muted">ideas considered and discarded</span></h2>
          <p className="panellede">The roads not taken, with reasons. So you don't have to wonder whether the agent was thorough.</p>
        </div>
      </div>
      {!ledger.length && <div className="muted empty-inline">No discarded ideas captured this run.</div>}
      {stages.map((st) => {
        const items = ledger.filter((d) => d.stage === st)
        if (!items.length) return null
        return (
          <section className="card" key={st}>
            <h3>Ruled out at {st}</h3>
            {items.map((d, i) => (
              <div className="discard" key={i}>
                <div className="discardidea">{d.idea}</div>
                <div className="discardwhy muted">{d.reason}</div>
              </div>
            ))}
          </section>
        )
      })}
    </div>
  )
}

function CapabilitiesTab({ caps, trace }: { caps: Capability[]; trace: Ev[] }) {
  // fall back to trace-derived bindings if the final snapshot hasn't arrived
  const liveBound = trace.filter((e) => e.type === 'tool_bound' || e.type === 'skill_bound')
  const tools = caps.filter((c) => c.kind === 'tool')
  const skills = caps.filter((c) => c.kind === 'skill')
  return (
    <div className="tabpanel">
      <div className="panelhead">
        <div>
          <h2>Capabilities <span className="muted">tools and skills, bound at runtime</span></h2>
          <p className="panellede">The agent isn't limited to what it had at plan-time. When it needs a tool or a channel voice it lacks, it discovers and binds one on the fly.</p>
        </div>
      </div>

      {!caps.length && !liveBound.length && <div className="muted empty-inline">Run the agent to see which tools and skills it binds.</div>}

      {tools.length > 0 && (
        <section className="card">
          <h3>Tools</h3>
          <div className="capgrid">
            {tools.map((c, i) => (
              <div className={'capcard ' + (c.bound_at === 'runtime' ? 'discovered' : '')} key={i}>
                <div className="caphead"><b>{c.slug || c.name}</b>
                  <span className={'capsrc ' + c.source}>{c.bound_at === 'runtime' ? 'discovered' : c.source}</span></div>
                {c.why && <div className="muted capwhy">{c.why}</div>}
              </div>
            ))}
          </div>
        </section>
      )}

      {skills.length > 0 && (
        <section className="card">
          <h3>Writing skills</h3>
          <div className="capgrid">
            {skills.map((c, i) => (
              <div className={'capcard ' + (c.source === 'generated' ? 'discovered' : '')} key={i}>
                <div className="caphead"><b>{c.name.replace('skill:', '')}</b>
                  <span className={'capsrc ' + c.source}>{c.source}</span></div>
                {c.why && <div className="muted capwhy">{c.why}</div>}
              </div>
            ))}
          </div>
        </section>
      )}

      {!caps.length && liveBound.length > 0 && (
        <section className="card">
          <h3>Binding live…</h3>
          {liveBound.map((e, i) => (
            <div className="discard" key={i}><div className="discardidea">{e.label}</div></div>
          ))}
        </section>
      )}
    </div>
  )
}

function OpenUIPanel({ profile, objective, strategic, radar }: any) {
  const [html, setHtml] = useState('')
  const [busy, setBusy] = useState(false)
  const [via, setVia] = useState('')
  async function gen() {
    setBusy(true)
    try {
      const r = await uiRender({ profile, objective, opportunities: strategic, radar })
      setHtml(r.html || ''); setVia(r.via || '')
    } catch { /* ignore */ }
    setBusy(false)
  }
  return (
    <section className="card">
      <h3>Live view <span className="muted">a bespoke dashboard generated by OpenUI</span>
        <button className="mini" style={{ marginLeft: 'auto' }} onClick={gen} disabled={busy}>{busy ? 'generating…' : '✨ generate'}</button>
        {via && <span className="muted">via {via}</span>}
      </h3>
      {html
        ? <iframe className="openui-frame" srcDoc={html} title="OpenUI generated view" />
        : <div className="muted">generate a bespoke, company-specific dashboard view with OpenUI.</div>}
    </section>
  )
}

// #4 — generate a single-use-case landing page spec, then a copyable, stack-agnostic
// Claude Code prompt the founder pastes into their own repo's coding agent. The prompt is
// generated lazily, on click — not by default.
function LandingPanel({ profile, objective }: { profile: Profile | null; objective: Objective | null }) {
  const [useCase, setUseCase] = useState('')
  const [spec, setSpec] = useState<any>(null)
  const [prompt, setPrompt] = useState('')
  const [busy, setBusy] = useState(false)
  const [pbusy, setPbusy] = useState(false)
  const [copied, setCopied] = useState(false)

  async function gen() {
    setBusy(true); setPrompt('')
    try {
      const r = await landingSpec({ profile, objective, use_case: useCase.trim() })
      setSpec(r.spec || null)
    } catch { /* ignore */ }
    setBusy(false)
  }
  async function genPrompt() {
    setPbusy(true)
    try {
      const r = await landingPrompt(spec, profile?.name || '')
      setPrompt(r.prompt || '')
    } catch { /* ignore */ }
    setPbusy(false)
  }
  function copyPrompt() {
    navigator.clipboard?.writeText(prompt)
    setCopied(true); setTimeout(() => setCopied(false), 1400)
  }

  return (
    <section className="card">
      <h3>Landing page <span className="muted">one use-case, handed to your coding agent</span></h3>
      <p className="muted" style={{ marginTop: 4 }}>A dedicated page per use-case beats a generic homepage. We write the page; you paste a prompt into your repo's Claude Code and it builds it in your stack.</p>
      <div className="landinggen">
        <input value={useCase} onChange={(e) => setUseCase(e.target.value)} placeholder="optional: a specific use-case (else we pick the sharpest)" />
        <button className="mini" onClick={gen} disabled={busy || !profile}>{busy ? 'writing…' : '✨ Generate page'}</button>
      </div>

      {spec && (
        <div className="landingspec">
          {spec.positioning_oneliner && <div className="landingpos">“{spec.positioning_oneliner}”</div>}
          {spec.use_case && <div className="muted landinguc">for: {spec.use_case}</div>}
          {spec.headline && <div className="landingh1">{spec.headline}</div>}
          {spec.subhead && <div className="landingsub">{spec.subhead}</div>}
          {Array.isArray(spec.sections) && spec.sections.length > 0 && (
            <ol className="landingsections">
              {spec.sections.map((s: any, i: number) => (
                <li key={i}><b>{s.heading}</b>{s.purpose ? <span className="muted"> · {s.purpose}</span> : null}</li>
              ))}
            </ol>
          )}
          <div className="draftactions" style={{ marginTop: 12 }}>
            <button onClick={genPrompt} disabled={pbusy}>{pbusy ? 'building prompt…' : 'Generate Claude Code prompt'}</button>
          </div>
        </div>
      )}

      {prompt && (
        <div className="draft" style={{ marginTop: 12 }}>
          <div className="drafthead">Paste this into Claude Code in your repo</div>
          <pre className="draftbody">{prompt}</pre>
          <div className="draftactions">
            <button onClick={copyPrompt}>{copied ? 'copied ✓' : 'copy prompt'}</button>
          </div>
        </div>
      )}
    </section>
  )
}

function ChatDock({ url }: { url: string }) {
  const [msgs, setMsgs] = useState<{ role: string; text: string; model?: string }[]>([])
  const [inp, setInp] = useState('')
  const [busy, setBusy] = useState(false)
  const [research, setResearch] = useState(false)
  async function send() {
    const m = inp.trim(); if (!m || busy) return
    setInp(''); setMsgs((x) => [...x, { role: 'user', text: m }]); setBusy(true)
    try {
      const r = research ? await researchApi(url, m) : await chatApi(url, m)
      setMsgs((x) => [...x, { role: 'assistant', text: (research ? r.takeaways : r.reply) || '(no result)', model: r.model }])
    } catch { setMsgs((x) => [...x, { role: 'assistant', text: '(error)' }]) }
    setBusy(false)
  }
  return (
    <section className="card chat">
      <h3>Chat with your CMO
        <button className={'mini ' + (research ? 'on' : '')} onClick={() => setResearch(!research)}>{research ? 'research mode' : 'chat mode'}</button>
      </h3>
      <div className="msgs">
        {msgs.map((m, i) => (
          <div key={i} className={'msg ' + m.role}><div className="msgtext">{m.text}</div>{m.model && <Badge model={m.model} />}</div>
        ))}
        {busy && <div className="msg assistant"><div className="msgtext muted">thinking…</div></div>}
        {!msgs.length && <div className="muted">ask anything — or flip to research mode to trigger a fresh web pull.</div>}
      </div>
      <div className="chatinput">
        <input value={inp} onChange={(e) => setInp(e.target.value)} placeholder={research ? 'research a question live…' : 'ask your CMO cofounder…'} onKeyDown={(e) => e.key === 'Enter' && send()} />
        <button onClick={send} disabled={busy}>send</button>
      </div>
    </section>
  )
}
