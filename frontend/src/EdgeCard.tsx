import { useEffect, useRef, useState } from 'react'
import { readEdge } from './api'
import type { Lesson, MomentumAward } from './types'

/** The Daily Edge: one tailored marketing-psychology lesson, tied to the founder's own work,
 *  that ends by pointing at a real card on their board (a Trojan horse for the next send). */
export default function EdgeCard({ lesson, onMomentum, onGoToBoard }: {
  lesson: Lesson
  onMomentum?: (a: MomentumAward) => void
  onGoToBoard?: () => void
}) {
  const [state, setState] = useState(lesson.state)
  const marked = useRef(false)

  // Mark read once when the founder sees it (fires lesson_read +1).
  useEffect(() => {
    if (marked.current || state !== 'unread') return
    marked.current = true
    readEdge(lesson.id).then((r) => {
      setState('read')
      if (r?.momentum && onMomentum) onMomentum(r.momentum)
    }).catch(() => {})
  }, [lesson.id])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="edge-card">
      <div className="edge-head">
        <span className="edge-kicker">Today’s Edge</span>
        {lesson.tie_back?.platform && (
          <span className="chip">tied to your {lesson.tie_back.platform} draft</span>
        )}
      </div>
      <h2 className="edge-title">{lesson.title}</h2>
      <div className="edge-body">
        {lesson.body.split('\n').filter(Boolean).map((p, i) => <p key={i}>{p}</p>)}
      </div>
      {lesson.cta_card_id && onGoToBoard && (
        <button className="run edge-cta" onClick={onGoToBoard}>
          {lesson.cta_label || 'Apply it on your board'} →
        </button>
      )}
    </div>
  )
}
