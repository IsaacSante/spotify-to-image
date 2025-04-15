# image_embedding_generator.py
import os
import numpy as np
import torch
from PIL import Image
# Suppress specific Pillow warning for large images, if needed
Image.MAX_IMAGE_PIXELS = None # or set a large integer like 10000*10000
from transformers import CLIPProcessor, CLIPModel
import logging
import pickle
from tqdm import tqdm # Progress bar

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImageEmbeddingGenerator:
    """Generates and saves embeddings for images using CLIP."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """
        Initializes the embedding generator, detecting GPU, MPS, or CPU.

        Args:
            model_name (str): The name of the CLIP model to use from Hugging Face.
        """
        # --- Device Selection (CUDA > MPS > CPU) ---
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
             # Check if MPS is available (requires PyTorch >= 1.12 on macOS arm64)
            self.device = "mps"
             # Optional: Check if built correctly, though is_available() should suffice
            # if not torch.backends.mps.is_built():
            #     logging.warning("MPS not available because the current PyTorch install was not built with MPS enabled.")
            #     self.device = "cpu" # Fallback if built check fails
        else:
            self.device = "cpu"
        logging.info(f"ImageEmbedGen using device: {self.device}")

        try:
            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
            logging.info(f"ImageEmbedGen loaded CLIP model '{model_name}' successfully.")
        except Exception as e:
            logging.error(f"ImageEmbedGen failed to load CLIP model '{model_name}': {e}")
            raise

    def _find_image_files(self, image_dir: str) -> list[str]:
        """Recursively finds all image files in a directory."""
        supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp') # Added webp
        image_files = []
        logging.info(f"Searching for images in: {os.path.abspath(image_dir)}")
        if not os.path.isdir(image_dir):
             logging.error(f"Image directory not found: {image_dir}")
             return []

        for root, _, files in os.walk(image_dir):
            for file in files:
                if file.lower().endswith(supported_extensions):
                    image_files.append(os.path.join(root, file))

        logging.info(f"Found {len(image_files)} potential image files in '{image_dir}'.")
        if not image_files:
             logging.warning(f"No image files found matching extensions {supported_extensions} in {image_dir}")
        return image_files

    def generate_embeddings(self, image_dir: str, output_dir: str = "embeddings", batch_size: int = 16):
        """
        Generates embeddings for all images in the directory and saves them.

        Args:
            image_dir (str): The directory containing the image files.
            output_dir (str): The directory to save embeddings and mapping.
            batch_size (int): Number of images to process in one batch. Adjust based on VRAM/RAM.
        """
        os.makedirs(output_dir, exist_ok=True)
        embeddings_file = os.path.join(output_dir, "image_embeddings.npy")
        paths_file = os.path.join(output_dir, "image_paths.pkl")

        if os.path.exists(embeddings_file) and os.path.exists(paths_file):
            logging.warning(f"Embeddings files already exist in '{output_dir}'. Skipping generation.")
            print(f"Embeddings found at: {embeddings_file}")
            print(f"Image paths mapping found at: {paths_file}")
            return embeddings_file, paths_file

        image_paths = self._find_image_files(image_dir)
        if not image_paths:
            logging.error(f"No image files found in '{image_dir}'. Cannot generate embeddings.")
            return None, None

        all_embeddings = []
        valid_image_paths = []

        # Adjust batch size based on device perhaps? MPS might need smaller batches than CUDA.
        # For now, use the provided batch_size.
        logging.info(f"Starting embedding generation for {len(image_paths)} images (batch size: {batch_size}, device: {self.device})...")

        for i in tqdm(range(0, len(image_paths), batch_size), desc="Generating Embeddings"):
            batch_paths = image_paths[i:i+batch_size]
            images = []
            current_batch_valid_paths = []

            # Load images in the batch
            for img_path in batch_paths:
                try:
                    # Ensure images are loaded in RGB format for CLIP
                    img = Image.open(img_path).convert("RGB")
                    images.append(img)
                    current_batch_valid_paths.append(img_path)
                except Exception as e:
                    logging.warning(f"Could not open or process image {img_path}: {e}. Skipping.")

            if not images:
                continue # Skip if batch ended up empty

            # Process batch
            try:
                # Prepare inputs for CLIP model
                inputs = self.processor(text=None, images=images, return_tensors="pt", padding=True)
                # Move inputs to the selected device (GPU, MPS, or CPU)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                # Generate embeddings using the model
                with torch.no_grad(): # Disable gradient calculation for inference
                    image_features = self.model.get_image_features(**inputs)

                # Move embeddings back to CPU, convert to numpy array
                batch_embeddings = image_features.cpu().numpy()

                all_embeddings.extend(batch_embeddings)
                valid_image_paths.extend(current_batch_valid_paths)

            except Exception as e:
                 logging.error(f"Error processing batch starting with image {batch_paths[0]}: {e}")
                 # Consider adding more robust error handling here if needed

            finally:
                 # Explicitly clear memory, especially important on devices with limited VRAM/RAM
                 del images, inputs
                 if 'image_features' in locals():
                     del image_features
                 if self.device == 'cuda':
                     torch.cuda.empty_cache()
                 # There isn't a direct equivalent for torch.mps.empty_cache() yet AFAIK
                 # Garbage collection should help implicitly


        if not all_embeddings:
            logging.error("No embeddings were generated. Check image files and processing errors.")
            return None, None

        # Save embeddings and paths
        embeddings_array = np.array(all_embeddings)
        logging.info(f"Generated {embeddings_array.shape[0]} embeddings with dimension {embeddings_array.shape[1]}.")

        try:
            np.save(embeddings_file, embeddings_array)
            logging.info(f"Image embeddings saved to: {embeddings_file}")

            with open(paths_file, 'wb') as f:
                pickle.dump(valid_image_paths, f)
            logging.info(f"Image paths mapping saved to: {paths_file}")

            return embeddings_file, paths_file

        except Exception as e:
            logging.error(f"Failed to save embeddings or paths: {e}")
            return None, None


# --- Main Execution Block ---
if __name__ == "__main__":
    # !!! IMPORTANT: Update this path based on where 'download_dataset.py' actually extracted the images !!!
    # After running the updated download script, inspect the 'dataset' folder.
    # Common locations:
    # - 'dataset/images/images/'
    # - 'dataset/resized/resized/'
    # - 'dataset/images/'
    # Use os.listdir('dataset') or your file browser to find the correct image folder.
    IMAGE_DATA_DIR = "dataset/train2014" # <--- SET THIS PATH # <--- !!! VERIFY AND CHANGE THIS PATH !!!
    OUTPUT_DIR = "embeddings"
    # Consider reducing batch size if running on MPS or low-memory GPU/CPU
    PROCESSING_BATCH_SIZE = 16 # Maybe 8 or 16 for MPS/CPU, 32+ for good CUDA GPU

    print(f"Attempting to generate embeddings for images in: {os.path.abspath(IMAGE_DATA_DIR)}")
    if not os.path.isdir(IMAGE_DATA_DIR):
        print("\n" + "="*30)
        print("ERROR: Image directory not found!")
        print(f"Directory checked: {os.path.abspath(IMAGE_DATA_DIR)}")
        print("Please ensure the dataset was downloaded and extracted correctly using 'download_dataset.py'.")
        print("Then, inspect the 'dataset' folder to find the actual subdirectory containing the images.")
        print("Update the 'IMAGE_DATA_DIR' variable in this script ('image_embedding_generator.py') accordingly.")
        print("="*30 + "\n")

    else:
        print(f"Found image directory: {os.path.abspath(IMAGE_DATA_DIR)}")
        generator = ImageEmbeddingGenerator()
        try:
            embeddings_file, paths_file = generator.generate_embeddings(
                image_dir=IMAGE_DATA_DIR,
                output_dir=OUTPUT_DIR,
                batch_size=PROCESSING_BATCH_SIZE
            )
            if embeddings_file and paths_file:
                print("\nImage embedding generation complete.")
                print(f"Embeddings saved to: {embeddings_file}")
                print(f"Paths mapping saved to: {paths_file}")
            else:
                print("\nImage embedding generation may have failed or produced no results. Check logs for details.")
        except Exception as e:
            print(f"\nAn critical error occurred during embedding generation: {e}")
            import traceback
            traceback.print_exc() # Print detailed traceback for debugging