"""Spotify playback controller using Spotipy."""

import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger("radio.spotify")


class SpotifyController:
    """Controls Spotify desktop app via Web API."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=(
                "user-modify-playback-state user-read-playback-state "
                "user-read-currently-playing playlist-read-private"
            ),
            cache_path=".spotify_cache",
            open_browser=True,
        )
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
        self.device_id: str | None = None
        logger.info("SpotifyController initialized")

    def get_auth_url(self) -> str:
        """Get the Spotify OAuth authorization URL."""
        return self.auth_manager.get_authorize_url()

    def handle_callback(self, code: str) -> bool:
        """Handle OAuth callback with authorization code."""
        try:
            self.auth_manager.get_access_token(code, as_dict=False)
            self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
            logger.info("Spotify authenticated successfully")
            return True
        except Exception as e:
            logger.error(f"Spotify auth failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if we have a valid Spotify token."""
        token = self.auth_manager.get_cached_token()
        return token is not None

    def find_device(self) -> str:
        """Find the Spotify desktop app device."""
        devices = self.sp.devices()["devices"]
        for d in devices:
            if d["is_active"] or d["type"] == "Computer":
                self.device_id = d["id"]
                logger.info(f"Found Spotify device: {d['name']}")
                return d["name"]
        raise RuntimeError("No Spotify device found. Is the desktop app running?")

    def play_track(self, track_uri: str):
        self.sp.start_playback(device_id=self.device_id, uris=[track_uri])

    def play_playlist(self, playlist_uri: str, shuffle: bool = True):
        self.sp.shuffle(shuffle, device_id=self.device_id)
        self.sp.start_playback(device_id=self.device_id, context_uri=playlist_uri)

    def pause(self):
        try:
            self.sp.pause_playback(device_id=self.device_id)
        except spotipy.exceptions.SpotifyException as e:
            if "Player command failed: Restriction violated" in str(e):
                logger.debug("Already paused")
            else:
                raise

    def resume(self):
        self.sp.start_playback(device_id=self.device_id)

    def set_volume(self, percent: int):
        """Set volume 0-100."""
        percent = max(0, min(100, percent))
        try:
            self.sp.volume(percent, device_id=self.device_id)
        except spotipy.exceptions.SpotifyException as e:
            logger.warning(f"Volume set failed: {e}")

    def skip(self):
        self.sp.next_track(device_id=self.device_id)

    def get_now_playing(self) -> dict | None:
        """Returns current track info."""
        try:
            data = self.sp.current_playback()
        except Exception as e:
            logger.warning(f"Failed to get playback: {e}")
            return None

        if not data or not data.get("item"):
            return None

        track = data["item"]
        return {
            "id": track["id"],
            "uri": track["uri"],
            "title": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "art_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "progress_ms": data["progress_ms"],
            "duration_ms": track["duration_ms"],
            "is_playing": data["is_playing"],
        }

    def get_audio_features(self, track_id: str) -> dict | None:
        """Energy, danceability, tempo, valence, etc."""
        try:
            features = self.sp.audio_features(track_id)
            return features[0] if features else None
        except Exception as e:
            logger.warning(f"Failed to get audio features: {e}")
            return None

    def get_user_playlists(self) -> list[dict]:
        """Returns user's playlists."""
        try:
            results = self.sp.current_user_playlists(limit=50)
        except Exception as e:
            logger.error(f"Failed to get playlists: {e}")
            return []

        return [{
            "id": p["id"],
            "uri": p["uri"],
            "name": p["name"],
            "track_count": p["tracks"]["total"],
            "image_url": p["images"][0]["url"] if p["images"] else None,
        } for p in results["items"]]

    def get_playlist_tracks(self, playlist_id: str) -> list[dict]:
        """Returns tracks in a playlist."""
        try:
            results = self.sp.playlist_tracks(playlist_id)
        except Exception as e:
            logger.error(f"Failed to get playlist tracks: {e}")
            return []

        return [{
            "id": t["track"]["id"],
            "uri": t["track"]["uri"],
            "title": t["track"]["name"],
            "artist": ", ".join(a["name"] for a in t["track"]["artists"]),
            "duration_ms": t["track"]["duration_ms"],
        } for t in results["items"] if t.get("track")]
