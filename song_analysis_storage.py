# song_analysis_storage.py
import threading
import string
import logging
from typing import Dict, Optional, List, Union # Ensure correct imports

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SongAnalysisStorage:
    """
    Stores line-by-line analysis data (specifically, concrete visual sentences)
    for multiple songs, optimized for fast lookup by the original lyric text.
    """
    def __init__(self):
        # Key: song_title (str)
        # Value: dict { normalized_original_lyric_text (str): concrete_sentence (str) }
        self.song_data: Dict[str, Dict[str, str]] = {}
        self.current_song_title: Optional[str] = None
        self._lock = threading.Lock()
        logging.info("SongAnalysisStorage initialized (Storing Visual Sentences).")

    def _normalize_lyric(self, lyric_text: str) -> str:
        """Simple normalization: lowercase and remove punctuation/extra whitespace."""
        if not lyric_text:
            return ""
        # Keep apostrophes as they might be important for matching lyrics
        # Remove other punctuation
        punctuation_to_remove = string.punctuation.replace("'", "")
        translator = str.maketrans('', '', punctuation_to_remove)
        normalized = lyric_text.translate(translator)
        normalized = normalized.lower().strip()
        # Replace multiple spaces with single space
        normalized = ' '.join(normalized.split())
        return normalized

    def start_new_song(self, song_title: str):
        """
        Registers a new song title and prepares its storage. Clears previous data.
        """
        if not song_title:
            logging.warning("Storage: Attempted to start analysis for an empty song title.")
            return

        with self._lock:
            logging.info(f"Storage: Starting analysis collection for song: '{song_title}'")
            self.current_song_title = song_title
            # Clear previous analysis for this song title if it exists
            self.song_data[song_title] = {}

    def add_analysis_line(self, analysis_data: Dict[str, str]):
        """
        Adds the generated visual sentence for a single lyric line to the
        current song's storage, keyed by the normalized original lyric text.

        Args:
            analysis_data (dict): Expected format {'lyric': str, 'sentence': str}
        """
        original_lyric = analysis_data.get('lyric')
        concrete_sentence = analysis_data.get('sentence')

        if not original_lyric or not concrete_sentence:
            logging.warning(f"Storage: Received incomplete analysis data. Need 'lyric' and 'sentence'. Ignored: {analysis_data}")
            return

        normalized_lyric = self._normalize_lyric(original_lyric)
        if not normalized_lyric:
             logging.warning(f"Storage: Original lyric '{original_lyric}' normalized to empty string. Ignored.")
             return

        with self._lock:
            if self.current_song_title is None:
                logging.warning(f"Storage: add_analysis_line called but no current song title set. Lyric ignored: '{original_lyric}'")
                return

            # Ensure the dictionary for the current song exists (should be created by start_new_song)
            if self.current_song_title not in self.song_data:
                logging.warning(f"Storage: Dictionary for current song '{self.current_song_title}' missing during add. Re-creating.")
                self.song_data[self.current_song_title] = {}

            # Store the concrete sentence using the normalized original lyric as the key
            # logging.debug(f"Storage: Storing '{concrete_sentence}' for lyric (normalized): '{normalized_lyric}'")
            self.song_data[self.current_song_title][normalized_lyric] = concrete_sentence

    def find_analysis_by_lyric(self, song_title: str, current_lyric_text: str) -> Optional[str]:
        """
        Finds the stored concrete visual sentence for a specific lyric within a given song.
        Uses normalized matching.

        Args:
            song_title: The title of the song.
            current_lyric_text: The text of the lyric being currently sung/displayed.

        Returns:
            The concrete visual sentence (str) or None if not found.
        """
        if not song_title or not current_lyric_text:
            # logging.debug("Storage Find: Missing title or lyric text.")
            return None

        normalized_lookup = self._normalize_lyric(current_lyric_text)
        if not normalized_lookup:
             # logging.debug(f"Storage Find: Lookup lyric '{current_lyric_text}' normalized to empty.")
             return None

        with self._lock:
            song_analysis_dict = self.song_data.get(song_title)
            if song_analysis_dict:
                found_sentence = song_analysis_dict.get(normalized_lookup)
                # if not found_sentence:
                #      logging.debug(f"Storage Find: Lyric '{normalized_lookup}' not found in dict for '{song_title}'.")
                # else:
                #      logging.debug(f"Storage Find: Found sentence for '{normalized_lookup}': '{found_sentence}'")
                return found_sentence # Returns the sentence string or None if key not found
            else:
                # logging.debug(f"Storage Find: No analysis dict found for song '{song_title}'.")
                return None

    def get_analysis_dict_for_song(self, song_title: str) -> Optional[Dict[str, str]]:
         """Retrieves the dictionary {normalized_lyric: concrete_sentence} for a song."""
         with self._lock:
             return self.song_data.get(song_title)

    def get_current_song_title(self) -> Optional[str]:
        with self._lock:
            return self.current_song_title

    def get_all_stored_songs(self) -> List[str]:
        with self._lock:
            return list(self.song_data.keys())