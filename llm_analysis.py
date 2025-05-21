import google.generativeai as genai
import google.api_core.exceptions 
import os
from dotenv import load_dotenv
import time
import asyncio
import threading
import traceback
import logging
from typing import Optional, Dict, Callable

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

load_dotenv()

MODEL = "gemini-2.0-flash-lite"
MAX_RETRIES = 3 
INITIAL_RETRY_DELAY_SECONDS = 2 
MAX_RETRY_DELAY_SECONDS = 16 

class LLMAnalysis:
    def __init__(self, model_name: str = MODEL):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if self.api_key is None:
            raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in your .env file.")
        self.model_name = model_name
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        if not self.client:
            try:
                genai.configure(api_key=self.api_key)
                # --- Check if model name is valid ---
                # Optional: List available models to verify the name
                # models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # model_names = [m.name for m in models]
                # logging.debug(f"Available GenAI Models: {model_names}")
                # if f"models/{self.model_name}" not in model_names and self.model_name not in model_names:
                #     logging.warning(f"Model name '{self.model_name}' might not be listed as available. Trying anyway.")
                # --- End Check ---

                self.model = genai.GenerativeModel(self.model_name)
                logging.info(f"Google GenAI Model '{self.model_name}' initialized.")
                self.client = True
            except Exception as e:
                logging.error(f"Error initializing Google GenAI Model: {e}")
                # Check for common errors like invalid API key or model name issues
                if "API key not valid" in str(e):
                    logging.error("Please check if the GOOGLE_API_KEY in your .env file is correct and has the Generative Language API enabled.")
                elif "Resource not found" in str(e) or "Could not find model" in str(e):
                     logging.error(f"The model name '{self.model_name}' might be incorrect or not available for your API key. Try 'gemini-1.5-flash-latest'.")

                self.client = None
                raise

    def generate_prompt(self, cleaned_lyrics: str) -> str:
        prompt = (
            "Turn the song into a flowing storyboard of images for an image‑search engine.\n\n"

            "Guidelines (read carefully):\n"
            "1.  Maintain **narrative continuity**: keep an internal idea of the CURRENT image.\n"
            "2.  For each new lyric line, decide between:\n"
            "    a. **KEEP** – if the line merely deepens the same moment, stay with the\n"
            "       current image tag OR make a *subtle* adjustment (e.g., add one adjective).\n"
            "    b. **SHIFT** – if using the same tag twice in a row would make two nearly\n"
            "       identical pictures, create a NEW 2‑4‑word tag that is *visually distinct* \n"
            "       yet still fits the story (e.g., change camera angle, pick another object\n"
            "       in the scene, switch mood adjective).\n"
            "   ➜  Never let the exact same tag repeat more than once consecutively.\n"
            "3.  Tags must be 2‑4 lower‑case words, no filler (a, the, and, with…).\n"
            "4.  Format for every line, exactly:\n"
            "       LYRIC: [original line]\n"
            "       SENTENCE: [image‑tag]\n"
            "       <<END>>\n\n"

            "--- tiny continuity example ---\n"
            "LYRIC: I walk alone at night\n"
            "SENTENCE: lonely city street\n"
            "<<END>>\n"
            "LYRIC: The moon follows me\n"
            "SENTENCE: moonlit city street   # subtle tweak, still one image\n"
            "<<END>>\n"
            "LYRIC: Footsteps echo behind\n"
            "SENTENCE: shadowed alleyway     # new distinct view to avoid repetition\n"
            "<<END>>\n\n"

            "--- lyrics to transform ---\n"
            f"{cleaned_lyrics}"
        )
        return prompt

    # def generate_prompt(self, cleaned_lyrics: str) -> str:
    #     prompt = (
    #         "You are an assistant creating extremely simple visual keywords from song lyrics for an image search.\n"
    #         "Analyze these song lyrics line by line. For EACH line, generate a **minimal visual description** focusing on the absolute core subject, action, or object.\n\n"
    #         "**Key Requirements:**\n"
    #         "1.  **Extreme Simplicity:** Use only 2-4 essential words. Think Subject-Verb, Subject-Adjective, or core Noun-Phrase.\n"
    #         "2.  **Keywords:** Output should resemble search keywords (e.g., 'sun shining', 'man running', 'sad face', 'red car').\n"
    #         "3.  **Omit Unnecessary Words:** STRICTLY AVOID articles (a, an, the), prepositions (in, on, under, with), conjunctions (and, but), and descriptive filler unless absolutely essential for meaning.\n"
    #         "4.  **Core Visual Only:** If a lyric has multiple ideas, pick the SINGLE most dominant, concrete visual element.\n"
    #         "5.  **Abstract Concepts:** Translate to the simplest possible visual icon/keyword (e.g., 'love' -> 'heart shape', 'sadness' -> 'crying face' or 'rain cloud', 'idea' -> 'lightbulb').\n"
    #         "6.  **Non-Visual Lyrics:** If a lyric is vocalization ('la la', 'ooh') or has no clear visual, output exactly: SENTENCE: (No visual)\n\n"
    #         "Output *exactly* in this format for each line (NO extra words or explanation):\n"
    #         "LYRIC: [the original lyric text]\n"
    #         "SENTENCE: [the generated minimal visual description OR (No visual)]\n"
    #         "<<END>>\n\n"
    #         "--- Examples ---\n\n"
    #         "Example 1:\n"
    #         "LYRIC: The sky is crying tears of joy\n"
    #         "SENTENCE: Sun showers falling\n"
    #         "<<END>>\n\n"
    #         "Example 2:\n"
    #         "LYRIC: I'm lost in the crowd\n"
    #         "SENTENCE: Person lost crowd\n"
    #         "<<END>>\n\n"
    #         "Example 3:\n"
    #         "LYRIC: She walks in beauty, like the night\n"
    #         "SENTENCE: Woman under stars\n"
    #         "<<END>>\n\n"
    #         "Example 4 (Abstract):\n"
    #         "LYRIC: My heart is broken\n"
    #         "SENTENCE: Broken heart shape\n"
    #         "<<END>>\n\n"
    #         "Example 5 (Non-Visual):\n"
    #         "LYRIC: Fa-la-la-la-la\n"
    #         "SENTENCE: (No visual)\n"
    #         "<<END>>\n\n"
    #         "Example 6 (Action Focus):\n"
    #         "LYRIC: He ran fast through the field\n"
    #         "SENTENCE: Man running field\n"
    #         "<<END>>\n\n"
    #         "Example 7 (Object Focus):\n"
    #         "LYRIC: I see a red door and I want it painted black\n"
    #         "SENTENCE: Red door painted black\n" # Focuses on the transformation/key objects
    #         "<<END>>\n\n"
    #         "Example 8 (More Complex Lyric -> Simplification):\n"
    #         "LYRIC: The answer, my friend, is blowin' in the wind\n"
    #         "SENTENCE: Wind blowing leaves\n" # Simplest related visual
    #         "<<END>>\n\n"
    #         "--- Lyrics to Analyze ---\n"
    #         f"{cleaned_lyrics}"
    #     )
    #     return prompt





    def parse_section(self, section_text: str) -> Optional[Dict[str, str]]:
        section = section_text.strip()
        if not section:
            return None

        result = {'lyric': None, 'sentence': None}
        lines = section.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('LYRIC:'):
                result['lyric'] = line[len('LYRIC:'):].strip()
            elif line.startswith('SENTENCE:'):
                result['sentence'] = line[len('SENTENCE:'):].strip()

        # Check if we got both parts
        if result['lyric'] and result['sentence']:
            return result
        elif section: # Only warn if the section wasn't just whitespace/empty
            logging.warning(f"LLM Parse Warning: Could not parse LYRIC and SENTENCE from section:\n---\n{section}\n---")
        return None

    def _print_analysis_data(self, data: dict):
        # ... (keep existing _print_analysis_data method) ...
        try:
            print(f"  [LLM Result] Lyric: {data.get('lyric', 'N/A')}")
            print(f"             Sentence: {data.get('sentence', 'N/A')}")
            print("-" * 20)
        except Exception as e:
            logging.error(f"Error printing analysis data chunk: {e}")
            logging.error(f"Problematic data: {data}")

    def _process_stream(self, chunk_stream, storage_callback: callable):
        """Processes the stream, parses sections, and calls the storage_callback."""
        buffer = ""
        total_items_processed = 0
        first_chunk_received = False
        start_time = time.time()

        for chunk in chunk_stream:
            # Accessing text can differ slightly depending on SDK version / stream type
            try:
                chunk_text = "".join(part.text for part in chunk.parts)
                # --- ADDED: Log the raw chunk text for debugging ---
                # Set logging level to DEBUG in main config to see these
                logging.debug(f"[LLM RAW CHUNK]: {chunk_text!r}")
                # --- END ADDED ---
            except (AttributeError, TypeError, ValueError) as e:
                 logging.debug(f"Debug: Error accessing chunk text (likely empty finish chunk): {e}")
                 chunk_text = ""
            except Exception as e: # Catch potential other errors during chunk processing
                 logging.error(f"[LLM Thread] Unexpected error processing chunk content: {e}")
                 logging.debug(f"Chunk causing error: {chunk!r}")
                 chunk_text = ""


            if not first_chunk_received and chunk_text:
                first_chunk_received = True
                elapsed = time.time() - start_time
                logging.info(f"[LLM Thread] {elapsed:.2f}s until first token.")

            buffer += chunk_text

            # Process sections delimited by <<END>>
            while "<<END>>" in buffer:
                try:
                    parts = buffer.split("<<END>>", 1)
                    section = parts[0].strip()
                    buffer = parts[1] # Keep the rest for the next iteration

                    if section:
                        parsed_data = self.parse_section(section)
                        if parsed_data:
                            # 1. Print locally (optional)
                            # self._print_analysis_data(parsed_data)

                            # 2. Call the storage callback
                            if storage_callback:
                                try:
                                    storage_callback(parsed_data)
                                except Exception as cb_e:
                                    logging.error(f"[LLM Thread] Error in storage_callback: {cb_e}")
                                    traceback.print_exc()
                            total_items_processed += 1
                        # else: # Parsing failed, warning already logged in parse_section
                            # pass
                except Exception as e:
                    logging.error(f"[LLM Thread] Error processing <<END>> block: {e}")
                    traceback.print_exc()
                    # Attempt to recover by finding the next <<END>>
                    if "<<END>>" in buffer:
                         buffer = buffer.split("<<END>>", 1)[1]
                    else:
                         buffer = "" # Can't recover, clear buffer

        # Process any remaining content in the buffer after the stream ends
        try:
            remaining_section = buffer.strip()
            if remaining_section:
                 # Only process if it looks like a valid start
                 if 'LYRIC:' in remaining_section or 'SENTENCE:' in remaining_section:
                    logging.info("[LLM Thread] Processing remaining buffer content...")
                    parsed_data = self.parse_section(remaining_section)
                    if parsed_data:
                         # self._print_analysis_data(parsed_data) # Optional print
                         if storage_callback:
                             try:
                                 storage_callback(parsed_data)
                             except Exception as cb_e:
                                 logging.error(f"[LLM Thread] Error in final storage_callback: {cb_e}")
                                 traceback.print_exc()
                         total_items_processed += 1
        except Exception as e:
            logging.error(f"[LLM Thread] Error processing final buffer content: {e}")
            traceback.print_exc()

        return {"total_items_processed": total_items_processed}


    def _perform_analysis_thread(self, cleaned_lyrics: str, storage_callback: callable):
        """Runs the LLM analysis and processes results. Intended for threading. Includes retry logic."""
        logging.info("[LLM Thread] Analysis thread started.")
        thread_start_time = time.time()
        response_stream = None # Initialize outside the loop

        try:
            if not self.client or not self.model:
                logging.error("[LLM Thread] Error: LLM Client/Model not initialized.")
                return

            prompt = self.generate_prompt(cleaned_lyrics)

            # --- Retry Logic Loop ---
            current_delay = INITIAL_RETRY_DELAY_SECONDS
            for attempt in range(MAX_RETRIES + 1): # +1 because range is exclusive at the end
                try:
                    logging.info(f"[LLM Thread] Attempt {attempt + 1}/{MAX_RETRIES + 1}: Sending prompt to Google GenAI model...")
                    response_stream = self.model.generate_content(
                        prompt,
                        stream=True,
                        generation_config={'temperature': 0.3, 'top_p': 0.8}
                        # safety_settings={'HARASSMENT':'block_none'} # Optional
                    )

                    # If generate_content succeeded, process the stream
                    summary_info = self._process_stream(response_stream, storage_callback)
                    total_elapsed = time.time() - thread_start_time
                    items = summary_info.get('total_items_processed', 0)
                    logging.info(f"[LLM Thread] Stream processing completed in {total_elapsed:.2f} seconds. Stored {items} items.")
                    break # Exit retry loop on success

                # --- Catch Retriable Errors ---
                except (google.api_core.exceptions.ServiceUnavailable,
                        google.api_core.exceptions.ResourceExhausted, # Often means rate limit or quota
                        google.api_core.exceptions.DeadlineExceeded) as e:
                    logging.warning(f"[LLM Thread] Attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                    if attempt < MAX_RETRIES:
                        logging.info(f"[LLM Thread] Retrying in {current_delay:.2f} seconds...")
                        time.sleep(current_delay)
                        # Exponential backoff with jitter (optional but good practice)
                        current_delay = min(current_delay * 2 + (os.urandom(1)[0] / 255.0), MAX_RETRY_DELAY_SECONDS)
                    else:
                        logging.error(f"[LLM Thread] Max retries ({MAX_RETRIES + 1}) reached. Giving up.")
                        # Optionally, re-raise the last exception or handle failure state
                        # raise e # Or just log and exit thread
                # --- Catch Non-Retriable API Errors ---
                except google.api_core.exceptions.GoogleAPIError as e:
                    logging.error(f"\n[LLM Thread] A non-retriable Google API error occurred: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    break # Don't retry on auth errors, invalid requests etc.
                # --- Catch Other Unexpected Errors ---
                except Exception as e:
                    logging.error(f"\n[LLM Thread] An unexpected error occurred during LLM API call or stream setup: {e}")
                    traceback.print_exc()
                    break # Don't retry unknown errors

        # --- Catch errors outside the retry loop (e.g., prompt generation) ---
        except Exception as e:
            logging.error(f"\n[LLM Thread] An error occurred before or after API interaction: {e}")
            traceback.print_exc()
        finally:
             logging.info("[LLM Thread] Analysis thread finished.")

    # --- ADDED BACK: The Public Method to Start the Thread ---
    def analyze_lyrics_in_background(self, cleaned_lyrics: str, storage_callback: callable):
        """
        Starts the lyrics-to-visual-sentence analysis in a separate background thread.

        Args:
            cleaned_lyrics: The full lyrics text (cleaned) for the song.
            storage_callback: A callable function that accepts a dict
                              (e.g., {'lyric': str, 'sentence': str})
                              to store the result (e.g., SongAnalysisStorage.add_analysis_line).
        """
        if not cleaned_lyrics or cleaned_lyrics.isspace():
             logging.warning("LLMAnalysis: No lyrics provided, skipping analysis.")
             return {"status": "No lyrics provided"}
        if not self.client:
             logging.error("LLMAnalysis: Client not initialized, cannot start analysis.")
             return {"status": "LLM Client not ready"}

        logging.info("LLMAnalysis: Received request. Starting analysis in background thread...")
        try:
            analysis_thread = threading.Thread(
                target=self._perform_analysis_thread,
                args=(cleaned_lyrics, storage_callback),
                name="LLMAnalysisThread", # Give the thread a distinct name
                daemon=True # Ensures thread exits if main program exits
            )
            analysis_thread.start()
            return {"status": "Analysis started in background"}

        except Exception as e:
            logging.error(f"LLMAnalysis: Error starting analysis thread: {e}")
            traceback.print_exc()
            return {"status": "Error starting analysis", "error": str(e)}