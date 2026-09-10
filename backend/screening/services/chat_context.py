import re

from screening.models import AnalysisSession

from .ollama import chat, embed
from .vector_store import search_chunks

SCORE_QUESTION_PATTERN = re.compile(
    r"\b(match\s*score|score|percent|percentage|rating|why.*\d+\s*%|"
    r"how.*score|what.*score|only\s+\d+|got\s+\d+)\b",
    re.IGNORECASE,
)

SECTION_HINTS: list[tuple[str, str]] = [
    ("education", "Education"),
    ("university", "Education"),
    ("degree", "Education"),
    ("experience", "Work experience"),
    ("employment", "Work experience"),
    ("work history", "Work experience"),
    ("project", "Projects"),
    ("skills", "Skills"),
    ("technical skills", "Skills"),
    ("certification", "Certifications"),
    ("summary", "Summary"),
    ("objective", "Summary"),
    ("award", "Awards"),
    ("volunteer", "Volunteer work"),
]


def _is_score_question(question: str) -> bool:
    return SCORE_QUESTION_PATTERN.search(question) is not None


def _chunk_index(chunk_key: str) -> int | None:
    match = re.search(r"(\d+)$", chunk_key)
    if not match:
        return None
    return int(match.group(1)) + 1


def _infer_section(text: str) -> str:
    sample = text[:400].lower()
    for keyword, label in SECTION_HINTS:
        if keyword in sample:
            return label
    return "Resume excerpt"


def _document_label(session: AnalysisSession) -> str:
    if session.candidate_name:
        return session.candidate_name
    return session.resume_filename


def _format_list(items: list) -> str:
    if not items:
        return "None listed"
    return "\n".join(f"- {item}" for item in items)


def _build_analysis_context(session: AnalysisSession) -> str:
    evaluation = session.evaluation if isinstance(session.evaluation, dict) else {}
    breakdown = evaluation.get("scoreBreakdown") or {}

    lines = [
        f"Candidate: {_document_label(session)}",
        f"Target position: {session.position or session.jd_filename}",
        f"Resume file: {session.resume_filename}",
        f"Job description file: {session.jd_filename}",
        f"Final match score: {evaluation.get('score', 'unknown')}/100",
    ]

    if breakdown:
        lines.extend([
            f"Skill overlap component: {breakdown.get('skillOverlap', 'n/a')}% "
            f"(weight {int((breakdown.get('skillWeight') or 0) * 100)}%)",
            f"Embedding similarity component: {breakdown.get('embeddingSimilarity', 'n/a')}% "
            f"(weight {int((breakdown.get('embeddingWeight') or 0) * 100)}%)",
            "Matched requirements:",
            _format_list(breakdown.get("matchedSkills", [])),
            "Unmatched requirements:",
            _format_list(breakdown.get("missingSkills", [])),
        ])

    lines.extend([
        "Strengths:",
        _format_list(evaluation.get("strengths", [])),
        "Skill gaps:",
        _format_list(evaluation.get("gaps", [])),
        "Improvement suggestions:",
        _format_list(evaluation.get("suggestions", [])),
    ])

    if session.resume_summary:
        lines.extend(["Resume summary:", session.resume_summary[:1200]])

    return "\n".join(lines)


def _source_reason(question: str, section: str, score: float, source_type: str) -> str:
    relevance = f"{score * 100:.0f}% semantic similarity to the question"
    if source_type == "analysis":
        return (
            "Included because your question is about the match score or evaluation. "
            "This comes from the structured analysis report, not a resume chunk."
        )
    return (
        f"Included because this {section.lower()} excerpt from the candidate resume "
        f"had {relevance} and may contain evidence related to: \"{question[:120]}\"."
    )


def _build_resume_sources(session: AnalysisSession, chunks: list[dict], question: str) -> list[dict]:
    document_name = _document_label(session)
    total_chunks = session.chunk_count or len(chunks)
    sources: list[dict] = []

    for item in chunks:
        chunk_key = item["id"]
        section = _infer_section(item["text"])
        index = _chunk_index(chunk_key)
        part_label = f"part {index} of {total_chunks}" if index else chunk_key

        sources.append({
            "id": chunk_key,
            "type": "resume",
            "documentName": document_name,
            "resumeFilename": session.resume_filename,
            "candidateName": session.candidate_name,
            "section": section,
            "part": part_label,
            "score": item["score"],
            "reason": _source_reason(question, section, item["score"], "resume"),
            "preview": item["text"][:240].strip(),
        })

    return sources


def _build_analysis_source(session: AnalysisSession, question: str) -> dict:
    evaluation = session.evaluation if isinstance(session.evaluation, dict) else {}
    preview_parts = [
        f"Match score: {evaluation.get('score', 'n/a')}/100",
    ]
    breakdown = evaluation.get("scoreBreakdown") or {}
    if breakdown.get("missingSkills"):
        preview_parts.append(
            "Unmatched requirements: " + ", ".join(breakdown["missingSkills"][:4])
        )
    if evaluation.get("gaps"):
        preview_parts.append("Gaps: " + "; ".join(evaluation["gaps"][:2]))

    return {
        "id": "analysis-report",
        "type": "analysis",
        "documentName": "Match analysis report",
        "resumeFilename": session.resume_filename,
        "candidateName": session.candidate_name,
        "section": "Scoring breakdown",
        "part": "evaluation summary",
        "score": 1.0,
        "reason": _source_reason(question, "Scoring breakdown", 1.0, "analysis"),
        "preview": " · ".join(preview_parts),
    }


def _build_prompt(
    session: AnalysisSession,
    question: str,
    resume_chunks: list[dict],
    include_analysis: bool,
) -> str:
    analysis_context = _build_analysis_context(session)
    document_name = _document_label(session)

    excerpt_blocks = []
    for item in resume_chunks:
        section = _infer_section(item["text"])
        excerpt_blocks.append(
            f"[Resume: {document_name} | Section: {section} | "
            f"Relevance: {item['score'] * 100:.0f}%]\n{item['text']}"
        )

    resume_context = "\n\n".join(excerpt_blocks) if excerpt_blocks else "No resume excerpts retrieved."

    instructions = [
        "Answer as a helpful HR assistant reviewing this candidate.",
        "Use MATCH ANALYSIS for questions about match score, percentage, ranking, strengths, gaps, or requirements fit.",
        "Use RESUME EXCERPTS for questions about the candidate's background, skills, education, or experience.",
        "When explaining a score, cite specific matched and unmatched requirements from MATCH ANALYSIS.",
        "Do not answer with exactly \"Not found in resume.\" if MATCH ANALYSIS or RESUME EXCERPTS contain relevant information.",
        "Be concise and specific.",
    ]

    return f"""
{chr(10).join(instructions)}

MATCH ANALYSIS:
{analysis_context}

RESUME EXCERPTS:
{resume_context}

QUESTION:
{question}
"""


def answer_question(session: AnalysisSession, question: str) -> dict:
    score_question = _is_score_question(question)
    q_embed = embed(question)
    top_chunks = search_chunks(str(session.id), q_embed, 4)

    prompt = _build_prompt(session, question, top_chunks, include_analysis=True)
    answer = chat([
        {"role": "system", "content": "You are a helpful HR assistant."},
        {"role": "user", "content": prompt},
    ])

    sources = _build_resume_sources(session, top_chunks, question)
    if score_question:
        sources.insert(0, _build_analysis_source(session, question))

    return {
        "answer": answer.strip(),
        "sources": sources,
    }
