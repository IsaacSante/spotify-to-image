# text_embedding_generator.py
import torch
import numpy as np
from transformers import CLIPProcessor, CLIPModel
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TextEmbeddingGenerator:
    """Generates CLIP embeddings for text queries."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """
        Initializes the text embedding generator, detecting GPU, MPS, or CPU.

        Args:
            model_name (str): The name of the CLIP model to use.
        """
       # --- Device Selection (CUDA > MPS > CPU) ---
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
             # Check if MPS is available (requires PyTorch >= 1.12 on macOS arm64)
            self.device = "mps"
        else:
            self.device = "cpu"
        logging.info(f"TextEmbedGen using device: {self.device}")

        try:
            # Load model and processor
            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
            logging.info(f"TextEmbedGen loaded CLIP model '{model_name}'.")
        except Exception as e:
            logging.error(f"TextEmbedGen failed to load CLIP model '{model_name}': {e}")
            raise

    def generate_embedding(self, text: str) -> np.ndarray | None:
        """
        Generates an embedding for the given text.

        Args:
            text (str): The text query.

        Returns:
            np.ndarray | None: The generated embedding as a NumPy array, or None if error.
        """
        if not text:
            logging.warning("Received empty text, cannot generate embedding.")
            return None

        try:
            # Process the text
            inputs = self.processor(text=text, return_tensors="pt", padding=True, truncation=True)
            # Move inputs to the selected device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate embedding
            with torch.no_grad(): # No need for gradients during inference
                text_features = self.model.get_text_features(**inputs)

            # Move embedding to CPU, convert to numpy array
            # Embedding should already be normalized by CLIP, but explicit normalization can be added if needed
            embedding = text_features.cpu().numpy()
            # Optional normalization:
            # embedding /= np.linalg.norm(embedding, axis=1, keepdims=True)

            # Return the first (and only) embedding in the batch
            return embedding[0]

        except Exception as e:
            logging.error(f"Failed to generate embedding for text '{text}': {e}")
            return None
        finally:
             # Clean up tensors
             del inputs
             if 'text_features' in locals():
                 del text_features
             if self.device == 'cuda':
                 torch.cuda.empty_cache()