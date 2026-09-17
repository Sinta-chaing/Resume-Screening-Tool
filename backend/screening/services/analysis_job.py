import logging
import threading

from django.db import close_old_connections

from screening.models import AnalysisSession
from screening.services.ats import evaluate_resume
from screening.services.chunking import chunk_text
from screening.services.metadata import extract_record_metadata
from screening.services.ollama import embed_many
from screening.services.summary import summarize_resume
from screening.services.vector_store import add_chunk

logger = logging.getLogger(__name__)

# Serialize analysis work: only one heavy job at a time so a small server
# doesn't run out of RAM running multiple Ollama models in parallel.
_analysis_workers: set[threading.Thread] = set()
_analysis_lock = threading.Lock()


def _run_analysis(
    session_id: str,
    resume_text: str,
    jd_text: str,
    resume_filename: str,
    jd_filename: str,
) -> None:
    """Run the full analysis pipeline for a session.

    Called from a worker thread. Updates the session in place and sets its
    status to COMPLETED or FAILED. Connection lifecycle is handled by
    `_worker_wrapper`.
    """
    try:
        session = AnalysisSession.objects.get(pk=session_id)
        session.status = AnalysisSession.Status.PROCESSING
        session.save(update_fields=["status"])

        chunks = chunk_text(resume_text)
        chunk_embeddings = embed_many(chunks) if chunks else []
        evaluation = evaluate_resume(resume_text, jd_text, chunk_embeddings)
        resume_summary = summarize_resume(resume_text)
        metadata = extract_record_metadata(
            resume_text,
            jd_text,
            resume_filename,
            jd_filename,
        )

        for i, chunk in enumerate(chunks):
            add_chunk(session, f"resume-{i}", chunk, chunk_embeddings[i])

        session.evaluation = evaluation
        session.resume_summary = resume_summary
        session.chunk_count = len(chunks)
        session.candidate_name = metadata["candidate_name"]
        session.position = metadata["position"]
        session.status = AnalysisSession.Status.COMPLETED
        session.error_message = ""
        session.save()
    except Exception as exc:  # noqa: BLE001 - persist any failure
        logger.exception("Analysis failed for session %s", session_id)
        try:
            session = AnalysisSession.objects.get(pk=session_id)
            session.status = AnalysisSession.Status.FAILED
            session.error_message = str(exc)[:2000]
            session.save(update_fields=["status", "error_message"])
        except AnalysisSession.DoesNotExist:
            logger.warning("Analysis session %s deleted; skipping failure update", session_id)


def _worker_wrapper(*args) -> None:
    """Thread entrypoint: run the job, then free this thread's DB connection."""
    try:
        _run_analysis(*args)
    finally:
        close_old_connections()
        with _analysis_lock:
            _analysis_workers.discard(threading.current_thread())


def queue_analysis(
    session_id: str,
    resume_text: str,
    jd_text: str,
    resume_filename: str,
    jd_filename: str,
) -> None:
    """Start analysis in a background worker thread.

    Runs sequentially (one at a time) so memory stays bounded on small servers.
    """
    worker = threading.Thread(
        target=_worker_wrapper,
        args=(session_id, resume_text, jd_text, resume_filename, jd_filename),
        daemon=True,
    )
    with _analysis_lock:
        _analysis_workers.add(worker)
    worker.start()