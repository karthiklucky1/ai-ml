from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict
from collections import Counter


class PromptRepresentation:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Representation engine.
        Converts text into semantic vectors.
        """
        self.model = SentenceTransformer(model_name)

    def encode(self, text: str) -> np.ndarray:
        """
        Convert prompt text into an embedding vector.
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding


class RequirementInferencer:
    def __init__(self, llm_client):
        """
        llm_client: abstract interface to any LLM
        """
        self.llm = llm_client

    def infer(self, prompt: str, n_samples: int = 5) -> List[Dict]:
        """
        Returns ranked missing information concepts
        """
        probes = []

        for _ in range(n_samples):
            response = self.llm.complete(
                f"""
                The following user query may be missing information.
                Query: "{prompt}"

                List the types of additional information that would
                improve the accuracy of the answer.
                """
            )
            probes.append(response)

        return self._aggregate_requirements(probes)

    def _aggregate_requirements(self, probes: List[str]) -> List[Dict]:
        concepts = []

        for text in probes:
            # Convert raw text into semantic concepts later
            concepts.extend(self._extract_concepts(text))

        freq = Counter(concepts)

        return [
            {"concept": c, "importance": round(freq[c] / len(probes), 2)}
            for c in freq
        ]

    def _extract_concepts(self, text: str) -> List[str]:
        """
        Placeholder: convert free text into abstract concepts.
        This will later be embedding-based.
        """
        return [t.strip().lower() for t in text.split(",")]
