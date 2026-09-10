from django.test import SimpleTestCase

from screening.services.chunking import MAX_CHUNKS, chunk_text


class ChunkTextTests(SimpleTestCase):
    def test_empty_string_returns_empty_list(self):
        self.assertEqual(chunk_text(""), [])

    def test_whitespace_only_returns_empty_list(self):
        self.assertEqual(chunk_text("   \n\t  "), [])

    def test_invalid_max_chars_raises(self):
        for bad in (0, -1, 1.5, "800"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    chunk_text("some text", max_chars=bad)

    def test_small_text_is_single_chunk(self):
        text = "word " * 50
        chunks = chunk_text(text)
        self.assertEqual(chunks, [text.strip()])

    def test_large_text_splits_into_fixed_size_chunks(self):
        text = "word " * 1000
        chunks = chunk_text(text, max_chars=800)
        self.assertEqual(len(chunks), 7)
        self.assertTrue(all(len(c) <= 800 for c in chunks))
        self.assertEqual("".join(chunks), text.replace("\r", "").strip())

    def test_crlf_is_normalized(self):
        chunks = chunk_text("line1\r\nline2\r\nline3", max_chars=10)
        self.assertNotIn("\r", "".join(chunks))

    def test_too_large_document_raises(self):
        with self.assertRaises(ValueError):
            chunk_text("a" * (MAX_CHUNKS * 800 + 1))