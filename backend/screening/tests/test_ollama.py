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
        self.assertEqual(request_payload["input"], ["some resume text"])
        self.assertTrue(request_payload["truncate"])
        self.assertEqual(request_payload["keep_alive"], ollama.settings.OLLAMA_KEEP_ALIVE)

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


class EmbedManyTests(SimpleTestCase):
    @patch("requests.post")
    def test_embed_many_sends_batch_and_returns_in_order(self, mock_post):
        mock_post.return_value = FakeResponse(payload={"embeddings": [[1.0, 2.0], [3.0, 4.0]]})
        result = ollama.embed_many(["first chunk", "second chunk"])
        self.assertEqual(result, [[1.0, 2.0], [3.0, 4.0]])

        request_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(request_payload["input"], ["first chunk", "second chunk"])
        self.assertEqual(request_payload["keep_alive"], ollama.settings.OLLAMA_KEEP_ALIVE)

    @patch("requests.post")
    def test_embed_many_raises_on_http_error(self, mock_post):
        mock_post.return_value = FakeResponse(ok=False, text="boom")
        with self.assertRaises(RuntimeError):
            ollama.embed_many(["a"])

    @patch("requests.post")
    def test_embed_many_sub_batches_large_inputs(self, mock_post):
        # More inputs than EMBED_BATCH_SIZE must be split into several calls
        # (each returning quickly) while preserving the original order.
        batch = ollama.EMBED_BATCH_SIZE
        texts = [f"chunk {i}" for i in range(batch * 3 + 1)]
        mock_post.side_effect = [
            FakeResponse(
                payload={
                    "embeddings": [[float(i)] for i in range(batch * n, batch * (n + 1))]
                }
            )
            for n in range(3)
        ] + [FakeResponse(payload={"embeddings": [[float(batch * 3)]]})]

        result = ollama.embed_many(texts)

        self.assertEqual(mock_post.call_count, 4)
        sent = [call.kwargs["json"]["input"] for call in mock_post.call_args_list]
        self.assertEqual(len(sent[0]), batch)
        self.assertEqual(len(sent[-1]), 1)
        flattened = [item for batch_inputs in sent for item in batch_inputs]
        self.assertEqual(flattened, texts)
        self.assertEqual(result, [[float(i)] for i in range(batch * 3 + 1)])

    @patch("requests.post")
    def test_embed_many_empty_returns_empty_without_calls(self, mock_post):
        self.assertEqual(ollama.embed_many([]), [])
        mock_post.assert_not_called()


class ChatTests(SimpleTestCase):
    @patch("requests.post")
    def test_chat_returns_response_text(self, mock_post):
        mock_post.return_value = FakeResponse(payload={"response": "hello there"})
        messages = [{"role": "user", "content": "hi"}]
        self.assertEqual(ollama.chat(messages), "hello there")

        request_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(request_payload["keep_alive"], ollama.settings.OLLAMA_KEEP_ALIVE)
        self.assertEqual(request_payload["options"]["num_predict"], 1024)

    @patch("requests.post")
    def test_chat_raises_on_http_error(self, mock_post):
        mock_post.return_value = FakeResponse(ok=False, text="nope")
        with self.assertRaises(RuntimeError):
            ollama.chat([{"role": "user", "content": "hi"}])