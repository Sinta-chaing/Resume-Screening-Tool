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
    def test_uses_filename_for_name_and_first_jd_line_for_position(self):
        metadata = extract_record_metadata(
            "resume text",
            "Backend Engineer\n(2nd line)",
            "Alex_Chen.pdf",
            "jd.txt",
        )
        self.assertEqual(metadata["candidate_name"], "Alex Chen")
        self.assertEqual(metadata["position"], "Backend Engineer")

    def test_position_skips_empty_first_lines(self):
        metadata = extract_record_metadata(
            "resume text",
            "\n\nData Scientist with Python\n(2nd line)",
            "CV_Maria Doe.pdf",
            "jd.txt",
        )
        self.assertEqual(metadata["candidate_name"], "Maria Doe")
        self.assertEqual(metadata["position"], "Data Scientist with Python")

    def test_position_falls_back_to_filename(self):
        metadata = extract_record_metadata(
            "resume text", "", "Omar_P.md", "DevOps_Engineer_job.md"
        )
        self.assertEqual(metadata["candidate_name"], "Omar P")
        self.assertEqual(metadata["position"], "DevOps Engineer job")