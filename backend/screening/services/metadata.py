import os
import re


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

    # Position is derived deterministically from the first short JD line to
    # avoid a second LLM round-trip on CPU-only servers.
    position = _position_from_jd(jd_text, jd_filename)

    return {"candidate_name": candidate_name, "position": position}
