import type React from 'react'
import { usePresentation, useScale, STAGE_W, STAGE_H } from './engine'

export type SlideComponent = React.FC<{ beat: number }>

interface Props {
  /** One component per slide. Each receives `beat: number` as its only prop. */
  slides: SlideComponent[]
  /**
   * Max beat index per slide (parallel array to `slides`).
   * beats[i] = N means slide i has N clickable sub-steps after the initial state.
   * Example: beats[i] = 2 means 3 visible states (beat 0, 1, 2).
   */
  beats: number[]
  /** Document title shown in the browser tab. */
  title?: string
}

export function Presentation({ slides, beats, title = 'Presentation' }: Props) {
  const { slide, beat, slideKey, advance, retreat, total } = usePresentation(beats)
  const scale = useScale()
  const Slide = slides[slide]

  document.title = title

  return (
    <div
      className="wrapper"
      onClick={advance}
      onContextMenu={e => { e.preventDefault(); retreat() }}
    >
      <div
        className="stage"
        style={{ transform: `translate(-50%, -50%) scale(${scale})`, width: STAGE_W, height: STAGE_H }}
      >
        <div key={slideKey} className="slide-enter">
          <Slide beat={beat} />
        </div>

        {/* Progress bar */}
        <div className="progress">
          <div className="progress-fill" style={{ width: `${((slide + 1) / total) * 100}%` }} />
        </div>

        {/* Slide counter */}
        <div className="counter">{slide + 1} / {total}</div>
      </div>
    </div>
  )
}
