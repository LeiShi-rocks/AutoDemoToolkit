# auto-pre Toolkit

A React + TypeScript + Vite engine for generating cinematic, click-driven web presentations from any source material — papers, articles, reports. Builds to a single self-contained `index.html`. No server required to view.

---

## File Structure

```
auto-pre/
├── TOOLKIT.md          ← you are here
├── GENERATE.md         ← AI prompt template for new decks
├── package.json
├── vite.config.ts      ← singlefile plugin pre-configured
├── src/
│   ├── main.tsx        ← entry point; swap theme import here
│   ├── engine.ts       ← usePresentation, useScale, a(), as_()
│   ├── Presentation.tsx← <Presentation slides beats title />
│   ├── theme.css       ← layout, animations, all components (theme-independent)
│   ├── themes/         ← color/font tokens only; one import = one look
│   │   ├── warm-keynote.css     warm off-white + royal blue (default)
│   │   ├── midnight.css         dark slate + electric blue
│   │   ├── corporate.css        pure white + deep navy
│   │   ├── minimal.css          white + black + red accent
│   │   ├── indigo-porcelain.css indigo ink + porcelain white (academic)
│   │   └── newsroom.css         newspaper cream + flag red (editorial)
│   └── slides/
│       └── example.tsx ← 3 annotated demo slides; replace for your deck
└── dist/
    └── index.html      ← built output; share this single file
```

---

## Core Concepts

### The Beat System
Each slide has a **beat counter**. Beat 0 = initial state when the slide loads. Each click advances the beat by 1. When the beat reaches its maximum, the next click advances to the next slide.

```ts
// In engine.ts
const BEATS = [2, 3, 1]   // slide 0 has 2 beats, slide 1 has 3, slide 2 has 1

// In a slide component
function MySlide({ beat }: { beat: number }) {
  return (
    <div className="slide">
      <h2>Always visible</h2>                          {/* beat 0 — no class */}
      <p className={a(1, beat)}>Appears on click 1</p> {/* beat 1 */}
      <p className={a(2, beat)}>Appears on click 2</p> {/* beat 2 */}
    </div>
  )
}
```

### Animation Helpers

| Helper | Effect | Best for |
|--------|--------|----------|
| `a(n, beat)` | Fade + slide up (22px) | Most content: text, columns, tables, notes |
| `as_(n, beat)` | Scale spring (.88→1) | Cards, stat tiles, metric callouts |
| `.stagger` parent | Adds 0/90/180/270/360ms delays to nth-children | Sibling groups revealed at the same beat |
| `style={{ transitionDelay }}` | Custom per-item delay | Item bars, sequential lists |

### Navigation
- **Click** → advance beat (or slide when at max beat)
- **Right-click** → retreat
- **→ / ↓ / Space** → advance
- **← / ↑** → retreat

---

## Theme Reference

Switch theme by changing one import in `src/main.tsx`:
```ts
import './themes/warm-keynote.css'
```

| Theme | Mood | Best for |
|-------|------|----------|
| `warm-keynote` | Warm, modern, SaaS keynote | General academic, product demos |
| `midnight` | Cinematic dark, electric blue | Tech talks, ML/AI papers, video recording |
| `corporate` | Clean, pure white, deep navy | Business presentations, stakeholder decks |
| `minimal` | Stark, red accent, no decoration | Design, art, high-concept pitches |
| `indigo-porcelain` | Scholarly, slow-paced, serif | Research papers, academic conferences |
| `newsroom` | Newspaper, zero-radius, italic serif | Data journalism, policy, factual reporting |

To create a new theme: copy any `themes/*.css`, override the 15 `:root` variables, import it in `main.tsx`. No other files need changing.

### Token Contract (required in every theme)

```css
:root {
  /* Backgrounds */
  --bg, --surface, --surface2

  /* Text hierarchy */
  --text, --text2, --text3

  /* Accent palette (color + light tint) */
  --accent, --accent-lt
  --amber,  --amber-lt
  --purple, --purple-lt
  --green,  --green-lt
  --red,    --red-lt

  /* Chrome */
  --border, --shadow, --r   /* r = border-radius */
}
```

---

## Layout Pattern Catalog

### 1. Title Slide
```tsx
<div className="slide s-title">
  <div className="badge venue">Conference 2026</div>
  <div className={`s-title__acronym ${a(1, beat)}`}>ACRONYM</div>
  <h1 className={`s-title__full ${a(1, beat)}`}>Full Title</h1>
  <div className={`rule ${a(2, beat)}`} />
  <p className={`s-title__authors ${a(2, beat)}`}>Author · Author</p>
</div>
// beats: 2
```

