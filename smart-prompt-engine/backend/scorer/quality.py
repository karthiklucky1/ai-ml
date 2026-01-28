# def score_prompt(prompt: str):
#     score = 0.0
#     words = prompt.split()

#     if len(words) >= 4:
#         score += 0.5

#     if any(word in prompt.lower() for word in ["explain", "build", "compare", "create"]):
#         score += 0.5

#     return score

# backend/scorer/quality.py

from typing import List

# List of action/quality words that make a prompt strong

ACTION_WORDS = ["explain", "compare",
                "create", "build", "analyze", "summarize"]


def score_prompt(prompt: str) -> float:
    """
    Scores a prompt between 0 and 1.
    Higher score = better prompt
    """

    if not prompt or len(prompt.strip()) == 0:
        return 0.0

    score = 0.0
    words = prompt.strip().split()

    # 1️⃣ Length contribution
    if len(words) >= 4:
        score += 0.4
    elif len(words) >= 2:
        score += 0.2

    # 2️⃣ Action keyword contribution
    for word in ACTION_WORDS:
        if word in prompt.lower():
            score += 0.3
            break  # only count once

    # 3️⃣ Cap the score at 1.0
    score = min(score, 1.0)
    return score


def quality_label(score: float) -> str:
    """
    Return weak/medium/strong based on score
    """
    if score < 0.4:
        return "weak"
    elif score < 0.7:
        return "medium"
    else:
        return "strong"
