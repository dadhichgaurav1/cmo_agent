import type { Ev } from './types'
import { accessToken } from './supabase'

const EVENT_TYPES = [
  'step', 'memory', 'profile', 'objective', 'sources', 'plan',
  'finding', 'reflect', 'opportunities', 'radar', 'artifact',
  'tool_bound', 'skill_bound', 'capabilities', 'discarded', 'monitors', 'update',
]

// JSON headers + bearer token when signed in (no-op in demo mode).
async function jsonHeaders(): Promise<Record<string, string>> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' }
  const t = await accessToken()
  if (t) h.Authorization = `Bearer ${t}`
  return h
}

async function authedHeaders(): Promise<Record<string, string>> {
  const t = await accessToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

export async function analyze(
  url: string,
  mode: string,
  onEv: (e: Ev) => void,
  onDone: () => void,
  onErr: (m: string) => void,
): Promise<EventSource> {
  // EventSource can't set headers, so the token rides as a query param (backend accepts both).
  const t = await accessToken()
  const tok = t ? `&access_token=${encodeURIComponent(t)}` : ''
  const es = new EventSource(`/api/analyze/stream?url=${encodeURIComponent(url)}&mode=${mode}${tok}`)
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
    headers: await jsonHeaders(),
    body: JSON.stringify({ url, message }),
  })
  return r.json()
}

export async function researchApi(url: string, query: string) {
  const r = await fetch('/api/research', {
    method: 'POST',
    headers: await jsonHeaders(),
    body: JSON.stringify({ url, query }),
  })
  return r.json()
}

export async function uiRender(payload: any) {
  const r = await fetch('/api/ui/render', {
    method: 'POST',
    headers: await jsonHeaders(),
    body: JSON.stringify(payload),
  })
  return r.json()
}

export async function landingSpec(payload: { profile: any; objective: any; use_case?: string }) {
  const r = await fetch('/api/landing/spec', { method: 'POST', headers: await jsonHeaders(), body: JSON.stringify(payload) })
  return r.json()
}

export async function landingPrompt(spec: any, company: string) {
  const r = await fetch('/api/landing/prompt', { method: 'POST', headers: await jsonHeaders(), body: JSON.stringify({ spec, company }) })
  return r.json()
}

