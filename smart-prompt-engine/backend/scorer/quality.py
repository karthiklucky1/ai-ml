def score_prompt(prompt: str):
    score = 0.0
    words = prompt.split()

    if len(words) >= 4:
        score += 0.5

    if any(word in prompt.lower() for word in ["explain", "build", "compare", "create"]):
        score += 0.5

    return score
