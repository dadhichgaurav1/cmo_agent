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
      <Problem />
      <Returns />
      <Features />
      <HowItWorks onEnter={onEnter} />
      <Founder />
      <Compare />
      <Proof />
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

function Problem() {
  const beats = [
    'Your buyers are answering each other in subreddits, Slacks and threads you don’t even know exist — and your competitors are already in there.',
    'You’ve tried the tools. They count mentions and hand you a dashboard. A dashboard is not a decision.',
    'You don’t need more data about the market. You need someone who tells you the next move — and drafts it.',
  ]
  return (
    <section className="lp-problem">
      <span className="lp-kicker">The job nobody trained you for</span>
      <h2>You can build the product. Nobody taught you the marketing.</h2>
      <div className="lp-problem-beats">
        {beats.map((b, i) => (
          <p className="lp-problem-beat" key={i}>{b}</p>
        ))}
      </div>
      <div className="lp-problem-bridge">That’s the read StratCMO gives you.</div>
    </section>
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
        <h2>One job, done end to end: get into the right room with the right words.</h2>
      </div>

      {/* The one thing — locate + draft, the headline capability */}
      <Feature
        verb="Locate + draft"
        title="Find the room. Walk in with the right line."
        body="StratCMO maps the subreddits, communities and threads your buyers actually use — ranked by how warm each one is — then drafts the reply for the ones worth joining, in a voice that fits the room. Copy it, edit it, send it."
        art={
          <div className="lp-fart">
            <div className="lp-mock-sources">
              <span className="lp-mock-chip">r/SaaS <em>warm</em></span>
              <span className="lp-mock-chip">Indie Hackers <em>open</em></span>
              <span className="lp-mock-chip">Hacker News <em>earn it</em></span>
              <span className="lp-mock-chip">Lenny's Slack <em>gated</em></span>
            </div>
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

      {/* …and it keeps working — secondary capabilities, demoted to a compact row */}
      <div className="lp-subhead"><h3>…and it keeps working for you.</h3></div>
      <div className="lp-minigrid">
        <MiniFeature
          verb="Prioritize"
          title="The moves worth making, ranked."
          body="Opportunities arrive ranked P0–P2 with impact, effort and steps — a plan to execute, not a list to triage."
          art={
            <>
              <div className="lp-mock-move"><span className="pri p0">P0</span><span>Deliverability teardown on Hacker News</span></div>
              <div className="lp-mock-move"><span className="pri p1">P1</span><span>Seed an Indie Hackers migration thread</span></div>
              <div className="lp-mock-move"><span className="pri p2">P2</span><span>Ship a “Postmark vs.” page</span></div>
            </>
          }
        />
        <MiniFeature
          verb="Remember"
          title="Run #2 is sharper than #1."
          body="Synap — the company's durable memory — recalls what's known, reasons, then writes back, so context compounds across runs."
          art={
            <>
              <div className="lp-mock-loop">
                <span className="lp-loopnode">recall</span><span className="lp-looparrow">→</span>
                <span className="lp-loopnode">reason</span><span className="lp-looparrow">→</span>
                <span className="lp-loopnode write">write</span><span className="lp-looparrow">↺</span>
              </div>
              <div className="lp-mock-memline">128 facts · 9 episodes · connected</div>
            </>
          }
        />
        <MiniFeature
          verb="Watch"
          title="Read what changed, not another dashboard."
          body="The agent sets recurring monitors and surfaces only what's new — a feed of changes, not noise."
          art={
            <>
              <div className="lp-mock-monitor">
                <div className="lp-mock-monitorhead"><b>Competitor pricing</b><span className="lp-cadence">weekly</span></div>
              </div>
              <div className="lp-mock-delta">+ Mailgun cut its free tier — 2 threads already complaining.</div>
            </>
          }
        />
      </div>

      <p className="lp-truststrip">
        And every brief <b>shows its work</b> — the ideas it ruled out, with reasons, and the tools
        it bound along the way. No black box.
      </p>
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

function MiniFeature({ verb, title, body, art }: {
  verb: string; title: string; body: string; art: React.ReactNode
}) {
  return (
    <div className="lp-mini">
      <div className="lp-verb">{verb}</div>
      <h4>{title}</h4>
      <p>{body}</p>
      <div className="lp-mini-art">{art}</div>
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

/**
 * Founder demo — a 60–90s screen recording of a real run. High-trust for an
 * unproven tool. Renders nothing until FOUNDER_VIDEO is set to an embed URL,
 * so we never ship an empty placeholder. Fill in at launch.
 */
const FOUNDER_VIDEO = '' // e.g. 'https://www.loom.com/embed/<id>'

function Founder() {
  if (!FOUNDER_VIDEO) return null
  return (
    <section className="lp-founder">
      <div className="lp-section-head">
        <span className="lp-kicker">Watch a real run</span>
        <h2>Ninety seconds, one URL, a full brief.</h2>
      </div>
      <div className="lp-video">
        <iframe src={FOUNDER_VIDEO} title="StratCMO walkthrough" allowFullScreen />
      </div>
    </section>
  )
}

/**
 * Social proof. Populate TESTIMONIALS with real beta-user quotes before driving
 * traffic — never ship invented ones. Empty array → section renders nothing.
 */
const TESTIMONIALS: { quote: string; name: string; role: string }[] = []

function Proof() {
  if (TESTIMONIALS.length === 0) return null
  return (
    <section className="lp-proof">
      <div className="lp-section-head">
        <span className="lp-kicker">From the founders using it</span>
        <h2>Built with the people it's for.</h2>
      </div>
      <div className="lp-proof-grid">
        {TESTIMONIALS.map((t, i) => (
          <figure className="lp-quote" key={i}>
            <blockquote>{t.quote}</blockquote>
            <figcaption><b>{t.name}</b> · {t.role}</figcaption>
          </figure>
        ))}
      </div>
    </section>
  )
}

function Compare() {
  const rows = [
    { f: 'Finds where buyers actually gather', chat: 'generic guess', dash: 'mentions only', us: true },
    { f: 'Drafts the reply in the room’s voice', chat: 'sometimes', dash: false, us: true },
    { f: 'Tells you what to do next, ranked', chat: false, dash: false, us: true },
    { f: 'Remembers your company across runs', chat: false, dash: false, us: true },
    { f: 'Reports only what changed', chat: false, dash: 'partial', us: true },
  ]
  const cell = (v: boolean | string) =>
    v === true ? <span className="lp-yes">✓</span>
      : v === false ? <span className="lp-no">—</span>
        : <span className="lp-partial">{v}</span>
  return (
    <section className="lp-compare">
      <div className="lp-section-head">
        <span className="lp-kicker">Why not just a chatbot</span>
        <h2>Trackers tell you what happened. A cofounder tells you what to do.</h2>
      </div>
      <div className="lp-table-wrap">
        <table className="lp-table">
          <thead>
            <tr>
              <th />
              <th>Generic AI chatbot</th>
              <th>Listening dashboard</th>
              <th className="us">StratCMO</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.f}>
                <td className="lp-rowlabel">{r.f}</td>
                <td>{cell(r.chat)}</td>
                <td>{cell(r.dash)}</td>
                <td className="us">{cell(r.us)}</td>
              </tr>
            ))}
          </tbody>
        </table>
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

export function Footer() {
  return (
    <footer className="lp-footer">
      <div className="lp-footer-brand">
        <span className="mark">◆</span> StratCMO
        <span className="lp-footer-by">by Maximem</span>
      </div>
      <nav className="lp-footer-links">
        <a href="/pricing">Pricing</a>
        <a href="/terms">Terms</a>
        <a href="/privacy">Privacy</a>
        <a href="mailto:gaurav@maximem.ai">Support</a>
      </nav>
      <div className="lp-footer-copy">© {2026} Maximem. All rights reserved.</div>
    </footer>
  )
}
