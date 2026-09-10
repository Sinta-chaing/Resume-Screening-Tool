from .ollama import chat

MAX_RESUME_INPUT = 8000


def summarize_resume(resume_text: str) -> str:
    """Generate a descriptive summary of the candidate from resume text."""
    text = resume_text[:MAX_RESUME_INPUT]
    if len(resume_text) > MAX_RESUME_INPUT:
        text += "\n\n[Resume truncated for summarization]"

    summary_prompt = f"""
You are an expert HR assistant. Read the resume below and write a concise professional summary describing this candidate.

Your summary should cover:
1. Who the candidate is (current role or focus area)
2. Years of experience (if stated)
3. Core skills and technologies
4. Notable work experience or achievements
5. Education background (if present)

Write 2-4 short paragraphs in plain English.
Use complete sentences — do not use markdown, bullet points, or JSON.
Only include facts that appear in the resume. Do not invent details.

RESUME:
{text}
"""

    summary = chat([
        {"role": "system", "content": "You write clear, factual candidate summaries for recruiters."},
        {"role": "user", "content": summary_prompt},
    ])

    return summary.strip()
