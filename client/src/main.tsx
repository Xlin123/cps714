import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './auth/AuthContext.tsx'
import { RemindersProvider } from './lending/RemindersContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <RemindersProvider>
          <App />
        </RemindersProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
