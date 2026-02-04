from backend.scorer.gap_reasoner import GapReasoner
from backend.scorer.intent import IntentDetector


class PromptOptimizer:
    def __init__(self, intent_detector: IntentDetector, gap_reasoner: GapReasoner):
        self.intent_detector = intent_detector
        self.gap_reasoner = gap_reasoner

    def optimize(self, prompt: str, confidence: float) -> dict:
        """
        Optimizes prompt by detecting missing info using LLM.
        Returns JSON with optimized prompt and metadata.
        """
        # If prompt is already high confidence, return as-is
        if confidence > 0.75:
            return {
                "needs_improvement": False,
                "optimized_prompt": prompt
            }

        # Detect intent
        intent = self.intent_detector.detect(prompt)

        # Detect missing info / clarifications
        clarification = self.gap_reasoner.reason(prompt)

        # Combine original prompt + missing info
        optimized_prompt = f"{prompt}\n\nConsider clarifying:\n{clarification}"

        return {
            "needs_improvement": True,
            "optimized_prompt": optimized_prompt,
            "intent": intent
        }
