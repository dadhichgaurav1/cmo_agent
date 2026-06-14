# Launch checklist — the manual steps

Code is wired; these are the dashboard/ops steps only you can do. Do them in order.

---

## 1. Spend circuit-breaker + verified-email signup (do FIRST — protects your bill)

You proxy paid APIs for free signups, so cap exposure before any public link goes out.

**a. Require email verification (Supabase)**
1. Supabase dashboard → **Authentication → Providers → Email** → enable **Confirm email**.
2. **Authentication → URL Configuration** → set **Site URL** and **Redirect URLs** to your Render
   URL (e.g. `https://stratcmo.onrender.com`).

**b. Hard spend caps at every upstream provider** (these are the real stops — the app can't cap a vendor's bill):
- **Anthropic Console → Billing → Usage limits**: set a monthly cap + email alerts.
- **OpenAI → Billing → Limits**: set a hard limit + soft alert.
- **Exa**, **Browserbase**, **Composio**: set usage caps / billing alerts in each dashboard.

**c. App-level kill switch (already in code)**
- To disable an abusive workspace: set `disabled: true` in its `org_settings.settings` JSON
  (`usage.org_disabled` reads it → all metered endpoints 403). SQL:
  ```sql
  update org_settings set settings = settings || '{"disabled": true}'::jsonb where org_id = '<uuid>';
  ```
- Per-user exposure is already bounded by the new free quotas (1 run/week + 3 onboarding) and the
  per-key burst rate limits in `main.py`. No automated global signup cap exists yet — watch the
  Anthropic/Exa dashboards for the first week.

---

## 2. Stripe — test → live

1. Stripe dashboard → switch to **Live mode** (toggle, top-right).
2. **Products → Add product**: "StratCMO Pro", recurring **$49/mo**. Copy the **price id**
   (`price_...`) → env `STRIPE_PRICE_PRO`. *(Optional: add a second $390/yr price; create a
   `FOUNDING` promotion code for $39/mo — checkout already accepts promo codes.)*
3. **Developers → API keys**: copy the **live secret key** (`sk_live_...`) → `STRIPE_SECRET_KEY`.
4. **Developers → Webhooks → Add endpoint**:
   - URL: `https://<your-app>.onrender.com/api/billing/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.created`,
     `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
   - Copy the **Signing secret** (`whsec_...`) → `STRIPE_WEBHOOK_SECRET`.
5. **Settings → Billing → Customer portal**: enable it (so "Manage billing" works).
6. **Settings → Business**: set support email `gaurav@maximem.ai`, statement descriptor, and add your
   **Terms** (`/terms`) and **Privacy** (`/privacy`) URLs.
7. The 14-day trial is already set in `create_checkout` — no extra config. (Trial subs come through
   as `trialing`, which maps to the `pro` plan.)

After setting the three Stripe env vars on Render, billing flips from "disabled" to live automatically.

---

## 3. Render — do we still need DNS/TLS? (mostly no)

**You do NOT need:** a registrar, custom DNS, or manual TLS. Render serves your app at
`https://<name>.onrender.com` with automatic HTTPS. Skip the whole domain step for now.

**You DO still need:**
1. **Env vars** on the Render service (Settings → Environment) — all the keys from
   `backend/.env.example`, plus:
   - `APP_BASE_URL=https://<name>.onrender.com` (Stripe redirects)
   - `ALLOWED_ORIGINS=https://<name>.onrender.com` (locks CORS — without this it's permissive `*`)
   - `SENTRY_DSN=...` (turn on error tracking)
2. **Apply DB migrations** to your production Supabase, in order: `0001` → `0006` (SQL editor or
   `supabase db push`). RLS is in the migrations.
3. **Supabase redirect URLs** = your Render URL (step 1a above).
4. **Stripe webhook URL** = your Render URL (step 2.4 above).
5. **Email sender (optional):** `RESEND_FROM` currently points at `stratcmo.app`. On a bare Render
   subdomain you can't verify that domain — either leave `RESEND_API_KEY` unset (Supabase sends its
   own auth emails) or verify a domain you own in Resend. Not a launch blocker.

When you later add a custom domain: point it in Render (it issues the cert), then update
`APP_BASE_URL`, `ALLOWED_ORIGINS`, the Supabase redirect URLs, and the Stripe webhook URL to match.
