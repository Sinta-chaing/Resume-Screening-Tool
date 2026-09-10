from pgvector.django import CosineDistance

from screening.models import AnalysisSession, ResumeChunk

EMBEDDING_DIMENSIONS = 1024


def create_session(
    resume_filename: str,
    jd_filename: str,
    evaluation: dict,
    resume_summary: str,
    chunk_count: int,
    candidate_name: str = "",
    position: str = "",
) -> AnalysisSession:
    return AnalysisSession.objects.create(
        resume_filename=resume_filename,
        jd_filename=jd_filename,
        candidate_name=candidate_name,
        position=position,
        evaluation=evaluation,
        resume_summary=resume_summary,
        chunk_count=chunk_count,
    )


def add_chunk(session: AnalysisSession, chunk_key: str, text: str, embedding: list[float]) -> None:
    ResumeChunk.objects.create(
        session=session,
        chunk_key=chunk_key,
        text=text,
        embedding=embedding,
    )


def get_session(session_id: str) -> AnalysisSession | None:
    try:
        return AnalysisSession.objects.get(pk=session_id)
    except (AnalysisSession.DoesNotExist, ValueError):
        return None


def search_chunks(session_id: str, query_embedding: list[float], k: int = 4) -> list[dict]:
    """Return top-k chunks by cosine similarity for a session."""
    chunks = (
        ResumeChunk.objects.filter(session_id=session_id)
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .order_by("distance")[:k]
    )

    results = []
    for chunk in chunks:
        # Cosine distance: 0 = identical; similarity ≈ 1 - distance for normalized vectors
        score = max(0.0, 1.0 - float(chunk.distance))
        results.append({
            "id": chunk.chunk_key,
            "text": chunk.text,
            "score": score,
        })
    return results
