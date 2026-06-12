import type { Ev } from './types'

const EVENT_TYPES = [
  'step', 'memory', 'profile', 'objective', 'sources', 'plan',
  'finding', 'reflect', 'opportunities', 'radar', 'artifact',
]

export function analyze(
  url: string,
  mode: string,
  onEv: (e: Ev) => void,
  onDone: () => void,
  onErr: (m: string) => void,
): EventSource {
  const es = new EventSource(`/api/analyze/stream?url=${encodeURIComponent(url)}&mode=${mode}`)
  let finished = false
  for (const t of EVENT_TYPES) {
    es.addEventListener(t, (e: MessageEvent) => {
      try { onEv(JSON.parse(e.data)) } catch { /* ignore */ }
    })
  }
  es.addEventListener('done', (e: MessageEvent) => {
    try { onEv(JSON.parse(e.data)) } catch { /* ignore */ }
    finished = true
    onDone()
    es.close()
  })
  es.addEventListener('error', (e: any) => {
    if (finished) return
    if (e?.data) { try { onErr(JSON.parse(e.data).label) } catch { /* ignore */ } }
    finished = true
    onErr('stream ended')
    es.close()
  })
  return es
}

export async function chatApi(url: string, message: string) {
  const r = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, message }),
  })
  return r.json()
}

export async function researchApi(url: string, query: string) {
  const r = await fetch('/api/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, query }),
  })
  return r.json()
}

export function escapeHtml(s: string): string {
  return (s || '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string
  ))
}

// Open any agent artifact/reasoning in a standalone tab for inspection.
export function openInTab(title: string, bodyHtml: string) {
  const w = window.open('', '_blank')
  if (!w) return
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
  <style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0f;color:#e7e7ea;max-width:760px;margin:48px auto;padding:0 24px;line-height:1.65}
  h1{font-size:19px;letter-spacing:-.01em}pre{white-space:pre-wrap;word-break:break-word;background:#15151c;padding:18px;border-radius:12px;border:1px solid #23232b;font-size:13px}
  a{color:#67e8f9}.meta{color:#8b8b95;font-size:12px;margin-bottom:18px}</style></head><body>${bodyHtml}</body></html>`)
  w.document.close()
}
