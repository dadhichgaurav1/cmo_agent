import { Footer } from './Landing'

const EFFECTIVE = 'June 13, 2026'
const CONTACT = 'gaurav@maximem.ai'

/** Shared reading shell for the static legal pages — brand link home, prose column, footer. */
function LegalShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="lp">
      <header className="lp-nav">
        <a className="lp-brand" href="/">
          <span className="mark">◆</span> StratCMO
        </a>
        <nav className="lp-navlinks">
          <a href="/pricing">Pricing</a>
          <a href="/terms">Terms</a>
          <a href="/privacy">Privacy</a>
        </nav>
      </header>
      <main className="legal">
        <h1>{title}</h1>
        <p className="legal-meta">Effective {EFFECTIVE}</p>
        {children}
      </main>
      <Footer />
    </div>
  )
}

export function Privacy() {
  return (
    <LegalShell title="Privacy Policy">
      <p>
        StratCMO is a product of Maximem (“we”, “us”). This policy explains what we collect, why,
        who we share it with, and the choices you have. Questions: <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
      </p>

      <h2>1. What we collect</h2>
      <ul>
        <li><strong>Account data</strong> — your email and authentication identifiers, via our auth provider.</li>
        <li><strong>Workspace content</strong> — the company URLs you analyze, the marketing objectives,
          opportunities, drafts, monitors, and notes the product generates or you provide, and the durable
          “memory” we keep so the agent improves for your company over time.</li>
        <li><strong>Usage &amp; billing</strong> — metered events (runs, chats, research, monitors) to enforce
          plan limits, and, if you subscribe, billing identifiers held by our payment processor (we never store
          your full card details).</li>
        <li><strong>Technical data</strong> — standard logs and error reports needed to operate and secure the service.</li>
      </ul>

      <h2>2. How we use it</h2>
      <p>
        To run the product (research, draft, monitor), to enforce plan limits and prevent abuse, to process
        payments, to provide support, and to keep the service secure. We do <strong>not</strong> sell your data,
        and we do not use your private workspace content to train our own foundation models.
      </p>

      <h2>3. Subprocessors we share data with</h2>
      <p>
        To deliver the product we send the minimum necessary data to vetted third parties. As of the effective
        date these include: <strong>Anthropic</strong> and <strong>OpenAI</strong> (language models that draft and
        analyze), <strong>Exa</strong> and <strong>Browserbase</strong> (web research and page reading),
        <strong> Composio</strong> (connections to platforms you authorize), <strong>Maximem Synap</strong>
        (durable company memory), <strong>Supabase</strong> (authentication and database), <strong>Stripe</strong>
        (payments), <strong>Sentry</strong> (error monitoring), <strong>Resend</strong> (transactional email), and
        our hosting provider. Each processes data under its own terms; we share only what a given feature needs.
      </p>

      <h2>4. AI-generated content</h2>
      <p>
        The product drafts posts and suggestions using language models. These are <em>drafts for your review</em> —
        you decide what, if anything, to publish, and you publish it under your own identity and accounts. You are
        responsible for complying with the rules of any platform you post to.
      </p>

      <h2>5. Retention &amp; deletion</h2>
      <p>
        We keep workspace data while your account is active. You can delete a workspace or your entire account from
        the app at any time, which removes the associated content from our primary systems; we then request deletion
        from subprocessors where applicable. Backups and logs age out on a rolling basis. To request deletion by
        email, contact <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
      </p>

      <h2>6. Security</h2>
      <p>
        We use encryption in transit, scoped access controls, and tenant isolation so workspaces don’t bleed into one
        another. No system is perfectly secure, but we work to protect your data and to disclose material incidents
        promptly.
      </p>

      <h2>7. Your rights</h2>
      <p>
        Depending on where you live, you may have rights to access, correct, export, or delete your personal data.
        Email <a href={`mailto:${CONTACT}`}>{CONTACT}</a> and we’ll honor valid requests.
      </p>

      <h2>8. Changes</h2>
      <p>
        We’ll update this page when our practices change and revise the effective date above. Material changes will be
        communicated through the product or by email.
      </p>
    </LegalShell>
  )
}

export function Terms() {
  return (
    <LegalShell title="Terms of Service">
      <p>
        These terms govern your use of StratCMO, a product of Maximem (“we”, “us”). By using the service you agree to
        them. If you’re using it on behalf of a company, you represent that you’re authorized to bind that company.
      </p>

      <h2>1. The service</h2>
      <p>
        StratCMO researches your market and drafts marketing opportunities, posts, and recurring monitors. Output is
        generated by AI and is provided for your judgment and editing — it is not professional, legal, or financial
        advice, and we don’t guarantee any particular result, ranking, reach, or revenue.
      </p>

      <h2>2. Your responsibilities</h2>
      <ul>
        <li>You publish content under your own identity and accounts, and you’re responsible for what you post and for
          following each platform’s rules (several communities restrict self-promotion — review every draft before posting).</li>
        <li>You won’t use the service to break the law, spam, harass, infringe others’ rights, or abuse the platforms
          you connect.</li>
        <li>You’re responsible for keeping your account credentials secure.</li>
      </ul>

      <h2>3. Plans, billing &amp; fair use</h2>
      <p>
        The Free plan includes a limited allowance (e.g., a weekly strategic run and a daily chat allowance) and does
        not run automated monitors. The Pro plan unlocks recurring monitors, additional runs, and multiple companies,
        and is billed in advance on a recurring basis through our payment processor. Subscriptions renew until canceled;
        you can cancel anytime and retain access through the end of the paid period. Fees are non-refundable except where
        required by law or stated otherwise. “Unlimited” paid usage is subject to reasonable fair-use limits to prevent
        abuse. We may change pricing with notice for future billing periods.
      </p>

      <h2>4. Your content &amp; our IP</h2>
      <p>
        You own the content you provide and the drafts you create with the service. You grant us the limited rights
        needed to operate the product for you (storing, processing, and sending it to the subprocessors described in our
        Privacy Policy). We own the StratCMO software, brand, and trademarks; these terms don’t grant you rights to them
        beyond using the service.
      </p>

      <h2>5. Third-party platforms</h2>
      <p>
        When you connect external accounts (e.g., social or community platforms), your use of those is governed by their
        terms. We’re not responsible for their availability or actions, including any moderation or account decisions they
        make about content you post.
      </p>

      <h2>6. Disclaimers &amp; liability</h2>
      <p>
        The service is provided “as is,” without warranties of any kind. To the maximum extent permitted by law, we are
        not liable for indirect, incidental, or consequential damages, and our total liability for any claim is limited to
        the amount you paid us in the three months before the claim.
      </p>

      <h2>7. Termination</h2>
      <p>
        You can stop using the service and delete your account anytime. We may suspend or terminate accounts that violate
        these terms or create risk for the service or other users.
      </p>

      <h2>8. Changes &amp; contact</h2>
      <p>
        We may update these terms and will revise the effective date above; continued use means you accept the updated
        terms. Questions: <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
      </p>
    </LegalShell>
  )
}
