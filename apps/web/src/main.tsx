import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import {ReviewPage} from './components/ReviewPage'
import { ChangesPage, EditionChooser } from './components/EditionChooser'
import { editionFromPath } from './lib/edition'
import './styles.css'

const path = window.location.pathname.replace(/\/+$/, '') || '/'
const edition = editionFromPath()
const content = path === '/' ? <EditionChooser />
  : path === '/review' || !!path.match(/^\/v[1-9][0-9]*\/review$/) ? <ReviewPage editionId={edition} />
  : edition && path === `/${edition}/changes` ? <ChangesPage editionId={edition} />
  : edition && path === `/${edition}/research` ? <App editionId={edition} initialView="council" />
  : edition && path === `/${edition}` ? <App editionId={edition} />
  : <EditionChooser />

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {content}
  </StrictMode>,
)