function slugify(url: string): string {
  const host = (url || '').toLowerCase().replace(/^https?:\/\//, '').split('/')[0]
  return host.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'company'
}

export async function memoryView(url: string) {
  const r = await fetch(`/api/memory/${slugify(url)}`, { headers: await authedHeaders() })
  return r.json()
}

export async function monitorsView(url: string) {
  const r = await fetch(`/api/monitors/${slugify(url)}`, { headers: await authedHeaders() })
  return r.json()
}

export async function runMonitors(url: string) {
  const r = await fetch(`/api/monitors/${slugify(url)}/run`, { method: 'POST', headers: await authedHeaders() })
  return r.json()
}

export async function runsView() {
  const r = await fetch('/api/runs', { headers: await authedHeaders() })
  return r.json()
}

// --- action board ---------------------------------------------------------
export async function listCards(url: string) {
  const r = await fetch(`/api/cards?slug=${slugify(url)}`, { headers: await authedHeaders() })
  return r.json()
}

export async function createCard(payload: any) {
  const r = await fetch('/api/cards', { method: 'POST', headers: await jsonHeaders(), body: JSON.stringify(payload) })
  return r.json()
}

export async function patchCard(id: string, patch: any) {
  const r = await fetch(`/api/cards/${id}`, { method: 'PATCH', headers: await jsonHeaders(), body: JSON.stringify(patch) })
  return r.json()
}

export async function deleteCard(id: string) {
  const r = await fetch(`/api/cards/${id}`, { method: 'DELETE', headers: await authedHeaders() })
  return r.json()
}

export async function generateCards(url: string, platforms?: string[], perPlatform = 2) {
  const r = await fetch('/api/cards/generate', {
    method: 'POST', headers: await jsonHeaders(),
    body: JSON.stringify({ slug: slugify(url), platforms, per_platform: perPlatform }),
  })
  return r.json()
}

export async function setFeeder(url: string, enabled: boolean) {
  const r = await fetch('/api/cards/feeder', {
    method: 'POST', headers: await jsonHeaders(),
    body: JSON.stringify({ slug: slugify(url), enabled }),
  })
  return r.json()
}

// --- momentum (founder activation score) ----------------------------------
export async function getMomentum(url: string) {
  const r = await fetch(`/api/momentum?slug=${slugify(url)}`, { headers: await authedHeaders() })
  return r.json()
}

export async function getMomentumEvents(url: string, since?: string) {
  const q = since ? `&since=${encodeURIComponent(since)}` : ''
  const r = await fetch(`/api/momentum/events?slug=${slugify(url)}${q}`, { headers: await authedHeaders() })
  return r.json()
}

export async function setOrgTimezone(timezone: string) {
  const r = await fetch('/api/org/timezone', {
    method: 'POST', headers: await jsonHeaders(), body: JSON.stringify({ timezone }),
  })
  return r.json()
}

// CLI personal access token for the build-in-public skill. Raw token returned once.
export async function createCliToken(label: string) {
  const r = await fetch('/api/cli-tokens', { method: 'POST', headers: await jsonHeaders(), body: JSON.stringify({ label }) })
  return r.json()
}

export async function usageView() {
  const r = await fetch('/api/usage', { headers: await authedHeaders() })
  return r.json()
}

// Redirects the browser to Stripe Checkout / Customer Portal.
export async function startCheckout() {
  const r = await fetch('/api/billing/checkout', { method: 'POST', headers: await authedHeaders() })
  const j = await r.json()
  if (j.url) window.location.href = j.url
  return j
}

export async function openBillingPortal() {
  const r = await fetch('/api/billing/portal', { method: 'POST', headers: await authedHeaders() })
  const j = await r.json()
  if (j.url) window.location.href = j.url
  return j
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

// Open a print-optimized document (A4, page breaks, no app chrome) and let the
// browser's print dialog save it as a PDF. A "Save as PDF" button is offered for
// the user to click when ready; it hides itself in the printed output.
export function openPrintable(title: string, bodyHtml: string) {
  const w = window.open('', '_blank')
  if (!w) return
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Newsreader:wght@400;500&display=swap" rel="stylesheet">
  <style>
    @page { size: A4; margin: 18mm 16mm; }
    *{box-sizing:border-box}
    body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#211f1c;max-width:760px;margin:0 auto;padding:32px 28px 64px;line-height:1.6}
    h1{font-family:'Newsreader',Georgia,serif;font-weight:500;font-size:26px;letter-spacing:-.01em;margin:0 0 2px}
    h2{font-family:'Newsreader',Georgia,serif;font-weight:500;font-size:18px;margin:26px 0 8px;border-bottom:1px solid #e7e2d8;padding-bottom:5px;page-break-after:avoid}
    h3{font-size:14px;margin:14px 0 3px}
    p{margin:6px 0}
    .meta{color:#8b857a;font-size:12px;margin-bottom:18px}
    .doc-objective{font-size:16px;line-height:1.5;background:#faf9f5;border:1px solid #e7e2d8;border-radius:10px;padding:14px 16px;margin:8px 0}
    .doc-why{color:#5c574e;font-size:13px;margin-top:6px}
    .doc-not{color:#9a5436;font-size:13px;margin-top:4px}
    .doc-item{border:1px solid #e7e2d8;border-radius:10px;padding:12px 14px;margin:8px 0;page-break-inside:avoid}
    .doc-pri{font-weight:600;font-size:11px;letter-spacing:.04em;color:#c2603f;margin-right:6px}
    .doc-sub{color:#8b857a;font-size:12px;margin:2px 0 6px}
    .doc-chip{display:inline-block;font-size:11px;color:#5c574e;background:#f3f0e8;border-radius:6px;padding:2px 7px;margin:0 5px 4px 0}
    .doc-draft{white-space:pre-wrap;word-break:break-word;background:#faf9f5;border:1px solid #e7e2d8;border-radius:8px;padding:12px;font-size:12.5px;margin-top:6px}
    ol,ul{margin:6px 0;padding-left:20px}li{margin:3px 0}
    a{color:#c2603f;text-decoration:none;word-break:break-all}
    .doc-actions{position:fixed;top:14px;right:14px;display:flex;gap:8px}
    .doc-actions button{font:inherit;font-size:13px;cursor:pointer;border:1px solid #d9d3c7;background:#211f1c;color:#faf9f5;border-radius:8px;padding:7px 14px}
    .doc-actions button.ghost{background:#fff;color:#211f1c}
    @media print { .doc-actions{display:none} body{padding-top:8px} }
  </style></head><body>
  <div class="doc-actions">
    <button onclick="window.print()">⬇ Save as PDF</button>
    <button class="ghost" onclick="window.close()">close</button>
  </div>
  ${bodyHtml}</body></html>`)
  w.document.close()
}
