# backend/rewrite/suggestions.py
# coding: utf-8

from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.llm.openai_client import OpenAITextClient, LLMError


SYSTEM = """You are a prompt doctor. You improve prompts BEFORE they are sent to an AI.

Your tasks:
1) Extract what the user ALREADY specified in the prompt (provided_info).
2) Identify ONLY the missing information needed for a high-quality answer (missing_info).
   - Do NOT include anything already present in provided_info.
   - Missing items must be specific to the topic (not generic like "add context").
3) missing_info should include ONLY the highest-impact fields for choosing the best answer.
   - Prefer: budget/region/constraints/priority criteria.
   - Avoid low-value fields like OS version unless the prompt explicitly asks.
   - Return at most 4 required + 2 optional.
   - You MUST NOT list a field in missing_info if it is already mentioned in the prompt.
   - If the user prompt already contains a "Fill these" block: only return still-blank ____ fields.
   - Field naming rule:
     - Use short snake_case field names only.
     - Examples: storage_min, carrier_unlocked, budget_max, time_limit, audience_level.
     - Do NOT output generic placeholders like "field", "field1".

4) Produce 3 rewritten prompt suggestions (rewrite_cards) that look like real prompts a human would send.
   - Use blanks like ____ ONLY for missing items.
   - Do NOT answer the prompt.

Critical output rule:
- Return ONLY valid JSON (no markdown, no extra text).

HARD RULES:
- NEVER replace or blank-out information that is already present in the user's prompt.
- rewrite_cards must NOT list provided fields inside Fill blocks.
- rewrite_cards must include ALL missing fields as blanks in ONE place.
- Use this exact format:

<One-line rewritten prompt>

Fill these (required):
- field_name: ____ (example)

Fill these (optional):
- field_name: ____ (example)

If required_missing is empty -> use:
- none ✅

If optional_missing is empty -> use:
- none
"""


USER_TEMPLATE = """User prompt:
{prompt}

Return ONLY JSON with this schema:
{{
  "provided_info": [
    {{"field": "...", "value": "...", "evidence": "quote from prompt"}}
  ],
  "missing_info": [
    {{"field": "...", "why": "...", "example": "...", "evidence":"not mentioned", "optional": false}}
  ],
  "rewrite_cards": [
    "...",
    "...",
    "..."
  ],
  "intent": "decision|instruction|explanation|debugging|estimation|other"
}}

Rules:
- rewrite_cards: exactly 3.
- missing_info: at most 4 required + 2 optional.
- Do NOT put provided_info fields in missing_info.
- If prompt already has Fill these block, only return blanks still ____.
"""
SYSTEM_VERSION = "v3.2"


# ---------- Normalization / safety helpers ----------

def _clean_field_name(x: str) -> str:
    x = (x or "").strip()
    bad = {"field1", "field2", "field3", "field", "unknown", "..."}
    if x.lower() in bad:
        return ""
    return x


def _sanitize_missing_info(missing_info: Any) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for item in (missing_info or []):
        if isinstance(item, str):
            field = _clean_field_name(item)
            if field:
                cleaned.append(
                    {"field": field, "optional": False, "why": "", "example": ""})
            continue

        if isinstance(item, dict):
            field = _clean_field_name(item.get("field", ""))
            if not field:
                continue
            cleaned.append({
                "field": field,
                "optional": bool(item.get("optional", False)),
                "why": item.get("why", "") or "",
                "example": item.get("example", "") or "",
                "evidence": item.get("evidence", "") or "",
            })

    # limit: 4 required + 2 optional
    req = [m for m in cleaned if not m.get("optional", False)]
    opt = [m for m in cleaned if m.get("optional", False)]
    req = req[:4]
    opt = opt[:2]
    return req + opt


