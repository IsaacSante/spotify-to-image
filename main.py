# main.py (Server 1 - Enhanced Visibility & Delay)
import logging
import os
import sys
import threading
import time
import queue
from typing import Optional, Dict
from dotenv import load_dotenv

from PIL import Image
os.environ["TOKENIZERS_PARALLELISM"] = "false"


# Local imports
from text_embedding_generator import TextEmbeddingGenerator
from image_searcher import ImageSearcher
from song_info import SongInfo  # Using the reverted version
from llm_analysis import LLMAnalysis
from song_analysis_storage import SongAnalysisStorage

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
load_dotenv()

# --- Constants ---
EMBEDDINGS_DIR = "embeddings"
EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "image_embeddings.npy")
PATHS_FILE = os.path.join(EMBEDDINGS_DIR, "image_paths.pkl")
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
TOP_K_RESULTS = 1
POLL_INTERVAL_SECONDS = 3.0
SPOTIFY_URL = "https://open.spotify.com/lyrics"
# --- New Constant for Delay ---
DISPLAY_DELAY_SECONDS = 0

# --- Shared State & Events ---
stop_event = threading.Event()

# --- Global instances (initialized in main) ---
song_info: Optional[SongInfo] = None
llm_analyzer: Optional[LLMAnalysis] = None
storage: Optional[SongAnalysisStorage] = None
text_embedder: Optional[TextEmbeddingGenerator] = None
searcher: Optional[ImageSearcher] = None

# --- Function to Display Image ---
def display_top_image(image_path: str, query: str):
    """
    Tries to display the image at the given path using the default system viewer.

    NOTE: This function opens a *new* window for each image using the OS default
    viewer. It does NOT automatically close the previous image window due to
    limitations in controlling external applications launched this way.
    You will need to manually close the image windows as they appear.
    """
    if not image_path:
        logging.warning("display_top_image called with no image path.")
        return

    print(f"\n---> Displaying Image for Visual Sentence: '{query}'") # Make this stand out more
    print(f"      Image Path: {os.path.relpath(image_path)}")

    # Check display environment (same as before)
    display_env = os.environ.get('DISPLAY')
    is_windows = sys.platform == "win32"
    is_macos = sys.platform == "darwin"

    if not display_env and not is_windows and not is_macos:
         logging.warning("No display environment detected. Skipping image display.")
         print("(Skipping image display - no graphical environment detected)")
         return

    try:
        img = Image.open(image_path)
        # .show() opens in the default viewer. Closing it is manual.
        img.show(title=f"Lyric Visual: {query}")
        print("(Remember to manually close previous image windows)") # Add reminder
    except FileNotFoundError:
        logging.error(f"Image file not found at path: {image_path}")
        print(f"\nError: Could not find the image file at {image_path}")
    except Exception as e:
        logging.error(f"Failed to open or display image {image_path}: {e}")
        print(f"\nError: Could not display the image {image_path}. Reason: {e}")
        print("(Ensure you have a default image viewer application.)")

# --- Callback for New Lyrics ---
def handle_new_lyric(lyric_line: str):
    """
    Callback function executed by SongInfo when a new lyric line is detected.
    Looks up the pre-analyzed sentence and triggers the image search with delay.
    """
    global storage, text_embedder, searcher

    if not storage or not text_embedder or not searcher:
        logging.warning("Components not ready, skipping lyric processing.")
        return

    current_song_title = storage.get_current_song_title()
    if not current_song_title:
        # This warning is normal when starting or between songs
        # logging.debug("No current song title known, cannot process lyric yet.")
        return

    # --- Enhanced Print Statements ---
    print("\n" + "="*70)
    print(f"===> [LYRIC DETECTED] :: '{lyric_line}'")
    # --- End Enhanced Print ---

    # 1. Find the pre-generated concrete visual sentence
    visual_sentence = storage.find_analysis_by_lyric(current_song_title, lyric_line)

    if visual_sentence:
        # --- Enhanced Print Statements ---
        print(f"===> [VISUAL SENTENCE] :: '{visual_sentence}'")
        print(f"----- Searching for image based on visual sentence...")
        # --- End Enhanced Print ---

        # 2. Generate text embedding for the visual sentence
        text_embedding = text_embedder.generate_embedding(visual_sentence)

        if text_embedding is not None:
            # 3. Perform image search
            results = searcher.search(text_embedding, top_k=TOP_K_RESULTS)

            # 4. Introduce Delay and Display the top result
            if results:
                top_image_path, score = results[0]
                logging.info(f"      Top Image Match (Score: {score:.4f}): {os.path.relpath(top_image_path)}")

                # --- Add Delay Here ---
                print(f"----- Waiting {DISPLAY_DELAY_SECONDS}s before display...")
                time.sleep(DISPLAY_DELAY_SECONDS)
                # --- End Delay ---

                display_top_image(top_image_path, visual_sentence)
            else:
                logging.warning(f"      No image results found for sentence: '{visual_sentence}'")
                print("----- No matching image found.") # Add clear console message
        else:
            logging.error(f"      Could not generate text embedding for: '{visual_sentence}'")
            print("----- Failed to generate text embedding.") # Add clear console message
    else:
        # This might happen if LLM analysis hasn't finished yet or failed for this line
        logging.warning(f"      Visual sentence not found in storage for lyric: '{lyric_line}'")
        print(f"===> [ANALYSIS PENDING] Visual sentence for this line not yet available.")
    print("="*70 + "\n") # Footer separator


