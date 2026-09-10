import json
import re

from .ollama import chat
from .scoring import compute_hybrid_score

NARRATIVE_TEXT_LIMIT = 4500


def safe_json_from_text(text: str) -> dict | None:
    if not text:
        return None

    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None

    return None


def to_string_list(value) -> list[str]:
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text") or item.get("name") or item.get("skill") or item.get("description")
                if text:
                    items.append(str(text).strip())
            else:
                text = str(item).strip()
                if text:
                    items.append(text)
        return items

    if isinstance(value, str) and value.strip():
        lines = [line.strip(" \t-•*") for line in value.splitlines() if line.strip()]
        return lines if len(lines) > 1 else [value.strip()]

    return []


def _first_list(raw: dict, *keys: str) -> list[str]:
    for key in keys:
        if key in raw:
            items = to_string_list(raw[key])
            if items:
                return items
    return []


def normalize_narrative(raw: dict | None, fallback_raw: str) -> dict:
    if not raw:
        return {
            "strengths": [],
            "gaps": [],
            "suggestions": [],
            "narrativeRaw": fallback_raw,
        }

    return {
        "strengths": _first_list(
            raw,
            "strengths",
            "strength",
            "top_strengths",
            "matching_strengths",
            "key_strengths",
        ),
        "gaps": _first_list(
            raw,
            "gaps",
            "gap",
            "skill_gaps",
            "missing_skills",
            "weaknesses",
            "missing",
        ),
        "suggestions": _first_list(
            raw,
            "suggestions",
            "improvement_suggestions",
            "recommendations",
            "improvements",
        ),
    }


def _truncate_for_prompt(text: str, limit: int = NARRATIVE_TEXT_LIMIT) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "\n...[truncated]"


def _fallback_narrative(breakdown: dict) -> dict:
    matched = breakdown.get("matchedSkills", [])
    missing = breakdown.get("missingSkills", [])

    strengths = [
        f"Matches requirement: {item}" if len(item) < 80 else f"Matches: {item[:77]}..."
        for item in matched[:6]
    ]
    gaps = [
        f"Missing or weak match: {item}" if len(item) < 80 else f"Gap: {item[:77]}..."
        for item in missing[:6]
    ]

    suggestions: list[str] = []
    for item in missing[:3]:
        suggestions.append(f"Add clearer evidence of experience with: {item}")
    while len(suggestions) < 3:
        suggestions.append("Align resume wording more closely with the job description requirements.")

    return {
        "strengths": strengths,
        "gaps": gaps,
        "suggestions": suggestions[:3],
    }


def _merge_narrative(primary: dict, fallback: dict) -> dict:
    return {
        "strengths": primary["strengths"] or fallback["strengths"],
        "gaps": primary["gaps"] or fallback["gaps"],
        "suggestions": primary["suggestions"] or fallback["suggestions"],
    }


def evaluate_resume(
    resume_text: str,
    jd_text: str,
    resume_embeddings: list[list[float]] | None = None,
) -> dict:
    hybrid = compute_hybrid_score(resume_text, jd_text, resume_embeddings)
    breakdown = hybrid["scoreBreakdown"]
    fallback = _fallback_narrative(breakdown)

    matched_preview = ", ".join(breakdown.get("matchedSkills", [])[:8]) or "None detected"
    missing_preview = ", ".join(breakdown.get("missingSkills", [])[:8]) or "None detected"

    evaluation_prompt = f"""
Compare RESUME vs JOB DESCRIPTION and return narrative feedback as JSON.

RESUME:
{_truncate_for_prompt(resume_text)}

JOB DESCRIPTION:
{_truncate_for_prompt(jd_text)}

DETECTED MATCHES:
{matched_preview}

DETECTED GAPS:
{missing_preview}

Return ONLY valid JSON with exactly these keys:
- strengths: array of 3-6 strings describing top matching strengths
- gaps: array of 3-6 strings describing missing skills or weak areas
- suggestions: array of exactly 3 improvement suggestions

Rules:
- Use plain strings in each array
- Do not include a score field
- No markdown fences or extra commentary
"""

    evaluation_raw = chat([
        {"role": "system", "content": "You return strict JSON only."},
        {"role": "user", "content": evaluation_prompt},
    ])

    parsed = safe_json_from_text(evaluation_raw)
    narrative = normalize_narrative(parsed, evaluation_raw)
    merged = _merge_narrative(narrative, fallback)

    result = {
        "score": hybrid["score"],
        "scoreBreakdown": breakdown,
        "strengths": merged["strengths"],
        "gaps": merged["gaps"],
        "suggestions": merged["suggestions"],
    }

    if narrative.get("narrativeRaw") and not narrative["strengths"] and not narrative["gaps"]:
        result["narrativeRaw"] = narrative["narrativeRaw"]

    return result
