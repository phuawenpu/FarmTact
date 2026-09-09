import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import {ReviewPage} from './components/ReviewPage'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {window.location.pathname.replace(/\/$/,'')==='/review'?<ReviewPage/>:<App/>}
  </StrictMode>,
)
