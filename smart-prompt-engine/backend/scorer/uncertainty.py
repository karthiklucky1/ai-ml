# backend/scorer/uncertainty.py

import numpy as np
from typing import List
from sklearn.metrics.pairwise import cosine_similarity


class PromptUncertaintyEstimator:
    def __init__(self, reference_embeddings: List[np.ndarray]):
        """
        reference_embeddings:
        embeddings of prompts related to the same task domain
        """
        self.refs = np.vstack(reference_embeddings)

    def estimate(self, prompt_embedding: np.ndarray) -> float:
        """
        Returns uncertainty score between 0 and 1
        Higher = more uncertainty
        """
        similarities = cosine_similarity(
            prompt_embedding.reshape(1, -1),
            self.refs
        ).flatten()

        # Variance of similarities reflects ambiguity
        variance = np.var(similarities)

        # Normalize into uncertainty score
        uncertainty = min(1.0, variance * 5)
        return round(float(uncertainty), 3)
