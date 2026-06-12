import type { Ev } from './types'

const EVENT_TYPES = [
  'step', 'memory', 'profile', 'objective', 'sources', 'plan',
  'finding', 'reflect', 'opportunities', 'radar', 'artifact',
  'tool_bound', 'skill_bound', 'capabilities', 'discarded', 'monitors', 'update',
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

export async function uiRender(payload: any) {
  const r = await fetch('/api/ui/render', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return r.json()
}

function slugify(url: string): string {
  const host = (url || '').toLowerCase().replace(/^https?:\/\//, '').split('/')[0]
  return host.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'company'
}

export async function memoryView(url: string) {
  const r = await fetch(`/api/memory/${slugify(url)}`)
  return r.json()
}

export async function monitorsView(url: string) {
  const r = await fetch(`/api/monitors/${slugify(url)}`)
  return r.json()
}

export async function runMonitors(url: string) {
  const r = await fetch(`/api/monitors/${slugify(url)}/run`, { method: 'POST' })
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
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Newsreader:wght@400;500&display=swap" rel="stylesheet">
  <style>body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#faf9f5;color:#211f1c;max-width:720px;margin:48px auto;padding:0 24px;line-height:1.65}
  h1{font-family:'Newsreader',Georgia,serif;font-weight:500;font-size:23px;letter-spacing:-.01em}pre{white-space:pre-wrap;word-break:break-word;background:#fff;padding:18px;border-radius:12px;border:1px solid #e7e2d8;font-size:13px}
  a{color:#c2603f}.meta{color:#8b857a;font-size:12px;margin-bottom:18px}</style></head><body>${bodyHtml}</body></html>`)
  w.document.close()
}
