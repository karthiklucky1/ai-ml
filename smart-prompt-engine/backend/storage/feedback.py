# backend/storage/feedback.py
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Dict, Any, List

FEEDBACK_PATH = Path(__file__).resolve().parent / "feedback.jsonl"


def append_feedback(event: Dict[str, Any]) -> None:
    event = dict(event)
    event["ts"] = event.get("ts", time.time())
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_recent(limit: int = 200) -> List[Dict[str, Any]]:
    if not FEEDBACK_PATH.exists():
        return []
    lines = FEEDBACK_PATH.read_text(encoding="utf-8").splitlines()[-limit:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def summary(limit: int = 500) -> Dict[str, Any]:
    events = read_recent(limit=limit)
    clicks = [e for e in events if e.get("type") == "rewrite_click"]
    by_intent = {}
    for e in clicks:
        intent = e.get("intent", "other")
        by_intent[intent] = by_intent.get(intent, 0) + 1
    return {
        "events": len(events),
        "rewrite_clicks": len(clicks),
        "clicks_by_intent": by_intent
    }
