import { useState, useEffect, useRef, useCallback } from 'react'
import type { RadioState, ServerMessage, ClientMessage, StationState } from '../types/radio'

const WS_URL = `ws://${window.location.hostname}:8000/ws/radio`
const RECONNECT_DELAY = 2000

export function useRadioSocket() {
  const [state, setState] = useState<RadioState>({
    stationState: 'idle',
    track: null,
    audioData: { amplitude: 0, bands: new Array(16).fill(0) },
    djText: '',
    djSegment: '',
    progressMs: 0,
    durationMs: 0,
    connected: false,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Use refs for high-frequency data to avoid re-renders
  const audioDataRef = useRef({ amplitude: 0, bands: new Array(16).fill(0) })
  const stationStateRef = useRef<StationState>('idle')

  const send = useCallback((msg: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  useEffect(() => {
    let mounted = true

    const connect = () => {
      if (!mounted) return

      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[Radio WS] Connected')
        if (mounted) setState(s => ({ ...s, connected: true }))
      }

      ws.onmessage = (event) => {
        try {
          const msg: ServerMessage = JSON.parse(event.data)

          switch (msg.type) {
            case 'audio_data':
              // Update ref only - components read via ref for 30fps canvas
              audioDataRef.current = { amplitude: msg.amplitude, bands: msg.bands }
              stationStateRef.current = msg.state
              break

            case 'now_playing':
              if (mounted) setState(s => ({
                ...s,
                track: msg.track,
                progressMs: msg.track.progress_ms,
                durationMs: msg.track.duration_ms,
              }))
              break

            case 'track_progress':
              if (mounted) setState(s => ({
                ...s,
                progressMs: msg.progress_ms,
                durationMs: msg.duration_ms,
              }))
              break

            case 'dj_text':
              if (mounted) setState(s => ({
                ...s,
                djText: msg.text,
                djSegment: msg.segment,
              }))
              break

            case 'station_state':
              stationStateRef.current = msg.state
              if (mounted) setState(s => ({ ...s, stationState: msg.state }))
              break
          }
        } catch (err) {
          console.error('[Radio WS] Parse error:', err)
        }
      }

      ws.onclose = () => {
        console.log('[Radio WS] Disconnected')
        if (mounted) {
          setState(s => ({ ...s, connected: false }))
          reconnectRef.current = setTimeout(connect, RECONNECT_DELAY)
        }
      }

      ws.onerror = (err) => {
        console.error('[Radio WS] Error:', err)
      }
    }

    connect()

    return () => {
      mounted = false
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  return { state, send, audioDataRef, stationStateRef }
}
