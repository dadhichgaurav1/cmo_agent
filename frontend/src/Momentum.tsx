import { useEffect, useState } from 'react'
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

export default function Momentum({ url, m }: { url: string; m: Mom | null }) {
  const [events, setEvents] = useState<MomentumEvent[]>([])

  useEffect(() => {
    getMomentumEvents(url).then((r) => setEvents(r.events || [])).catch(() => {})
  }, [url, m?.total_points])

  if (!m) {
    return <div className="tabpanel"><p className="panellede">Momentum is turned off for this workspace.</p></div>
  }

  const ships = m.ships_total
  const toNext = m.next_persona_at != null ? Math.max(0, m.next_persona_at - ships) : 0
  const pct = m.next_persona_at ? Math.min(100, Math.round((ships / m.next_persona_at) * 100)) : 100

  return (
    <div className="tabpanel momentum">
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

      {/* History */}
      <h3 className="momentum-h3">Recent activity</h3>
      {events.length === 0 ? (
        <div className="empty-momentum">
          <p>No moves yet. Your first ship is worth double — and most founders never send one.</p>
          <p className="muted">Open the Action Board, copy a draft, post it, and mark it shipped.</p>
        </div>
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
