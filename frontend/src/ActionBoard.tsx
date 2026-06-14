import { useEffect, useState } from 'react'
import { listCards, patchCard, deleteCard, generateCards, createCliToken, setFeeder } from './api'
import { PLATFORMS, cardAction, classifyPlatform } from './deeplinks'
import type { ActionCard, CardState, Opp, Artifact } from './types'

// Minimal mint UI for the build-in-public CLI skill. The full Settings home is deferred;
// the board is where CLI-pushed cards land, so set-up belongs here.
function CliSetup({ url }: { url: string }) {
  const [open, setOpen] = useState(false)
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const slug = (url || '').toLowerCase().replace(/^https?:\/\//, '').split('/')[0].replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
  async function mint() {
    setBusy(true)
    try { const r = await createCliToken('build-in-public CLI'); setToken(r.token || '') } catch { /* ignore */ }
    setBusy(false)
  }
  return (
    <div className="clisetup">
      <button className="clitoggle" onClick={() => setOpen(!open)}>
        {open ? '−' : '+'} Post build-in-public from your editor
      </button>
      {open && (
        <div className="clibody">
          <p className="muted">Install the StratCMO skill in Claude Code. It reads your git log locally and pushes a
            drafted post here. Your code never leaves your machine — only the post text does.</p>
          {!token
            ? <button className="mini" onClick={mint} disabled={busy}>{busy ? 'minting…' : 'Generate CLI token'}</button>
            : (
              <div className="clitoken">
                <div className="muted">Copy this token now — it is shown once:</div>
                <pre className="draftbody">{token}</pre>
                <div className="muted">Then set it up:</div>
                <pre className="draftbody">{`export STRATCMO_TOKEN=${token}\nexport STRATCMO_SLUG=${slug}`}</pre>
                <button className="mini" onClick={() => navigator.clipboard?.writeText(token)}>copy token</button>
              </div>
            )}
        </div>
      )}
    </div>
  )
}

// Workflow columns. Platform is fixed per card (it's a Reddit reply or it isn't), so the
// only meaningful motion is advancing a card through these states — done with a button,
// not drag-drop. Swimlanes (rows) are platforms; columns are the workflow.
const COLUMNS: { id: string; label: string; states: CardState[] }[] = [
  { id: 'review', label: 'To review', states: ['suggested', 'drafted'] },
  { id: 'approved', label: 'Approved', states: ['approved'] },
  { id: 'posted', label: 'Posted', states: ['posted', 'engaged'] },
]
const bucketOf = (s: CardState) =>
  COLUMNS.find((c) => c.states.includes(s))?.id ?? null  // null = dismissed (hidden)

// Derive ephemeral cards from the live run already in App state, so the board has content
// in demo/local mode (no Supabase) and immediately after a run, before any server seed.
function deriveLocalCards(radar: Opp[], artifacts: Record<string, Artifact>): ActionCard[] {
  return (radar || [])
    .filter((o) => o.type === 'engagement' || o.thread_url)
    .map((o) => {
      const art = artifacts[o.id]
      const thread = o.thread_url || ''
      const body = art?.body || ''
      return {
        id: `local-${o.id}`,
        platform: classifyPlatform(o.source_name, o.template_id, art?.channel, thread),
        kind: thread ? 'reply' : 'post',
        target_url: thread || null,
        target_title: o.title,
        title: o.title,
        body,
        state: (body ? 'drafted' : 'suggested') as CardState,
        metadata: { why: o.why },
        _local: true,
      }
    })
}

function CardView({ card, onChange, onDismiss }: {
  card: ActionCard; onChange: (patch: Partial<ActionCard>) => void; onDismiss: () => void
}) {
  const [copied, setCopied] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(card.body)
  const act = cardAction(card)
  const bucket = bucketOf(card.state)

  function copy() {
    navigator.clipboard?.writeText(card.body)
    setCopied(true); setTimeout(() => setCopied(false), 1200)
  }
  function open() {
    if (act.openUrl) window.open(act.openUrl, '_blank', 'noopener')
  }

  return (
    <div className={'swimcard ' + bucket + (card.state === 'engaged' ? ' engaged' : '')}>
      <div className="swimcardhead">
        <span className="swimkind">{card.kind === 'post' ? 'new post' : 'reply'}</span>
        <button className="swimx" title="dismiss" onClick={onDismiss}>×</button>
      </div>
      {card.target_url
        ? <a className="swimtitle link" href={card.target_url} target="_blank" rel="noreferrer">{card.target_title || card.title} ↗</a>
        : <div className="swimtitle">{card.target_title || card.title}</div>}
      {card.metadata?.why && <div className="swimwhy">{card.metadata.why}</div>}

      {editing ? (
        <div className="swimedit">
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={6} />
          <div className="swimactions">
            <button onClick={() => { onChange({ body: draft }); setEditing(false) }}>save</button>
            <button className="ghost" onClick={() => { setDraft(card.body); setEditing(false) }}>cancel</button>
          </div>
        </div>
      ) : card.body ? (
        <pre className="swimbody" onClick={() => setEditing(true)} title="click to edit">{card.body}</pre>
      ) : (
        <div className="swimnodraft">No draft yet — generate or write one.</div>
      )}

      <div className="swimactions">
        {card.body && <button onClick={copy}>{copied ? 'copied ✓' : 'copy'}</button>}
        <button onClick={open} disabled={!act.openUrl} className={act.prefills ? 'prefill' : ''}>
          {act.openLabel} ↗
        </button>
        {bucket === 'review' && <button className="adv" onClick={() => onChange({ state: 'approved' })}>approve →</button>}
        {bucket === 'approved' && <button className="adv" onClick={() => onChange({ state: 'posted' })}>mark posted ✓</button>}
        {card.state === 'posted' && <button className="ghost" onClick={() => onChange({ state: 'engaged' })}>got a reply ⭐</button>}
        {card.state === 'engaged' && <span className="swimengaged">⭐ engaged</span>}
        {!card.body && !editing && <button className="ghost" onClick={() => setEditing(true)}>write</button>}
      </div>
      {!act.prefills && card.body && bucket !== 'posted' && (
        <div className="swimhint">copy · open · paste — you press send</div>
      )}
      {card.body && card.metadata?.review && (card.metadata.review.flags?.length || card.metadata.review.note) && (
        <div className={'swimreview ' + (card.metadata.review.level || 'ok')}>
          {card.metadata.review.flags?.length > 0 && (
            <ul>{card.metadata.review.flags.map((f: string, i: number) => <li key={i}>{f}</li>)}</ul>
          )}
          <div className="swimreview-note">{card.metadata.review.note}</div>
        </div>
      )}
    </div>
  )
}

export default function ActionBoard({ url, radar, artifacts, onMomentum }: {
  url: string; radar: Opp[]; artifacts: Record<string, Artifact>
  onMomentum?: (award: any) => void
}) {
  const [cards, setCards] = useState<ActionCard[]>([])
  const [busy, setBusy] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [note, setNote] = useState('')
  const [serverBacked, setServerBacked] = useState(false)
  const [feeder, setFeederOn] = useState(false)

  async function load() {
    setBusy(true)
    try {
      const r = await listCards(url)
      const got: ActionCard[] = r.cards || []
      setFeederOn(!!r.feeder)
      if (got.length) { setCards(got); setServerBacked(true) }
      else { setCards(deriveLocalCards(radar, artifacts)); setServerBacked(false) }
    } catch {
      setCards(deriveLocalCards(radar, artifacts)); setServerBacked(false)
    }
    setBusy(false)
  }

  async function toggleFeeder() {
    const next = !feeder
    setFeederOn(next)  // optimistic
    try { await setFeeder(url, next) } catch { setFeederOn(!next) }
  }

  async function generate() {
    setGenerating(true); setNote('')
    try {
      const r = await generateCards(url)
      if (r.created > 0) { await load(); setNote(`${r.created} fresh ${r.created === 1 ? 'card' : 'cards'} drafted`) }
      else setNote('No new threads found this round. Try again later, or run an analysis first.')
    } catch { setNote('Could not generate cards.') }
    setGenerating(false)
  }
  useEffect(() => { load() }, [url])  // eslint-disable-line react-hooks/exhaustive-deps
  // when a fresh run lands new radar/artifacts and we have no server cards, reflect them
  useEffect(() => {
    if (!serverBacked) setCards(deriveLocalCards(radar, artifacts))
  }, [radar, artifacts])  // eslint-disable-line react-hooks/exhaustive-deps

  function applyLocal(id: string, patch: Partial<ActionCard>) {
    setCards((cs) => cs.map((c) => (c.id === id ? { ...c, ...patch } : c)))
  }
  function onChange(card: ActionCard, patch: Partial<ActionCard>) {
    applyLocal(card.id, patch)
    if (!card._local) {
      patchCard(card.id, patch)
        .then((r) => { if (r?.momentum && onMomentum) onMomentum(r.momentum) })  // toast the award
        .catch(() => {})
    }
  }
  function onDismiss(card: ActionCard) {
    setCards((cs) => cs.filter((c) => c.id !== card.id))
    if (!card._local) deleteCard(card.id).catch(() => {})
  }

  const visible = cards.filter((c) => bucketOf(c.state))
  const lanes = PLATFORMS.filter((p) => visible.some((c) => c.platform === p.id))
  const cardsIn = (platform: string, col: string) =>
    visible.filter((c) => c.platform === platform && bucketOf(c.state) === col)

  return (
    <div className="tabpanel">
      <div className="panelhead">
        <div>
          <h2>Action Board <span className="muted">specific places to post — drafted, ready to ship</span></h2>
          <p className="panellede">One swimlane per platform. Copy the draft, open the thread, paste, and you press send.
            StratCMO drafts and queues; it never posts for you.</p>
        </div>
        <div className="panelactions">
          {note && <span className="muted boardnote">{note}</span>}
          <button className={'feedertoggle' + (feeder ? ' on' : '')} onClick={toggleFeeder}
            title="When on, the board auto-refills with fresh drafted cards once a day">
            <span className="feederdot" />Auto-refill daily {feeder ? 'on' : 'off'}
          </button>
          <button className="mini" onClick={load} disabled={busy || generating}>{busy ? 'loading…' : 'refresh'}</button>
          <button className="run" onClick={generate} disabled={generating || busy}>
            {generating ? 'finding threads…' : '✨ Generate cards'}
          </button>
        </div>
      </div>

      {!visible.length && (
        <div className="muted empty-inline">
          No cards yet. Run an analysis — its engagement opportunities and drafts land here as cards.
        </div>
      )}

      {!!lanes.length && (
        <div className="board">
          <div className="boardrow boardhead">
            <div className="lanelabel" />
            {COLUMNS.map((c) => <div key={c.id} className="colhead">{c.label}</div>)}
          </div>
          {lanes.map((p) => (
            <div className="boardrow lane" key={p.id}>
              <div className="lanelabel">{p.label}<span className="lanecount">{visible.filter((c) => c.platform === p.id).length}</span></div>
              {COLUMNS.map((col) => (
                <div className="lanecell" key={col.id}>
                  {cardsIn(p.id, col.id).map((card) => (
                    <CardView key={card.id} card={card}
                      onChange={(patch) => onChange(card, patch)} onDismiss={() => onDismiss(card)} />
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      <CliSetup url={url} />
    </div>
  )
}
