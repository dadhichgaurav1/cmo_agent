import { useRef, useState } from 'react'
import { analyze, chatApi, researchApi, openInTab, escapeHtml } from './api'
import type { Ev, Profile, Objective, Source, Opp, Artifact } from './types'

function modelColor(m?: string) {
  if (!m) return '#94a3b8'
  if (m.includes('sonnet')) return '#c084fc'
  if (m.includes('haiku')) return '#67e8f9'
  if (m.includes('gpt')) return '#34d399'
  if (m.includes('exa')) return '#fbbf24'
  if (m.includes('hackernews')) return '#fb923c'
  if (m.includes('synap')) return '#f472b6'
  return '#94a3b8'
}

function Badge({ model }: { model?: string }) {
  if (!model) return null
  const c = modelColor(model)
  return <span className="badge" style={{ color: c, borderColor: c + '55' }}>{model}</span>
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
      <div className="radarhead"><span className="radardot" /><span className="opptitle">{o.title}</span></div>
      <p className="why">{o.why}</p>
      <div className="radarmeta">
        {o.source_name && <span className="chip">{o.source_name}</span>}
        {o.template_id && <span className="chip ghost">{o.template_id}</span>}
        {o.thread_url && <a href={o.thread_url} target="_blank" rel="noreferrer" className="chip link">open thread ↗</a>}
      </div>
      {art && (
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

export default function App() {
  const [url, setUrl] = useState('resend.com')
  const [mode, setMode] = useState<'cached' | 'live'>('cached')
  const [running, setRunning] = useState(false)
  const [trace, setTrace] = useState<Ev[]>([])
  const [profile, setProfile] = useState<Profile | null>(null)
  const [objective, setObjective] = useState<Objective | null>(null)
  const [companyType, setCompanyType] = useState('')
  const [sources, setSources] = useState<Source[]>([])
  const [strategic, setStrategic] = useState<Opp[]>([])
  const [radar, setRadar] = useState<Opp[]>([])
  const [artifacts, setArtifacts] = useState<Record<string, Artifact>>({})
  const esRef = useRef<EventSource | null>(null)

  function run() {
    if (running || !url.trim()) return
    setRunning(true); setTrace([]); setProfile(null); setObjective(null); setSources([]); setCompanyType('')
    setStrategic([]); setRadar([]); setArtifacts({})
    esRef.current = analyze(url.trim(), mode,
      (e) => {
        if (e.type === 'step' || e.type === 'memory' || e.type === 'finding' || e.type === 'reflect') setTrace((t) => [...t, e])
        else if (e.type === 'profile') setProfile(e.data)
        else if (e.type === 'objective') { setObjective(e.data); setTrace((t) => [...t, e]) }
        else if (e.type === 'sources') { setSources(e.data?.sources || []); setCompanyType(e.data?.company_type || ''); setTrace((t) => [...t, e]) }
        else if (e.type === 'plan') setTrace((t) => [...t, e])
        else if (e.type === 'opportunities') setStrategic(e.data || [])
        else if (e.type === 'radar') setRadar(e.data || [])
        else if (e.type === 'artifact') { const a = e.data as Artifact; setArtifacts((m) => ({ ...m, [a.opportunity_id || a.id]: a })) }
      },
      () => setRunning(false),
      () => setRunning(false),
    )
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
        <div className="brand">◆ CMO Cofounder<span className="sub">market intelligence that acts like a cofounder, not a tracker</span></div>
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

      {objective && (
        <div className="objbanner">
          <div className="objlabel">OBJECTIVE{profile?.stage ? ' · ' + profile.stage : ''}</div>
          <div className="objtext">{objective.objective}</div>
          {objective.reasoning && <div className="objwhy">{objective.reasoning}</div>}
          {objective.not_this && <div className="objnot">Not: {objective.not_this}</div>}
        </div>
      )}

      <div className="grid">
        <aside className="rail">
          <div className="railhead">Agent trace {running && <span className="spin" />}</div>
          <div className="tracelist">
            {trace.map((e, i) => (
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
          {profile && (
            <div className="profilebar">
              <b>{profile.name}</b> — {profile.one_liner}
              <div className="muted">{profile.category} · ICP: {profile.icp}</div>
            </div>
          )}

          {sources.length > 0 && (
            <section className="card">
              <h3>Where your customers actually are <span className="muted">{companyType}</span></h3>
              <div className="sourcemap">
                {sources.map((s, i) => (
                  <div className="srcchip" key={i} title={s.why}><b>{s.name}</b><span className="srckind">{s.access}</span></div>
                ))}
              </div>
            </section>
          )}

          {radar.length > 0 && (
            <section className="card">
              <h3>Engagement radar <span className="muted">specific places to show up — with drafts</span></h3>
              {radar.map((o) => <RadarCard key={o.id} o={o} art={artifacts[o.id]} />)}
            </section>
          )}

          {strategic.length > 0 && (
            <section className="card">
              <h3>Prioritized moves</h3>
              {PRIORITIES.map((p) => {
                const list = strategic.filter((o) => (o.priority || 'P1').toUpperCase().startsWith(p))
                if (!list.length) return null
                return <div key={p} className="prigroup">{list.map((o) => <OpportunityCard key={o.id} o={o} />)}</div>
              })}
            </section>
          )}

          {started && <ChatDock url={url} />}
        </main>
      </div>
    </div>
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