# --- Thread Function for Monitoring Song Title & Triggering Analysis (Unchanged) ---
def monitor_song_title_and_trigger_analysis():
    """
    Runs in a thread. Periodically checks for song title changes using SongInfo.
    If a new song is detected, it fetches all lyrics and starts the LLM analysis
    in another background thread via LLMAnalysis.
    """
    global song_info, llm_analyzer, storage
    logging.info("Song title monitor thread started.")
    last_processed_title = None

    while not stop_event.is_set():
        if not song_info or not llm_analyzer or not storage:
            logging.warning("Monitor Thread: Components not ready, waiting...")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        try:
            current_title = song_info.update_song_title()

            if current_title and current_title != last_processed_title:
                logging.info(f"\n{'='*20} New Song Detected: {current_title} {'='*20}")
                last_processed_title = current_title
                storage.start_new_song(current_title)
                print(f"Fetching full lyrics for '{current_title}'...")
                time.sleep(1.0)
                full_lyrics = song_info.get_fullscreen_lyrics()

                if full_lyrics:
                    logging.info(f"Got {len(full_lyrics.splitlines())} lines. Triggering LLM analysis (this may take a moment)...")
                    analysis_status = llm_analyzer.analyze_lyrics_in_background(
                        full_lyrics,
                        storage.add_analysis_line
                    )
                    logging.info(f"LLM background analysis status: {analysis_status}")
                else:
                    logging.warning(f"Could not fetch full lyrics for '{current_title}'. Skipping LLM analysis.")

        except Exception as e:
            if stop_event.is_set() and "invalid session id" in str(e).lower():
                 break
            logging.error(f"Error in song title monitoring loop: {e}")
            wait_time = POLL_INTERVAL_SECONDS * 2
        else:
            wait_time = POLL_INTERVAL_SECONDS
        stop_event.wait(timeout=wait_time)

    logging.info("Song title monitor thread stopped.")


# --- Main Application Logic (Initialization largely unchanged) ---
def run_visualizer_app():
    """Initializes components and starts monitoring threads."""
    global song_info, llm_analyzer, storage, text_embedder, searcher

    print("--- Spotify Lyric Visualizer ---")
    print("NOTE: This app will open image windows using your default viewer.")
    print("      You will need to manually close previous image windows.")
    print("-" * 40)

    try:
        logging.info("Initializing components...")
        if not os.getenv("GOOGLE_API_KEY"):
            print("\nERROR: GOOGLE_API_KEY not found in environment variables...")
            sys.exit(1)

        storage = SongAnalysisStorage()
        llm_analyzer = LLMAnalysis()
        text_embedder = TextEmbeddingGenerator(model_name=CLIP_MODEL_NAME)
        searcher = ImageSearcher(embeddings_file=EMBEDDINGS_FILE, paths_file=PATHS_FILE)

        print("Initializing Selenium and loading Spotify...")
        song_info = SongInfo(headless=True) # Using the reverted SongInfo class
        song_info.load_site(SPOTIFY_URL) # Uses the original short wait

        logging.info("Components initialized successfully.")

    except FileNotFoundError as e:
         logging.error(f"Initialization failed: {e}")
         print(f"\nError: Embeddings files not found...")
         return
    except ValueError as e:
        logging.error(f"Initialization failed: {e}")
        print(f"\nError: {e} (Check .env file)")
        return
    except Exception as e:
        logging.critical(f"Critical initialization failed: {e}")
        print(f"\nAn unexpected error occurred during initialization: {e}")
        if song_info: song_info.close()
        return

    # --- Start Monitoring Threads (Unchanged) ---
    threads = []
    try:
        print("\nStarting monitoring threads...")
        title_monitor_thread = threading.Thread(
            target=monitor_song_title_and_trigger_analysis,
            name="TitleMonitorThread",
            daemon=True
        )
        threads.append(title_monitor_thread)
        title_monitor_thread.start()

        lyric_monitor_thread = threading.Thread(
            target=song_info.monitor_current_lyric,
            args=(handle_new_lyric, stop_event),
            name="LyricMonitorThread",
            daemon=True
        )
        threads.append(lyric_monitor_thread)
        lyric_monitor_thread.start()

        print("\nMonitoring Spotify for lyrics...")
        print("Visualizations will appear as lyrics change.")
        print("Press Ctrl+C to stop.")

        while not stop_event.is_set():
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nCtrl+C detected! Initiating shutdown...")
    except Exception as e:
        logging.critical(f"An unexpected error occurred during runtime: {e}")
    finally:
        print("\nShutting down...")
        stop_event.set()
        for thread in threads:
            if thread.is_alive():
                print(f"Waiting for {thread.name} to finish...")
                thread.join(timeout=5.0)
                if thread.is_alive():
                    logging.warning(f"Thread {thread.name} did not finish cleanly.")
        if song_info:
            print("Closing browser...")
            song_info.close()
        print("Shutdown complete. Exited.")


if __name__ == "__main__":
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow library not found. pip install Pillow")
        sys.exit(1)

    print("Note: Ensure ChromeDriver is installed and compatible with your Chrome browser.")
    print("      It should be accessible via your system's PATH.")

    run_visualizer_app()