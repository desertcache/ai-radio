export type StationState = 'idle' | 'music' | 'dj_transition' | 'dj_break'

export interface Track {
  id: string
  uri: string
  title: string
  artist: string
  album?: string
  art_url: string | null
  progress_ms: number
  duration_ms: number
  is_playing?: boolean
}

export interface Playlist {
  id: string
  uri: string
  name: string
  track_count: number
  image_url: string | null
}

export interface AudioData {
  amplitude: number
  bands: number[]
}

export interface RadioState {
  stationState: StationState
  track: Track | null
  audioData: AudioData
  djText: string
  djSegment: string
  progressMs: number
  durationMs: number
  connected: boolean
}

// WebSocket message types from server
export type ServerMessage =
  | { type: 'audio_data'; amplitude: number; bands: number[]; state: StationState }
  | { type: 'now_playing'; track: Track }
  | { type: 'track_progress'; progress_ms: number; duration_ms: number }
  | { type: 'dj_text'; text: string; segment: string }
  | { type: 'station_state'; state: StationState }
  | { type: 'playlists'; items: Playlist[] }

// WebSocket message types to server
export type ClientMessage =
  | { type: 'skip' }
  | { type: 'set_volume'; value: number }
  | { type: 'select_playlist'; playlist_id: string }
  | { type: 'request_segment'; segment: string }
