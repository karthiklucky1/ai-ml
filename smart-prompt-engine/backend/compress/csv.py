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
            "stats": {"chars_in": 0, "chars_out": 0},
        }

    chars_in = len(raw)

    lines = [ln for ln in raw.splitlines() if ln.strip()]
    lines_in = len(lines)

    # Parse CSV safely (handles quoted commas and delimiter variants)
    try:
        sample = "\n".join(lines[:20])
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        reader = csv.reader(io.StringIO(raw), dialect)
        rows = list(reader)
    except Exception:
        # If parse fails, return compact line sample fallback.
        kept_lines = lines if len(lines) <= 7 else [lines[0]] + lines[1:6] + [lines[-1]]
        compressed = "\n".join(kept_lines).strip()
        return {
            "detected_type": "csv",
            "compressed": compressed,
            "stats": {"lines_in": lines_in, "lines_out": len(kept_lines), "chars_in": chars_in, "chars_out": len(compressed)},
        }

    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if len(rows) < 2:
        return {
            "detected_type": "csv",
            "compressed": raw,
            "stats": {"lines_in": lines_in, "lines_out": lines_in, "chars_in": chars_in, "chars_out": chars_in},
        }

    header = rows[0]
    data_rows = rows[1:]

    row_count = len(data_rows)
    col_count = len(header)

    # Take first N and last N rows as samples
    samples: List[List[str]] = []
    samples.extend(data_rows[:sample_rows])

    if row_count > sample_rows * 2:
        samples.append(["…"] * col_count)

    samples.extend(data_rows[-sample_rows:])

    # Build compact CSV-like output to keep tokens low.
    kept_rows: List[List[str]] = [header] + samples
    out_io = io.StringIO()
    writer = csv.writer(out_io, dialect=dialect)
    writer.writerows(kept_rows)
    compressed = out_io.getvalue().strip()
    chars_out = len(compressed)

    return {
        "detected_type": "csv",
        "compressed": compressed,
        "stats": {
            "lines_in": lines_in,
            "lines_out": len(kept_rows),
            "chars_in": chars_in,
            "chars_out": chars_out,
            "row_count": row_count,
            "column_count": col_count,
        },
    }
