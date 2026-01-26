# from fastapi import FastAPI
# from pydantic import BaseModel
# from fastapi.testclient import TestClient

# # --------------------------
# # 1️⃣ Create FastAPI app
# # --------------------------
# app = FastAPI()

# # --------------------------
# # 2️⃣ Data Models
# # --------------------------


# class PromptData(BaseModel):
#     prompt: str


# class SuggestData(BaseModel):
#     prompt: str


# class OptimizeData(BaseModel):
#     prompt: str
#     answers: dict = {}

# # --------------------------
# # 3️⃣ Scoring Logic (Placeholder)
# # --------------------------


# def score_prompt(prompt: str):
#     score = 0.0
#     words = prompt.split()
#     if len(words) >= 4:
#         score += 0.5
#     if any(word in prompt.lower() for word in ["explain", "build", "compare", "create"]):
#         score += 0.5
#     return score

# # --------------------------
# # 4️⃣ Suggest Questions Logic (Placeholder)
# # --------------------------


# def suggest_questions(prompt: str):
#     questions = []
#     if len(prompt.split()) < 4:
#         questions.append("What exactly do you want to achieve?")
#         questions.append("Do you want explanation or code?")
#         questions.append("Who is this for (beginner or expert)?")
#     return questions

# # --------------------------
# # 5️⃣ Optimize Prompt Logic (Placeholder)
# # --------------------------


# def optimize_prompt(prompt: str, answers: dict):
#     optimized = prompt.strip()
#     if "task" in answers:
#         optimized += f" for {answers['task']}"
#     if "output" in answers:
#         optimized += f". Provide the output as {answers['output']}."
#     if "level" in answers:
#         optimized += f" Keep the explanation {answers['level']}."
#     return optimized

# # --------------------------
# # 6️⃣ Endpoints
# # --------------------------


# @app.post("/score")
# def score_endpoint(data: PromptData):
#     score = score_prompt(data.prompt)
#     quality = "good" if score >= 0.7 else "weak"
#     return {"score": score, "quality": quality}


# @app.post("/suggest")
# def suggest_endpoint(data: SuggestData):
#     questions = suggest_questions(data.prompt)
#     return {"questions": questions}


# @app.post("/optimize")
# def optimize_endpoint(data: OptimizeData):
#     optimized_prompt = optimize_prompt(data.prompt, data.answers)
#     return {"optimized_prompt": optimized_prompt}


# # --------------------------
# # 7️⃣ Test Client (Optional)
# # --------------------------
# if __name__ == "__main__":
#     client = TestClient(app)

#     # Test /score
#     response = client.post("/score", json={"prompt": "Explain CNN"})
#     print("SCORE:", response.json())

#     # Test /suggest
#     response = client.post("/suggest", json={"prompt": "ML model"})
#     print("SUGGEST:", response.json())

#     # Test /optimize
#     response = client.post("/optimize", json={
#         "prompt": "Build ML model",
#         "answers": {
#             "task": "classification",
#             "output": "Python code",
#             "level": "beginner-friendly"
#         }
#     })
#     print("OPTIMIZE:", response.json())


from fastapi import FastAPI
from pydantic import BaseModel
from backend.scorer.quality import score_prompt
from backend.suggester.questions import suggest_questions
from backend.optimizer.prompt_builder import optimize_prompt
from fastapi.middleware.cors import CORSMiddleware


# Create app
app = FastAPI()

# Data models
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all origins (OK for development)
    allow_credentials=True,
    allow_methods=["*"],   # allow POST, OPTIONS, etc.
    allow_headers=["*"],
)


class PromptData(BaseModel):
    prompt: str


class SuggestData(BaseModel):
    prompt: str


class OptimizeData(BaseModel):
    prompt: str
    answers: dict = {}

# Endpoints


@app.post("/score")
def score_endpoint(data: PromptData):
    score = score_prompt(data.prompt)
    quality = "good" if score >= 0.7 else "weak"
    return {"score": score, "quality": quality}


@app.post("/suggest")
def suggest_endpoint(data: SuggestData):
    questions = suggest_questions(data.prompt)
    return {"questions": questions}


@app.post("/optimize")
def optimize_endpoint(data: OptimizeData):
    optimized_prompt = optimize_prompt(data.prompt, data.answers)
    return {"optimized_prompt": optimized_prompt}
