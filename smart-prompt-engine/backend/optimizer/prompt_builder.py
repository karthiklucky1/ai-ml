def optimize_prompt(prompt: str, answers: dict):
    optimized = prompt.strip()
    if "task" in answers:
        optimized += f" for {answers['task']}"
    if "output" in answers:
        optimized += f". Provide the output as {answers['output']}."
    if "level" in answers:
        optimized += f" Keep the explanation {answers['level']}."
    return optimized
