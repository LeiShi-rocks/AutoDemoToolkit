import { useState, useEffect, useCallback } from 'react'

// ── Animation class helpers ───────────────────────────────────────────────────
// Elements start hidden (opacity 0). Add beat threshold n; when beat >= n the
// 'in' class is applied and the CSS transition plays.

/** Fade + slide-up animation. Use for most content elements. */
export const a = (n: number, beat: number, extra = '') =>
  ['anim', extra, beat >= n ? 'in' : ''].filter(Boolean).join(' ')

/** Scale spring animation. Use for cards and stat tiles. */
export const as_ = (n: number, beat: number) =>
  `anim-scale${beat >= n ? ' in' : ''}`

// ── Stage dimensions ──────────────────────────────────────────────────────────
export const STAGE_W = 1920
export const STAGE_H = 1080

// ── useScale ──────────────────────────────────────────────────────────────────
// Scales the fixed 1920×1080 stage to fill the viewport while maintaining 16:9.
export function useScale() {
  const [scale, setScale] = useState(1)
  useEffect(() => {
    const update = () =>
      setScale(Math.min(window.innerWidth / STAGE_W, window.innerHeight / STAGE_H))
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])
  return scale
}

// ── usePresentation ───────────────────────────────────────────────────────────
// Manages slide index + beat (sub-step) state and keyboard navigation.
//
// beats[i] = max beat index for slide i.
// Clicking advances the beat; when beat reaches max, next click advances slide.
// Right-click / ← goes back one beat (or to the previous slide at its max beat).
export function usePresentation(beats: number[]) {
  const [slide, setSlide] = useState(0)
  const [beat, setBeat] = useState(0)
  const [slideKey, setSlideKey] = useState(0) // changes on slide transition → re-triggers entrance animation

  const advance = useCallback(() => {
    if (beat < beats[slide]) {
      setBeat(b => b + 1)
    } else if (slide < beats.length - 1) {
      setSlide(s => s + 1)
      setBeat(0)
      setSlideKey(k => k + 1)
    }
  }, [beat, slide, beats])

  const retreat = useCallback(() => {
    if (beat > 0) {
      setBeat(b => b - 1)
    } else if (slide > 0) {
      const prev = slide - 1
      setSlide(prev)
      setBeat(beats[prev])
      setSlideKey(k => k + 1)
    }
  }, [beat, slide, beats])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (['ArrowRight', 'ArrowDown', ' '].includes(e.key)) {
        e.preventDefault(); advance()
      } else if (['ArrowLeft', 'ArrowUp'].includes(e.key)) {
        e.preventDefault(); retreat()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [advance, retreat])

  return { slide, beat, slideKey, advance, retreat, total: beats.length }
}
