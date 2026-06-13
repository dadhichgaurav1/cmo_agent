import type { Momentum } from './types'

// Glyph per persona tier — the identity made visible (carried mostly by the words, §6.3).
export const PERSONA_GLYPH: Record<string, string> = {
  lurker: '👁',
  first_blood: '🩸',
  poster: '✍',
  regular: '📣',
  operator: '🜂',
  distribution_machine: '🛰',
}

/** Compact header signal that pulls into the Momentum page. The flame is the loss-aversion
 *  hook; it goes hollow with a nudge on a day you haven't shipped yet (§8.1). */
export default function MomentumChip({ m, onClick, unreadEdge }: {
  m: Momentum | null
  onClick: () => void
  unreadEdge?: boolean
}) {
  if (!m) return null
  const lit = m.shipped_today
  const flameTitle = lit
    ? `Streak safe for today — ${m.current_streak}-day streak`
    : 'Ship one thing to keep your streak'
  return (
    <button className="momentumchip" onClick={onClick} title="Your momentum">
      <span className={'mc-flame' + (lit ? ' lit' : '')} title={flameTitle}>🔥</span>
      <span className="mc-streak">{m.current_streak}</span>
      <span className="mc-sep">·</span>
      <span className="mc-pts">⚡{m.total_points.toLocaleString()}</span>
      <span className="mc-sep">·</span>
      <span className="mc-persona">{PERSONA_GLYPH[m.persona_key] || '◆'} {m.persona_title}</span>
      {unreadEdge && <span className="mc-dot" title="New Daily Edge" />}
    </button>
  )
}
