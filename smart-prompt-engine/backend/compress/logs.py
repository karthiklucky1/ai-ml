# backend/compress/logs.py
from __future__ import annotations
import re
from typing import Dict, Any, Tuple


LOG_LEVEL = re.compile(
    r"(?m)^\s*(INFO|ERROR|WARN|WARNING|DEBUG|CRITICAL)\s*[:\]]")
TIMESTAMP = re.compile(r"(?m)^\s*\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")
TRACEBACK = re.compile(r"traceback \(most recent call last\):?", re.IGNORECASE)
FILE_LINE = re.compile(r'(?m)^\s*File ".*", line \d+')
EXC_NAME = re.compile(
    r"(ModuleNotFoundError|TypeError|ValueError|KeyError|RuntimeError|Exception|Error)\b"
)


def detect_log_reason(text: str) -> Tuple[bool, str]:
    t = (text or "").strip()
    if not t:
        return False, "empty"

    m = TRACEBACK.search(t)
    if m:
        return True, f"TRACEBACK:{m.group(0)}"

    if FILE_LINE.search(t) and EXC_NAME.search(t):
        return True, "FILE_LINE+EXCEPTION"

    log_lines = LOG_LEVEL.findall(t)
    if len(log_lines) >= 2:
        return True, f"LOG_LEVEL_LINES:{len(log_lines)}"

    if TIMESTAMP.search(t) and LOG_LEVEL.search(t):
        return True, "TIMESTAMP+LOG_LEVEL"

    return False, ""


def looks_like_log(text: str) -> bool:
    ok, _ = detect_log_reason(text)
    return ok


def compress_logs(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {
            "detected_type": "empty",
            "compressed": "",
            "stats": {"lines_in": 0, "lines_out": 0, "chars_in": 0, "chars_out": 0}
        }

    lines = raw.splitlines()
    lines_in = len(lines)
    chars_in = len(raw)

    # Find the first "ERROR" / "Traceback" block start
    start_idx = None
    for i, ln in enumerate(lines):
        low = ln.lower()
        if "traceback" in low or low.startswith("error:") or "exception in asgi" in low:
            start_idx = i
            break

    # If we found a traceback block, focus around it
    window = lines
    if start_idx is not None:
        window = lines[start_idx:]  # from traceback/error to end

    # Remove noisy INFO lines (keep only if inside traceback block and useful)
    filtered = []
    for ln in window:
        if ln.startswith("INFO:"):
            continue
        filtered.append(ln)

    # Keep essential patterns
    essentials = []
    for ln in filtered:
        if "Exception in ASGI application" in ln:
            essentials.append(ln)
        elif "Traceback (most recent call last)" in ln:
            essentials.append(ln)
        elif re.search(r'File ".*", line \d+', ln):
            essentials.append(ln)
        elif re.search(r"(ModuleNotFoundError|TypeError|ValueError|KeyError|RuntimeError|Exception):", ln):
            essentials.append(ln)
        elif ln.strip().startswith(("result =", "await", "raise", "import ")):
            essentials.append(ln)

    # Add last 10 lines of filtered block as context (often includes cause)
    tail = filtered[-10:] if len(filtered) > 10 else filtered
    essentials.extend(tail)

    # Dedupe (stronger: normalize whitespace)
    seen = set()
    out_lines = []
    for ln in essentials:
        key = " ".join(ln.strip().split())
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out_lines.append(ln)

    compressed = "\n".join(out_lines).strip()

    return {
        "detected_type": "logs",
        "compressed": compressed,
        "stats": {
            "lines_in": lines_in,
            "lines_out": len(out_lines),
            "chars_in": chars_in,
            "chars_out": len(compressed),
        }
    }
