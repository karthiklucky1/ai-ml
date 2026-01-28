# from fastapi import FastAPI
# from pydantic import BaseModel
# from fastapi.middleware.cors import CORSMiddleware

# # Steps 1–5 imports
# from backend.scorer.representation import PromptRepresentation
# from backend.scorer.confidence import PromptConfidenceScorer
# from backend.scorer.uncertainty import PromptUncertaintyEstimator
# from backend.optimizer.prompt_builder import PromptOptimizer
# from backend.scorer.intent import IntentDetector
# from backend.scorer.gap_reasoner import GapReasoner


# def dummy_llm_call(prompt: str) -> str:
#     # TEMP: replace later with real LLM
#     return "Consider clarifying relevant context, preferences, or constraints that affect the answer."


# intent_detector = IntentDetector()
# gap_reasoner = GapReasoner(dummy_llm_call)
# optimizer = PromptOptimizer(intent_detector, gap_reasoner)

# # Initialize shared objects
# rep = PromptRepresentation()

# # Reference prompts for the domain
# good_prompts = [
#     # Explanation
#     "Explain how a neural network works step by step",
#     "Describe the process of photosynthesis",

#     # Comparison
#     "Compare CNN and RNN with examples",
#     "Difference between SQL and NoSQL databases",

#     # Instruction
#     "Build a REST API using FastAPI",
#     "Create a machine learning pipeline in Python",

#     # Decision
#     "Which laptop should I buy for data science?",
#     "Should I choose React or Angular for frontend?",

#     # Calculation
#     "How many calories should I eat per day?",
#     "Estimate monthly expenses for a student",

#     # Debugging
#     "Why is my Python code throwing IndexError?",
#     "Fix this React useEffect infinite loop"
# ]

# # Encode once
# good_vectors = [rep.encode(p) for p in good_prompts]

# # Initialize scorers and optimizer
# confidence_scorer = PromptConfidenceScorer(good_vectors)
# uncertainty_estimator = PromptUncertaintyEstimator(good_vectors)
# # optimizer = PromptOptimizer(llm_client=None)  # LLM client optional for now
# intent_detector = IntentDetector()
# gap_reasoner = GapReasoner(dummy_llm_call)

# optimizer = PromptOptimizer(
#     intent_detector=intent_detector,
#     gap_reasoner=gap_reasoner
# )

# # Shared mock requirements (can be replaced with dynamic inference later)
# requirements = [
#     {"concept": "user constraints", "importance": 0.8},
#     {"concept": "goal", "importance": 0.7},
#     {"concept": "context", "importance": 0.6}

# ]


# # Initialize app
# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],   # allow all origins (for dev)
#     allow_credentials=True,
#     allow_methods=["*"],   # allow POST, OPTIONS
#     allow_headers=["*"],
# )


# @app.get("/")
# def root():
#     return {"message": "Smart Prompt Engine API running"}

# # Data models


# class PromptData(BaseModel):
#     prompt: str


# class OptimizeData(BaseModel):
#     prompt: str

# # Endpoints


# @app.post("/score")
# def score_endpoint(data: PromptData):
#     """
#     Returns confidence and uncertainty
#     """
#     # Step 1: embedding
#     user_vec = rep.encode(data.prompt)

#     # Step 2: confidence
#     confidence = confidence_scorer.score(user_vec)

#     # Step 3: uncertainty
#     uncertainty = uncertainty_estimator.estimate(user_vec)

#     return {
#         "confidence": confidence,
#         "uncertainty": uncertainty
#     }


# @app.post("/optimize")
# def optimize_endpoint(data: OptimizeData):
#     # """
#     # Returns suggestion and optimized prompt
#     # """
#     # # Step 1–3: embedding + confidence + uncertainty (optional, can be used)
#     # user_vec = rep.encode(data.prompt)
#     # confidence = confidence_scorer.score(user_vec)
#     # uncertainty = uncertainty_estimator.estimate(user_vec)

#     # # Step 5: generate suggestion
#     # result = optimizer.suggest(data.prompt, requirements)

#     # return {
#     #     "confidence": confidence,
#     #     "uncertainty": uncertainty,
#     #     "suggestion_text": result["suggestion_text"],
#     #     "optimized_prompt": result["optimized_prompt"]
#     # }
#     confidence = 0.42
#     result = optimizer.optimize(data.prompt, confidence)
#     return result

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Internal modules
from backend.scorer.representation import PromptRepresentation
from backend.scorer.confidence import PromptConfidenceScorer
from backend.scorer.uncertainty import PromptUncertaintyEstimator
from backend.scorer.intent import IntentDetector
from backend.optimizer.prompt_builder import PromptOptimizer
from backend.scorer.gap_reasoner import GapReasoner

# -----------------------------
# Initialize shared objects
# -----------------------------
rep = PromptRepresentation()
intent_detector = IntentDetector()
gap_reasoner = GapReasoner()  # OpenAI-based reasoner
optimizer = PromptOptimizer(intent_detector, gap_reasoner)

# Reference prompts for confidence
good_prompts = [
    "Explain how a neural network works step by step",
    "Compare CNN and RNN with examples",
    "Build a REST API using FastAPI",
    "How many calories should I eat per day?",
    "Fix this React useEffect infinite loop"
]

good_vectors = [rep.encode(p) for p in good_prompts]
confidence_scorer = PromptConfidenceScorer(good_vectors)
uncertainty_estimator = PromptUncertaintyEstimator(good_vectors)

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# -----------------------------
# Data models
# -----------------------------


class PromptData(BaseModel):
    prompt: str


class OptimizeData(BaseModel):
    prompt: str

# -----------------------------
# Endpoints
# -----------------------------


@app.get("/")
def root():
    return {"message": "Smart Prompt Engine API running"}


@app.post("/score")
def score_endpoint(data: PromptData):
    """
    Returns confidence and uncertainty scores for user prompt
    """
    user_vec = rep.encode(data.prompt)
    confidence = confidence_scorer.score(user_vec)
    uncertainty = uncertainty_estimator.estimate(user_vec)
    return {
        "confidence": confidence,
        "uncertainty": uncertainty
    }


@app.post("/optimize")
def optimize_endpoint(data: OptimizeData):
    """
    Returns optimized prompt with missing info detected by LLM
    """
    user_vec = rep.encode(data.prompt)
    confidence = confidence_scorer.score(user_vec)

    result = optimizer.optimize(data.prompt, confidence)
    return result