### 2. Stat Row (scale-spring cards)
```tsx
<div className="slide s-content" style={{display:'flex',flexDirection:'column'}}>
  <header className="slide-header">
    <span className="label">Section</span>
    <h2>Headline</h2>
  </header>
  <div className="stat-row">
    <div className={`stat-card ${as_(1, beat)}`}>
      <div className="stat-n">42</div>
      <div className="stat-l">Metric Name</div>
      <div className="stat-s">Detail</div>
    </div>
    {/* repeat for more cards */}
  </div>
  <div className={a(3, beat)}><div className="callout">Key insight</div></div>
</div>
// beats: 3 (header always + card per beat + callout)
```

### 3. Two-column / Three-column
```tsx
<div className="two-col">  {/* or three-col */}
  <div className={`col-block ${a(1, beat)}`}>
    <div className="col-head green-head">Left heading</div>
    <ul className="sl spaced"><li>Point</li></ul>
  </div>
  <div className={`col-block ${a(2, beat)}`}>
    <div className="col-head amber-head">Right heading</div>
    <p>Content</p>
  </div>
</div>
// beats: 2
```

### 4. Pipeline (staged reveal)
```tsx
<div className="pipeline">
  <div className={`pipe-stage blue ${a(1, beat)}`}>
    <div className="pipe-num">01</div>
    <div className="pipe-title">Stage Name</div>
    <div className="pipe-desc">Description</div>
  </div>
  <div className={`pipe-arrow ${a(2, beat)}`}>→</div>
  <div className={`pipe-stage amber ${a(2, beat)}`}>…</div>
  {/* continue for more stages */}
</div>
// beats: N stages - 1 (first stage at beat 1, each subsequent pair +1)
```

### 5. Finding Cards (2×2 grid)
```tsx
<div className="findings-grid stagger">
  {cards.map(({ cls, icon, title, body }, i) => (
    <div className={`finding-card ${cls} ${a(i < 2 ? 1 : 2, beat)}`} key={title}>
      <div className="fc-icon">{icon}</div>
      <div className="fc-title">{title}</div>
      <p>{body}</p>
    </div>
  ))}
</div>
// beats: 2 (first pair at beat 1, second pair at beat 2)
// cls options: blue, red, green, amber, purple
```

### 6. Data Table
```tsx
<div className={a(1, beat)}>
  <table className="dtable">
    <thead><tr><th>Col A</th><th>Col B</th></tr></thead>
    <tbody>
      <tr className="best-row"><td>Best result</td><td>0.99</td></tr>
      <tr><td>Baseline</td><td>0.50</td></tr>
      <tr className="dim-row"><td className="bad">Worst</td><td className="bad">0.10</td></tr>
    </tbody>
  </table>
</div>
// beats: 1-2 (reveal table, then optionally a result-callout below)
```

### 7. Formula Block
```tsx
<div className={a(1, beat)}>
  <div className="formula-block large">
    <div className="formula">
      <span className="frac-wrap">
        <span className="num">numerator</span>
        <span className="den">denominator</span>
      </span>
      <span className="sum">Σ</span>
      <span className="op"> + term</span>
    </div>
    <div className="formula-name">Name<sup>label</sup></div>
    <div className="formula-legend">
      <span><strong>x</strong> meaning</span>
    </div>
  </div>
</div>
// beats: 1 (formula) + 1 (three-col explanation below)
```

### 8. Case Study
```tsx
<div className="slide s-case">
  <div className="case-tag">Case Study N</div>
  <h2>Title</h2>
  <div className="case-body">
    <div className={`case-text ${a(1, beat)}`}>
      <p>Background</p>
      <div className="finding">
        <div className="finding-label">Key Finding</div>
        <p>Finding text</p>
      </div>
    </div>
    <div className={`case-metrics ${a(2, beat)}`}>
      <div className="metric-tile bad"><div className="metric-val">−9.72</div><div className="metric-lbl">Before</div></div>
      <div className="metric-tile good"><div className="metric-val">0.555</div><div className="metric-lbl">After</div></div>
    </div>
  </div>
</div>
// beats: 2
```

