def suggest_questions(prompt: str):
    questions = []
    if len(prompt.split()) < 4:
        questions.append("What exactly do you want to achieve?")
        questions.append("Do you want explanation or code?")
        questions.append("Who is this for (beginner or expert)?")
    return questions
