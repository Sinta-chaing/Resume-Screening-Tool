import os
import re

from .ats import safe_json_from_text
from .ollama import chat


def _name_from_filename(filename: str) -> str:
    base = os.path.splitext(filename)[0]
    base = re.sub(r"[._-]+", " ", base)
    base = re.sub(r"\b(cv|resume)\b", "", base, flags=re.IGNORECASE).strip()
    return base or "Unknown candidate"


def _position_from_jd(jd_text: str, jd_filename: str) -> str:
    for line in jd_text.splitlines():
        cleaned = line.strip()
        if cleaned and len(cleaned) < 120:
            return cleaned

    base = os.path.splitext(jd_filename)[0]
    return re.sub(r"[._-]+", " ", base).strip() or "Unknown position"


def extract_record_metadata(
    resume_text: str,
    jd_text: str,
    resume_filename: str,
    jd_filename: str,
) -> dict[str, str]:
    # Record name comes from the upload filename (deterministic) instead of a
    # resume text guess, which can return the wrong person's name.
    candidate_name = _name_from_filename(resume_filename)

    prompt = f"""
Extract the job title or role described in the job description below.

Return ONLY valid JSON with key:
- position: the job title or role from the job description

JOB DESCRIPTION (excerpt):
{jd_text[:1500]}

Rules:
- no markdown, no extra text
- use a plain string for position
"""

    position = None
    try:
        raw = chat([
            {"role": "system", "content": "You extract structured hiring metadata."},
            {"role": "user", "content": prompt},
        ])
        parsed = safe_json_from_text(raw)
        if parsed:
            position = str(parsed.get("position", "")).strip()
    except Exception:
        pass

    if not position:
        position = _position_from_jd(jd_text, jd_filename)

    return {"candidate_name": candidate_name, "position": position}