### 9. Statement (big quote + reveal cards)
```tsx
<div className="slide s-statement">
  <blockquote className="big-quote">"Your memorable statement."</blockquote>
  <div className="problem-cards stagger">
    {[card1, card2, card3].map((c, i) => (
      <div className={`problem-card ${a(i + 1, beat)}`} key={c.title}>
        <div className="problem-icon">{c.icon}</div>
        <div className="problem-title">{c.title}</div>
        <p>{c.body}</p>
      </div>
    ))}
  </div>
</div>
// beats: 3 (one card per beat; quote always visible)
```

### 10. Conclusion (numbered points)
```tsx
<div className="slide s-conclusion">
  <header className="slide-header centered">…</header>
  <div className="conclusion-points">
    {points.map(({ title, body }, i) => (
      <div className={`conclusion-pt ${a(i + 1, beat)}`} key={title}>
        <div className="conclusion-num">{i + 1}</div>
        <div><strong>{title}</strong><p>{body}</p></div>
      </div>
    ))}
  </div>
  <div className={a(points.length, beat)}>
    <div className="conclusion-footer">…</div>
  </div>
</div>
// beats: N points (one per beat, footer at last beat)
```

---

## Chapter-Craft Rules (adapted from garden-skills)

These rules ensure every slide is worth watching, not just reading.

1. **Every slide needs at least one animated/interactive element.** Pure static text fails.
2. **One beat = one focused idea.** Never reveal two competing concepts at the same time.
3. **Lists reveal sequentially.** When narrating "first X, second Y, third Z", each item appears at its own beat.
4. **Hero numbers must be large** — stat-n is 72px minimum.
5. **Whitespace is content.** Resist filling every pixel.
6. **No hardcoded colors or font names** in slide code — use `var(--accent)` etc.
7. **Beat counts must match narration length** if audio is used — one beat per spoken paragraph.
8. **Avoid**: gradient blobs, emoji as decoration, fabricated charts, AI-cliché visuals.

---

## Script Guidelines (adapted from garden-skills)

When an AI generates narration text for each slide:

- **Information retention ≥ 60%** — reformulate, don't summarize; keep facts, data, examples, logic chains.
- **Colloquialization** — convert passive voice and formal nouns to natural spoken language.
- **Short sentences** — each clause under ~15 words when spoken aloud.
- **Strong opening** — first 5 seconds must hook with contrast, a question, or a striking number.
- **No AI flavor**: remove fake empathy ("great question!"), false profundity, self-promotion, parallel structures that feel robotic.
- **Concrete over abstract** — "R² rose from 0.36 to 0.70" beats "significant improvement in model quality."
- **Use `---` to mark rhythm breaks** between complete ideas.

---

## AI Generation Workflow

See `GENERATE.md` for the step-by-step prompt template.

The high-level phases are:

| Phase | Output | Key decision |
|-------|--------|--------------|
| 1. Outline | `outline.md` — slide list, beats, info pools | Slide count, theme choice |
| 2. Script | Narration notes per slide | Tone, audience, language |
| 3. Code | `src/slides/deck.tsx` — all slide components + beats array | Layout patterns per slide |
| 4. Build | `dist/index.html` — single portable file | `npm run build` |

---

## Quality Checklist

Before shipping a deck, verify:

- [ ] Every slide has at least one animated element (not just text)
- [ ] No slide reveals all content at beat 0 (that's a static slide)
- [ ] TypeScript compiles without errors (`npm run typecheck`)
- [ ] Stat numbers are large (≥ 72px via `.stat-n`)
- [ ] Colors reference CSS variables, not hex literals
- [ ] Table rows use `.best-row`, `.dim-row`, `.bad` for hierarchy
- [ ] Pipeline stages reveal one-at-a-time (not all at once)
- [ ] Beat count in BEATS array matches the max beat used in the component
- [ ] `npm run build` produces a working `dist/index.html`

---

## Extending the Toolkit

### Add a layout pattern
1. Write the component in `src/slides/your-deck.tsx`
2. Add its CSS to `src/theme.css` using `var(--*)` tokens only
3. Document it in this file under Layout Pattern Catalog

### Add a theme
1. Copy `src/themes/warm-keynote.css` → `src/themes/my-theme.css`
2. Override the 15 `:root` variables
3. Optionally add theme-specific element overrides below `:root`
4. Import in `main.tsx`

### Add audio narration
The original skill supports step-level TTS audio. To add:
1. Create `src/slides/narrations.ts` with one string per beat per slide
2. Add an audio player that advances on `ended` event
3. Supported providers: MiniMax, OpenAI, ElevenLabs, edge-tts, Azure, Google Cloud TTS
See `GENERATE.md` §Audio for the narration file format.
