import uuid
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from screening.models import AnalysisSession, ResumeChunk
from screening.services.vector_store import add_chunk, create_session, search_chunks

EMB = [0.1] * 1024


def pdf_file(name="Alex_Chen-CV.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 fake pdf bytes", content_type="application/pdf")


def text_file(name="jd.txt"):
    return SimpleUploadedFile(name, b"job description", content_type="text/plain")


class HealthTests(TestCase):
    def test_health_endpoint(self):
        resp = self.client.get(reverse("health"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["embeddingModel"], settings.EMBEDDING_MODEL)

    def test_unknown_route_is_404(self):
        resp = self.client.get("/api/nope")
        self.assertEqual(resp.status_code, 404)


class AnalyzeTests(TestCase):
    @patch(
        "screening.views.extract_record_metadata",
        return_value={"candidate_name": "Alex Chen", "position": "AI Engineer"},
    )
    @patch("screening.views.summarize_resume", return_value="A solid Python candidate.")
    @patch(
        "screening.views.evaluate_resume",
        return_value={
            "score": 80,
            "scoreBreakdown": {
                "skillOverlap": 80,
                "embeddingSimilarity": 80,
                "skillWeight": 0.7,
                "embeddingWeight": 0.3,
                "matchedSkills": ["Python"],
                "missingSkills": [],
                "jdSkillCount": 1,
                "semanticThreshold": 0.62,
            },
            "strengths": ["Strong Python"],
            "gaps": [],
            "suggestions": [],
        },
    )
    @patch("screening.views.embed", return_value=EMB)
    @patch(
        "screening.views.extract_text_from_file",
        side_effect=["Python developer with machine learning experience", "Python engineer role"],
    )
    def test_analyze_creates_session_and_chunks(self, *mocks):
        resp = self.client.post(reverse("analyze"), {"resume": pdf_file(), "jd": text_file()})
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["candidateName"], "Alex Chen")
        self.assertEqual(data["position"], "AI Engineer")
        self.assertEqual(data["chunks"], 1)

        session = AnalysisSession.objects.get(pk=data["sessionId"])
        chunks = ResumeChunk.objects.filter(session=session)
        self.assertEqual(chunks.count(), 1)
        self.assertEqual(len(chunks.first().embedding), 1024)

    def test_analyze_requires_files(self):
        resp = self.client.post(reverse("analyze"), {})
        self.assertEqual(resp.status_code, 400)


class ChatTests(TestCase):
    def setUp(self):
        self.session = create_session(
            "resume.pdf",
            "jd.txt",
            {"score": 85, "scoreBreakdown": {"matchedSkills": ["Python"]}},
            "summary",
            1,
            "Alex Chen",
            "AI Engineer",
        )
        add_chunk(self.session, "resume-0", "Python expert with 4 years", EMB)

    @patch("screening.services.chat_context.chat", return_value="Yes, strong Python skills.")
    @patch("screening.services.chat_context.embed", return_value=EMB)
    def test_chat_answers_with_sources(self, mock_embed, mock_chat):
        resp = self.client.post(
            reverse("chat"),
            {"question": "Does the candidate know Python?", "sessionId": str(self.session.id)},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIn("answer", data)
        self.assertIn("sources", data)

    def test_chat_requires_question(self):
        resp = self.client.post(
            reverse("chat"),
            {"sessionId": str(self.session.id)},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_chat_rejects_unknown_session(self):
        resp = self.client.post(
            reverse("chat"),
            {"question": "hi", "sessionId": str(uuid.uuid4())},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class RecordsTests(TestCase):
    def setUp(self):
        self.session = create_session(
            "resume.pdf", "jd.txt", {"score": 90}, "summary", 1, "Alex Chen", "AI Engineer"
        )
        add_chunk(self.session, "resume-0", "Python expert", EMB)

    def test_list_records(self):
        resp = self.client.get(reverse("records-list"))
        self.assertEqual(resp.status_code, 200)
        records = resp.json()["records"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["candidateName"], "Alex Chen")
        self.assertEqual(records[0]["score"], 90)

    def test_list_records_sorts_desc(self):
        create_session("b.pdf", "jd.txt", {"score": 10}, "summary", 0, "B Candidate", "Dev")
        resp = self.client.get(f"{reverse('records-list')}?order=desc")
        records = resp.json()["records"]
        self.assertEqual(len(records), 2)
        self.assertGreaterEqual(records[0]["score"], records[1]["score"])

    def test_record_detail(self):
        resp = self.client.get(reverse("record-detail", args=[self.session.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["sessionId"], str(self.session.id))
        self.assertEqual(data["candidateName"], "Alex Chen")

    def test_record_detail_404(self):
        resp = self.client.get(reverse("record-detail", args=[uuid.uuid4()]))
        self.assertEqual(resp.status_code, 404)

    def test_delete_record(self):
        resp = self.client.delete(reverse("record-detail", args=[self.session.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AnalysisSession.objects.filter(pk=self.session.id).exists())


class VectorStoreTests(TestCase):
    def test_search_chunks_returns_top_match(self):
        session = create_session("resume.pdf", "jd.txt", {}, "summary", 2, "Candidate", "Role")
        add_chunk(session, "resume-0", "Python and Django", EMB)
        add_chunk(session, "resume-1", "Go and Rust", EMB)

        results = search_chunks(str(session.id), EMB, k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("resume-", results[0]["id"])
        self.assertGreater(results[0]["score"], 0.9)