import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase, authEnabled } from './supabase'

/**
 * Wraps the app in a Supabase auth gate. In demo mode (no VITE_SUPABASE_* configured) it renders
 * children unchanged. Otherwise it shows a sign-in screen until there's a session, then renders
 * the app plus a small sign-out control. Hooks always run (rules-of-hooks safe).
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(authEnabled)

  useEffect(() => {
    if (!authEnabled || !supabase) return
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => sub.subscription.unsubscribe()
  }, [])

  if (!authEnabled) return <>{children}</>
  if (loading) return <div style={S.center}>…</div>
  if (!session) return <Login />
  return (
    <>
      {children}
      <SignOut email={session.user.email} />
    </>
  )
}

function Login() {
  const [mode, setMode] = useState<'in' | 'up'>('in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase || busy) return
    setBusy(true); setErr(''); setMsg('')
    try {
      if (mode === 'in') {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
      } else {
        const { data, error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
        if (!data.session) setMsg('Check your email to confirm your account, then sign in.')
      }
    } catch (e: any) {
      setErr(e?.message || 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={S.center}>
      <form onSubmit={submit} style={S.card}>
        <div style={S.brand}><span style={{ color: '#c2603f' }}>◆</span> StratCMO</div>
        <div style={S.sub}>{mode === 'in' ? 'Sign in to your workspace' : 'Create your workspace'}</div>
        <input style={S.input} type="email" placeholder="email" value={email}
               onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
        <input style={S.input} type="password" placeholder="password" value={password}
               onChange={(e) => setPassword(e.target.value)}
               autoComplete={mode === 'in' ? 'current-password' : 'new-password'} required minLength={6} />
        <button style={S.primary} type="submit" disabled={busy}>
          {busy ? '…' : mode === 'in' ? 'Sign in' : 'Create account'}
        </button>
        {err && <div style={S.err}>{err}</div>}
        {msg && <div style={S.msg}>{msg}</div>}
        <div style={S.switch} onClick={() => { setMode(mode === 'in' ? 'up' : 'in'); setErr(''); setMsg('') }}>
          {mode === 'in' ? "No account? Create one" : 'Have an account? Sign in'}
        </div>
      </form>
    </div>
  )
}

function SignOut({ email }: { email?: string }) {
  return (
    <button title={email} style={S.signout} onClick={() => supabase?.auth.signOut()}>
      Sign out
    </button>
  )
}

const S: Record<string, React.CSSProperties> = {
  center: {
    minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: '#faf9f5', color: '#211f1c', fontFamily: "'Inter',-apple-system,sans-serif",
  },
  card: {
    width: 320, display: 'flex', flexDirection: 'column', gap: 10, padding: 28,
    background: '#fff', border: '1px solid #e7e2d8', borderRadius: 16,
    boxShadow: '0 2px 20px rgba(0,0,0,.04)',
  },
  brand: { fontSize: 20, fontWeight: 600, letterSpacing: '-.01em' },
  sub: { fontSize: 13, color: '#8b857a', marginBottom: 8 },
  input: {
    padding: '10px 12px', borderRadius: 10, border: '1px solid #e7e2d8',
    fontSize: 14, background: '#faf9f5', outline: 'none',
  },
  primary: {
    padding: '10px 12px', borderRadius: 10, border: 'none', cursor: 'pointer',
    background: '#c2603f', color: '#fff', fontSize: 14, fontWeight: 500, marginTop: 4,
  },
  err: { fontSize: 12.5, color: '#b3402a', background: '#c2603f14', padding: '8px 10px', borderRadius: 8 },
  msg: { fontSize: 12.5, color: '#3e7c74', background: '#3e7c7414', padding: '8px 10px', borderRadius: 8 },
  switch: { fontSize: 12.5, color: '#c2603f', cursor: 'pointer', textAlign: 'center', marginTop: 4 },
  signout: {
    position: 'fixed', bottom: 14, right: 14, zIndex: 50, padding: '6px 12px',
    fontSize: 12, color: '#8b857a', background: '#fff', border: '1px solid #e7e2d8',
    borderRadius: 8, cursor: 'pointer',
  },
}
