import { useState, useCallback, useEffect } from 'react'
import { useRadioSocket } from './hooks/useRadioSocket'
import { RadioCabinet } from './components/RadioCabinet'
import { DisplayPanel } from './components/DisplayPanel'
import { VUMeter } from './components/VUMeter'
import { FrequencyBars } from './components/FrequencyBars'
import { ControlKnobs } from './components/ControlKnobs'
import { PowerButton } from './components/PowerButton'
import { NowPlaying } from './components/NowPlaying'
import { SegmentIndicator } from './components/SegmentIndicator'
import { PlaylistPicker } from './components/PlaylistPicker'

export default function App() {
  const { state, send, audioDataRef } = useRadioSocket()
  const [powered, setPowered] = useState(false)
  const [authenticated, setAuthenticated] = useState(false)

  // Check auth status on mount and after URL param
  useEffect(() => {
    fetch('/api/spotify/status')
      .then(r => r.json())
      .then(data => {
        if (data.authenticated) setAuthenticated(true)
      })
      .catch(() => {})

    // Check for auth success redirect
    const params = new URLSearchParams(window.location.search)
    if (params.get('auth') === 'success') {
      setAuthenticated(true)
      window.history.replaceState({}, '', '/')
    }
  }, [])

  const handlePower = useCallback(() => {
    if (!powered) {
      setPowered(true)
    } else {
      setPowered(false)
      fetch('/api/radio/stop', { method: 'POST' }).catch(() => {})
    }
  }, [powered])

  const handleAuth = useCallback(() => {
    window.location.href = '/api/spotify/auth'
  }, [])

  const handleDemo = useCallback(() => {
    fetch('/api/radio/demo', { method: 'POST' })
      .then(() => setPowered(true))
      .catch(err => console.error('Failed to start demo:', err))
  }, [])

  const handleSelectPlaylist = useCallback((playlistId: string) => {
    fetch('/api/radio/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: playlistId }),
    }).catch(err => console.error('Failed to start radio:', err))
  }, [])

  const handleSkip = useCallback(() => {
    send({ type: 'skip' })
  }, [send])

  return (
    <RadioCabinet powered={powered}>
      {/* Display panel */}
      <DisplayPanel
        track={state.track}
        djText={state.djText}
        djSegment={state.djSegment}
        stationState={state.stationState}
        progressMs={state.progressMs}
        durationMs={state.durationMs}
        powered={powered}
      />

      {/* VU Meters + Segment Indicator row */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <VUMeter audioDataRef={audioDataRef} channel="left" powered={powered} />
        </div>
        <div className="flex flex-col items-center gap-2">
          <SegmentIndicator
            stationState={state.stationState}
            djSegment={state.djSegment}
            powered={powered}
          />
          <NowPlaying track={state.track} powered={powered} />
        </div>
        <div className="flex-1">
          <VUMeter audioDataRef={audioDataRef} channel="right" powered={powered} />
        </div>
      </div>

      {/* Frequency bars */}
      <FrequencyBars audioDataRef={audioDataRef} powered={powered} />

      {/* Controls row */}
      <div className="flex items-center justify-between">
        <ControlKnobs send={send} powered={powered} />

        <div className="flex items-center gap-3">
          {/* Skip button */}
          {powered && (
            <button
              onClick={handleSkip}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
              style={{
                background: 'rgba(124,92,255,0.1)',
                color: '#a78bfa',
                border: '1px solid rgba(124,92,255,0.2)',
              }}
            >
              SKIP
            </button>
          )}

          <PowerButton powered={powered} onToggle={handlePower} />
        </div>
      </div>

      {/* Spotify auth or playlist picker */}
      {powered && !authenticated && (
        <div className="flex flex-col gap-2">
          <button
            onClick={handleAuth}
            className="w-full py-2.5 rounded-lg text-sm font-medium transition-colors"
            style={{
              background: '#1DB954',
              color: '#fff',
            }}
          >
            Connect Spotify
          </button>
          <button
            onClick={handleDemo}
            className="w-full py-2.5 rounded-lg text-sm font-medium transition-colors"
            style={{
              background: 'rgba(124,92,255,0.12)',
              color: '#a78bfa',
              border: '1px solid rgba(124,92,255,0.2)',
            }}
          >
            Demo Mode
          </button>
        </div>
      )}

      {powered && authenticated && (
        <PlaylistPicker onSelect={handleSelectPlaylist} powered={powered} />
      )}

      {/* Connection indicator */}
      {powered && (
        <div className="flex items-center gap-1.5 justify-center">
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: state.connected ? '#22c55e' : '#ef4444' }}
          />
          <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
            {state.connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      )}
    </RadioCabinet>
  )
}
