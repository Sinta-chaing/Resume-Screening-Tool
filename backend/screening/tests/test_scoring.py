from unittest.mock import patch

from django.test import SimpleTestCase

from screening.services.scoring import (
    EMBED_TEXT_LIMIT,
    _cached_embed,
    _cosine_similarity,
    compute_hybrid_score,
    embedding_similarity_score,
    requirement_match_score,
)


class CosineSimilarityTests(SimpleTestCase):
    def test_identical_vectors(self):
        self.assertAlmostEqual(_cosine_similarity([1, 2, 3], [1, 2, 3]), 1.0)

    def test_orthogonal_vectors(self):
        self.assertAlmostEqual(_cosine_similarity([1, 0], [0, 1]), 0.0)

    def test_zero_vector_returns_zero(self):
        self.assertEqual(_cosine_similarity([0, 0], [1, 1]), 0.0)

    def test_opposite_vectors_are_negative(self):
        self.assertAlmostEqual(_cosine_similarity([1, 0], [-1, 0]), -1.0)


class EmbeddingSimilarityTests(SimpleTestCase):
    def setUp(self):
        _cached_embed.cache_clear()

    @patch("screening.services.scoring.embed", return_value=[1.0, 0.0, 0.0])
    def test_identical_embeddings_give_100(self, mock_embed):
        score = embedding_similarity_score("resume alpha", "jd alpha")
        self.assertEqual(score, 100.0)
        self.assertEqual(mock_embed.call_count, 2)

    @patch("screening.services.scoring.embed", side_effect=[[1.0, 0.0], [0.0, 1.0]])
    def test_orthogonal_embeddings_give_zero(self, mock_embed):
        score = embedding_similarity_score("resume beta", "jd gamma")
        self.assertEqual(score, 0.0)

    @patch("screening.services.scoring.embed", return_value=[1.0, 1.0])
    def test_inputs_are_truncated_to_embed_limit(self, mock_embed):
        embedding_similarity_score("r" * 5000, "j" * 5000)
        for call in mock_embed.call_args_list:
            self.assertLessEqual(len(call.args[0]), EMBED_TEXT_LIMIT)


class RequirementMatchTests(SimpleTestCase):
    def setUp(self):
        _cached_embed.cache_clear()

    def test_resume_text_matches_skills(self):
        resume = "Python developer with 5 years of React experience."
        jd = "Skills:\n- Python\n- React"
        result = requirement_match_score(resume, jd, resume_embeddings=[[0.5, 0.5]])
        self.assertEqual(result["score"], 100.0)
        self.assertIn("Python", result["matchedSkills"])
        self.assertIn("React", result["matchedSkills"])

    @patch("screening.services.scoring.embed")
    def test_phrase_match_skips_embedding_calls(self, mock_embed):
        resume = "Python engineer"
        jd = "Requirements:\n- Python"
        requirement_match_score(resume, jd, resume_embeddings=[[0.5]])
        mock_embed.assert_not_called()

    @patch("screening.services.scoring.embed", return_value=[1.0, 0.0])
    def test_alias_match_counts(self, mock_embed):
        resume = "Built data pipelines on EC2 and S3 for 4 years."
        jd = "Requirements:\n- AWS"
        result = requirement_match_score(resume, jd)
        self.assertEqual(result["score"], 100.0)
        self.assertIn("aws", result["matchedSkills"])

    @patch("screening.services.scoring.embed", return_value=[0.0, 1.0])
    def test_missing_skill_is_unmatched(self, mock_embed):
        resume = "Python backend developer."
        jd = "Requirements:\n- Python\n- Kubernetes"
        result = requirement_match_score(resume, jd, resume_embeddings=[[1.0, 0.0]])
        self.assertEqual(result["score"], 50.0)
        self.assertIn("Python", result["matchedSkills"])
        self.assertIn("Kubernetes", result["missingSkills"])

    def test_empty_jd_returns_zero_score(self):
        result = requirement_match_score("Python", "")
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["jdSkillCount"], 0)


class HybridScoreTests(SimpleTestCase):
    @patch("screening.services.scoring.embed", return_value=[1.0, 0.0])
    def test_compute_hybrid_score_shape(self, mock_embed):
        resume = "Python developer with React experience"
        jd = "Skills:\n- Python\n- React"
        result = compute_hybrid_score(resume, jd, resume_embeddings=[[1.0, 0.0]])
        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

        breakdown = result["scoreBreakdown"]
        for key in ("skillOverlap", "embeddingSimilarity", "skillWeight",
                    "embeddingWeight", "matchedSkills", "missingSkills", "jdSkillCount"):
            self.assertIn(key, breakdown)