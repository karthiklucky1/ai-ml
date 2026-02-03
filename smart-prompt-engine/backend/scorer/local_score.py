# backend/scorer/local_score.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Tuple
import numpy as np

from backend.scorer.representation import PromptRepresentation


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class LocalScoreConfig:
    # Similarity thresholds for “dimension is covered”
    dim_threshold: float = 0.22

    # Weights for completeness calculation
    dim_weights: Dict[str, float] = None

    # How much completeness vs (1-uncertainty) contributes
    alpha_completeness: float = 0.70
    alpha_certainty: float = 0.30

    # If score above this, you can show “Looks good”
    good_score_threshold: int = 75


class LocalScorer:
    """
    Local, no-LLM scoring:
    - Intent: embedding similarity to intent prototypes
    - Missing dims: embedding similarity to dimension prototypes
    - Uncertainty: 1 - top intent similarity (simple, works well)
    - Score: weighted combination
    """

    def __init__(self, rep: PromptRepresentation, cfg: LocalScoreConfig | None = None):
        self.rep = rep
        self.cfg = cfg or LocalScoreConfig()

        if self.cfg.dim_weights is None:
            # Universal, domain-agnostic weights
            self.cfg.dim_weights = {
                "goal": 1.0,
                "context": 1.0,
                "constraints": 1.0,
                "format": 0.8,
                "detail_level": 0.8,
                "inputs": 1.0,  # important for “debugging”, “estimation”, etc.
            }

        # Intent prototypes (semantic phrases, not rules)
        self.intent_prototypes: Dict[str, str] = {
            "instruction": "how to do steps procedure recipe guide",
            "explanation": "explain concept what is how it works",
            "decision": "which should I choose compare best option recommendation",
            "debugging": "error bug issue not working fix troubleshoot",
            "estimation": "how much how many calculate estimate",
            "other": "general question discussion"
        }

        # Dimension prototypes (universal information types)
        self.dimension_prototypes: Dict[str, str] = {
            "goal": "desired outcome objective what you want to achieve",
            "context": "background situation environment where and why",
            "constraints": "limits preferences budget time dietary restrictions requirements",
            "format": "output format steps table bullets code short summary",
            "detail_level": "depth beginner advanced simple detailed explanation",
            "inputs": "necessary inputs like numbers examples data error message code snippet"
        }

        # Pre-encode prototypes once
        self.intent_vecs: Dict[str, np.ndarray] = {
            k: self.rep.encode(v) for k, v in self.intent_prototypes.items()
        }
        self.dim_vecs: Dict[str, np.ndarray] = {
            k: self.rep.encode(v) for k, v in self.dimension_prototypes.items()
        }

        # Suggestions text for UI (generic + helpful)
        self.dim_suggestions: Dict[str, str] = {
            "goal": "Add your goal (what outcome you want).",
            "context": "Add context/background so the answer can be tailored.",
            "constraints": "Add constraints (time, budget, preferences, limits).",
            "format": "Ask for an output format (steps, bullets, table, code).",
            "detail_level": "Specify depth (beginner vs advanced, brief vs detailed).",
            "inputs": "Add key inputs (numbers, examples, code/error, ingredients, etc.)."
        }

        # Human-readable missing items (what user should add)
        self.dim_to_missing_items: Dict[str, List[str]] = {
            "goal": ["goal/outcome"],
            "context": ["context/background"],
            "constraints": ["constraints (time/budget/preferences)"],
            "format": ["output format (steps/table/bullets/code)"],
            "detail_level": ["detail level (beginner/advanced, brief/detailed)"],
            "inputs": ["key inputs/examples/data (numbers, code, errors, ingredients)"],
        }

        # Prompt rewrite templates per intent (domain-agnostic, editable)
        self.intent_rewrite_templates: Dict[str, List[str]] = {
            "instruction": [
                "{p}\n\nGive step-by-step instructions. Include: {items}.",
                "{p}\n\nExplain the steps clearly for a beginner. Include: {items}.",
                "{p}\n\nProvide a short checklist + detailed steps. Include: {items}."
            ],
            "explanation": [
                "{p}\n\nExplain it clearly with a simple example. Include: {items}.",
                "{p}\n\nExplain for a beginner, then add deeper technical detail. Include: {items}.",
                "{p}\n\nExplain with intuition + 1 real-world application. Include: {items}."
            ],
            "decision": [
                "{p}\n\nAsk me 2–3 quick questions if needed, then recommend the best option. Consider: {items}.",
                "{p}\n\nCompare 3 options with pros/cons and recommend one. Consider: {items}.",
                "{p}\n\nGive a table comparing top choices and conclude with a recommendation. Consider: {items}."
            ],
            "debugging": [
                "{p}\n\nFind the root cause and give step-by-step fix. Include: {items}.",
                "{p}\n\nExplain why it happens, how to reproduce, and how to fix. Include: {items}.",
                "{p}\n\nList 3 likely causes (ranked) and how to test each. Include: {items}."
            ],
            "estimation": [
                "{p}\n\nEstimate using clear assumptions and show calculation steps. Include: {items}.",
                "{p}\n\nGive a range estimate and explain factors affecting it. Include: {items}.",
                "{p}\n\nExplain how to compute it and provide an example with sample values. Include: {items}."
            ],
            "other": [
                "{p}\n\nAnswer clearly and ask for missing details if needed. Missing: {items}.",
                "{p}\n\nProvide a short answer then a detailed explanation. Missing: {items}.",
                "{p}\n\nGive 3 approaches and recommend the best. Missing: {items}."
            ],
        }

    def detect_intent(self, prompt_vec: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
        sims: Dict[str, float] = {}
        for intent, vec in self.intent_vecs.items():
            sims[intent] = _cosine(prompt_vec, vec)

        # Pick best intent except "other" unless it truly wins
        best_intent = max(sims, key=sims.get)
        best_sim = sims[best_intent]
        return best_intent, best_sim, sims

    def detect_missing_dimensions(self, prompt_vec: np.ndarray) -> Tuple[List[str], Dict[str, float]]:
        dim_sims: Dict[str, float] = {}
        missing: List[str] = []
        thr = self.cfg.dim_threshold

        for dim, vec in self.dim_vecs.items():
            sim = _cosine(prompt_vec, vec)
            dim_sims[dim] = sim
            if sim < thr:
                missing.append(dim)

        # Sort missing dims by “how missing” (lowest similarity first)
        missing.sort(key=lambda d: dim_sims[d])
        return missing, dim_sims

    def compute_scores(
        self,
        missing_dims: List[str],
        dim_sims: Dict[str, float],
        top_intent_sim: float
    ) -> Dict[str, float]:
        # Completeness = weighted average of (dimension coverage)
        weights = self.cfg.dim_weights
        total_w = sum(weights.values())
        covered_sum = 0.0

        for dim, w in weights.items():
            coverage = _clamp01(dim_sims.get(dim, 0.0))
            covered_sum += w * coverage

        completeness = covered_sum / total_w if total_w > 0 else 0.0

        # Uncertainty: simple but effective
        uncertainty = _clamp01(1.0 - _clamp01(top_intent_sim))

        # Overall
        overall = (
            self.cfg.alpha_completeness * completeness
            + self.cfg.alpha_certainty * (1.0 - uncertainty)
        )
        overall = _clamp01(overall)

        return {
            "completeness": float(completeness),
            "uncertainty": float(uncertainty),
            "overall": float(overall),
        }

    def build_missing_items(self, missing_dims: List[str]) -> List[str]:
        items: List[str] = []
        for d in missing_dims:
            items.extend(self.dim_to_missing_items.get(d, [d]))
        # remove duplicates while keeping order
        seen = set()
        out = []
        for x in items:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def build_rewrite_cards(self, prompt: str, intent: str, missing_items: List[str]) -> List[str]:
        p = prompt.strip()
        if not p.endswith("?") and intent in ["decision", "estimation", "explanation", "other"]:
            # optional: normalize to a question-like prompt
            p = p + "?"

        # keep items short in cards
        items_text = ", ".join(
            missing_items[:4]) if missing_items else "any relevant details"

        templates = self.intent_rewrite_templates.get(
            intent, self.intent_rewrite_templates["other"])

        cards: List[str] = []
        for t in templates:
            card = t.format(p=p, items=items_text).strip()
            if card not in cards:
                cards.append(card)

        return cards[:3]

    def score(self, prompt: str) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        if not prompt:
            return {
                "score": 0,
                "intent": "other",
                "completeness": 0.0,
                "uncertainty": 1.0,
                "overall": 0.0,
                "missing_dimensions": ["goal", "context", "constraints", "format", "detail_level", "inputs"],
                "live_suggestions": [
                    "Type a question or task you want help with.",
                    "Add what you want (goal) and any constraints."
                ],
                "debug": {"note": "Empty prompt"}
            }

        prompt_vec = self.rep.encode(prompt)

        intent, top_sim, intent_sims = self.detect_intent(prompt_vec)
        missing_dims, dim_sims = self.detect_missing_dimensions(prompt_vec)
        scores = self.compute_scores(missing_dims, dim_sims, top_sim)

        score_100 = int(round(100.0 * scores["overall"]))

        # Suggestions: show top 3 missing dims as hints
        top_missing = missing_dims[:3]
        suggestions = [self.dim_suggestions[d] for d in top_missing]

        # Nice UX message
        label = "good" if score_100 >= self.cfg.good_score_threshold else "needs_more_detail"
        draft_prompts = self.build_drafts(prompt, intent, missing_dims)

        missing_items = self.build_missing_items(missing_dims)
        rewrite_cards = self.build_rewrite_cards(prompt, intent, missing_items)

        return {
            "score": score_100,
            "label": label,
            "intent": intent,
            **scores,
            "missing_dimensions": missing_dims,
            "missing_items": missing_items,
            "rewrite_cards": rewrite_cards,
            "live_suggestions": suggestions,
            "draft_prompts": draft_prompts,
            # Optional debug info (keep for dev; you can remove later)
            "debug": {
                "top_intent_similarity": float(top_sim),
                "intent_similarities": {k: float(v) for k, v in intent_sims.items()},
                "dimension_similarities": {k: float(v) for k, v in dim_sims.items()},
                "dim_threshold": self.cfg.dim_threshold,
            }
        }

    def build_drafts(self, prompt: str, intent: str, missing_dims: List[str]) -> List[str]:
        # Keep it short and editable
        base = prompt.strip().rstrip("?")

        # Map dims to short add-ons
        dim_add = {
            "goal": "Add your goal (what outcome you want).",
            "context": "Add relevant context/background.",
            "constraints": "Add constraints (time/budget/preferences/limits).",
            "format": "Ask for output format (steps/bullets/table/code).",
            "detail_level": "Specify depth (beginner/advanced, brief/detailed).",
            "inputs": "Add key inputs (numbers/examples/data/code/error/etc.).",
            "summarization": "summarize summary key points tl;dr extract highlights"

        }

        # Use top 3 missing dims
        missing_top = missing_dims[:3]
        add_lines = [dim_add[d] for d in missing_top if d in dim_add]

        # Draft 1: Minimal improvement
        if add_lines:
            draft1 = base + "?\n\n" + "\n".join(f"- {x}" for x in add_lines)
        else:
            draft1 = base + "?"

        # Draft 2: Guided based on intent
        if intent == "instruction":
            draft2 = base + "?\n\nGive a step-by-step answer. " + \
                " ".join(add_lines)
        elif intent == "explanation":
            draft2 = base + "?\n\nExplain clearly with a simple example. " + \
                " ".join(add_lines)
        elif intent == "decision":
            draft2 = base + "?\n\nCompare options with pros/cons and recommend one. " + \
                " ".join(add_lines)
        elif intent == "debugging":
            draft2 = base + "?\n\nHelp me debug. Include expected vs actual behavior. " + \
                " ".join(add_lines)
        elif intent == "estimation":
            draft2 = base + "?\n\nState assumptions and show the calculation steps. " + \
                " ".join(add_lines)
        else:
            draft2 = base + "?\n\n" + " ".join(add_lines)

        # Draft 3: Structured output request
        draft3 = (
            base
            + "?\n\nAnswer in this structure:\n"
            + "1) Key factors\n2) Steps/approach\n3) Example\n4) Common mistakes"
        )

        # Keep unique + non-empty
        drafts: List[str] = []
        for d in [draft1, draft2, draft3]:
            d = d.strip()
            if d and d not in drafts:
                drafts.append(d)

        return drafts[:3]
