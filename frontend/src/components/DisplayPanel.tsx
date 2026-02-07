import { useState, useEffect, useRef } from 'react'
import LiquidGlass from 'liquid-glass-react'
import { useGlassContainer } from '../context/GlassContext'
import { glassCard } from '../utils/glassPresets'
import type { Track, StationState } from '../types/radio'

interface Props {
  track: Track | null
  djText: string
  djSegment: string
  stationState: StationState
  progressMs: number
  durationMs: number
  powered: boolean
}

function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000)
  const min = Math.floor(s / 60)
  const sec = s % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}

function formatClock(): string {
  const now = new Date()
  let h = now.getHours()
  const ampm = h >= 12 ? 'PM' : 'AM'
  h = h % 12 || 12
  const m = now.getMinutes().toString().padStart(2, '0')
  return `${h}:${m} ${ampm}`
}

export function DisplayPanel({ track, djText, stationState, progressMs, durationMs, powered }: Props) {
  const [clock, setClock] = useState(formatClock())
  const [scrollPos, setScrollPos] = useState(0)
  const textRef = useRef<HTMLDivElement>(null)
  const container = useGlassContainer()

  // Update clock every 30s
  useEffect(() => {
    const interval = setInterval(() => setClock(formatClock()), 30000)
    return () => clearInterval(interval)
  }, [])

  // Scroll long text
  useEffect(() => {
    if (!track) return
    const fullText = `${track.title} — ${track.artist}`
    if (fullText.length <= 35) {
      setScrollPos(0)
      return
    }
    const interval = setInterval(() => {
      setScrollPos(p => (p + 1) % (fullText.length + 10))
    }, 200)
    return () => clearInterval(interval)
  }, [track])

  const isDj = stationState === 'dj_transition' || stationState === 'dj_break'

  const trackText = track ? `${track.title} — ${track.artist}` : 'No track'
  const displayText = trackText.length > 35
    ? (trackText + '          ' + trackText).slice(scrollPos, scrollPos + 40)
    : trackText

  return (
    <LiquidGlass {...glassCard} mouseContainer={container ?? undefined} padding="0">
      <div className={`relative p-4 transition-opacity duration-500 ${powered ? 'opacity-100' : 'opacity-0'}`}>
        {/* Track / DJ text row */}
        <div className="mb-2">
          {isDj ? (
            <div
              className="text-sm leading-relaxed line-clamp-2"
              style={{ color: 'var(--text-secondary)' }}
            >
              {djText || '...'}
            </div>
          ) : (
            <div
              ref={textRef}
              className="text-base font-semibold whitespace-nowrap overflow-hidden"
              style={{ color: 'var(--text-primary)' }}
            >
              {displayText}
            </div>
          )}
        </div>

        {/* Progress bar */}
        {track && !isDj && (
          <div className="mb-2">
            <div className="h-1 rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }}>
              <div
                className="h-full rounded-full transition-all duration-1000"
                style={{
                  width: durationMs > 0 ? `${(progressMs / durationMs) * 100}%` : '0%',
                  background: 'linear-gradient(90deg, var(--accent), var(--accent-blue))',
                  boxShadow: '0 0 8px rgba(124,92,255,0.4)',
                }}
              />
            </div>
          </div>
        )}

        {/* Bottom info row */}
        <div className="flex items-center justify-between text-[11px]" style={{ color: 'var(--text-muted)' }}>
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>
            {track && !isDj ? `${formatTime(progressMs)} / ${formatTime(durationMs)}` : stationState.toUpperCase()}
          </span>
          <span className="flex items-center gap-2">
            {stationState !== 'idle' && (
              <span className="flex items-center gap-1">
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full animate-pulse"
                  style={{ background: 'var(--accent-pink)' }}
                />
                LIVE
              </span>
            )}
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>{clock}</span>
          </span>
        </div>
      </div>
    </LiquidGlass>
  )
}
