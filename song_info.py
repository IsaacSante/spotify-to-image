# song_info.py (Reverted to Original Logic)

import os
import getpass
import time
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from typing import Callable, Optional # Added Optional for type hints if needed later
import logging # Added for consistency with Server 1 logging

# Basic logging setup (can be configured further in main.py)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SongInfo:
    def __init__(self, headless=False):
        """
        Initializes the SongInfo instance.
        :param headless: Whether to run Chrome in headless mode.
        """
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None # Added type hint
        self.current_song_title: Optional[str] = None # Added type hint
        self.song_title_history: list[str] = [] # Added type hint
        # WARNING: This class name might change with Spotify updates!
        self._active_lyric_class = "EhKgYshvOwpSrTv399Mw" # Keep the original selector name

    def _initialize_driver(self):
        """
        Sets up the Chrome WebDriver with desired options, using the HOME directory profile path.
        """
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-gpu")

        username = getpass.getuser()
        # --- Using HOME directory profile path (Original Behavior) ---
        base_profile_dir = os.path.join(os.path.expanduser("~"), ".selenium_profiles")
        os.makedirs(base_profile_dir, exist_ok=True) # Ensure base dir exists
        user_profile_dir = os.path.join(base_profile_dir, f"chrome_profile_{username}")
        # NOTE: The original code also did os.makedirs(user_profile_dir, exist_ok=True)
        # This is technically not needed as --user-data-dir creates it, but including for faithfulness:
        os.makedirs(user_profile_dir, exist_ok=True)
        # --- End Original Behavior Path ---

        logging.info(f"Using Selenium profile directory: {user_profile_dir}")
        chrome_options.add_argument(f"--user-data-dir={user_profile_dir}")
        # Optional: Add argument to allow insecure localhost if needed for certain setups, but be cautious
        # chrome_options.add_argument('--allow-running-insecure-content')
        # chrome_options.add_argument('--ignore-certificate-errors')

        try:
            # Assuming chromedriver is in PATH or use webdriver-manager (as before)
            self.driver = webdriver.Chrome(options=chrome_options)
            logging.info("ChromeDriver initialized.")
        except Exception as e:
            logging.error(f"Error initializing ChromeDriver: {e}")
            logging.error("Ensure ChromeDriver is installed and accessible in your PATH, or use webdriver-manager.")
            raise

    def load_site(self, url="https://open.spotify.com/lyrics"):
        """
        Loads the given URL using Selenium and returns the page source.
        Uses the original short wait time.
        """
        if self.driver is None:
            self._initialize_driver()
        logging.info(f"Attempting to load URL: {url}")
        try:
            self.driver.get(url)
            logging.info("URL loaded successfully.")
            # --- Original short wait ---
            time.sleep(2)
            logging.info("Initial 2-second wait finished.")
            # --- End Original Wait ---
        except Exception as e:
            logging.error(f"Error loading URL {url}: {e}")
            raise # Re-raise the exception to be handled by the caller
        return self.driver.page_source if self.driver else None

    def get_song_title(self):
        """Gets song title using the original selector."""
        if not self.driver: return None
        attempts = 0
        while attempts < 3:
            try:
                # --- Using original single selector ---
                element = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="context-item-link"]')
                # --- End original selector ---
                title = element.text.strip()
                 # Original didn't explicitly split artist/title if on separate lines
                return title
            except StaleElementReferenceException:
                attempts += 1
                time.sleep(0.1)  # short wait before retrying
            except NoSuchElementException:
                # logging.debug("Song title element not found.")
                return None # Element not found
            except Exception as e:
                 logging.warning(f"Unexpected error in get_song_title: {e}")
                 return None
        logging.warning("Failed to get song title after multiple attempts (stale element).")
        return None

    def update_song_title(self):
        """Original update logic."""
        new_title = self.get_song_title()
        # Check if new_title is None or empty, or if it hasn't changed
        if not new_title or new_title == self.current_song_title:
            return None
        # New title detected.
        logging.info(f"Detected new song title: '{new_title}'") # Kept logging here
        self.current_song_title = new_title
        self.song_title_history.append(new_title)
        return new_title

    def clean_lyrics(self, lyrics: str) -> str:
        """Original cleaning logic."""
        if not lyrics: return ""
        cleaned = lyrics.replace("♪", "")
        cleaned_lines = [line.strip() for line in cleaned.splitlines() if line.strip()] # Also remove empty lines
        return "\n".join(cleaned_lines)

    def get_fullscreen_lyrics(self):
        """Original fullscreen lyrics fetching logic."""
        if not self.driver: return ""
        lyrics = []
        try:
            # Locate all lyric containers using the original selector
            lyric_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="fullscreen-lyric"]')
            if not lyric_elements:
                logging.warning("Primary fullscreen lyric selector found no elements.")

            for elem in lyric_elements:
                try:
                    # Get the inner div that holds the actual lyric text
                    inner_div = elem.find_element(By.XPATH, './div')
                    text = inner_div.text.strip()
                    if text:
                        lyrics.append(text)
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
                except Exception as e:
                     # Original used print, using logging warning here
                     logging.warning(f"Minor error getting text from one lyric element: {e}")
                     continue
        except Exception as e:
            # Original used print, using logging error here
            logging.error(f"Error finding fullscreen lyric elements: {e}")
            return "" # Return empty string if main selector fails

        # Join the lyrics and clean them before returning
        full_lyrics = "\n".join(lyrics)
        cleaned = self.clean_lyrics(full_lyrics)
        # Added logging for clarity
        if cleaned:
             logging.info(f"Retrieved and cleaned {len(cleaned.splitlines())} lines of fullscreen lyrics.")
        else:
             logging.warning("Could not retrieve any fullscreen lyrics.")
        return cleaned


    def monitor_current_lyric(self, new_lyric_callback: Callable[[str], None], stop_event: threading.Event):
        """Original lyric monitoring logic."""
        if not self.driver:
            logging.error("Error: Driver not initialized. Cannot monitor lyrics.") # Changed print to logging
            return

        last_active_lyric_text = None
        active_lyric_selector = f'div[data-testid="fullscreen-lyric"].{self._active_lyric_class}'
        logging.info(f"Using active lyric selector: {active_lyric_selector}") # Changed print to logging

        logging.info("Starting current lyric monitoring...") # Changed print to logging
        while not stop_event.is_set():
            current_active_lyric_text = None
            if not self.driver: break # Added check in case driver closed
            try:
                active_elements = self.driver.find_elements(By.CSS_SELECTOR, active_lyric_selector)

                if active_elements:
                    target_element = active_elements[-1]
                    try:
                        inner_div = target_element.find_element(By.XPATH, './div')
                        current_active_lyric_text = inner_div.text.strip()
                    except (NoSuchElementException, StaleElementReferenceException):
                        pass

                if current_active_lyric_text and current_active_lyric_text != last_active_lyric_text:
                    cleaned_lyric = self.clean_lyrics(current_active_lyric_text)
                    if cleaned_lyric:
                        try:
                            new_lyric_callback(cleaned_lyric)
                        except Exception as cb_err:
                            logging.error(f"Error executing new_lyric_callback: {cb_err}") # Changed print to logging
                        last_active_lyric_text = current_active_lyric_text

                elif not current_active_lyric_text and last_active_lyric_text is not None:
                    last_active_lyric_text = None

            except StaleElementReferenceException:
                 pass
            except NoSuchElementException:
                 last_active_lyric_text = None
                 time.sleep(1)
            except Exception as e:
                 if "invalid session id" not in str(e).lower(): # Added check to avoid logging spam on close
                      logging.error(f"Unexpected error in lyric monitoring loop: {e}") # Changed print to logging
                 else:
                      logging.warning("Browser session likely closed.")
                      break # Exit loop
                 last_active_lyric_text = None
                 time.sleep(1)

            # --- Original Polling Interval ---
            time.sleep(0.6)
            # --- End Original Interval ---

        logging.info("Current lyric monitoring stopped.") # Changed print to logging


    def close(self):
        """Original close logic."""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("Browser closed via SongInfo.close().") # Changed print to logging
            except Exception as e:
                 if "invalid session id" not in str(e).lower() and "session deleted because of page crash" not in str(e).lower(): # Added checks
                      logging.error(f"Error during driver quit: {e}") # Changed print to logging
            finally:
                self.driver = None