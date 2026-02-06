from __future__ import annotations
import csv
import json
import re
from typing import Dict, Any, Tuple, List

LOG_LEVEL_LINE = re.compile(r"(?mi)^\s*(INFO|ERROR|WARN|WARNING|DEBUG|CRITICAL|FATAL)\b")
ISO_DATE = re.compile(r"(?m)\b\d{4}-\d{2}-\d{2}\b")
TIME_HMS = re.compile(r"(?m)\b\d{2}:\d{2}:\d{2}\b")
TRACEBACK = re.compile(r"Traceback \(most recent call last\):")
FILE_LINE = re.compile(r'(?m)^\s*File ".*", line \d+')
JAVA_STACK = re.compile(r"(?m)^\s*at\s+[A-Za-z0-9_.$]+\(.*:\d+\)\s*$")

PY_MARKERS = re.compile(r"(?m)^\s*(def|class)\s+\w+|\bimport\b|\bfrom\b\s+\w+\s+import\b")
JS_MARKERS = re.compile(r"(?m)^\s*(function\s+\w+|\w+\s*=>|const\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*=)")
C_LIKE_MARKERS = re.compile(r"(?m)^\s*(#include|public\s+static\s+void|using\s+namespace)\b")


def _is_probably_json(text: str) -> Tuple[bool, str]:
    t = text.strip()
    if not t:
        return False, "empty"
    if not ((t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]"))):
        return False, "missing_braces_or_brackets"
    try:
        json.loads(t)
        return True, "valid_json_parse"
    except Exception as e:
        return False, f"json_parse_error:{type(e).__name__}"


def _is_probably_logs(text: str) -> Tuple[bool, str]:
    t = text.strip()
    if not t:
        return False, "empty"

    if TRACEBACK.search(t):
        return True, "TRACEBACK"
    if FILE_LINE.search(t):
        return True, "FILE_LINE"
    if JAVA_STACK.search(t):
        return True, "JAVA_STACK"

    lines = [ln for ln in t.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False, "need_multiline"

    level_lines = sum(1 for ln in lines if LOG_LEVEL_LINE.search(ln))
    has_date = bool(ISO_DATE.search(t))
    has_time = bool(TIME_HMS.search(t))

    if level_lines >= 2:
        return True, f"LOG_LEVEL_LINES:{level_lines}"
    if level_lines >= 1 and (has_date or has_time) and len(lines) >= 3:
        return True, "LOG_LEVEL_PLUS_TIMESTAMP"
    if (has_date and has_time) and len(lines) >= 3:
        return True, "DATE+TIME_MULTILINE"

    return False, f"weak_signals(level_lines={level_lines}, date={has_date}, time={has_time})"


def _is_probably_csv(text: str) -> Tuple[bool, str]:
    t = text.strip()
    if not t:
        return False, "empty"

    lines = [ln for ln in t.splitlines() if ln.strip()]
    if len(lines) < 3:
        return False, "need_at_least_3_lines"

    sentencey = sum(1 for ln in lines if (len(ln) > 80 and "." in ln))
    if sentencey >= max(1, len(lines) // 2):
        return False, "mostly_paragraph_lines"

    sample = "\n".join(lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        delim = dialect.delimiter
    except Exception:
        return False, "sniffer_failed"

    counts = [ln.count(delim) for ln in lines[:20] if ln.strip()]
    with_delim = [c for c in counts if c > 0]
    if len(with_delim) < 3:
        return False, "not_enough_delimited_lines"

    mn, mx = min(with_delim), max(with_delim)
    if mx - mn > 2:
        return False, f"delimiter_variance_too_high({mn}->{mx})"

    return True, f"dialect_delimiter:{delim!r}"


def _is_probably_code(text: str) -> Tuple[bool, str]:
    t = text.strip()
    if not t:
        return False, "empty"

    lines = [ln for ln in t.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False, "need_multiline"

    strong = 0
    if PY_MARKERS.search(t):
        strong += 1
    if JS_MARKERS.search(t):
        strong += 1
    if C_LIKE_MARKERS.search(t):
        strong += 1

    has_braces = ("{" in t and "}" in t)
    has_semicolons = (";" in t)
    indented_lines = sum(1 for ln in lines if ln.startswith("    ") or ln.startswith("\t"))

    if strong >= 1:
        return True, f"STRONG_MARKERS:{strong}"
    if has_braces and has_semicolons and len(lines) >= 3:
        return True, "BRACES+SEMICOLONS"
    if indented_lines >= 2 and any(kw in t for kw in ["return", "if", "for", "while"]):
        return True, "INDENTED_BLOCKS"

    return False, "no_strong_signals"


def detect_type(text: str) -> Dict[str, Any]:
    raw = text or ""
    t = raw.strip()

    if not t:
        return {"type": "empty", "debug": {"matched": "empty"}}

    ok, why = _is_probably_json(t)
    if ok:
        return {"type": "json", "debug": {"matched": "json", "why": why}}

    ok, why = _is_probably_logs(t)
    if ok:
        return {"type": "logs", "debug": {"matched": "logs", "why": why}}

    ok, why = _is_probably_csv(t)
    if ok:
        return {"type": "csv", "debug": {"matched": "csv", "why": why}}

    ok, why = _is_probably_code(t)
    if ok:
        return {"type": "code", "debug": {"matched": "code", "why": why}}

    return {"type": "text", "debug": {"matched": "text", "why": "fallback"}}
