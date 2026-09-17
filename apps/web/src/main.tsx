import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import BeginnerApp from './components/BeginnerApp'
import './styles.css'

const path = window.location.pathname.replace(/\/+$/, '') || '/'
// Archived applications retain their immutable bundles. This release has one
// public introduction and one game; there is no historical-navigation shell.
const content = <BeginnerApp landing={path !== '/play' && !/^\/v14(?:\/play)?$/.test(path)} />

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {content}
  </StrictMode>,
)
