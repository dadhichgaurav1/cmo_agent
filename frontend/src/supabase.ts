import { createClient, type SupabaseClient } from '@supabase/supabase-js'

// Auth is enabled only when both env vars are present. When absent (local/demo), the app runs
// unauthenticated exactly as before and the backend's single-tenant fallbacks apply.
const env = (import.meta as any).env || {}
const url: string | undefined = env.VITE_SUPABASE_URL
const anon: string | undefined = env.VITE_SUPABASE_ANON_KEY

export const authEnabled = Boolean(url && anon)
export const supabase: SupabaseClient | null = authEnabled ? createClient(url!, anon!) : null

/** Current access token for the signed-in user, or null in demo mode / when signed out. */
export async function accessToken(): Promise<string | null> {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
