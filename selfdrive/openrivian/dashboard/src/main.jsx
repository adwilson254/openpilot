import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { TelemetryProvider } from './lib/mqtt'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <TelemetryProvider>
      <App />
    </TelemetryProvider>
  </StrictMode>,
)
