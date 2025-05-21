# song_state.py
import json, threading, requests
from typing import Optional

TD_ENDPOINT = "http://127.0.0.1:9980/songstate"   # ↙ match port/path you expose in TD
TIMEOUT      = 1.0                                # seconds for the POST

class SongState:
    """Keeps the current song‑level data and can push it to TouchDesigner."""

    def __init__(
        self,
        song_title:       Optional[str] = None,
        original_lyric:   Optional[str] = None,
        analyzed_lyric:   Optional[str] = None,
        lyric_image_path: Optional[str] = None,
        segmented_image_path: Optional[str] = None, 
        text_rect: dict | None = None 
    ):
        self.song_title       = song_title
        self.original_lyric   = original_lyric
        self.analyzed_lyric   = analyzed_lyric
        self.lyric_image_path = lyric_image_path
        self.segmented_image_path = segmented_image_path,
        self.text_rect = text_rect  
        self._lock = threading.Lock()

    # ---------- public helpers ----------
    def to_dict(self) -> dict:
        """Return a plain JSON‑serialisable dict."""
        return {
            "songTitle":       self.song_title,
            "originalLyric":   self.original_lyric,
            "analyzedLyric":   self.analyzed_lyric,
            "lyricImagePath":  self.lyric_image_path,
        }

    def update(self, **kwargs) -> None:
        """Update any subset of fields atomically."""
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    def send_to_td(self) -> bool:
        """POST the current dict to TouchDesigner.  Returns True if 2xx."""
        payload = self.to_dict()
        try:
            r = requests.post(TD_ENDPOINT, json=payload, timeout=TIMEOUT)
            return r.ok
        except requests.RequestException as e:
            print(f"[SongState] TD POST failed – {e}")
            return False
