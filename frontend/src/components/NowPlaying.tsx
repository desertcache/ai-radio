import type { Track } from '../types/radio'

interface Props {
  track: Track | null
  powered: boolean
}

export function NowPlaying({ track, powered }: Props) {
  if (!powered || !track) return null

  return (
    <div className="flex items-center gap-3">
      {/* Album art */}
      {track.art_url && (
        <div
          className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0"
          style={{
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
          }}
        >
          <img
            src={track.art_url}
            alt={track.album || track.title}
            className="w-full h-full object-cover"
          />
        </div>
      )}

      {/* Track info */}
      <div className="min-w-0 flex-1">
        <div
          className="text-sm font-medium truncate"
          style={{ color: 'var(--text-primary)' }}
        >
          {track.title}
        </div>
        <div
          className="text-xs truncate"
          style={{ color: 'var(--text-secondary)' }}
        >
          {track.artist}
        </div>
      </div>
    </div>
  )
}
