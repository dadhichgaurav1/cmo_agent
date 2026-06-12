import { useEffect, useState } from 'react'

export default function App() {
  const [health, setHealth] = useState<string>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((d) => setHealth(d.ok ? 'online' : 'down'))
      .catch(() => setHealth('unreachable'))
  }, [])

  return (
    <div className="wrap">
      <div className="card">
        <div className="logo">◆ CMO Cofounder</div>
        <p className="tag">An autonomous CMO cofounder for founders — not a tracker.</p>
        <div className={`status ${health === 'online' ? 'online' : 'pending'}`}>
          API: {health}
        </div>
        <p className="phase">Phase 0 — skeleton deployed. The agent lands in Phase 1.</p>
      </div>
    </div>
  )
}
