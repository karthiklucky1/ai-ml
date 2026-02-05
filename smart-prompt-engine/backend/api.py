from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
import hashlib
from backend.utils.cache import TTLCache, SimpleRateLimiter, normalize_prompt
from backend.cache_metrics import CacheStats, reset_stats


# Internal modules
from backend.scorer.representation import PromptRepresentation
from backend.scorer.confidence import PromptConfidenceScorer
from backend.scorer.uncertainty import PromptUncertaintyEstimator
from backend.scorer.intent import IntentDetector
from backend.optimizer.prompt_builder import PromptOptimizer
from backend.scorer.gap_reasoner import GapReasoner
from backend.scorer.local_score import LocalScorer
from backend.llm.openai_client import OpenAITextClient, LLMError
from backend.rewrite.suggestions import get_rewrite_suggestions, SYSTEM_VERSION as REWRITE_SYSTEM_VERSION
from backend.compress.logs import compress_logs, looks_like_log, detect_log_reason
from backend.compress.code import compress_code, looks_like_code, detect_code_reason
from backend.compress.data import compress_json, looks_like_json, detect_json_reason
from backend.compress.csv import compress_csv, looks_like_csv, detect_csv_reason
from backend.storage.feedback import append_feedback, summary as feedback_summary
from backend.compress.text import compress_text

# -----------------------------
# Initialize shared objects
# -----------------------------

rep = PromptRepresentation()
local_scorer = LocalScorer(rep)
intent_detector = IntentDetector()
gap_reasoner = GapReasoner()  # OpenAI-based reasoner
optimizer = PromptOptimizer(intent_detector, gap_reasoner)

# LLM client (used only for rewrite suggestions)
# Make sure you have OPENAI_API_KEY in your environment
try:
    llm_client = OpenAITextClient(model="gpt-4o-mini")
except Exception:
    llm_client = None

rewrite_cache = TTLCache(ttl_seconds=600, max_items=500)       # 10 minutes
rewrite_cache_stats = CacheStats(name="rewrite_cache")
rewrite_limiter = SimpleRateLimiter(
    max_requests=20, window_seconds=60)  # 20/min per IP


def _rewrite_cache_key(prompt: str, model: str, user_id: str) -> str:
    raw = f"{REWRITE_SYSTEM_VERSION}|{model}|{user_id.strip()}|{prompt.strip()}".encode(
        "utf-8", errors="ignore"
    )
    return hashlib.sha256(raw).hexdigest()


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


class RewriteData(BaseModel):
    prompt: str


class CompressData(BaseModel):
    text: str


class FeedbackData(BaseModel):
    type: str
    prompt: str
    intent: str | None = None
    card_index: int | None = None
    card_text: str | None = None

# -----------------------------
# Endpoints
# -----------------------------


def llm_score_from_missing(prompt: str, missing_info: list) -> int:
    # missing_info: list of dicts with "field"
    n_missing = len(missing_info) if isinstance(missing_info, list) else 0

    base = 90
    score = base - (n_missing * 10)

    # small penalty for very short prompts
    if len((prompt or "").strip()) < 25:
        score -= 10

    # clamp
    score = max(0, min(100, score))
    return int(score)


def _ensure_savings(result: dict, original: str) -> dict:
    comp = (result.get("compressed") or "").strip()
    if not comp:
        return result
    if len(comp) >= len(original):
        result["compressed"] = original
        stats = result.setdefault("stats", {})
        stats["chars_in"] = len(original)
        stats["chars_out"] = len(original)
        result["note"] = "Not compressed (would increase size)"
    return result


@app.get("/")
def root():
    return {"message": "Smart Prompt Engine API running"}


@app.post("/score")
def score_endpoint(data: PromptData):
    """
    Local (no-LLM) scoring for live typing:
    - score (0-100)
    - intent
    - missing dimensions
    - live suggestions
    """
    return local_scorer.score(data.prompt)


@app.post("/optimize")
def optimize_endpoint(data: OptimizeData):
    """
    Returns optimized prompt with missing info detected by LLM
    """
    user_vec = rep.encode(data.prompt)
    confidence = confidence_scorer.score(user_vec)

    result = optimizer.optimize(data.prompt, confidence)
    return result


