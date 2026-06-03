# GENERATE.md — AI Prompt Template for New Decks

Drop this file (along with `TOOLKIT.md`) into any project alongside your source material. Give both files to Claude (or any capable LLM) as context, then use the prompt below.

---

## How to Use

1. Copy your source material (paper PDF text, article, report) into context.
2. Give the AI `TOOLKIT.md` and `GENERATE.md` as references.
3. Run **Phase 1** to get an outline for approval.
4. Run **Phase 2** to generate the slide code.
5. Run **Phase 3** to build.

---

## Phase 1 — Outline (get approval before coding)

```
You are building a web presentation using the auto-pre toolkit (see TOOLKIT.md).

Source material: [paste paper abstract + section headings, or full text]

Task: Produce outline.md covering:

1. THEME — choose one from TOOLKIT.md §Theme Reference that fits the topic and audience.
   Justify your choice in one sentence.

2. SLIDE LIST — 15–22 slides. For each slide:
   - Slide number and title (≤ 6 words)
   - Layout pattern (from TOOLKIT.md §Layout Pattern Catalog)
   - beats: N  (max beat index; 0 means no sub-steps)
   - Info pool: 2–4 bullet points of content to show, with source section/line cited
   - Narration note: 1–2 sentences of what to say (spoken, not written)

3. BEAT BUDGET — confirm total beats sum to 35–60 (≈ 5–10 min at ~1 beat/8 sec).

Rules:
- Every slide must have beats ≥ 1 (no fully static slides).
- No slide should have beats > 5.
- Title slide: beats = 2.
- Conclusion slide: beats = N points (one per takeaway).
- Do NOT write any code yet. Outline only.

Output format:

---
Theme: <name> — <one-line justification>
Total slides: N  |  Total beats: N
---

## 1. <Title> [pattern: <layout>] beats: N
Info pool:
- <fact from source §X>
- <fact from source §X>
Narration: <spoken sentence or two>

## 2. …
```

---

## Phase 2 — Slide Code

```
Using the approved outline.md and TOOLKIT.md as your reference:

Generate src/slides/deck.tsx containing:
- All N slide components (named S01, S02, … S0N)
- Each component: function SNN({ beat }: { beat: number }) { … }
- Use a(n, beat) for fade+slide-up, as_(n, beat) for scale-spring
- Use .stagger on parent when 2+ siblings reveal at the same beat
- Use className layout names from TOOLKIT.md exactly (col-block, stat-card, etc.)
- NO hardcoded hex colors — use var(--accent), var(--green), etc.
- NO inline font-size overrides — use the semantic class system
- Bottom of file: export const slides = [S01, S02, …] and export const beats = [2, 3, …]

Also update src/main.tsx:
- Import the chosen theme from src/themes/<theme-name>.css
- Import slides and beats from src/slides/deck.tsx
- Set title="<Deck Title>"

Rules (from TOOLKIT.md §Chapter-Craft Rules):
- Every slide must animate at least one element (nothing purely static)
- Lists reveal one item per beat via .stagger + sequential a(n, beat) calls
- Stat numbers use .stat-n (large, bold, colored)
- Pipeline stages each get their own beat
- Table: wrap in a(1, beat); add result-callout at a final beat
- The beats array must exactly match the max beat index used in each component

After generating, run: npm run typecheck
Fix any TypeScript errors before reporting done.
```

---

## Phase 3 — Build

```bash
cd auto-pre
npm run build
# Output: dist/index.html  (~200–250 KB, self-contained)
# Share this single file — no server needed, works offline
```

To serve with live reload during development:
```bash
npm run dev
# Then: SSH tunnel  →  ssh -L 5175:localhost:5175 user@server
# Or:   VS Code Ports panel → Forward port 5175 → set visibility Public
```

---

## Narration File Format (optional — for TTS audio)

If you want recorded narration audio, create `src/slides/narrations.ts`:

```ts
// One string per beat per slide (index 0 = beat 1, i.e. first click)
// Length of each array must equal beats[i]
export const narrations: string[][] = [
  // S01 — Title slide (beats: 2)
  [
    "Welcome. Today we present BACON — a framework for calibrating AI judges with limited human labels.",
    "This work was submitted to NeurIPS 2026 by the following authors."
  ],
  // S02 — Scale slide (beats: 3)
  [
    "AI judges are now deployed at massive scale — here are three real domains we studied.",
    "Second card narration.",
    "Third card narration and the key tension: cheap but biased."
  ],
  // … one array per slide
]
```

Synthesis workflow:
1. Extract segments: `for each narrations[i][j], write to audio-segments.json`
2. Call TTS provider (MiniMax / OpenAI / ElevenLabs)
3. Save as `public/audio/s<NN>/beat-<N>.mp3`
4. In `Presentation.tsx`, play `audio/s{slide}/beat-{beat}.mp3` on each advance

Providers (set via env vars):
- **OpenAI**: `OPENAI_API_KEY` — model `tts-1`, voices: alloy, echo, fable, onyx, nova, shimmer
- **MiniMax**: `MINIMAX_API_KEY` + `MINIMAX_GROUP_ID` — good for Chinese
- **ElevenLabs**: `ELEVENLABS_API_KEY` — highest quality, clone-able voice

---

## Checklist Before Sharing

- [ ] `npm run typecheck` passes with zero errors
- [ ] `npm run build` produces `dist/index.html`
- [ ] Open `dist/index.html` locally — all 20 slides load, all beats work
- [ ] Every slide has at least one animated element
- [ ] No slide dumps all content at beat 0
- [ ] Stat numbers are visibly large
- [ ] Theme is consistent throughout (no hardcoded colors)
- [ ] Title and author info is correct on slide 1
- [ ] Conclusion slide lists the right number of takeaways
