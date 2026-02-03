# backend/compress/data.py
from __future__ import annotations
import json
from typing import Dict, Any, Tuple


def looks_like_json(text: str) -> bool:
    ok, _ = detect_json_reason(text)
    return ok


def detect_json_reason(text: str) -> Tuple[bool, str]:
    t = (text or "").strip()
    if not t:
        return False, "empty"
    if not ((t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]"))):
        return False, "missing_wrappers"
    try:
        json.loads(t)
    except Exception:
        return False, "invalid_json_parse"
    return True, "valid_json_parse"


def _safe_json_parse(text: str):
    return json.loads(text)


def compress_json(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    chars_in = len(raw)
    try:
        obj = _safe_json_parse(raw)
    except Exception:
        return {"detected_type": "json", "compressed": raw, "stats": {"chars_in": chars_in, "chars_out": chars_in}}

    def summarize_obj(o, depth=0):
        if depth > 2:
            return "..."
        if isinstance(o, dict):
            keys = list(o.keys())
            sample = {k: summarize_obj(o[k], depth + 1)
                      for k in keys[:8]}  # smaller
            extra = len(keys) - len(sample)
            if extra > 0:
                sample["_more_keys"] = extra
            return sample
        if isinstance(o, list):
            n = len(o)
            sample_items = []
            for idx in [0, n//2, n-1]:
                if 0 <= idx < n:
                    sample_items.append(summarize_obj(o[idx], depth + 1))
            return {"_type": "list", "count": n, "samples": sample_items[:3]}
        return o

    summary = summarize_obj(obj)

    # ✅ no indent, minified
    compressed = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))

    # ✅ if not smaller, keep original
    if len(compressed) >= chars_in:
        return {
            "detected_type": "json",
            "compressed": raw,
            "stats": {"chars_in": chars_in, "chars_out": chars_in},
            "note": "Not compressed (would increase size)"
        }

    return {
        "detected_type": "json",
        "compressed": compressed,
        "stats": {"chars_in": chars_in, "chars_out": len(compressed)}
    }
