import { useState, useEffect } from 'react'
import type { Playlist } from '../types/radio'

interface Props {
  onSelect: (playlistId: string) => void
  powered: boolean
}

export function PlaylistPicker({ onSelect, powered }: Props) {
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!powered) return
    setLoading(true)
    fetch('/api/spotify/playlists')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) setPlaylists(data)
      })
      .catch(err => console.error('Failed to fetch playlists:', err))
      .finally(() => setLoading(false))
  }, [powered])

  if (!powered) return null

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors"
        style={{
          background: 'rgba(255,255,255,0.05)',
          color: 'var(--text-secondary)',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        {loading ? 'Loading playlists...' : 'Select a playlist...'}
        <span className="float-right opacity-50">{open ? '\u25B2' : '\u25BC'}</span>
      </button>

      {open && (
        <div
          className="absolute left-0 right-0 mt-1 rounded-lg overflow-hidden z-10 max-h-64 overflow-y-auto"
          style={{
            background: 'rgba(11,13,26,0.9)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,255,255,0.08)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          }}
        >
          {playlists.map(pl => (
            <button
              key={pl.id}
              className="w-full text-left px-3 py-2 flex items-center gap-3 transition-colors"
              style={{ color: 'var(--text-primary)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              onClick={() => {
                onSelect(pl.id)
                setOpen(false)
              }}
            >
              {pl.image_url && (
                <img src={pl.image_url} alt="" className="w-8 h-8 rounded object-cover flex-shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <div className="text-sm truncate">{pl.name}</div>
                <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  {pl.track_count} tracks
                </div>
              </div>
            </button>
          ))}

          {playlists.length === 0 && !loading && (
            <div className="px-3 py-4 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
              No playlists found. Have you authenticated with Spotify?
            </div>
          )}
        </div>
      )}
    </div>
  )
}
