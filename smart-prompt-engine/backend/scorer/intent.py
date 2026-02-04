import numpy as np
from backend.scorer.representation import PromptRepresentation


class IntentDetector:
    def __init__(self, rep: PromptRepresentation | None = None):
        self.rep = rep or PromptRepresentation()

        self.intents = {
            "instruction": "how to make how to do steps procedure",
            "explanation": "explain concept theory understanding",
            "decision": "which one should I choose buy compare",
            "debugging": "error bug not working fix issue",
            "estimation": "how much how many calculate estimate"
        }

        self.intent_vectors = None

    def _ensure_intent_vectors(self):
        if self.intent_vectors is not None:
            return
        self.intent_vectors = {
            k: self.rep.encode(v)
            for k, v in self.intents.items()
        }

    def detect(self, prompt: str) -> str:
        self._ensure_intent_vectors()
        prompt_vec = self.rep.encode(prompt)

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
