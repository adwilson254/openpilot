import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { PrefsProvider } from './lib/prefs'
import { TelemetryProvider } from './lib/mqtt'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <PrefsProvider>
      <TelemetryProvider>
        <App />
      </TelemetryProvider>
    </PrefsProvider>
  </StrictMode>,
)

// PWA: register the offline shell only in production secure contexts (the comma serves
// over plain HTTP, where SWs are unavailable; this no-ops there and in the dev server).
if ('serviceWorker' in navigator && import.meta.env.PROD && window.isSecureContext) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* noop */ })
  })
}
