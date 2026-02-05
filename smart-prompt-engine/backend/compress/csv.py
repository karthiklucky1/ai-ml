# backend/compress/csv.py
from __future__ import annotations

from typing import Dict, Any, List, Tuple
import csv
import io


def looks_like_csv(text: str) -> bool:
    ok, _ = detect_csv_reason(text)
    return ok


def detect_csv_reason(text: str) -> Tuple[bool, str]:
    raw = (text or "").strip()
    if not raw:
        return False, "empty"

    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if len(lines) < 3:
        return False, "need_at_least_3_lines"

    sentencey = sum(1 for ln in lines if (len(ln) > 90 and "." in ln))
    if sentencey >= max(2, len(lines) // 2):
        return False, "looks_like_paragraph_text"

    sample = "\n".join(lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except Exception:
        return False, "sniffer_failed"

    try:
        rows = list(csv.reader(io.StringIO(sample), dialect))
    except Exception:
        return False, "csv_parse_failed"

    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if len(rows) < 2:
        return False, "not_enough_rows"

    widths = [len(r) for r in rows]
    if min(widths) < 2:
        return False, "too_few_columns"

    # Tabular data should keep nearly stable column counts.
    if max(widths) - min(widths) > 1:
        return False, "inconsistent_columns"

    return True, f"dialect_delimiter:{repr(dialect.delimiter)}"


def compress_csv(text: str, sample_rows: int = 3) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {
            "detected_type": "empty",
            "compressed": "",
            "stats": {"chars_in": 0, "chars_out": 0}
        }

    chars_in = len(raw)
    try:
        reader = csv.reader(io.StringIO(raw))
        rows = list(reader)
    except Exception:
        return {
            "detected_type": "csv",
            "compressed": raw,
            "stats": {"chars_in": chars_in, "chars_out": chars_in},
            "note": "Not compressed (parse failed)"
        }

    if len(rows) < 2:
        return {
            "detected_type": "csv",
            "compressed": raw,
            "stats": {"chars_in": chars_in, "chars_out": chars_in},
            "note": "Not compressed (too few rows)"
        }

    header = rows[0]
    data = rows[1:]
    row_count = len(data)
    col_count = len(header)

    first_idx = list(range(min(sample_rows, row_count)))
    last_idx = []
    if row_count > sample_rows:
        last_idx = list(range(max(sample_rows, row_count - sample_rows), row_count))
    idx = sorted(set(first_idx + last_idx))
    samples: List[List[str]] = [data[i] for i in idx]

    out: List[str] = []
    out.append("CSV COMPRESSED SUMMARY")
    out.append(f"columns ({col_count}): " + ", ".join(header))
    out.append(f"row_count: {row_count}")
    out.append("sample_rows:")
    for r in samples:
        out.append("- " + ", ".join(r))
    if row_count > (sample_rows * 2):
        out.append("- ... (middle rows omitted)")

    compressed = "\n".join(out)

    return {
        "detected_type": "csv",
        "compressed": compressed,
        "stats": {
            "chars_in": chars_in,
            "chars_out": len(compressed),
            "row_count": row_count,
            "column_count": col_count,
        },
    }
