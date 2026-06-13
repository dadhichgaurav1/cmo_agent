/**
 * Public-facing homepage. Marketing surface for logged-out visitors at "/".
 * The "images" here are authentic product mockups built from the real app's
 * design language (objective banner, engagement radar, drafted reply, source
 * map) — not stock art — so what you see on the page is what you get in the app.
 *
 * `onEnter` routes into the product (/app), where AuthGate decides whether to
 * show the login screen (auth mode) or the app directly (demo mode).
 */
export function Landing({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="lp">
      <Nav onEnter={onEnter} />
      <Hero onEnter={onEnter} />
      <Returns />
      <Features />
      <HowItWorks onEnter={onEnter} />
      <CTA onEnter={onEnter} />
      <Footer />
    </div>
  )
}

function Nav({ onEnter }: { onEnter: () => void }) {
  return (
    <header className="lp-nav">
      <a className="lp-brand" href="#top">
        <span className="mark">◆</span> StratCMO
      </a>
      <nav className="lp-navlinks">
        <a href="#features">What it does</a>
        <a href="#how">How it works</a>
        <a href="#returns">What you get</a>
      </nav>
      <div className="lp-navcta">
        <button className="lp-link" onClick={onEnter}>Sign in</button>
        <button className="lp-btn" onClick={onEnter}>Analyze a company</button>
      </div>
    </header>
  )
}

function Hero({ onEnter }: { onEnter: () => void }) {
  return (
    <section className="lp-hero" id="top">
      <div className="lp-hero-copy">
        <div className="lp-eyebrow">Market intelligence that acts like a cofounder</div>
        <h1>Point it at a company.<br />Get a CMO cofounder's read.</h1>
        <p className="lp-lede">
          StratCMO finds the rooms where your buyers actually gather and hands you the reply
          that earns a response — ranked by what's worth doing first. You bring the URL.
        </p>
        <div className="lp-hero-actions">
          <button className="lp-btn lg" onClick={onEnter}>Analyze a company →</button>
        </div>
        <a className="lp-seehow" href="#how">or see how it works ↓</a>
        <div className="lp-hero-note">Free to run your first brief. No setup.</div>
      </div>
      <div className="lp-hero-art">
        <BriefMock />
      </div>
    </section>
  )
}

/** A faux app window showing a real brief: objective → radar + drafted reply → source map. */
function BriefMock() {
  return (
    <div className="lp-frame">
      <div className="lp-frame-bar">
        <span className="lp-dot" /><span className="lp-dot" /><span className="lp-dot" />
        <span className="lp-url">stratcmo.app · resend.com</span>
      </div>
      <div className="lp-frame-body">
        <div className="lp-mock-obj">
          <span className="objlabel">Objective · Seed</span>
          <div className="lp-mock-objtext">
            Own “transactional email that just works” in the indie-hacker stack before the
            incumbents notice the segment.
          </div>
        </div>

        <div className="lp-mock-sectionlabel">Engagement radar — with drafts</div>
        <div className="lp-mock-radar">
          <div className="lp-mock-radarhead">
            <span className="radardot" />
            <span className="opptitle">“Best Postmark alternative for a side project?” — r/SaaS</span>
          </div>
          <div className="lp-mock-draft">
            <div className="lp-mock-drafthead">Drafted reply <span className="lp-mini-badge">sonnet</span></div>
            <div className="lp-mock-draftbody">
              Been down this road. For a side project the deliverability tax matters more than
              the dashboard — three things I'd check before you commit…
            </div>
          </div>
        </div>

        <div className="lp-mock-sectionlabel">Where your customers actually are</div>
        <div className="lp-mock-sources">
          <span className="lp-mock-chip">r/SaaS <em>warm</em></span>
          <span className="lp-mock-chip">Indie Hackers <em>open</em></span>
          <span className="lp-mock-chip">Hacker News <em>earn it</em></span>
          <span className="lp-mock-chip">dev.to <em>open</em></span>
        </div>
      </div>
    </div>
  )
}

