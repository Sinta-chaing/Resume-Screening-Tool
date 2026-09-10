from unittest.mock import patch

from django.test import SimpleTestCase

from screening.services import ollama


class FakeResponse:
    def __init__(self, ok=True, payload=None, text=""):
        self.ok = ok
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


class EmbedTests(SimpleTestCase):
    @patch("requests.post")
    def test_embed_returns_first_embedding(self, mock_post):
        mock_post.return_value = FakeResponse(payload={"embeddings": [[0.1, 0.2, 0.3], [9.9]]})
        result = ollama.embed("some resume text")
        self.assertEqual(result, [0.1, 0.2, 0.3])

        request_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(request_payload["model"], ollama.settings.EMBEDDING_MODEL)
        self.assertEqual(request_payload["input"], "some resume text")
        self.assertTrue(request_payload["truncate"])

    @patch("requests.post")
    def test_embed_raises_on_http_error(self, mock_post):
        mock_post.return_value = FakeResponse(ok=False, text="boom")
        with self.assertRaises(RuntimeError):
            ollama.embed("some text")

    @patch("requests.post")
    def test_embed_raises_on_empty_embeddings(self, mock_post):
        mock_post.return_value = FakeResponse(payload={"embeddings": []})
        with self.assertRaises(RuntimeError):
            ollama.embed("some text")


class ChatTests(SimpleTestCase):
    @patch("requests.post")
    def test_chat_returns_response_text(self, mock_post):
        mock_post.return_value = FakeResponse(payload={"response": "hello there"})
        messages = [{"role": "user", "content": "hi"}]
        self.assertEqual(ollama.chat(messages), "hello there")

    @patch("requests.post")
    def test_chat_raises_on_http_error(self, mock_post):
        mock_post.return_value = FakeResponse(ok=False, text="nope")
        with self.assertRaises(RuntimeError):
            ollama.chat([{"role": "user", "content": "hi"}])