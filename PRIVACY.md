# Privacy Policy — StratCMO

_Last updated: 2026-06-13. This is a starting template, not legal advice — have counsel review
before launch._

## 1. What we collect
- **Account data:** email, name, and authentication data (via Supabase Auth).
- **Workspace data:** companies you analyze, generated strategies/drafts, chat messages,
  monitor configurations, and run history.
- **Usage data:** metered events (runs, chats, research, monitors) for billing and abuse
  prevention, plus standard logs.
- **Billing data:** handled by Stripe; we store only identifiers and subscription status, not
  card details.

## 2. How we use it
To provide and improve the Service, generate output, enforce plan limits, prevent abuse, process
payments, and communicate with you (transactional email via Resend).

## 3. Subprocessors
We share data with the providers needed to run the Service, including: Anthropic and OpenAI
(model inference), Supabase (database + auth), Maximem Synap (durable memory), Exa and Composio
(research/tools), Browserbase (browser automation), Stripe (billing), Resend (email), and our
hosting provider (Render). A current list is available on request; we maintain Data Processing
Agreements (DPAs) with subprocessors that handle personal or customer data.

## 4. Data isolation
Workspace data is isolated per organization. Durable memory ("brains") is scoped to the
organization, not shared across tenants.

## 5. Retention & deletion
We retain workspace data while your account is active. You can delete data at any time:
- **Delete a workspace:** removes the organization and all its runs, monitors, memory references,
  and usage records (cascade).
- **Delete your account:** removes your user, profile, memberships, and the workspaces you own.

In-app: use account settings (Delete account / Delete workspace). API: `DELETE /api/workspace`
and `DELETE /api/account`. Deletion of data held by subprocessors is requested in turn; some may
retain backups for a limited period per their policies.

## 6. Security
Data is encrypted in transit. Access is gated by authentication and row-level security.
Service-role access is restricted to the backend. We apply rate limiting and per-org cost caps.

## 7. Your rights
Depending on your jurisdiction, you may have rights to access, correct, export, or delete your
personal data. Contact us to exercise them.

## 8. International transfers
Data may be processed in regions where our providers operate. We rely on standard contractual
protections where applicable.

## 9. Changes
We may update this Policy; material changes will be notified in-app or by email.

## 10. Contact
Privacy questions / data requests: privacy@stratcmo.app
