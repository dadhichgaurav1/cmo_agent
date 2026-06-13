import { useEffect, useMemo, useState } from 'react'
import { getMomentumEvents } from './api'
import { PERSONA_GLYPH } from './MomentumChip'
import type { Momentum as Mom, MomentumEvent } from './types'

const KIND_LABEL: Record<string, string> = {
  card_posted: 'Shipped',
  card_reviewed: 'Sharpened a draft',
  card_approved: 'Approved a draft',
  card_engaged: 'Got engagement',
  lesson_read: 'Read the Edge',
  lesson_applied: 'Applied the Edge',
}

// Ops (serious/B2B) vs Hype (indie/consumer) — same data, different skin (§6.4).
function inferSkin(companyType?: string): 'ops' | 'hype' {
  return /b2b|saas|enterprise|infra|api|dev|platform|fintech|security/i.test(companyType || '') ? 'ops' : 'hype'
}

function localDayKeys(n: number): string[] {
  const out: string[] = []
  const d = new Date()
  for (let i = 0; i < n; i++) {
    const dd = new Date(d.getFullYear(), d.getMonth(), d.getDate() - i)
    const k = `${dd.getFullYear()}-${String(dd.getMonth() + 1).padStart(2, '0')}-${String(dd.getDate()).padStart(2, '0')}`
    out.push(k)
  }
  return out.reverse()
}

export default function Momentum({ url, m, companyType }: { url: string; m: Mom | null; companyType?: string }) {
  const [events, setEvents] = useState<MomentumEvent[]>([])
  const [skin, setSkin] = useState<'ops' | 'hype'>(() =>
    (localStorage.getItem('momentum_skin') as 'ops' | 'hype') || inferSkin(companyType))

  useEffect(() => {
    getMomentumEvents(url).then((r) => setEvents(r.events || [])).catch(() => {})
  }, [url, m?.total_points])

  function flipSkin() {
    const next = skin === 'ops' ? 'hype' : 'ops'
    setSkin(next); localStorage.setItem('momentum_skin', next)
  }

  // Calendar: which of the last 30 local days had a ship vs only a lesson.
  const { shipDays, lessonDays } = useMemo(() => {
    const ship = new Set<string>(), lesson = new Set<string>()
    for (const e of events) {
      if (e.kind === 'card_posted') ship.add(e.day_key)
      else if (e.kind === 'lesson_read' || e.kind === 'lesson_applied') lesson.add(e.day_key)
    }
    return { shipDays: ship, lessonDays: lesson }
  }, [events])
  const days = useMemo(() => localDayKeys(30), [])

  if (!m) {
    return <div className="tabpanel"><p className="panellede">Momentum is turned off for this workspace.</p></div>
  }

  const ships = m.ships_total
  const toNext = m.next_persona_at != null ? Math.max(0, m.next_persona_at - ships) : 0
  const pct = m.next_persona_at ? Math.min(100, Math.round((ships / m.next_persona_at) * 100)) : 100
  const dayOne = ships === 0

  return (
    <div className={`tabpanel momentum skin-${skin}`}>
      <div className="momentum-top">
        <span className="muted">{skin === 'ops' ? 'Operator dashboard' : 'Your momentum'}</span>
        <button className="skin-toggle" onClick={flipSkin} title="Switch tone">
          {skin === 'ops' ? '⚙ Ops' : '🔥 Hype'}
        </button>
      </div>

      {/* Persona card */}
      <div className="persona-card">
        <div className="persona-glyph">{PERSONA_GLYPH[m.persona_key] || '◆'}</div>
        <div className="persona-body">
          <h2>{m.persona_title} <span className="muted">· {m.total_points.toLocaleString()} pts</span></h2>
          <p className="persona-blurb">{m.persona_blurb}</p>
          {m.next_persona_title && (
            <>
              <div className="persona-bar"><span style={{ width: `${pct}%` }} /></div>
              <p className="muted">{toNext} more {toNext === 1 ? 'ship' : 'ships'} to {m.next_persona_title}</p>
            </>
          )}
        </div>
      </div>

      {dayOne && (
        <div className="empty-momentum">
          <p><strong>Your first ship is worth double.</strong> Most founders never send one.</p>
          <p className="muted">Open the Action Board, copy a draft, post it, and hit “mark posted”. That’s the whole game.</p>
        </div>
      )}

      {/* Stat row */}
      <div className="stat-row">
        <Stat n={m.current_streak} label="day streak" hint={m.shipped_today ? 'safe today 🔥' : 'ship to keep it'} />
        <Stat n={m.freezes_left} label="freezes left" />
        <Stat n={ships} label="total ships" />
        <Stat n={m.ships_this_week} label="this week" />
        <Stat n={m.platforms_shipped.length} label="platforms" />
      </div>
      {m.platforms_shipped.length > 0 && (
        <p className="muted platforms">Shipped on: {m.platforms_shipped.join(' · ')}</p>
      )}

      {/* Streak calendar */}
      <h3 className="momentum-h3">Last 30 days</h3>
      <div className="streak-cal">
        {days.map((k) => {
          const cls = shipDays.has(k) ? 'ship' : lessonDays.has(k) ? 'lesson' : 'none'
          return <span key={k} className={`cal-cell ${cls}`} title={`${k}${cls === 'ship' ? ' · shipped' : cls === 'lesson' ? ' · read the Edge' : ''}`} />
        })}
      </div>
      <p className="cal-legend muted"><span className="cal-cell ship" /> shipped &nbsp; <span className="cal-cell lesson" /> learned &nbsp; <span className="cal-cell none" /> quiet</p>

      {/* History */}
      <h3 className="momentum-h3">Recent activity</h3>
      {events.length === 0 ? (
        <p className="muted">No moves yet — your activity will show up here.</p>
      ) : (
        <ul className="momentum-feed">
          {events.slice(0, 40).map((e) => (
            <li key={e.id}>
              <span className="feed-pts">+{e.points}</span>
              <span className="feed-kind">{KIND_LABEL[e.kind] || e.kind}</span>
              {e.platform && <span className="chip">{e.platform}</span>}
              <span className="feed-day muted">{e.day_key}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Stat({ n, label, hint }: { n: number; label: string; hint?: string }) {
  return (
    <div className="stat">
      <div className="stat-n">{n}</div>
      <div className="stat-label">{label}</div>
      {hint && <div className="stat-hint muted">{hint}</div>}
    </div>
  )
}