@app.post("/rewrite_suggestions")
def rewrite_suggestions_endpoint(data: RewriteData, request: Request):
    if llm_client is None:
        return {
            "error": "LLM not configured",
            "hint": "Set OPENAI_API_KEY and restart backend."
        }

    # Rate limit (by client IP)
    ip = request.client.host if request.client else "unknown"
    if not rewrite_limiter.allow(ip):
        return {
            "error": "rate_limited",
            "details": "Too many requests. Please wait a bit and try again."
        }

    # Normalize + cache lookup
    prompt = normalize_prompt(data.prompt)
    if not prompt:
        return {"error": "empty_prompt"}

    model_name = getattr(llm_client, "model", "unknown")
    user_id = request.headers.get("X-SPE-User", "").strip() or "anon"
    key = _rewrite_cache_key(prompt, model_name, user_id)
    cached = rewrite_cache.get(key)
    if cached is not None:
        rewrite_cache_stats.hits += 1
        out = dict(cached)
        out["meta"] = {"cache": "hit",
                       "system_version": REWRITE_SYSTEM_VERSION}
        return out
    rewrite_cache_stats.misses += 1

    # Call LLM
    try:
        result = get_rewrite_suggestions(prompt, llm_client)
        if isinstance(result, dict) and result.get("error"):
            return result

        # Keep model score if present; otherwise derive from missing fields.
        if not isinstance(result.get("score"), (int, float)):
            missing = result.get("required_missing", [])
            if not isinstance(missing, list):
                missing = []
            result["score"] = llm_score_from_missing(prompt, missing)
        result["label"] = "good" if result["score"] >= 75 else "needs_more_detail"

        # store in cache
        rewrite_cache.set(key, result)
        rewrite_cache_stats.sets += 1
        result["meta"] = {"cache": "miss",
                          "system_version": REWRITE_SYSTEM_VERSION}
        return result

    except LLMError as e:
        msg = str(e)
        # Make quota errors clear
        if "insufficient_quota" in msg or "exceeded your current quota" in msg:
            return {
                "error": "insufficient_quota",
                "details": "Your OpenAI account has no available quota/billing. Add billing or use a different provider."
            }
        return {"error": "LLM call failed", "details": msg}


@app.post("/compress")
def compress_endpoint(data: CompressData):
    text = (data.text or "").strip()
    # Normalize literal \n sequences into real newlines (common from contenteditable)
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n")

    if not text:
        return {"detected_type": "empty", "compressed": "", "stats": {"chars_in": 0, "chars_out": 0}}

    print("COMPRESS LEN:", len(text))
    print("FIRST 200 CHARS:\n", text[:200])

    is_log, why_log = detect_log_reason(text)
    is_json, why_json = detect_json_reason(text)
    is_code, why_code = detect_code_reason(text)
    is_csv, why_csv = detect_csv_reason(text)

    # Keep explicit debug parity with the detector booleans.
    print("[DETECT] logs =", looks_like_log(text), "|", why_log)
    print("[DETECT] json =", looks_like_json(text), "|", why_json)
    print("[DETECT] code =", looks_like_code(text), "|", why_code)
    print("[DETECT] csv  =", looks_like_csv(text), "|", why_csv)

    debug = {
        "logs": {"match": is_log, "why": why_log},
        "json": {"match": is_json, "why": why_json},
        "code": {"match": is_code, "why": why_code},
        "csv": {"match": is_csv, "why": why_csv},
    }

    if is_log:
        out = compress_logs(text)
        out["debug"] = {"matched": "logs", **debug}
        return _ensure_savings(out, text)
    if is_json:
        out = compress_json(text)
        out["debug"] = {"matched": "json", **debug}
        return _ensure_savings(out, text)
    if is_code:
        out = compress_code(text)
        out["debug"] = {"matched": "code", **debug}
        return _ensure_savings(out, text)
    if is_csv:
        out = compress_csv(text)
        out["debug"] = {"matched": "csv", **debug}
        return _ensure_savings(out, text)

    # ✅ NEW: default to text compression
    out = compress_text(text)
    out["debug"] = {"matched": "text", **debug}
    return _ensure_savings(out, text)


@app.post("/feedback")
def feedback_endpoint(data: FeedbackData):
    append_feedback(data.model_dump())
    return {"ok": True}


@app.get("/feedback/summary")
def feedback_summary_endpoint():
    return feedback_summary()


@app.get("/cache_metrics")
def cache_metrics():
    return {
        "rewrite_cache": {
            **rewrite_cache_stats.to_dict(),
            "maxsize": getattr(rewrite_cache, "maxsize", getattr(rewrite_cache, "max_items", None)),
            "ttl": getattr(rewrite_cache, "ttl", None),
            "currsize": len(getattr(rewrite_cache, "store", {})),
        }
    }


@app.post("/cache_metrics/reset")
def cache_metrics_reset():
    reset_stats(rewrite_cache_stats)
    return {"ok": True}
