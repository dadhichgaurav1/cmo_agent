import { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { AuthGate } from './Auth'
import { Landing } from './Landing'
import './styles.css'

// Error tracking — loaded only when VITE_SENTRY_DSN is set (keeps the bundle lean otherwise).
const _dsn = (import.meta as any).env?.VITE_SENTRY_DSN
if (_dsn) {
  import('@sentry/react').then((S) => S.init({ dsn: _dsn, tracesSampleRate: 0.1 })).catch(() => {})
}

/**
 * Tiny path-based router (no dependency). "/" serves the public Landing page; any other path
 * ("/app" and below) serves the product behind AuthGate. The backend's SPA fallback returns
 * index.html for every route, so client-side path switching is all that's needed.
 */
function Root() {
  const [path, setPath] = useState(window.location.pathname)

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  function navigate(to: string) {
    if (to !== window.location.pathname) window.history.pushState({}, '', to)
    setPath(to)
    window.scrollTo(0, 0)
  }

  if (path === '/' || path === '') {
    return <Landing onEnter={() => navigate('/app')} />
  }
  return (
    <AuthGate>
      <App />
    </AuthGate>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(<Root />)
