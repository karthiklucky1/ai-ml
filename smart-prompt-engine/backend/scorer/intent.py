from sentence_transformers import SentenceTransformer
import numpy as np


class IntentDetector:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        self.intents = {
            "instruction": "how to make how to do steps procedure",
            "explanation": "explain concept theory understanding",
            "decision": "which one should I choose buy compare",
            "debugging": "error bug not working fix issue",
            "estimation": "how much how many calculate estimate"
        }

        self.intent_vectors = {
            k: self.model.encode(v)
            for k, v in self.intents.items()
        }

    def detect(self, prompt: str) -> str:
        prompt_vec = self.model.encode(prompt)

        best_intent = "explanation"
        best_score = -1

        for intent, vec in self.intent_vectors.items():
            score = np.dot(prompt_vec, vec) / (
                np.linalg.norm(prompt_vec) * np.linalg.norm(vec)
            )
            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent
