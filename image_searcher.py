# image_searcher.py
import numpy as np
import pickle
import logging
import os
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImageSearcher:
    """Searches for images based on text query embedding."""

    def __init__(self, embeddings_file: str, paths_file: str):
        """
        Initializes the searcher by loading embeddings and paths.

        Args:
            embeddings_file (str): Path to the .npy file with image embeddings.
            paths_file (str): Path to the .pkl file with image file paths.

        Raises:
            FileNotFoundError: If embedding or path files are not found.
            Exception: For other loading errors.
        """
        self.embeddings_file = embeddings_file
        self.paths_file = paths_file
        self.image_embeddings = None
        self.image_paths = None
        self._load_data()
        # Pre-normalize image embeddings for faster cosine similarity calculation
        self._normalize_embeddings()


    def _load_data(self):
        """Loads the image embeddings and corresponding paths."""
        if not os.path.exists(self.embeddings_file):
            raise FileNotFoundError(f"Embeddings file not found: {self.embeddings_file}")
        if not os.path.exists(self.paths_file):
             raise FileNotFoundError(f"Image paths file not found: {self.paths_file}")

        try:
            logging.info(f"Loading image embeddings from: {self.embeddings_file}")
            self.image_embeddings = np.load(self.embeddings_file)
            logging.info(f"Loaded {self.image_embeddings.shape[0]} image embeddings.")

            logging.info(f"Loading image paths from: {self.paths_file}")
            with open(self.paths_file, 'rb') as f:
                self.image_paths = pickle.load(f)
            logging.info(f"Loaded {len(self.image_paths)} image paths.")

            if len(self.image_paths) != self.image_embeddings.shape[0]:
                logging.warning("Mismatch between number of embeddings and paths!")
                # Decide how to handle: error out, or truncate? For now, log warning.

        except Exception as e:
            logging.error(f"Failed to load embeddings or paths: {e}")
            raise

    def _normalize_embeddings(self):
        """Normalizes the loaded image embeddings (L2 norm)."""
        if self.image_embeddings is not None:
            logging.info("Normalizing image embeddings...")
            norms = np.linalg.norm(self.image_embeddings, axis=1, keepdims=True)
            # Add epsilon to avoid division by zero for zero vectors (if any)
            self.normalized_image_embeddings = self.image_embeddings / (norms + 1e-8)
            logging.info("Image embeddings normalized.")
        else:
            logging.error("Cannot normalize embeddings, they were not loaded.")


    def search(self, text_embedding: np.ndarray, top_k: int = 5) -> list[tuple[str, float]] | None:
        """
        Finds the top_k most similar images to the given text embedding.

        Args:
            text_embedding (np.ndarray): The embedding of the text query.
            top_k (int): The number of top results to return.

        Returns:
            list[tuple[str, float]] | None: A list of tuples, where each tuple contains
                                           (image_path, similarity_score), sorted by
                                           similarity. Returns None if search cannot be performed.
        """
        if self.normalized_image_embeddings is None or self.image_paths is None:
            logging.error("Embeddings or paths not loaded. Cannot perform search.")
            return None
        if text_embedding is None:
            logging.error("Invalid text embedding provided.")
            return None

        try:
            # Ensure text embedding is a 2D array for cosine_similarity
            text_embedding = text_embedding.reshape(1, -1)

            # Normalize the text embedding
            text_norm = np.linalg.norm(text_embedding, axis=1, keepdims=True)
            normalized_text_embedding = text_embedding / (text_norm + 1e-8)


            # Calculate cosine similarities (dot product of normalized vectors)
            # Shape: (1, num_images)
            similarities = np.dot(normalized_text_embedding, self.normalized_image_embeddings.T)[0]


            # Get the indices of the top_k highest scores
            # argsort sorts in ascending order, so we take the last 'top_k' indices
            # and reverse them to get descending order.
            # Using argpartition is faster for finding top k, but argsort is simpler here.
            top_k_indices = np.argsort(similarities)[-top_k:][::-1]

            # Get the corresponding paths and scores
            results = []
            for i in top_k_indices:
                 # Check index boundary, though argsort should be safe if len matches
                if 0 <= i < len(self.image_paths):
                    results.append((self.image_paths[i], similarities[i]))
                else:
                    logging.warning(f"Index {i} out of bounds for image paths (len: {len(self.image_paths)}). Skipping.")


            logging.info(f"Found {len(results)} results for top {top_k}.")
            return results

        except Exception as e:
            logging.error(f"Error during search: {e}")
            return None