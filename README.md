# Text-Based Image Search Project (Now with Spotify Lyric Visualization!)

This project allows you to search for images within a dataset based on a textual description **OR** visualize Spotify song lyrics in real-time by finding images related to the meaning of each line.

## Features

*   Downloads an image dataset (e.g., from Kaggle).
*   Generates CLIP embeddings for all images in the dataset (accelerated on CUDA/MPS if available).
*   Connects to Spotify's web lyrics page using Selenium.
*   Monitors the currently playing song title and lyrics.
*   Uses a Google Generative AI model (Gemini) to interpret each lyric line into a concrete visual description.
*   Searches the image dataset using the generated description for the current lyric.
*   Displays the best matching image, updating as the song progresses.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <repository-directory>
    ```

2.  **Install Python dependencies:**
    Ensure you have Python 3.8+ installed.
    ```bash
    pip install -r requirements.txt
    ```
    *   **Note:** This includes `selenium`, `google-generativeai`, `python-dotenv`, and the original CLIP/Torch dependencies.
    *   **GPU/MPS:** Follow PyTorch installation instructions for your specific hardware (NVIDIA CUDA or Apple Silicon MPS) for acceleration.

3.  **Install ChromeDriver:**
    *   Selenium requires a WebDriver to control the browser. You need to install `ChromeDriver`.
    *   Check your installed Google Chrome version (`chrome://settings/help`).
    *   Download the matching ChromeDriver version from [https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads) or [https://googlechromelabs.github.io/chrome-for-testing/](https://googlechromelabs.github.io/chrome-for-testing/).
    *   Place the `chromedriver` executable somewhere in your system's `PATH` (e.g., `/usr/local/bin` on macOS/Linux) or ensure the script can find it. Alternatively, install `webdriver-manager` (`pip install webdriver-manager`) and uncomment the relevant lines in `song_info.py`'s `_initialize_driver` method.

4.  **Set up Google API Key:**
    *   You need a Google API key enabled for the Generative Language API (Gemini). Obtain one from the [Google AI Studio](https://aistudio.google.com/) or Google Cloud Console.
    *   Create a file named `.env` in the root project directory.
    *   Add your API key to the `.env` file:
        ```
        GOOGLE_API_KEY=your_actual_google_api_key
        ```

5.  **Download and Prepare Image Dataset:**
    *   Run the dataset download script:
        ```bash
        python download_dataset.py
        ```
        *   Follow the script's instructions, potentially using the Kaggle CLI if the direct download fails.
        *   **Crucially:** Identify the *exact* subfolder containing the images within the extracted `dataset` directory.

6.  **Generate Image Embeddings:**
    *   **Edit `image_embedding_generator.py`:** Update the `IMAGE_DATA_DIR` variable near the bottom to point to the correct image folder identified in the previous step.
    *   Run the embedding generator. This can take time.
        ```bash
        python image_embedding_generator.py
        ```
    *   This will create `image_embeddings.npy` and `image_paths.pkl` in the `embeddings` folder.

## How to Run

1.  **Log in to Spotify:** Ensure you are logged into `open.spotify.com` in your default Chrome profile (the script uses a dedicated profile but might pick up cookies initially).
2.  **Start the Visualizer:**
    ```bash
    python main.py
    ```
3.  **Open Spotify Lyrics:** The script will launch a Chrome browser window controlled by Selenium. Navigate it to `https://open.spotify.com/lyrics` (or the script will try to load it). Make sure the lyrics view is active for a playing song.
4.  **Observe:**
    *   The console will show logs indicating song detection, lyric processing, and image searching.
    *   When a new lyric line becomes active in Spotify, the script should:
        *   Look up its generated visual sentence.
        *   Search for a matching image.
        *   Open the image using your system's default image viewer.

5.  **Stop:** Press `Ctrl+C` in the console where `main.py` is running to shut down gracefully (closes the browser, stops threads).

## File Structure (Updated)

*   `download_dataset.py`: Downloads image dataset.
*   `image_embedding_generator.py`: Creates CLIP embeddings for images.
*   `text_embedding_generator.py`: Creates CLIP embeddings for text queries.
*   `image_searcher.py`: Performs image search based on embeddings.
*   **`song_info.py`**: (Ported) Handles Selenium interaction with Spotify.
*   **`llm_analysis.py`**: (Ported & Modified) Uses Google GenAI to create visual sentences from lyrics.
*   **`song_analysis_storage.py`**: (Ported & Modified) Stores the lyric-to-sentence mapping.
*   **`main.py`**: (Overhauled) Main application orchestrating Spotify monitoring, LLM analysis, and image search/display.
*   `requirements.txt`: Python dependencies.
*   `README.md`: This file.
*   `.env`: Stores your Google API key (DO NOT COMMIT).
*   `dataset/`: Folder for the downloaded image dataset.
*   `embeddings/`: Folder for generated image embeddings.
*   `.selenium_profiles/`: Folder created by `SongInfo` to store the browser profile.

## Notes & Troubleshooting

*   **Spotify Class Names:** The CSS class name (`_active_lyric_class` in `song_info.py`) used to identify the active lyric might change if Spotify updates its website. You may need to inspect the lyrics page source using browser developer tools and update this class name.
*   **LLM Costs:** Using the Google Generative AI API incurs costs based on usage. Monitor your usage in the Google Cloud Console.
*   **Performance:** LLM analysis takes time. The system pre-processes all lyrics when a new song starts. There might be a delay before visualizations appear for the first few lines. Lyric lookup and image search should be fast afterwards.
*   **ChromeDriver Issues:** Ensure ChromeDriver matches your Chrome version and is in your PATH. Consider using `webdriver-manager`.
*   **Display Issues:** Image display relies on `PIL.Image.show()`, which uses default system viewers. It might not work in headless environments or if no viewer is configured.