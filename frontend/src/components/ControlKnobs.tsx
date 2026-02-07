import { useState, useRef, useCallback } from 'react'
import type { ClientMessage } from '../types/radio'

interface Props {
  send: (msg: ClientMessage) => void
  powered: boolean
}

export function ControlKnobs({ send, powered }: Props) {
  const [volume, setVolume] = useState(75)
  const knobRef = useRef<HTMLDivElement>(null)
  const draggingRef = useRef(false)
  const startYRef = useRef(0)
  const startVolRef = useRef(75)

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (!powered) return
    draggingRef.current = true
    startYRef.current = e.clientY
    startVolRef.current = volume
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }, [volume, powered])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!draggingRef.current) return
    const delta = startYRef.current - e.clientY
    const newVol = Math.max(0, Math.min(100, startVolRef.current + delta))
    setVolume(newVol)
    send({ type: 'set_volume', value: Math.round(newVol) })
  }, [send])

  const handlePointerUp = useCallback(() => {
    draggingRef.current = false
  }, [])

  // Knob rotation: 0-100 maps to -135 to +135 degrees
  const rotation = -135 + (volume / 100) * 270

  return (
    <div className="flex items-center gap-3">
      {/* Volume knob */}
      <div className="flex flex-col items-center gap-1">
        <div
          ref={knobRef}
          className="relative w-12 h-12 rounded-full cursor-grab active:cursor-grabbing select-none"
          style={{
            background: `
              radial-gradient(circle at 35% 35%, rgba(255,255,255,0.2), rgba(255,255,255,0.05) 40%, rgba(255,255,255,0.02) 70%, transparent)
            `,
            border: '1px solid rgba(255,255,255,0.1)',
            boxShadow: `
              0 2px 6px rgba(0,0,0,0.3),
              inset 0 1px 2px rgba(255,255,255,0.1),
              0 0 ${powered ? '8' : '0'}px rgba(124,92,255,0.2)
            `,
          }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        >
          {/* Indicator line */}
          <div
            className="absolute top-[6px] left-1/2 w-0.5 h-3 -ml-px rounded-full"
            style={{
              background: powered ? '#7c5cff' : 'rgba(255,255,255,0.2)',
              transform: `rotate(${rotation}deg)`,
              transformOrigin: `center ${12 * 2}px`,
              boxShadow: powered ? '0 0 4px #7c5cff' : 'none',
            }}
          />
        </div>
        <span className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
          Vol
        </span>
      </div>

      {/* Volume display */}
      <span
        className="text-xs tabular-nums"
        style={{ color: powered ? 'var(--text-secondary)' : 'rgba(255,255,255,0.1)', fontVariantNumeric: 'tabular-nums' }}
      >
        {Math.round(volume)}
      </span>
    </div>
  )
}