function Returns() {
  const items = [
    { k: 'A stage-right objective', v: 'One sentence, defensible — the goal a CMO would set for this exact stage.' },
    { k: 'A map of real channels', v: 'Where your buyers already gather, ranked by how reachable they are.' },
    { k: 'Threads + drafted replies', v: 'Specific conversations to join, each with an on-voice reply ready to send.' },
    { k: 'Ranked moves, P0–P2', v: 'Impact, effort and steps — a plan to execute, not a brainstorm to sort.' },
  ]
  return (
    <section className="lp-returns" id="returns">
      <div className="lp-section-head">
        <span className="lp-kicker">What lands in your brief</span>
        <h2>Every run returns something you can act on today.</h2>
      </div>
      <div className="lp-returns-grid">
        {items.map((it) => (
          <div className="lp-return" key={it.k}>
            <div className="lp-return-k">{it.k}</div>
            <div className="lp-return-v">{it.v}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function Features() {
  return (
    <section className="lp-features" id="features">
      <div className="lp-section-head">
        <span className="lp-kicker">What it does</span>
        <h2>It does the CMO work, then shows you the receipts.</h2>
      </div>

      <Feature
        verb="Locate"
        title="Find where your customers already are."
        body="StratCMO maps the subreddits, communities and threads your buyers actually use — and tells you how warm each one is before you spend a minute there."
        art={
          <div className="lp-fart">
            <div className="lp-mock-sources">
              <span className="lp-mock-chip">r/SaaS <em>warm</em></span>
              <span className="lp-mock-chip">Indie Hackers <em>open</em></span>
              <span className="lp-mock-chip">Hacker News <em>earn it</em></span>
              <span className="lp-mock-chip">Lenny's Slack <em>gated</em></span>
            </div>
          </div>
        }
      />

      <Feature
        flip
        verb="Draft"
        title="Show up with the reply that earns a response."
        body="For every thread worth joining, the agent drafts a reply in a voice that fits the room — specific, helpful, never salesy. Copy it, edit it, send it."
        art={
          <div className="lp-fart">
            <div className="lp-mock-draft tall">
              <div className="lp-mock-drafthead">Drafted reply <span className="lp-mini-badge">sonnet</span></div>
              <div className="lp-mock-draftbody">
                Been down this road. For a side project the deliverability tax matters more than
                the dashboard — here's what I'd check before committing, and where each option
                quietly falls down…
              </div>
              <div className="lp-mock-draftactions"><span>copy</span><span>open in tab ↗</span></div>
            </div>
          </div>
        }
      />

      <Feature
        verb="Prioritize"
        title="Get the three moves worth making this week."
        body="Opportunities arrive ranked P0 to P2, each with impact, effort and concrete steps — so you start at the top and execute, instead of triaging a list."
        art={
          <div className="lp-fart">
            <div className="lp-mock-move"><span className="pri p0">P0</span><span>Launch a deliverability teardown on Hacker News</span></div>
            <div className="lp-mock-move"><span className="pri p1">P1</span><span>Seed an Indie Hackers thread on migration pain</span></div>
            <div className="lp-mock-move"><span className="pri p2">P2</span><span>Publish a “Postmark vs.” comparison page</span></div>
          </div>
        }
      />

      <Feature
        flip
        verb="Remember"
        title="Run #2 is sharper than run #1."
        body="Synap is the company's durable market brain. Every run recalls what's known, reasons, then writes back — so context compounds instead of resetting each time."
        art={
          <div className="lp-fart">
            <div className="lp-mock-loop">
              <span className="lp-loopnode">recall</span><span className="lp-looparrow">→</span>
              <span className="lp-loopnode">reason</span><span className="lp-looparrow">→</span>
              <span className="lp-loopnode write">write</span><span className="lp-looparrow">↺</span>
            </div>
            <div className="lp-mock-memline">128 facts · 9 episodes · Synap connected</div>
          </div>
        }
      />

      <Feature
        verb="Watch"
        title="Read deltas, not dashboards."
        body="The agent decides what's worth watching and sets recurring monitors. Each run diffs against memory and surfaces only what's new — a feed of changes, not noise."
        art={
          <div className="lp-fart">
            <div className="lp-mock-monitor">
              <div className="lp-mock-monitorhead"><b>Competitor pricing moves</b><span className="lp-cadence">weekly</span></div>
              <div className="lp-mock-monitorq">pricing or free-tier changes across Postmark, Mailgun, SendGrid</div>
            </div>
            <div className="lp-mock-delta">+ Mailgun dropped its free tier to 100/day — 2 threads already complaining.</div>
          </div>
        }
      />

      <Feature
        flip
        verb="Show its work"
        title="Trust it was thorough — see what it ruled out."
        body="A reasoning log records the ideas the agent considered and discarded, with reasons. And it binds new tools and writing skills at runtime when a task needs them."
        art={
          <div className="lp-fart">
            <div className="lp-mock-discard"><div className="lp-mock-idea">Cold outbound to VP Marketing lists</div><div className="lp-mock-reason">Ruled out — wrong stage, burns reputation before product-market fit.</div></div>
            <div className="lp-mock-discard"><div className="lp-mock-idea">Paid search on “email API”</div><div className="lp-mock-reason">Ruled out — incumbents own the auction; CAC won't clear at seed.</div></div>
          </div>
        }
      />
    </section>
  )
}

function Feature({ verb, title, body, art, flip }: {
  verb: string; title: string; body: string; art: React.ReactNode; flip?: boolean
}) {
  return (
    <div className={'lp-feature' + (flip ? ' flip' : '')}>
      <div className="lp-feature-copy">
        <div className="lp-verb">{verb}</div>
        <h3>{title}</h3>
        <p>{body}</p>
      </div>
      <div className="lp-feature-art">{art}</div>
    </div>
  )
}

function HowItWorks({ onEnter }: { onEnter: () => void }) {
  const steps = [
    { n: '01', verb: 'Paste a URL', body: 'Drop in any company — yours or a competitor\'s. No onboarding, no integrations to wire up first.' },
    { n: '02', verb: 'Watch it think', body: 'The agent researches live and streams its trace: what it found, what it reasoned, which tools it bound.' },
    { n: '03', verb: 'Act on the brief', body: 'Send the drafts, work the ranked moves, and let the monitors run. Come back to deltas, not a blank page.' },
  ]
  return (
    <section className="lp-how" id="how">
      <div className="lp-section-head">
        <span className="lp-kicker">How it works</span>
        <h2>Three steps from URL to executable plan.</h2>
      </div>
      <div className="lp-steps">
        {steps.map((s) => (
          <div className="lp-step" key={s.n}>
            <div className="lp-step-n">{s.n}</div>
            <div className="lp-step-verb">{s.verb}</div>
            <p>{s.body}</p>
          </div>
        ))}
      </div>
      <div className="lp-how-cta">
        <button className="lp-btn lg" onClick={onEnter}>Run your first brief →</button>
      </div>
    </section>
  )
}

function CTA({ onEnter }: { onEnter: () => void }) {
  return (
    <section className="lp-band">
      <h2>Stop tracking the market. Start moving on it.</h2>
      <p>Point StratCMO at a company and get a cofounder's read in minutes.</p>
      <button className="lp-btn lg invert" onClick={onEnter}>Analyze a company →</button>
    </section>
  )
}

function Footer() {
  return (
    <footer className="lp-footer">
      <div className="lp-footer-brand">
        <span className="mark">◆</span> StratCMO
        <span className="lp-footer-by">by Maximem</span>
      </div>
      <nav className="lp-footer-links">
        <a href="#features">What it does</a>
        <a href="#how">How it works</a>
        <a href="/terms">Terms</a>
        <a href="/privacy">Privacy</a>
      </nav>
      <div className="lp-footer-copy">© {2026} Maximem. All rights reserved.</div>
    </footer>
  )
}
