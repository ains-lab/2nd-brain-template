"""Incremental storage contract; synthetic local fixtures, never live services."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import pipeline


class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / 'data'
        self.config = {'queries': [
            {'id': 'a', 'platform': 'x', 'query': 'Hermes'},
            {'id': 'b', 'platform': 'x', 'query': 'OMH'}]}

    def rows(self, sql, params=()):
        with sqlite3.connect(self.data / 'pipeline.sqlite3') as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute(sql, params)]

    def test_same_run_keywords_share_version_keep_observations(self):
        self.assertEqual(pipeline.run(self.config, self.data, 'demo'), 0)
        tables = {row['name'] for row in self.rows('SELECT name FROM sqlite_master')}
        self.assertIn('post_versions', tables, 'incremental content versions required')
        versions = self.rows('SELECT * FROM post_versions')
        observations = self.rows('SELECT * FROM observations ORDER BY query_id')
        self.assertEqual(len(versions), 1)
        self.assertEqual(len(observations), 2)
        self.assertEqual([row['query_id'] for row in observations], ['a', 'b'])
        self.assertEqual({row['version_id'] for row in observations}, {versions[0]['version_id']})
        self.assertEqual(len({row['run_id'] for row in observations}), 1)
        content = {'platform': 'x', **pipeline.demo_page('x', '', None)['posts'][0]}
        content.pop('metrics')
        expected = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False,
                                             separators=(',', ':')).encode('utf-8')).hexdigest()
        self.assertEqual(versions[0]['version_id'], expected)
        self.assertEqual(versions[0]['content_hash'], expected)
        for observation in observations:
            payload = json.loads(Path(observation['payload_path']).read_text())
            self.assertEqual(observation['run_id'], payload['run_id'])
            self.assertEqual(observation['observed_at'], payload['collected_at'])
            self.assertEqual(json.loads(observation['metrics_json']), {})
        self.assertEqual(versions[0]['first_collected_at'], observations[0]['observed_at'])
        self.assertEqual(len(self.rows('SELECT * FROM posts')), 1)
        self.assertEqual(len(self.rows('SELECT * FROM matches')), 2)

    def test_unchanged_repeat_reports_new_observations_not_versions(self):
        self.assertEqual(pipeline.run(self.config, self.data, 'demo'), 0)
        originals = self.rows('SELECT * FROM post_versions')
        self.assertEqual(pipeline.run(self.config, self.data, 'demo'), 0)
        report = pipeline.report(self.data)
        self.assertIn('versions', report, 'report must count incremental versions')
        self.assertEqual((report['versions'], report['observations']), (1, 4))
        self.assertEqual((report['posts'], report['matches'], report['runs']), (1, 2, 2))
        self.assertEqual(self.rows('SELECT * FROM post_versions'), originals)
        self.assertEqual(len({row['run_id'] for row in self.rows('SELECT * FROM observations')}), 2)
        exported = [json.loads(line) for line in Path(report['export']).read_text().splitlines()]
        self.assertEqual(len(exported), 2)
        self.assertTrue(all('metrics' in row and 'external_urls' in row for row in exported))

    def test_query_meaning_locked_even_when_first_run_is_empty(self):
        empty = lambda *args: {'posts': [], 'next_token': None}
        self.assertEqual(pipeline.run(self.config, self.data, 'demo', empty), 0)
        for change in ({'query': 'new meaning'}, {'platform': 'reddit'}):
            with self.subTest(change=change):
                altered = {'queries': [{**self.config['queries'][0], **change}]}
                calls = []
                def must_not_fetch(*args):
                    calls.append(args)
                    return empty()
                before = self.rows('SELECT * FROM runs')
                files = set(self.data.iterdir())
                with self.assertRaisesRegex(ValueError, '^query_id conflict$'):
                    pipeline.run(altered, self.data, 'demo', must_not_fetch)
                self.assertEqual(calls, [])
                self.assertEqual(self.rows('SELECT * FROM runs'), before)
                self.assertEqual(set(self.data.iterdir()), files)
        self.assertEqual(self.rows('SELECT * FROM query_definitions ORDER BY query_id'), [
            {'query_id': q['id'], 'platform': q['platform'], 'query': q['query']}
            for q in self.config['queries']])

    def test_metrics_only_change_is_visible_in_analysis_not_a_version(self):
        self.config['queries'] = self.config['queries'][:1]
        def with_metrics(likes):
            def fetch(*args):
                page = pipeline.demo_page(*args)
                page['posts'][0]['metrics'] = {'like_count': likes}
                return page
            return fetch
        self.assertEqual(pipeline.run(self.config, self.data, 'demo', with_metrics(1)), 0)
        originals = self.rows('SELECT * FROM posts')
        versions = self.rows('SELECT * FROM post_versions')
        self.assertEqual(pipeline.run(self.config, self.data, 'demo', with_metrics(9)), 0)
        self.assertEqual(self.rows('SELECT * FROM post_versions'), versions)
        self.assertEqual(self.rows('SELECT * FROM posts'), originals)
        views = {row['name'] for row in self.rows("SELECT name FROM sqlite_master WHERE type='view'")}
        self.assertIn('observation_facts', views, 'analysis must expose every observation')
        facts = self.rows('SELECT * FROM observation_facts ORDER BY observation_id')
        self.assertEqual([json.loads(row['metrics_json'])['like_count'] for row in facts], [1, 9])
        for fact in facts:
            self.assertEqual(fact['query'], 'Hermes')
            for field in ('created_at', 'source_url', 'text', 'external_urls_json', 'content_hash'):
                self.assertEqual(fact[field], versions[0][field])
            observation = self.rows('SELECT * FROM observations WHERE observation_id=?',
                                    (fact['observation_id'],))[0]
            self.assertEqual({key: fact[key] for key in observation}, observation)

    def test_text_revision_retains_first_post_and_adds_version(self):
        # Supplemental coverage of the first storage slice, not a new RED claim.
        self.config['queries'] = self.config['queries'][:1]
        self.assertEqual(pipeline.run(self.config, self.data, 'demo'), 0)
        originals = self.rows('SELECT * FROM posts')
        original_version = self.rows('SELECT * FROM post_versions')[0]
        def changed(*args):
            page = pipeline.demo_page(*args)
            page['posts'][0]['text'] = '개정된 본문'
            return page
        self.assertEqual(pipeline.run(self.config, self.data, 'demo', changed), 0)
        versions = self.rows('SELECT * FROM post_versions')
        self.assertEqual(len(versions), 2)
        self.assertIn(original_version, versions)
        self.assertEqual(self.rows('SELECT * FROM posts'), originals)
        self.assertEqual([row['text'] for row in self.rows(
            'SELECT * FROM observation_facts ORDER BY observation_id')],
            [originals[0]['text'], '개정된 본문'])
        self.assertEqual(pipeline.run(self.config, self.data, 'demo'), 0)
        self.assertEqual(self.rows('SELECT * FROM post_versions'), versions)
        self.assertEqual(pipeline.report(self.data)['observations'], 3)

    def legacy(self):
        self.data.mkdir()
        (self.data / 'mode.json').write_text(json.dumps({'mode': 'demo'}))
        with sqlite3.connect(self.data / 'pipeline.sqlite3') as connection:
            connection.executescript('''
                CREATE TABLE posts (
                  platform TEXT, id TEXT, created_at TEXT, collected_at TEXT,
                  source_url TEXT, text TEXT, metrics_json TEXT, external_urls_json TEXT,
                  PRIMARY KEY(platform,id));
                CREATE TABLE matches (
                  query_id TEXT, platform TEXT, id TEXT, query TEXT, payload_path TEXT,
                  UNIQUE(query_id,platform,id));
                CREATE TABLE runs (id TEXT PRIMARY KEY, started_at TEXT, status TEXT);
                CREATE TABLE health (
                  run_id TEXT, query_id TEXT, platform TEXT, status TEXT, fetched INTEGER, reason TEXT);
                ''')
            connection.execute('INSERT INTO posts VALUES (?,?,?,?,?,?,?,?)', (
                'x', 'synthetic-1', '2026-01-01T00:00:00Z', '2026-01-02T03:04:05Z',
                'https://example.invalid/x/synthetic-1', 'legacy original', '{"likes": 2}', '[]'))
            connection.execute('INSERT INTO matches VALUES (?,?,?,?,?)', (
                'a', 'x', 'synthetic-1', 'Hermes', str(self.data / 'legacy-payload.json')))
            connection.execute('INSERT INTO runs VALUES (?,?,?)',
                               ('legacy-run', '2026-01-02T03:04:00Z', 'ok'))

    def test_legacy_report_migrates_original_once_without_inventing_provenance(self):
        self.legacy()
        originals = self.rows('SELECT * FROM posts')
        matches = self.rows('SELECT * FROM matches')
        report = pipeline.report(self.data)
        self.assertEqual(report['versions'], 1, 'legacy post must acquire an immutable version')
        self.assertEqual(report['observations'], 0, 'missing payload cannot establish a run observation')
        version = self.rows('SELECT * FROM post_versions')[0]
        self.assertEqual(version['text'], 'legacy original')
        self.assertEqual(version['first_collected_at'], originals[0]['collected_at'])
        for field in ('platform', 'id', 'created_at', 'source_url', 'external_urls_json'):
            self.assertEqual(version[field], originals[0][field])
        self.assertEqual(self.rows('SELECT * FROM posts'), originals)
        self.assertEqual(self.rows('SELECT * FROM matches'), matches)
        self.assertEqual(pipeline.report(self.data)['versions'], 1)
        self.assertEqual(pipeline.report(self.data)['runs'], 1)
        self.assertEqual(pipeline.run(self.config, self.data, 'demo'), 0)
        self.assertEqual(pipeline.report(self.data)['versions'], 2)
        self.assertEqual(pipeline.report(self.data)['observations'], 2)
        self.assertEqual(self.rows('SELECT * FROM posts'), originals)

    def test_legacy_matches_lock_query_before_fetch_or_run(self):
        self.legacy()
        before = self.rows('SELECT * FROM runs')
        calls = []
        def forbidden(*args):
            calls.append(args)
            return pipeline.demo_page(*args)
        for change in ({'query': 'changed'}, {'platform': 'threads'}):
            with self.subTest(change=change):
                config = {'queries': [
                    {'id': 'new', 'platform': 'x', 'query': 'not registered on failure'},
                    {**self.config['queries'][0], **change}]}
                with self.assertRaisesRegex(ValueError, '^query_id conflict$'):
                    pipeline.run(config, self.data, 'demo', forbidden)
                self.assertEqual(calls, [])
                self.assertEqual(self.rows('SELECT * FROM runs'), before)
                self.assertEqual(self.rows("SELECT * FROM query_definitions WHERE query_id='new'"), [])
        self.assertEqual(self.rows('SELECT * FROM query_definitions'), [
            {'query_id': 'a', 'platform': 'x', 'query': 'Hermes'}])

    def test_legacy_payload_backfills_only_evidenced_observation(self):
        self.legacy()
        payload_path = self.data / 'legacy-payload.json'
        post = pipeline.demo_page('x', '', None)['posts'][0]
        post.update(text='legacy original', metrics={'likes': 7})
        payload = {'run_id': 'legacy-run', 'mode': 'demo', 'platform': 'x',
                   'query_id': 'a', 'query': 'Hermes', 'collected_at': '2026-01-02T03:04:04Z',
                   'posts': [post], 'has_more': False}
        payload_path.write_text(json.dumps(payload))
        before = self.rows('SELECT * FROM posts')
        report = pipeline.report(self.data)
        self.assertEqual(report['observations'], 1, 'valid legacy envelope provides actual provenance')
        fact = self.rows('SELECT * FROM observation_facts')[0]
        self.assertEqual(fact['run_id'], 'legacy-run')
        self.assertEqual(fact['observed_at'], payload['collected_at'])
        self.assertEqual(fact['query'], 'Hermes')
        self.assertEqual(fact['text'], 'legacy original')
        self.assertEqual(json.loads(fact['metrics_json']), {'likes': 7})
        self.assertEqual(fact['payload_path'], str(payload_path))
        self.assertEqual(self.rows('SELECT * FROM post_versions')[0]['first_collected_at'],
                         before[0]['collected_at'])
        self.assertEqual(self.rows('SELECT * FROM posts'), before)
        self.assertEqual(pipeline.report(self.data)['observations'], 1)
        self.assertEqual(pipeline.report(self.data)['runs'], 1)

    def test_bad_page_rolls_back_its_posts_versions_matches_and_observations(self):
        for prior_page in (False, True):
            with self.subTest(prior_page=prior_page):
                self.data = Path(self.temp.name) / str(prior_page)
                config = {'queries': self.config['queries'][:1]}
                def fetch(platform, query, token):
                    page = pipeline.demo_page(platform, query, token)
                    if prior_page and token is None:
                        page['next_token'] = 'page2'
                    else:
                        page['posts'][0]['id'] = 'must-rollback'
                        broken = {'id': 'malformed', 'text': 'DO_NOT_LOG_SECRET'}
                        page['posts'].append(broken)
                    return page
                self.assertEqual(pipeline.run(config, self.data, 'demo', fetch), 1)
                health = self.rows('SELECT * FROM health')[0]
                self.assertEqual(health['fetched'], int(prior_page), 'failed page is not partially fetched')
                self.assertEqual(health['status'], 'partial' if prior_page else 'error')
                self.assertEqual(health['reason'], 'query_failed')
                for table in ('posts', 'post_versions', 'matches', 'observations'):
                    rows = self.rows('SELECT * FROM ' + table)
                    self.assertEqual(len(rows), int(prior_page), table)
                    self.assertFalse(any(row['id'] == 'must-rollback' for row in rows), table)
                report = pipeline.report(self.data)
                self.assertNotIn('DO_NOT_LOG_SECRET', json.dumps(report))
                payloads = [path for path in self.data.glob('*.json') if path.name != 'mode.json']
                self.assertEqual(len(payloads), int(prior_page))

    def test_malformed_page_shapes_never_enter_incremental_tables(self):
        cases = [
            ('id', None), ('id', ''), ('id', 123), ('text', None), ('source_url', None),
            ('created_at', None), ('external_urls', {}), ('external_urls', [None]),
            ('metrics', []), ('metrics', {'likes': float('nan')}),
            ('extra', object()), ('posts', {}), ('next_token', 'https://invalid.example/token')]
        for number, (field, value) in enumerate(cases):
            with self.subTest(field=field, value=value):
                self.data = Path(self.temp.name) / str(number)
                def fetch(*args):
                    page = pipeline.demo_page(*args)
                    if field in ('posts', 'next_token'):
                        page[field] = value
                    else:
                        page['posts'][0][field] = value
                    return page
                self.assertEqual(pipeline.run({'queries': self.config['queries'][:1]},
                                              self.data, 'demo', fetch), 1)
                for table in ('posts', 'matches', 'post_versions', 'observations'):
                    self.assertEqual(self.rows('SELECT * FROM ' + table), [], table)
                health = self.rows('SELECT * FROM health')[0]
                self.assertEqual((health['status'], health['fetched'], health['reason']),
                                 ('error', 0, 'query_failed'))
                self.assertEqual(list(self.data.glob('*.json')), [self.data / 'mode.json'])

    def test_legacy_uncertain_provenance_is_not_invented(self):
        cases = ['missing-run', 'wrong-query', 'changed-content', 'null-observed-at',
                 'invalid-time', 'invalid-metrics', 'outside-path', 'symlink']
        for case in cases:
            with self.subTest(case=case):
                self.data = Path(self.temp.name) / case
                self.legacy()
                post = pipeline.demo_page('x', '', None)['posts'][0]
                post.update(text='legacy original', metrics={'likes': 7})
                payload = {'run_id': 'legacy-run', 'platform': 'x', 'query_id': 'a',
                           'query': 'Hermes', 'collected_at': '2026-01-02T03:04:04Z', 'posts': [post]}
                if case == 'missing-run':
                    payload['run_id'] = 'unknown-run'
                elif case == 'wrong-query':
                    payload['query'] = 'different'
                elif case == 'changed-content':
                    post['text'] = 'changed later'
                elif case == 'null-observed-at':
                    payload['collected_at'] = None
                elif case == 'invalid-time':
                    payload['collected_at'] = 'unknown'
                elif case == 'invalid-metrics':
                    post['metrics'] = []
                path = self.data / 'legacy-payload.json'
                if case in ('outside-path', 'symlink'):
                    outside = Path(self.temp.name) / (case + '-outside.json')
                    outside.write_text(json.dumps(payload))
                    if case == 'symlink':
                        path.symlink_to(outside)
                    else:
                        with sqlite3.connect(self.data / 'pipeline.sqlite3') as connection:
                            connection.execute('UPDATE matches SET payload_path=?', (str(outside),))
                else:
                    path.write_text(json.dumps(payload))
                report = pipeline.report(self.data)
                self.assertEqual(report['versions'], 1)
                self.assertEqual(report['observations'], 0, case)
                self.assertEqual(report['runs'], 1)

    def test_sql_failure_after_first_post_uses_page_savepoint(self):
        # Supplemental regression: the earlier atomicity slice already implements this.
        self.assertEqual(pipeline.run({'queries': []}, self.data, 'demo'), 0)
        with sqlite3.connect(self.data / 'pipeline.sqlite3') as connection:
            connection.executescript('''CREATE TRIGGER reject_fixture BEFORE INSERT ON post_versions
                WHEN NEW.id='rejected' BEGIN SELECT RAISE(ABORT, 'DO_NOT_LOG_SECRET'); END;''')
        def fetch(*args):
            page = pipeline.demo_page(*args)
            page['posts'].append({**page['posts'][0], 'id': 'rejected'})
            return page
        self.assertEqual(pipeline.run({'queries': self.config['queries'][:1]}, self.data, 'demo', fetch), 1)
        for table in ('posts', 'matches', 'post_versions', 'observations'):
            self.assertEqual(self.rows('SELECT * FROM ' + table), [])
        health = self.rows('SELECT * FROM health')[0]
        self.assertEqual((health['status'], health['fetched'], health['reason']), ('error', 0, 'query_failed'))
        self.assertNotIn('DO_NOT_LOG_SECRET', str(pipeline.report(self.data)))

    def test_content_hash_contract_excludes_observation_fields(self):
        # Direct helper coverage of the original deterministic-content implementation.
        post = pipeline.demo_page('x', '', None)['posts'][0]
        post['text'] = '한글 본문'
        baseline = pipeline.content_hash('x', post)
        reordered = dict(reversed(list(post.items())))
        reordered.update(metrics={'likes': 999}, observed_at='later', query='other',
                         collected_at='later', query_id='new')
        self.assertEqual(pipeline.content_hash('x', reordered), baseline)
        self.assertEqual(pipeline.content_hash('x', {**post, 'created_at': '2026-01-01T09:00:00+09:00'}), baseline)
        changes = {'id': 'other', 'created_at': '2026-01-02T00:00:00Z', 'text': 'revised',
                   'source_url': 'https://example.invalid/revised', 'external_urls': ['https://example.invalid/article']}
        for key, value in changes.items():
            self.assertNotEqual(pipeline.content_hash('x', {**post, key: value}), baseline, key)
        self.assertNotEqual(pipeline.content_hash('reddit', post), baseline)

    def test_duplicate_pages_keep_first_observation_per_run_query_version(self):
        def fetch(*args):
            return {**pipeline.demo_page(*args), 'next_token': 'duplicate-page'}
        config = {'queries': self.config['queries'][:1], 'max_pages': 2}
        self.assertEqual(pipeline.run(config, self.data, 'demo', fetch), 1)
        report = pipeline.report(self.data)
        self.assertEqual((report['posts'], report['versions'], report['observations']), (1, 1, 1))
        self.assertEqual((report['health'][0]['status'], report['health'][0]['fetched']), ('partial', 2))
        connection = pipeline.database(self.data)
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_conflicting_legacy_definitions_fail_without_partial_backfill(self):
        self.legacy()
        with sqlite3.connect(self.data / 'pipeline.sqlite3') as connection:
            connection.execute('INSERT INTO matches VALUES (?,?,?,?,?)',
                               ('a', 'reddit', 'other', 'changed meaning', 'not-read.json'))
        with self.assertRaisesRegex(ValueError, '^query_id conflict$'):
            pipeline.database(self.data)
        self.assertEqual(self.rows('SELECT * FROM post_versions'), [])
        self.assertEqual(self.rows('SELECT * FROM query_definitions'), [])
        self.assertEqual(len(self.rows('SELECT * FROM runs')), 1)


if __name__ == '__main__':
    unittest.main()
