import { useEffect, useState } from 'react'
import { Footer } from './Landing'
import { usageView, startCheckout, openBillingPortal } from './api'
import { track, register, setOrg } from './analytics'

const FREE = [
  '1 company',
  '1 strategic run / week (+3 to start)',
  '10 agent chats / day, advice & drafts',
  'Action Board, momentum, streaks & the Daily Edge',
  'Create monitors & preview what they’d catch',
]

const PRO = [
  'Everything in Free, plus:',
  'Monitors fire daily, auto-refilling your board with fresh threads',
  'Unlimited re-runs, manual or automated (fair use)',
  'Agent chat that acts, not just advises',
  'Run StratCMO across all your products',
]

export function Pricing() {
  const [plan, setPlan] = useState<string>('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    track('pricing_viewed')
    usageView().then((u) => {
      setPlan(u?.plan || '')
      if (u?.plan) register({ plan: u.plan })
      if (u?.org_id) setOrg(u.org_id, { plan: u.plan })
    }).catch(() => {})
  }, [])

  const isPro = plan === 'pro'

  async function onCta() {
    if (busy) return
    if (!plan) { track('cta_clicked', { location: 'pricing_start_free' }); window.location.href = '/app'; return } // not signed in → start free
    setBusy(true)
    track(isPro ? 'portal_opened' : 'checkout_started', { source: 'pricing' })
    try {
      const r = isPro ? await openBillingPortal() : await startCheckout()
      if (r?.detail && !r?.url) alert(typeof r.detail === 'string' ? r.detail : 'Billing is not available right now.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="lp">
      <header className="lp-nav">
        <a className="lp-brand" href="/"><span className="mark">◆</span> StratCMO</a>
        <nav className="lp-navlinks">
          <a href="/#features">What it does</a>
          <a href="/#how">How it works</a>
        </nav>
        <div className="lp-navcta">
          <button className="lp-btn" onClick={() => (window.location.href = '/app')}>Open the app</button>
        </div>
      </header>

      <main className="pricing">
        <h1>Simple pricing</h1>
        <p className="pricing-sub">
          Free is the cold start and the manual loop. Pro is the engine that keeps your board full:
          monitors that wake up daily and refill it with fresh places to post.
        </p>

        <div className="pricing-grid">
          <div className="plan">
            <div className="plan-name">Free</div>
            <div className="plan-price">$0<span>/forever</span></div>
            <ul className="plan-feats">
              {FREE.map((f) => <li key={f}>{f}</li>)}
            </ul>
            <button className="lp-btn ghost" onClick={() => (window.location.href = '/app')}>
              Start free
            </button>
          </div>

          <div className="plan featured">
            <div className="plan-badge">Operator</div>
            <div className="plan-name">Pro</div>
            <div className="plan-price">$49<span>/month</span></div>
            <div className="plan-note">or $390/yr · founding rate $39/mo · 14-day trial</div>
            <ul className="plan-feats">
              {PRO.map((f) => <li key={f}>{f}</li>)}
            </ul>
            <button className="lp-btn" disabled={busy} onClick={onCta}>
              {isPro ? 'Manage billing' : busy ? 'One sec…' : 'Upgrade to Pro'}
            </button>
          </div>
        </div>

        <p className="pricing-foot">
          Fair-use limits apply to unlimited plans to keep things sustainable. Questions?{' '}
          <a href="mailto:gaurav@maximem.ai">gaurav@maximem.ai</a>
        </p>
      </main>

      <Footer />
    </div>
  )
}
