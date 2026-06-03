import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Presentation } from './Presentation'
import { slides, beats } from './slides/example'

// ── Theme — swap this one import to change the look ───────────────────────────
// import './themes/warm-keynote.css'  // warm off-white + royal blue (default)
// import './themes/midnight.css'      // dark slate + electric blue
// import './themes/corporate.css'     // pure white + deep navy
// import './themes/minimal.css'       // white + black + single red accent
import './themes/warm-keynote.css'

// ── Base styles (layout, animations — theme-independent) ──────────────────────
import './theme.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Presentation slides={slides} beats={beats} title="My Presentation" />
  </StrictMode>
)
