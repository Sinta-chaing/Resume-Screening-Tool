from django.conf import settings
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, OpenApiResponse, extend_schema, inline_serializer

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


def _error_response(msg: str) -> OpenApiResponse:
    return OpenApiResponse(description=msg)


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
    @extend_schema(
        tags=["Health"],
        summary="Service health",
        description="Returns service status and the Ollama models in use.",
        responses={
            200: inline_serializer(
                "HealthResponse",
                fields={
                    "ok": serializers.BooleanField(),
                    "useOllama": serializers.CharField(),
                    "ollamaBaseUrl": serializers.CharField(),
                    "embeddingModel": serializers.CharField(),
                    "chatModel": serializers.CharField(),
                },
            )
        },
    )
    def get(self, request: Request) -> Response:
        return Response({
            "ok": True,
            "useOllama": settings.USE_OLLAMA,
            "ollamaBaseUrl": settings.OLLAMA_BASE_URL,
            "embeddingModel": settings.EMBEDDING_MODEL,
            "chatModel": settings.CHAT_MODEL,
        })


class AnalyzeView(APIView):
    @extend_schema(
        tags=["Screening"],
        summary="Analyze a resume against a job description",
        description=(
            "Upload the candidate's resume (PDF) and a job description (PDF or text). "
            "Analysis starts in the background; returns immediately with a sessionId. "
            "Poll GET /api/records/{sessionId} until status is 'completed'."
        ),
        request=inline_serializer(
            "AnalyzeRequest",
            fields={
                "resume": serializers.FileField(required=True, write_only=True),
                "jd": serializers.FileField(required=True, write_only=True),
            },
        ),
        responses={
            202: inline_serializer(
                "AnalyzeResponse",
                fields={
                    "ok": serializers.BooleanField(),
                    "sessionId": serializers.UUIDField(),
                    "status": serializers.CharField(),
                },
            ),
            400: _error_response("Both resume and jd files are required, or a file has no readable text."),
            500: _error_response("Internal error while extracting text or queuing the job."),
        },
    )
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
    @extend_schema(
        tags=["Screening"],
        summary="Ask a RAG question about an analyzed resume",
        description=(
            "Requires a completed analysis session. The answer is grounded in the resume's "
            "embedded chunks."
        ),
        request=inline_serializer(
            "ChatRequest",
            fields={
                "question": serializers.CharField(required=True),
                "sessionId": serializers.UUIDField(required=True),
            },
        ),
        responses={
            200: inline_serializer(
                "ChatResponse",
                fields={
                    "ok": serializers.BooleanField(),
                    "answer": serializers.CharField(),
                    "sources": serializers.ListField(
                        child=inline_serializer(
                            "Source",
                            fields={
                                "sessionId": serializers.UUIDField(),
                                "chunkKey": serializers.CharField(),
                                "chunkIndex": serializers.IntegerField(),
                                "text": serializers.CharField(),
                            },
                        )
                    ),
                },
            ),
            400: _error_response("Missing question/sessionId, or unknown sessionId."),
            500: _error_response("Internal error while answering."),
        },
    )
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
    @extend_schema(
        tags=["Screening"],
        operation_id="list_records",
        summary="List screened records",
        description="Returns all analysis sessions ordered by match score.",
        parameters=[
            OpenApiParameter(
                "order",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["asc", "desc"],
                description="Sort direction by match score.",
                default="asc",
            ),
        ],
        responses={
            200: inline_serializer(
                "RecordsListResponse",
                fields={
                    "ok": serializers.BooleanField(),
                    "records": serializers.ListField(
                        child=inline_serializer(
                            "RecordSummary",
                            fields={
                                "id": serializers.UUIDField(),
                                "candidateName": serializers.CharField(),
                                "position": serializers.CharField(),
                                "score": serializers.IntegerField(),
                                "status": serializers.CharField(),
                                "createdAt": serializers.CharField(),
                                "resumeFilename": serializers.CharField(),
                                "jdFilename": serializers.CharField(),
                            },
                        )
                    ),
                },
            )
        },
    )
    def get(self, request: Request) -> Response:
        order = request.query_params.get("order", "asc").lower()
        ascending = order != "desc"

        sessions = AnalysisSession.objects.all()
        records = [_serialize_record_summary(session) for session in sessions]
        records.sort(key=lambda item: item["score"], reverse=not ascending)

        return Response({"ok": True, "records": records})


class RecordDetailView(APIView):
    @extend_schema(
        tags=["Screening"],
        operation_id="retrieve_record",
        summary="Get a single analysis result",
        parameters=[
            OpenApiParameter("session_id", OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
        responses={
            200: inline_serializer(
                "RecordDetailResponse",
                fields={
                    "ok": serializers.BooleanField(),
                    "sessionId": serializers.UUIDField(),
                    "candidateName": serializers.CharField(),
                    "position": serializers.CharField(),
                    "chunks": serializers.IntegerField(),
                    "evaluation": serializers.JSONField(),
                    "resumeSummary": serializers.CharField(),
                    "status": serializers.CharField(),
                    "error": serializers.CharField(),
                    "createdAt": serializers.CharField(),
                    "resumeFilename": serializers.CharField(),
                    "jdFilename": serializers.CharField(),
                },
            ),
            404: _error_response("Record not found."),
        },
    )
    def get(self, request: Request, session_id: str) -> Response:
        session = get_session(session_id)
        if session is None:
            return Response(
                {"error": "record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(_serialize_record_detail(session))

    @extend_schema(
        tags=["Screening"],
        operation_id="delete_record",
        summary="Delete an analysis result",
        parameters=[
            OpenApiParameter("session_id", OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
        responses={
            200: inline_serializer(
                "DeleteResponse",
                fields={
                    "ok": serializers.BooleanField(),
                    "id": serializers.UUIDField(),
                },
            ),
            404: _error_response("Record not found."),
        },
    )
    def delete(self, request: Request, session_id: str) -> Response:
        session = get_session(session_id)
        if session is None:
            return Response(
                {"error": "record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        session.delete()
        return Response({"ok": True, "id": str(session_id)})
