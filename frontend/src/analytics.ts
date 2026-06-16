/**
 * Thin PostHog wrapper. Every export is a no-op unless VITE_POSTHOG_KEY is set, so demo/local
 * builds ship no analytics and call sites stay clean (no env checks at the call site). posthog-js
 * is dynamically imported so it lands in a lazy chunk and never bloats the main bundle when
 * analytics is off, mirroring the Sentry pattern in main.tsx.
 *
 * Convention: event names are `object_action` (run_started, card_posted). Money/outcome/entitlement
 * events are emitted server-side (see backend/app/analytics.py); the client fires intent/UI events.
 */
import type { PostHog } from 'posthog-js'

const KEY = (import.meta as any).env?.VITE_POSTHOG_KEY as string | undefined
const HOST = ((import.meta as any).env?.VITE_POSTHOG_HOST as string | undefined) || 'https://us.i.posthog.com'

let ph: PostHog | null = null
let ready: Promise<PostHog | null> | null = null

export function analyticsEnabled(): boolean {
  return !!KEY
}

/** Load + init PostHog once. Safe to call when disabled (resolves null). Idempotent. */
export function initAnalytics(): Promise<PostHog | null> {
  if (!KEY) return Promise.resolve(null)
  if (ready) return ready
  ready = import('posthog-js')
    .then(({ default: posthog }) => {
      posthog.init(KEY, {
        api_host: HOST,
        capture_pageview: false, // SPA: pageviews captured manually on route change (see main.tsx)
        capture_pageleave: true,
        person_profiles: 'identified_only', // no person profile until identify() — keeps anon cost low
        autocapture: true, // click/breadth coverage; named events below drive the funnels
      })
      ph = posthog
      return posthog
    })
    .catch(() => null)
  return ready
}

/** Fire an event. If init hasn't resolved yet, waits for it then fires (no dropped events). */
export function track(event: string, props?: Record<string, any>): void {
  if (!KEY) return
  if (ph) { ph.capture(event, props); return }
  void initAnalytics().then((p) => p?.capture(event, props))
}

/** Tie the anonymous person to a known user; merges their pre-signup journey. */
export function identify(distinctId: string, props?: Record<string, any>): void {
  if (!KEY) return
  void initAnalytics().then((p) => p?.identify(distinctId, props))
}

/** Associate the user with their org for account-level (group) funnels. */
export function setOrg(orgId: string, props?: Record<string, any>): void {
  if (!KEY || !orgId) return
  void initAnalytics().then((p) => p?.group('organization', orgId, props))
}

/** Register super properties sent with every subsequent event (e.g. plan). */
export function register(props: Record<string, any>): void {
  if (!KEY) return
  void initAnalytics().then((p) => p?.register(props))
}

/** Manual SPA pageview (the app has no router lib). */
export function pageview(path?: string): void {
  if (!KEY) return
  const url = window.location.origin + (path || window.location.pathname)
  if (ph) { ph.capture('$pageview', { $current_url: url }); return }
  void initAnalytics().then((p) => p?.capture('$pageview', { $current_url: url }))
}

/** Clear identity on sign-out so the next user starts a fresh anonymous session. */
export function resetAnalytics(): void {
  if (!KEY) return
  ph?.reset()
}
