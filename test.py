# test.py (Updated to include image search)
import time
import random
import logging
import os
import sys
from song_state import SongState # Assuming song_state.py is in the same directory or Python path

# --- Add imports needed for image search ---
try:
    from text_embedding_generator import TextEmbeddingGenerator
    from image_searcher import ImageSearcher
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print("Please ensure text_embedding_generator.py and image_searcher.py are present.")
    sys.exit(1)

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SONG_TITLE = "test"
TD_ENDPOINT = "http://127.0.0.1:9980/songstate" # Match song_state.py

# --- Configuration for Image Search (Mirroring main.py) ---
EMBEDDINGS_DIR = "embeddings"
EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "image_embeddings.npy")
PATHS_FILE = os.path.join(EMBEDDINGS_DIR, "image_paths.pkl")
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32" # Match main.py
TOP_K_RESULTS = 1 # Match main.py

# --- Mock Data: Dictionary of Original Lyrics -> Analyzed Lyrics ---
# (Using the same dictionary as before)
mock_analysis_data = {
    "The sun dips low": "setting sun horizon",
    "Golden hour paints the clouds": "golden clouds sky",
    "A lone bird flies across the sky": "bird flying silhouette",
    "Streetlights start to flicker on": "glowing streetlights dusk",
    "Shadows lengthen on the ground": "long shadows ground",
    "A cool breeze whispers through the trees": "wind blowing trees",
    "Distant city hums alive": "cityscape lights night",
    "Stars begin to pierce the dark": "first stars appearing",
    "Moonlight spills onto the path": "moonlit path silver",
    "Empty benches in the park": "empty park bench",
    "Reflections shimmer on the lake": "water reflection moonlight",
    "Silent footsteps echo soft": "footsteps walking alone",
    "Windows glow with inner light": "warm window glow",
    "The world outside grows quiet now": "quiet peaceful night",
    "Thinking back on passing days": "fading memories thought",
    "Time slips through like grains of sand": "sand falling hourglass",
    "A single car drives slowly by": "car headlights moving",
    "Distant train whistle blows": "train sound distance",
    "Lost in thought, a quiet sigh": "person thinking sigh",
    "Another day draws to a close": "day ending peaceful",
    "Waiting for the night to fall": "anticipation darkness",
    "Crickets chirp their evening song": "cricket sound nature",
    "Fireflies dance in the air": "fireflies glowing dark",
    "The air is still and calm": "calm still air",
    "Feeling small beneath the vastness": "person under stars"
}

# Convert dictionary to a list of (original, analyzed) tuples for random.choice
mock_data_list = list(mock_analysis_data.items())

def run_test_sender():
    """
    Initializes components and periodically sends mock data including image paths.
    """
    logging.info(f"--- Test Sender Initializing (with Image Search) ---")
    logging.info(f"Targeting TouchDesigner endpoint: {TD_ENDPOINT}")
    logging.info(f"Using fixed song title: '{SONG_TITLE}'")

    # --- Initialize Components ---
    text_embedder: TextEmbeddingGenerator = None
    searcher: ImageSearcher = None
    song_state: SongState = None

    try:
        # Check for embedding files first
        if not os.path.exists(EMBEDDINGS_FILE):
            raise FileNotFoundError(f"Embeddings file not found: {EMBEDDINGS_FILE}")
        if not os.path.exists(PATHS_FILE):
             raise FileNotFoundError(f"Image paths file not found: {PATHS_FILE}")

        logging.info(f"Loading Text Embedder ({CLIP_MODEL_NAME})...")
        text_embedder = TextEmbeddingGenerator(model_name=CLIP_MODEL_NAME)

        logging.info("Loading Image Searcher...")
        searcher = ImageSearcher(embeddings_file=EMBEDDINGS_FILE, paths_file=PATHS_FILE)

        logging.info("Initializing SongState...")
        song_state = SongState(song_title=SONG_TITLE)

        logging.info("Components initialized successfully.")

    except FileNotFoundError as e:
         logging.error(f"Initialization failed: {e}")
         logging.error("Please ensure embeddings have been generated using 'image_embedding_generator.py'")
         logging.error("and the embedding files are in the 'embeddings' directory.")
         return
    except ImportError: # Already handled above, but as fallback
         logging.error("Failed due to missing modules. Check imports.")
         return
    except Exception as e:
        logging.error(f"Failed to initialize components: {e}")
        return # Cannot proceed

    logging.info(f"Starting mock data sending loop. Press Ctrl+C to stop.")

    try:
        while True:
            # 1. Get random data from the dictionary
            original_lyric, analyzed_lyric = random.choice(mock_data_list)
            logging.info(f"Selected: Lyric='{original_lyric}' -> Analyzed='{analyzed_lyric}'")

            image_path_to_send = None # Default to None

            # 2. Generate text embedding for the ANALYZED lyric
            logging.info(f"Generating embedding for: '{analyzed_lyric}'...")
            text_embedding = text_embedder.generate_embedding(analyzed_lyric)

            if text_embedding is not None:
                # 3. Perform image search
                logging.info(f"Searching for image...")
                results = searcher.search(text_embedding, top_k=TOP_K_RESULTS)

                if results:
                    top_image_path_relative, score = results[0]
                    # --- Ensure path is absolute for TD ---
                    image_path_to_send = os.path.abspath(top_image_path_relative)
                    logging.info(f"  Found Image (Score: {score:.4f}): {image_path_to_send}")
                else:
                    logging.warning(f"  No image results found for sentence: '{analyzed_lyric}'")
            else:
                logging.error(f"  Could not generate text embedding for: '{analyzed_lyric}'")

            # 4. Update the song state object (including the image path)
            song_state.update(
                original_lyric=original_lyric,
                analyzed_lyric=analyzed_lyric,
                lyric_image_path=image_path_to_send
                # song_title remains 'test'
            )

            logging.info(f"Sending State: Lyric='{original_lyric}', Analyzed='{analyzed_lyric}', ImagePath='{image_path_to_send}'")

            # 5. Send the state to TouchDesigner
            success = song_state.send_to_td()
            if success:
                logging.info(f"--> Successfully sent state to TD.")
            else:
                logging.warning(f"--> Failed to send state to TD. Is TD Web Server DAT running?")

            # 6. Wait for a random interval
            sleep_duration = random.uniform(5.0, 10.0)
            logging.info(f"--- Sleeping for {sleep_duration:.2f} seconds ---")
            time.sleep(sleep_duration)

    except KeyboardInterrupt:
        logging.info("\nCtrl+C detected. Shutting down test sender.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in the loop: {e}", exc_info=True) # Add traceback
    finally:
        logging.info("--- Test Sender Stopped ---")

if __name__ == "__main__":
    # Basic check for essential components
    required_files = ["song_state.py", "text_embedding_generator.py", "image_searcher.py"]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"Error: Missing required files: {', '.join(missing_files)}")
        print("Please ensure this test script is in the same directory as the main project files.")
    else:
        # Check for embeddings directory existence (optional but helpful)
        if not os.path.isdir(EMBEDDINGS_DIR):
             print(f"Warning: Embeddings directory '{EMBEDDINGS_DIR}' not found.")
             print("Image search will likely fail. Ensure embeddings are generated.")
        elif not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(PATHS_FILE):
             print(f"Warning: Embedding files '{EMBEDDINGS_FILE}' or '{PATHS_FILE}' not found inside '{EMBEDDINGS_DIR}'.")
             print("Image search will likely fail. Ensure embeddings are generated.")

        run_test_sender()