def _postprocess_missing(prompt: str, missing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    p = (prompt or "").lower()

    def drop_field(name_substr: str):
        nonlocal missing
        missing = [m for m in missing if name_substr not in (m.get("field", "").lower())]

    # If user already said iPhone/iOS, brand is already implied.
    if "iphone" in p or "ios" in p:
        drop_field("brand")
        drop_field("brand loyalty")
        drop_field("apple")

    # Specific model is usually optional unless explicit comparison intent appears.
    explicit_model_tokens = ["vs", "versus", "compare", "12", "13", "14", "15", "16", "pro", "max", "mini", "se"]
    asked_specific = any(t in p for t in explicit_model_tokens)

    for m in missing:
        f = (m.get("field") or "").lower()
        if "specific model" in f or "model preference" in f:
            m["optional"] = (not asked_specific)

    # Keep same limits: 4 required + 2 optional
    req = [m for m in missing if not m.get("optional", False)][:4]
    opt = [m for m in missing if m.get("optional", False)][:2]
    return req + opt


def _field_is_already_covered(prompt: str, item: dict) -> bool:
    p = (prompt or "").lower()

    field = (item.get("field") or "").lower()
    ex = (item.get("example") or "").lower()
    why = (item.get("why") or "").lower()

    # If prompt already has camera/battery and missing says "specific features" about camera/battery.
    if "specific feature" in field or "specific features" in field:
        if ("camera" in p or "battery" in p or "priority" in p) and (
            "camera" in ex or "battery" in ex or "camera" in why or "battery" in why
        ):
            return True

    # Covers table/compare format already requested.
    if "format" in field or "comparison_format" in field:
        if "table" in p or "compare" in p or "pros/cons" in p:
            return True

    # Covers final pick criteria already requested.
    if "final_pick_criteria" in field or ("criteria" in field and "pick" in field):
        if "priorit" in p or "camera" in p or "battery" in p or "final pick" in p:
            return True

    # Conservative keyword coverage check.
    for kw in [
        "budget", "region", "country", "usa", "price",
        "camera", "battery", "iphone", "android", "new", "refurb",
    ]:
        if kw in field and kw in p:
            return True

    return False


def _format_fill_block(required_missing: List[Dict[str, Any]],
                       optional_missing: List[Dict[str, Any]]) -> str:
    req_lines: List[str] = []
    if required_missing:
        for x in required_missing:
            field = (x.get("field") or "").strip()
            ex = (x.get("example") or "").strip()
            if not field:
                continue
            req_lines.append(
                f"- {field}: ____ ({ex})" if ex else f"- {field}: ____")
    else:
        req_lines.append("- none ✅")

    opt_lines: List[str] = []
    if optional_missing:
        for x in optional_missing:
            field = (x.get("field") or "").strip()
            ex = (x.get("example") or "").strip()
            if not field:
                continue
            opt_lines.append(
                f"- {field}: ____ ({ex})" if ex else f"- {field}: ____")
    else:
        opt_lines.append("- none")

    return (
        "Fill these (required):\n"
        + "\n".join(req_lines)
        + "\n\nFill these (optional):\n"
        + "\n".join(opt_lines)
    )


def _normalize_cards(original_prompt: str,
                     required_missing: List[Dict[str, Any]],
                     optional_missing: List[Dict[str, Any]],
                     cards: Any) -> List[str]:
    """
    Guarantees:
    - cards include ONLY missing blanks
    - cards include a Fill block exactly in our format
    - cards never list provided fields as required
    """
    fill = _format_fill_block(required_missing, optional_missing)

    # fallback "real" first lines if model output is messy
    fallback_first_lines = [
        original_prompt.strip().rstrip(".") + ".",
        "Compare a few good options and recommend the best one.",
        "Give a short recommendation with pros/cons and a final pick.",
    ]

    out: List[str] = []
    cards_list = cards if isinstance(cards, list) else []

    for i in range(3):
        first_line = ""
        if i < len(cards_list) and isinstance(cards_list[i], str) and cards_list[i].strip():
            # Take ONLY the first line; strip any "Fill these" junk the model wrote
            first_line = cards_list[i].strip().splitlines()[0].strip()

        if not first_line or "fill these" in first_line.lower():
            first_line = fallback_first_lines[i]

        card = f"{first_line}\n\n{fill}"
        out.append(card)

    return out


def _clean_rewrite_card(card: str) -> str:
    if not isinstance(card, str):
        return ""
    # Remove optional block when it only says none.
    card = card.replace("Fill these (optional):\n- none", "").strip()
    card = card.replace("Fill these (optional):\n- None", "").strip()
    return card


def _extract_fill_fields(prompt: str) -> set[str]:
    fields = set()
    for m in re.finditer(r"^\s*-\s*([^:]+):", prompt, flags=re.MULTILINE):
        fields.add(m.group(1).strip().lower())
    return fields


# ---------- Main function ----------

def get_rewrite_suggestions(prompt: str, client: OpenAITextClient) -> Dict[str, Any]:
    p = (prompt or "").strip()
    system = SYSTEM + f"\n\nSYSTEM_VERSION={SYSTEM_VERSION}"

    try:
        data = client.complete_json(
            system=system,
            user=USER_TEMPLATE.format(prompt=p),
            temperature=0.3,
            max_tokens=700,
        )
    except LLMError:
        raise

    provided_info = data.get("provided_info", [])
    missing_info = _sanitize_missing_info(data.get("missing_info", []))
    if "fill these" in p.lower():
        allowed = _extract_fill_fields(p)
        missing_info = [
            m for m in missing_info
            if (m.get("field", "").lower() in allowed)
        ]
    missing_info = [m for m in missing_info if not _field_is_already_covered(p, m)]
    missing_info = _postprocess_missing(p, missing_info)

    required_missing = [
        m for m in missing_info if not m.get("optional", False)]
    optional_missing = [m for m in missing_info if m.get("optional", False)]

    # LLM-based score: required fields only
    llm_score = max(20, 100 - 20 * len(required_missing) - 5 * len(optional_missing))

    # Normalize rewrite cards to our strict format
    rewrite_cards = _normalize_cards(
        p, required_missing, optional_missing, data.get("rewrite_cards", []))
    rewrite_cards = [_clean_rewrite_card(c) for c in rewrite_cards if isinstance(c, str)]

    if not isinstance(provided_info, list):
        raise LLMError("Bad JSON schema from LLM (provided_info not list).")

    return {
        "provided_info": provided_info[:10],
        "missing_info": missing_info[:6],
        "required_missing": required_missing[:4],
        "optional_missing": optional_missing[:2],
        "rewrite_cards": rewrite_cards[:3],
        "intent": data.get("intent", "other"),
        "score": llm_score,
    }
