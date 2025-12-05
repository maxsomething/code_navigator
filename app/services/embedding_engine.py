import logging
import os
import numpy as np
from app.config import Config 

try:
    from sentence_transformers import SentenceTransformer, util
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class EmbeddingEngine:
    """
    Wrapper for SentenceTransformers to generate semantic embeddings for code.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = None
        self.model_name = Config.EMBEDDING_MODEL_NAME
        self.cache_dir = str(Config.MODELS_DIR) 
        
    def _load_model(self):
        if self.model is None and TRANSFORMERS_AVAILABLE:
            self.logger.info(f"Loading embedding model: {self.model_name} from {self.cache_dir}...")
            try:
                self.model = SentenceTransformer(
                    self.model_name, 
                    cache_folder=self.cache_dir
                )
                self.logger.info("Model loaded successfully.")
            except Exception as e:
                self.logger.error(f"Failed to load embedding model: {e}")

    def embed_text(self, texts: list[str]) -> np.ndarray:
        if not TRANSFORMERS_AVAILABLE:
            self.logger.warning("sentence-transformers not installed.")
            return np.array([])
            
        self._load_model()
        if not self.model:
            return np.array([])
            
        try:
            # Truncate input to avoid massive tokenization delays
            truncated_texts = [t[:4096] for t in texts] 
            embeddings = self.model.encode(truncated_texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
            return np.array([])

    def cosine_similarity(self, query_vec, corpus_vecs):
        """
        Calculates similarity. optimized to prevent PyTorch list-conversion warnings.
        """
        if not TRANSFORMERS_AVAILABLE or self.model is None:
            return []
        
        # OPTIMIZATION: Stack list of arrays into a single matrix
        if isinstance(corpus_vecs, list):
            if len(corpus_vecs) == 0:
                return []
            # This converts List[np.array] -> np.array(matrix) which is fast for PyTorch
            corpus_matrix = np.vstack(corpus_vecs)
        else:
            corpus_matrix = corpus_vecs
            
        return util.cos_sim(query_vec, corpus_matrix)[0]