/**
 * Example slides demonstrating the three core layout patterns.
 * Copy this file and replace the content to create your own deck.
 *
 * Each slide component receives `beat: number`.
 * Use a(n, beat) for fade+slide-up, as_(n, beat) for scale-spring.
 * Elements with beat n appear on the n-th click within the slide.
 * Elements not wrapped in a()/as_() are always visible when the slide loads.
 */

import { a, as_ } from '../engine'

// ── Pattern 1: Title slide ────────────────────────────────────────────────────
// beats: 2  →  3 visible states (initial badge, acronym+title, authors)
function TitleSlide({ beat }: { beat: number }) {
  return (
    <div className="slide s-title">
      {/* Beat 0: always visible on slide load */}
      <div className="badge venue">Conference 2026</div>

      {/* Beat 1: revealed on first click */}
      <div className={`s-title__acronym ${a(1, beat)}`}>TITLE</div>
      <h1 className={`s-title__full ${a(1, beat)}`}>
        Your Full Presentation Title Goes Here
      </h1>

      {/* Beat 2: revealed on second click */}
      <div className={`rule ${a(2, beat)}`} />
      <p className={`s-title__authors ${a(2, beat)}`}>
        Author One · Author Two · Author Three
      </p>
      <p className={`s-title__hint ${a(2, beat)}`}>
        Click or → to advance · right-click or ← to go back
      </p>
    </div>
  )
}

// ── Pattern 2: Stat cards with staggered scale-in ─────────────────────────────
// beats: 3  →  header visible, then each card on its own click, then callout
function StatsSlide({ beat }: { beat: number }) {
  return (
    <div className="slide s-content" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Always visible */}
      <header className="slide-header">
        <span className="label">Section Label</span>
        <h2>A compelling headline that frames what follows</h2>
      </header>

      {/* Cards: each appears on its own beat via as_() scale-spring */}
      <div className="stat-row">
        <div className={`stat-card ${as_(1, beat)}`}>
          <div className="stat-n">42</div>
          <div className="stat-l">Key Metric</div>
          <div className="stat-s">Supporting detail or source</div>
        </div>
        <div className={`stat-card ${as_(2, beat)}`}>
          <div className="stat-n">7×</div>
          <div className="stat-l">Improvement</div>
          <div className="stat-s">Compared to baseline method</div>
        </div>
        <div className={`stat-card ${as_(2, beat)}`}>
          <div className="stat-n">99%</div>
          <div className="stat-l">Coverage</div>
          <div className="stat-s">Across all evaluated domains</div>
        </div>
      </div>

      {/* Callout appears with the last card group */}
      <div className={a(3, beat)}>
        <div className="callout">
          Key insight: summarise the "so what" of the numbers above in one sentence.
          This is what the audience should walk away remembering.
        </div>
      </div>
    </div>
  )
}

// ── Pattern 3: Two-column reveal ──────────────────────────────────────────────
// beats: 2  →  header visible, left col on click 1, right col on click 2
function TwoColSlide({ beat }: { beat: number }) {
  return (
    <div className="slide" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Always visible */}
      <header className="slide-header">
        <span className="label">Method</span>
        <h2>Two complementary perspectives on the same problem</h2>
      </header>

      <div className="two-col">
        {/* Left col: beat 1 */}
        <div className={`col-block ${a(1, beat)}`}>
          <div className="col-head green-head">Approach A</div>
          <ul className="sl spaced">
            <li><strong>First strength</strong> — elaboration of why this matters</li>
            <li><strong>Second strength</strong> — another key point with context</li>
            <li><strong>Third strength</strong> — supporting evidence or mechanism</li>
          </ul>
        </div>

        {/* Right col: beat 2 */}
        <div className={`col-block ${a(2, beat)}`}>
          <div className="col-head amber-head">Approach B</div>
          <ul className="sl spaced">
            <li><strong>First strength</strong> — elaboration of why this matters</li>
            <li><strong>Second strength</strong> — another key point with context</li>
            <li><strong>Third strength</strong> — supporting evidence or mechanism</li>
          </ul>
        </div>
      </div>

      {/* Note at the bottom: also beat 2 */}
      <div className={a(2, beat)}>
        <div className="note">
          Takeaway note: one sentence summarising the comparison or transition to the next idea.
        </div>
      </div>
    </div>
  )
}

// ── Deck assembly ─────────────────────────────────────────────────────────────
// Export slides + beats arrays — pass both to <Presentation />.
export const slides = [TitleSlide, StatsSlide, TwoColSlide]
export const beats  = [2, 3, 2]
