import type { StationState } from '../types/radio'

interface Props {
  stationState: StationState
  djSegment: string
  powered: boolean
}

const LABELS: Record<string, string> = {
  idle: 'OFF',
  music: 'MUSIC',
  dj_transition: 'DJ',
  dj_break: 'BREAK',
  news: 'NEWS',
  weather: 'WEATHER',
  ad: 'AD',
}

export function SegmentIndicator({ stationState, djSegment, powered }: Props) {
  if (!powered) return null

  // Use segment type for DJ breaks, otherwise use station state
  const label = djSegment && stationState.startsWith('dj')
    ? LABELS[djSegment] || djSegment.toUpperCase()
    : LABELS[stationState] || stationState.toUpperCase()

  const isActive = stationState !== 'idle'

  return (
    <div
      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase"
      style={{
        background: isActive ? 'rgba(124,92,255,0.12)' : 'rgba(255,255,255,0.05)',
        color: isActive ? '#a78bfa' : 'rgba(255,255,255,0.3)',
        border: `1px solid ${isActive ? 'rgba(124,92,255,0.25)' : 'rgba(255,255,255,0.08)'}`,
      }}
    >
      {isActive && (
        <span
          className="w-1.5 h-1.5 rounded-full mr-1.5 animate-pulse"
          style={{ background: '#7c5cff' }}
        />
      )}
      {label}
    </div>
  )
}
