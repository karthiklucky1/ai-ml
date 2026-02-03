# backend/compress/code.py
from __future__ import annotations
import re
from typing import Dict, Any, Tuple

CODE_SIGNALS = [
    r"\b(def|class|import|from|return|async|await|lambda)\b",     # python
    # braces/semicolons
    r"[{};]",
    r"==|!=|<=|>=|->|=>",                                         # operators
    r"\b(function|const|let|var|=>)\b",                           # js/ts
    r"#include\s*<",                                              # c/c++
    r"\b(public|private|protected|static|void|new)\b",            # java/c#
]

FENCE = re.compile(r"```")
PY_TRACE = re.compile(r'File ".*", line \d+')
STRONG_CODE = [
    r"\b(def|class)\b",
    r"\b(import|from)\b",
    r"\b(return|yield|raise)\b",
    r"\b(async|await|lambda)\b",
    r"\b(function|const|let|var)\b",
    r"#include\s*<",
    r"\b(public|private|protected|static|void|new)\b",
]
PARA_LINE = re.compile(r"^[A-Z][a-z].*[a-z][\.\!\?]$")


def detect_code_reason(text: str) -> Tuple[bool, str]:
    t = (text or "").strip()
    if not t:
        return False, "empty"

    # If it's clearly logs, don't call it code
    if "traceback" in t.lower() or PY_TRACE.search(t):
        return False, "looks_like_logs"

    # fenced code blocks
    if FENCE.search(t):
        return True, "FENCED_BLOCK"

    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    para_like = sum(1 for ln in lines if PARA_LINE.match(ln))
    if lines and (para_like / len(lines)) > 0.7:
        return False, "mostly_paragraph_lines"

    strong = sum(1 for pat in STRONG_CODE if re.search(pat, t))
    all_signals = sum(1 for pat in CODE_SIGNALS if re.search(pat, t))
    symbols = sum(t.count(ch) for ch in "{}();[]=<>")
    ratio = symbols / max(1, len(t))

    # Require at least 2 strong signals, or 1 strong + clear symbol density.
    if strong >= 2:
        return True, f"STRONG_SIGNALS:{strong}"
    if strong >= 1 and ratio > 0.02 and all_signals >= 2:
        return True, f"STRONG+SYMBOL_RATIO:{ratio:.3f}"

    return False, ""


def looks_like_code(text: str) -> bool:
    ok, _ = detect_code_reason(text)
    return ok


def compress_code(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    lines = raw.splitlines()
    lines_in = len(lines)
    chars_in = len(raw)

    # Remove very long blank/whitespace runs
    cleaned = []
    for ln in lines:
        if ln.strip() == "":
            continue
        cleaned.append(ln)

    # Prefer keeping: imports + function/class definitions + error-related lines
    keep = []

    for ln in cleaned:
        s = ln.strip()
        if s.startswith(("import ", "from ")):
            keep.append(ln)
        elif s.startswith(("def ", "class ", "function ")):
            keep.append(ln)
        elif re.search(r"(Error|Exception|Traceback|TypeError|ValueError|KeyError)", ln):
            keep.append(ln)
        elif s.startswith(("return", "raise", "await ", "async ")):
            keep.append(ln)

    # Also keep a small tail window (context)
    tail = cleaned[-40:] if len(cleaned) > 40 else cleaned
    keep.extend(tail)

    # Dedupe with whitespace normalization
    seen = set()
    out = []
    for ln in keep:
        key = " ".join(ln.strip().split())
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(ln)

    compressed = "\n".join(out).strip()

    return {
        "detected_type": "code",
        "compressed": compressed,
        "stats": {
            "lines_in": lines_in,
            "lines_out": len(out),
            "chars_in": chars_in,
            "chars_out": len(compressed),
        }
    }
