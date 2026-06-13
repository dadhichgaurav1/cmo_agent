import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { AuthGate } from './Auth'
import './styles.css'

// Error tracking — loaded only when VITE_SENTRY_DSN is set (keeps the bundle lean otherwise).
const _dsn = (import.meta as any).env?.VITE_SENTRY_DSN
if (_dsn) {
  import('@sentry/react').then((S) => S.init({ dsn: _dsn, tracesSampleRate: 0.1 })).catch(() => {})
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <AuthGate>
    <App />
  </AuthGate>,
)
