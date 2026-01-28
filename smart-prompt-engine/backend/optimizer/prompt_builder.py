# def optimize_prompt(prompt: str, answers: dict):
#     optimized = prompt.strip()
#     if "task" in answers:
#         optimized += f" for {answers['task']}"
#     if "output" in answers:
#         optimized += f". Provide the output as {answers['output']}."
#     if "level" in answers:
#         optimized += f" Keep the explanation {answers['level']}."
#     return optimized


# # backend/optimizer/prompt_builder.py


# class PromptOptimizer:
#     def __init__(self, llm_client):
#         self.llm = llm_client

#     def suggest(self, prompt: str, requirements: List[Dict]) -> Dict:
#         """
#         Returns:
#         - suggestion_text: human-readable suggestion
#         - optimized_prompt: enhanced prompt for LLM
#         """
#         # Build description of missing info
#         missing_info = ", ".join([r["concept"] for r in requirements])

#         # Human-readable suggestion
#         suggestion_text = (
#             f"Your prompt could be improved by adding the following information: "
#             f"{missing_info}."
#         )

#         # Optional: enhanced prompt for LLM
#         enhanced_prompt = f"{prompt} (Include details: {missing_info})"

#         return {
#             "suggestion_text": suggestion_text,
#             "optimized_prompt": enhanced_prompt
#         }

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
