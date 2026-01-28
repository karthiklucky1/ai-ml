# backend/scorer/confidence.py

import numpy as np
from typing import List
from sklearn.metrics.pairwise import cosine_similarity


class PromptConfidenceScorer:
    def __init__(self, reference_embeddings: List[np.ndarray]):
        """
        reference_embeddings = embeddings of known good prompts
        """
        self.reference_embeddings = np.vstack(reference_embeddings)

    def score(self, prompt_embedding: np.ndarray) -> float:
        """
        Returns confidence score between 0 and 1
        """
        similarities = cosine_similarity(
            prompt_embedding.reshape(1, -1),
            self.reference_embeddings
        )

        # Take highest similarity as confidence
        confidence = float(similarities.max())
        return round(confidence, 3)
