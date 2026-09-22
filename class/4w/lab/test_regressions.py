"""Regression cases found during the handout's integration review."""
import unittest
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from email.message import Message

import pipeline


class RegressionTests(unittest.TestCase):
    def test_article_query_identity_is_preserved_without_token(self):
        url = 'https://example.org/article?id=42&access_token=SECRET#section'
        self.assertEqual(pipeline.safe_url(url), 'https://example.org/article?id=42')

    def test_http_status_survives_without_secret_error_text(self):
        def denied(request, timeout):
            raise HTTPError('https://example.invalid/?token=DO_NOT_SAVE',
                            401, 'DO_NOT_SAVE', Message(), None)

        def fetch(*args):
            return pipeline.http_get('https://api.x.com/test', {}, {}, opener=denied)

        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            config = {'queries': [{'id': 'q', 'platform': 'x', 'query': 'Hermes'}]}
            self.assertEqual(pipeline.run(config, data, 'live', fetch), 1)
            health = pipeline.report(data)['health']
            self.assertEqual(health[0]['reason'], 'http_401')
            self.assertNotIn('DO_NOT_SAVE', str(health))

    def test_threads_final_cursor_without_next_stops(self):
        # Graph cursors may describe the current page even with no next page.
        payload = {'data': [], 'paging': {'cursors': {'after': 'last-cursor'}}}
        live = pipeline.Live({'THREADS_ACCESS_TOKEN': 'fixture-only-token'},
                             lambda *args: payload)
        self.assertIsNone(live('threads', 'Hermes', None)['next_token'])


if __name__ == '__main__':
    unittest.main()
