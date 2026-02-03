from __future__ import annotations
import re
from typing import Dict, Any


def compress_text(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {"detected_type": "empty", "compressed": "", "stats": {"chars_in": 0, "chars_out": 0}}

    # Remove extra blank lines
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    # Keep first line as title if it looks like a heading
    title = lines[0] if len(lines[0]) < 80 else ""

    # Convert into compact bullets (keeps meaning but reduces tokens)
    bullets = []
    for ln in lines[1:] if title else lines:
        # kill repeated headings, compress long sentences lightly
        ln = re.sub(r"\s+", " ", ln)
        bullets.append(ln)

    # Take top N bullets, plus a note
    max_bullets = 12
    kept = bullets[:max_bullets]

    out = []
    if title:
        out.append(title)
    out.append("Key points:")
    out.extend(f"- {b}" for b in kept)

    compressed = "\n".join(out).strip()

    return {
        "detected_type": "text",
        "compressed": compressed,
        "stats": {"chars_in": len(raw), "chars_out": len(compressed)}
    }
