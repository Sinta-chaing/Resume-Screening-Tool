from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.analysis_job import queue_analysis
from .services.chat_context import answer_question
from .services.pdf_extractor import extract_text_from_file
from .services.vector_store import get_session
from .models import AnalysisSession


def _match_score(evaluation: dict) -> int:
    score = evaluation.get("score", 0) if isinstance(evaluation, dict) else 0
    try:
        return int(score)
    except (TypeError, ValueError):
        return 0


def _serialize_record_summary(session: AnalysisSession) -> dict:
    return {
        "id": str(session.id),
        "candidateName": session.candidate_name or session.resume_filename,
        "position": session.position or session.jd_filename,
        "score": _match_score(session.evaluation),
        "status": session.status,
        "createdAt": session.created_at.isoformat(),
        "resumeFilename": session.resume_filename,
        "jdFilename": session.jd_filename,
    }


def _serialize_record_detail(session: AnalysisSession) -> dict:
    return {
        "ok": True,
        "sessionId": str(session.id),
        "candidateName": session.candidate_name,
        "position": session.position,
        "chunks": session.chunk_count,
        "evaluation": session.evaluation,
        "resumeSummary": session.resume_summary,
        "status": session.status,
        "error": session.error_message,
        "createdAt": session.created_at.isoformat(),
        "resumeFilename": session.resume_filename,
        "jdFilename": session.jd_filename,
    }


class HealthView(APIView):
    def get(self, request: Request) -> Response:
        return Response({
            "ok": True,
            "useOllama": settings.USE_OLLAMA,
            "ollamaBaseUrl": settings.OLLAMA_BASE_URL,
            "embeddingModel": settings.EMBEDDING_MODEL,
            "chatModel": settings.CHAT_MODEL,
        })


class AnalyzeView(APIView):
    def post(self, request: Request) -> Response:
        try:
            resume_file = request.FILES.get("resume")
            jd_file = request.FILES.get("jd")

            if not resume_file or not jd_file:
                return Response(
                    {"error": "resume and jd files are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            resume_text = extract_text_from_file(resume_file)
            jd_text = extract_text_from_file(jd_file)

            empty_files = []
            if not resume_text.strip():
                empty_files.append(f"resume ({resume_file.name})")
            if not jd_text.strip():
                empty_files.append(f"job description ({jd_file.name})")

            if empty_files:
                return Response(
                    {
                        "error": (
                            f"No readable text found in: {', '.join(empty_files)}. "
                            "The file appears to be empty or unreadable. "
                            "OCR was attempted for image-based (scanned) PDFs."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            session = AnalysisSession.objects.create(
                resume_filename=resume_file.name,
                jd_filename=jd_file.name,
                status=AnalysisSession.Status.PENDING,
            )

            queue_analysis(
                str(session.id),
                resume_text,
                jd_text,
                resume_file.name,
                jd_file.name,
            )

            return Response(
                {
                    "ok": True,
                    "sessionId": str(session.id),
                    "status": session.status,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as exc:
            return Response(
                {"error": str(exc) or "analyze failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChatView(APIView):
    def post(self, request: Request) -> Response:
        try:
            question = request.data.get("question")
            session_id = request.data.get("sessionId")

            if not question:
                return Response(
                    {"error": "question is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not session_id:
                return Response(
                    {"error": "sessionId is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            session = get_session(session_id)
            if session is None:
                return Response(
                    {"error": "invalid or expired sessionId"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = answer_question(session, question)

            return Response({
                "ok": True,
                "answer": result["answer"],
                "sources": result["sources"],
            })
        except Exception as exc:
            return Response(
                {"error": str(exc) or "chat failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecordsListView(APIView):
    def get(self, request: Request) -> Response:
        order = request.query_params.get("order", "asc").lower()
        ascending = order != "desc"

        sessions = AnalysisSession.objects.all()
        records = [_serialize_record_summary(session) for session in sessions]
        records.sort(key=lambda item: item["score"], reverse=not ascending)

        return Response({"ok": True, "records": records})


class RecordDetailView(APIView):
    def get(self, request: Request, session_id: str) -> Response:
        session = get_session(session_id)
        if session is None:
            return Response(
                {"error": "record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(_serialize_record_detail(session))

    def delete(self, request: Request, session_id: str) -> Response:
        session = get_session(session_id)
        if session is None:
            return Response(
                {"error": "record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        session.delete()
        return Response({"ok": True, "id": str(session_id)})
