import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


class PipelineTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('pipeline')
        self.assertIsNotNone(spec, 'pipeline implementation must exist')
        import pipeline
        self.p = pipeline
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / 'data'
        self.config = {'queries': [
            {'id': 'a', 'platform': 'x', 'query': 'Hermes'},
            {'id': 'b', 'platform': 'x', 'query': 'OMH'}]}

    def test_demo_dedup_and_multiple_matching_keywords(self):
        for _ in range(2):
            self.assertEqual(self.p.run(self.config, self.data, 'demo'), 0)
        report = self.p.report(self.data)
        self.assertEqual(report['posts'], 1)
        self.assertEqual(report['matches'], 2)
        self.assertEqual(report['runs'], 2)
        self.assertEqual(report['failed_runs'], 0)
        rows = [json.loads(line) for line in Path(report['export']).read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['mode'], 'demo')
        self.assertTrue(Path(rows[0]['payload_path']).is_file())
        self.assertTrue(rows[0]['created_at'].endswith('Z'))
        self.assertTrue(rows[0]['collected_at'].endswith('Z'))
        self.assertIn('SYNTHETIC', rows[0]['text'])
        payloads = [json.loads(p.read_text()) for p in self.data.glob('*.json') if p.name != 'mode.json']
        self.assertEqual(len(payloads), 4)
        self.assertTrue(all(p.get('run_id') and p.get('collected_at') and p.get('query_id') for p in payloads))
        self.assertTrue(all('next_token' not in p for p in payloads))
        self.assertEqual((self.data / 'pipeline.sqlite3').stat().st_mode & 0o777, 0o600)

    def test_live_snapshot_pagination_health_and_isolation(self):
        calls = []
        def fetch(platform, query, token):
            calls.append((query, token))
            if query == 'empty':
                return {'posts': [], 'next_token': None}
            if query == 'bad':
                raise RuntimeError('secret error body must not persist')
            return {**self.p.demo_page(platform, query, token), 'next_token': 'cursor123'}
        self.config['queries'].extend([
            {'id': 'empty', 'platform': 'reddit', 'query': 'empty'},
            {'id': 'bad', 'platform': 'threads', 'query': 'bad'}])
        self.assertEqual(self.p.run(self.config, self.data, 'live', fetch), 1)
        report = self.p.report(self.data)
        self.assertEqual([row['status'] for row in report['health']],
                         ['partial', 'partial', 'ok', 'error'])
        self.assertEqual([row['fetched'] for row in report['health']], [2, 2, 0, 0])
        self.assertEqual(report['failed_runs'], 1)
        self.assertIn(('Hermes', 'cursor123'), calls)
        self.assertNotIn('secret error body', json.dumps(report))
        with self.assertRaises(ValueError):
            self.p.run(self.config, self.data, 'demo')
        other = Path(self.temp.name) / 'existing'
        other.mkdir()
        (other / 'mine.txt').write_text('untouched')
        with self.assertRaises(ValueError):
            self.p.run(self.config, other, 'demo')
        self.assertEqual((other / 'mine.txt').read_text(), 'untouched')

    def test_live_adapters_use_fixed_endpoints_and_safe_cursors(self):
        self.assertTrue(hasattr(self.p, 'Live'), 'live adapters required')
        fixtures = {
            'x': {'data': [{'id': '1', 'text': 'x', 'created_at': '2026-01-01T00:00:00Z', 'public_metrics': {'like_count': 2}}], 'meta': {'next_token': 'abc'}},
            'threads': {'data': [{'id': '2', 'text': 't', 'timestamp': '2026-01-01T09:00:00+0900', 'permalink': 'https://www.threads.net/@a/post/b'}], 'paging': {'next': 'https://evil.invalid/?access_token=SECRET', 'cursors': {'after': 'def'}}},
            'reddit': {'data': {'children': [{'data': {'id': '3', 'title': 'r', 'created_utc': 1767225600, 'permalink': '/r/test/comments/3/title/', 'score': 3, 'url': 'https://example.org/'}}], 'after': 't3_abc'}}}
        env = {'X_BEARER_TOKEN': 'SECRET', 'THREADS_ACCESS_TOKEN': 'SECRET', 'REDDIT_ACCESS_TOKEN': 'SECRET', 'REDDIT_USER_AGENT': 'lab/1.0'}
        seen = []
        for platform, raw in fixtures.items():
            def transport(url, params, headers):
                seen.append((url, params, headers))
                return raw
            page = self.p.Live(env, transport)(platform, 'Hermes', 'cursor')
            self.assertEqual(len(page['posts']), 1)
            self.assertNotIn('SECRET', json.dumps(page))
            self.assertTrue(page['posts'][0]['created_at'].endswith('Z'))
        self.assertEqual(seen[0][0], 'https://api.x.com/2/tweets/search/recent')
        self.assertEqual(seen[0][1]['next_token'], 'cursor')
        self.assertEqual(seen[1][1]['after'], 'cursor')
        self.assertEqual(seen[1][1]['search_type'], 'RECENT')
        self.assertEqual(seen[2][1]['raw_json'], 1)
        with self.assertRaises(ValueError):
            self.p.Live(env, transport)('threads', 'q', 'https://evil.invalid')

    def test_http_retries_are_bounded_and_errors_sanitized(self):
        self.assertTrue(hasattr(self.p, 'http_get'), 'bounded transport required')
        from urllib.error import HTTPError
        attempts, delays = [], []
        def failing(request, timeout):
            attempts.append(request)
            raise HTTPError('https://secret.invalid', 429, 'SECRET', {}, None)
        with self.assertRaisesRegex(ValueError, '^request_failed$'):
            self.p.http_get('https://api.x.com/test', {}, {}, opener=failing, sleep=delays.append)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(delays, [1, 2])

    def test_cli_demo_report_and_invalid_config(self):
        import subprocess
        import sys
        script = str(Path(__file__).with_name('pipeline.py'))
        config = Path(self.temp.name) / 'config.json'
        config.write_text(json.dumps(self.config))
        args = [sys.executable, '-B', script, '--data-dir', str(self.data)]
        result = subprocess.run(args + ['--config', str(config), '--mode', 'demo'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip(), 'CLI must run and summarize')
        result = subprocess.run(args + ['--report'], capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['posts'], 1)
        with self.assertRaises(ValueError):
            self.p.run({'queries': [], 'max_pages': 0}, self.data, 'demo')


if __name__ == '__main__':
    unittest.main(verbosity=2)
