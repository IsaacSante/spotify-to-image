# download_dataset.py
import os
import subprocess
import zipfile
import logging
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatasetDownloaderCurl:
    """Handles downloading datasets using a curl command and unzipping."""

    def __init__(self, download_dir: str = "dataset_download", extract_dir: str = "dataset"):
        """
        Initializes the downloader.

        Args:
            download_dir (str): Directory to temporarily store the downloaded zip file.
            extract_dir (str): The target directory to extract the dataset into.
        """
        self.download_dir = download_dir
        self.extract_dir = extract_dir
        self.zip_filename = "image-dataset.zip"
        self.zip_filepath = os.path.join(self.download_dir, self.zip_filename)
        self.dataset_url = "https://www.kaggle.com/api/v1/datasets/download/starktony45/image-dataset"

        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.extract_dir, exist_ok=True)
        logging.info(f"Download directory set to: {os.path.abspath(self.download_dir)}")
        logging.info(f"Extraction directory set to: {os.path.abspath(self.extract_dir)}")

    def download_and_extract(self) -> str | None:
        """
        Downloads the dataset using curl and extracts it.

        Returns:
            str | None: The path to the extraction directory if successful, otherwise None.

        Raises:
            RuntimeError: If curl command fails or unzipping fails.
        """
        logging.info(f"Attempting to download dataset from Kaggle API...")
        logging.warning("Direct curl download might fail if Kaggle requires authentication cookies.")
        logging.warning("If download fails, try authenticating the Kaggle CLI (`pip install kaggle`, `kaggle configure`)")
        logging.warning("Then use: `kaggle datasets download -d ikarus777/best-artworks-of-all-time -p dataset --unzip`")


        # Construct curl command
        # Ensure curl follows redirects (-L) and outputs to the specified file (-o)
        curl_command = [
            "curl",
            "-L",
            "-o", self.zip_filepath,
            self.dataset_url
        ]

        logging.info(f"Executing command: {' '.join(curl_command)}")

        try:
            # Execute the curl command
            process = subprocess.run(curl_command, check=True, capture_output=True, text=True)
            logging.info("Curl command executed successfully.")
            logging.debug(f"Curl stdout: {process.stdout}")
            logging.debug(f"Curl stderr: {process.stderr}") # Curl often outputs progress to stderr

            # Check if the zip file was actually created and is not empty
            if not os.path.exists(self.zip_filepath) or os.path.getsize(self.zip_filepath) == 0:
                logging.error(f"Curl command seemed to succeed, but the zip file '{self.zip_filepath}' was not created or is empty.")
                logging.error("This often indicates an authentication issue with Kaggle.")
                logging.error("Please try the Kaggle CLI method mentioned above.")
                # Clean up empty file if it exists
                if os.path.exists(self.zip_filepath):
                     os.remove(self.zip_filepath)
                return None # Indicate failure

        except subprocess.CalledProcessError as e:
            logging.error(f"Curl command failed with exit code {e.returncode}.")
            logging.error(f"Stderr: {e.stderr}")
            logging.error("Download failed. Check network connection and Kaggle URL.")
            logging.error("If authentication is required, use the Kaggle CLI.")
            return None # Indicate failure
        except FileNotFoundError:
             logging.error("`curl` command not found. Please ensure curl is installed and in your system's PATH.")
             return None # Indicate failure


        # --- Unzip the downloaded file ---
        logging.info(f"Attempting to unzip '{self.zip_filepath}' into '{self.extract_dir}'...")
        try:
            with zipfile.ZipFile(self.zip_filepath, 'r') as zip_ref:
                zip_ref.extractall(self.extract_dir)
            logging.info(f"Successfully extracted dataset to: {os.path.abspath(self.extract_dir)}")

            # --- Clean up the zip file ---
            try:
                os.remove(self.zip_filepath)
                logging.info(f"Removed temporary zip file: {self.zip_filepath}")
                # Attempt to remove the temporary download directory if empty
                if not os.listdir(self.download_dir):
                    os.rmdir(self.download_dir)
                    logging.info(f"Removed temporary download directory: {self.download_dir}")
            except OSError as e:
                logging.warning(f"Could not remove zip file or directory: {e}")


            return self.extract_dir

        except zipfile.BadZipFile:
            logging.error(f"Failed to unzip file: '{self.zip_filepath}'. It might be corrupted or not a valid zip file.")
            return None # Indicate failure
        except Exception as e:
            logging.error(f"An unexpected error occurred during unzipping: {e}")
            return None # Indicate failure


# --- Main Execution Block ---
if __name__ == "__main__":
    DOWNLOAD_TEMP_DIR = "dataset_download_temp" # Temporary folder for zip
    EXTRACT_TARGET_DIR = "dataset" # Final location for extracted files

    downloader = DatasetDownloaderCurl(download_dir=DOWNLOAD_TEMP_DIR, extract_dir=EXTRACT_TARGET_DIR)
    try:
        final_path = downloader.download_and_extract()
        if final_path:
            print(f"\nDataset download and extraction process finished.")
            print(f"Extracted files should be located in: {os.path.abspath(final_path)}")
            print("\nIMPORTANT: Please inspect the contents of this directory.")
            print("Find the exact subfolder containing the image files (e.g., 'images/images', 'resized', etc.).")
            print("You will need this exact path for the 'IMAGE_DATA_DIR' variable in 'image_embedding_generator.py'.")
        else:
            print("\nDataset download or extraction failed. Please check the log messages above.")
            print("Consider using the official Kaggle CLI if authentication is needed:")
            print("1. `pip install kaggle`")
            print("2. `kaggle configure` (set up your API token)")
            print(f"3. `kaggle datasets download -d ikarus777/best-artworks-of-all-time -p {EXTRACT_TARGET_DIR} --unzip`")


    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")