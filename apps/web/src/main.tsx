import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import IntegratedApp from './components/IntegratedApp'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <IntegratedApp />
  </StrictMode>,
)
