from unittest.mock import patch

from django.test import SimpleTestCase

from screening.services.metadata import _name_from_filename, extract_record_metadata


class NameFromFilenameTests(SimpleTestCase):
    def test_underscore_separated(self):
        self.assertEqual(_name_from_filename("Abhay_Yemekar.pdf"), "Abhay Yemekar")

    def test_cv_prefix_removed(self):
        self.assertEqual(_name_from_filename("CV_Chaing Sinta.pdf"), "Chaing Sinta")

    def test_resume_word_removed(self):
        self.assertEqual(_name_from_filename("my-resume.pdf"), "my")

    def test_dotted_filename(self):
        self.assertEqual(_name_from_filename("john.smith.docx"), "john smith")

    def test_empty_returns_unknown_candidate(self):
        self.assertEqual(_name_from_filename("_CV_.pdf"), "Unknown candidate")


class ExtractMetadataTests(SimpleTestCase):
    @patch("screening.services.metadata.chat", return_value='{"position": "Backend Engineer"}')
    def test_uses_filename_for_name_and_llm_for_position(self, mock_chat):
        metadata = extract_record_metadata(
            "resume text", "job description text", "Alex_Chen.pdf", "jd.txt"
        )
        self.assertEqual(metadata["candidate_name"], "Alex Chen")
        self.assertEqual(metadata["position"], "Backend Engineer")

    @patch("screening.services.metadata.chat", return_value="not json at all")
    def test_position_fallback_uses_first_jd_line(self, mock_chat):
        metadata = extract_record_metadata(
            "resume text",
            "Data Scientist with Python\n(2nd line)",
            "CV_Maria Doe.pdf",
            "jd.txt",
        )
        self.assertEqual(metadata["candidate_name"], "Maria Doe")
        self.assertEqual(metadata["position"], "Data Scientist with Python")

    @patch("screening.services.metadata.chat", side_effect=RuntimeError("llm down"))
    def test_llm_failure_falls_back_gracefully(self, mock_chat):
        metadata = extract_record_metadata(
            "resume text", "DevOps Engineer\nSome more", "Omar_P.md", "jd.txt"
        )
        self.assertEqual(metadata["candidate_name"], "Omar P")
        self.assertEqual(metadata["position"], "DevOps Engineer")