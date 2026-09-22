"""Real tempfile/SQLite tests; canonical examples are synthetic UNIT fixtures.
These fixtures are not claimed to be actual Hermes/model output.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

LAB = Path(__file__).resolve().parent
SCHEMA = LAB.parents[2] / 'SCHEMA.md'


class WikiPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wiki = self.root / 'wiki'
        self.data = self.root / 'data'
        self.data.mkdir(mode=0o700)
        (self.data / 'mode.json').write_text('{"mode":"demo"}\n')
        self.db = sqlite3.connect(self.data / 'pipeline.sqlite3')
        self.addCleanup(self.db.close)
        self.db.execute('''CREATE TABLE post_versions (
            version_id TEXT PRIMARY KEY, platform TEXT, id TEXT, content_hash TEXT,
            created_at TEXT, source_url TEXT, text TEXT, external_urls_json TEXT,
            first_collected_at TEXT)''')

    def bridge(self):
        path = LAB / 'wiki_pipeline.py'
        self.assertTrue(path.exists(), 'wiki_pipeline implementation is missing')
        spec = importlib.util.spec_from_file_location('wiki_pipeline', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def version(self, text='UNIT fixture evidence', platform='x', identifier='post/1'):
        digest = hashlib.sha256(text.encode()).hexdigest()
        self.db.execute('INSERT OR IGNORE INTO post_versions VALUES (?,?,?,?,?,?,?,?,?)',
                        (digest, platform, identifier, digest, '2026-01-01T00:00:00Z',
                         'https://example.invalid/source', text, '[]', '2026-01-02T00:00:00Z'))
        self.db.commit()
        return digest

    def initialized(self):
        bridge = self.bridge()
        bridge.init_wiki(self.wiki, SCHEMA, 'demo')
        return bridge

    def test_init_new_private_wiki_preserves_schema_and_refuses_nonempty(self):
        bridge = self.initialized()
        self.assertEqual((self.wiki / 'SCHEMA.md').read_bytes(), SCHEMA.read_bytes())
        self.assertEqual(self.wiki.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.wiki / 'SCHEMA.md').stat().st_mode & 0o777, 0o600)
        self.assertIn('Total pages: 0', (self.wiki / 'index.md').read_text())
        self.assertNotIn('## [', (self.wiki / 'log.md').read_text())
        for folder in ('raw/web', 'entities', 'concepts', 'comparisons', 'queries'):
            self.assertTrue((self.wiki / folder).is_dir())
        marker = json.loads((self.wiki / '.wiki-pipeline.json').read_text())
        self.assertEqual(marker['mode'], 'demo')
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            bridge.init_wiki(self.wiki, SCHEMA, 'demo')

    def test_export_is_deterministic_immutable_allowlisted_capture(self):
        bridge = self.initialized()
        version = self.version('본문\r\nUNIT fixture')
        self.assertTrue(hasattr(bridge, 'export'), 'export API is missing')
        result = bridge.export(self.data, self.wiki)
        self.assertEqual(result['exported'], 1)
        raw = self.wiki / ('raw/web/sns-x-' + version + '.md')
        captured = raw.read_bytes()
        front, body = captured.split(b'---\n', 2)[1:]
        meta = dict((line.split(': ', 1)[0], json.loads(line.split(': ', 1)[1]))
                    for line in front.decode().splitlines())
        self.assertEqual(meta['sha256'], hashlib.sha256(body).hexdigest())
        self.assertEqual(meta['version_id'], version)
        self.assertEqual(meta['post_id'], 'post/1')
        self.assertEqual(meta['ingested'], '2026-01-02T00:00:00Z')
        self.assertIn(b'allowlisted', body)
        self.assertIn(b'not a byte-exact HTTP', body)
        self.assertNotIn(b'metrics', body)
        self.assertNotIn(b'\r', captured)
        self.assertEqual(raw.stat().st_mode & 0o777, 0o600)
        logged = (self.wiki / 'log.md').read_bytes()
        self.assertEqual(bridge.export(self.data, self.wiki)['exported'], 0)
        self.assertEqual(raw.read_bytes(), captured)
        self.assertEqual((self.wiki / 'log.md').read_bytes(), logged)
        row = self.db.execute('SELECT * FROM raw_exports').fetchone()
        self.assertIsNotNone(row)
        # Crash after filesystem work but before the ledger commit: reconcile.
        self.db.execute('DELETE FROM raw_exports')
        self.db.commit()
        bridge.export(self.data, self.wiki)
        self.assertEqual(raw.read_bytes(), captured)
        self.assertEqual((self.wiki / 'log.md').read_bytes(), logged)

    def test_mode_and_dataset_bindings_refuse_cross_contamination(self):
        bridge = self.initialized()
        self.version()
        (self.data / 'mode.json').write_text('{"mode":"live"}')
        with self.assertRaisesRegex(ValueError, 'mode'):
            bridge.export(self.data, self.wiki)
        self.assertEqual(list((self.wiki / 'raw/web').iterdir()), [])
        (self.data / 'mode.json').write_text('{"mode":"demo"}')
        bridge.export(self.data, self.wiki)
        second = self.root / 'second'
        bridge.init_wiki(second, SCHEMA, 'demo')
        with self.assertRaisesRegex(ValueError, 'binding'):
            bridge.export(self.data, second)
        import shutil
        copied = self.root / 'copied-data'
        shutil.copytree(self.data, copied)
        with self.assertRaisesRegex(ValueError, 'binding'):
            bridge.export(copied, self.wiki)
        fresh = self.root / 'fresh-data'
        fresh.mkdir()
        (fresh / 'mode.json').write_text('{"mode":"demo"}')
        sqlite3.connect(fresh / 'pipeline.sqlite3').close()
        with self.assertRaisesRegex(ValueError, 'binding'):
            bridge.export(fresh, self.wiki)

    def test_raw_publication_is_atomic_and_differing_bytes_never_overwritten(self):
        from unittest.mock import patch
        bridge = self.initialized()
        version = self.version()
        raw = self.wiki / ('raw/web/sns-x-' + version + '.md')
        # Fault on the actual atomic publication boundary, not a fake filesystem.
        with patch.object(bridge.os, 'link', side_effect=OSError('injected publish failure')):
            with self.assertRaises(OSError):
                bridge.export(self.data, self.wiki)
        self.assertFalse(raw.exists())
        self.assertEqual(list((self.wiki / 'raw/web').iterdir()), [])
        bridge.export(self.data, self.wiki)
        raw.write_bytes(b'partial earlier capture')
        with self.assertRaisesRegex(ValueError, 'immutable'):
            bridge.export(self.data, self.wiki)
        self.assertEqual(raw.read_bytes(), b'partial earlier capture')

    def test_export_rejects_traversal_and_symlink_before_write(self):
        bridge = self.initialized()
        self.version()
        self.db.execute("UPDATE post_versions SET version_id='../escape'")
        self.db.commit()
        with self.assertRaisesRegex(ValueError, 'identifier'):
            bridge.export(self.data, self.wiki)
        self.assertEqual(list((self.wiki / 'raw/web').iterdir()), [])
        self.db.execute('DELETE FROM post_versions')
        self.db.commit()
        version = self.version()
        outside = self.root / 'outside'
        outside.mkdir()
        (self.wiki / 'raw/web').rmdir()
        (self.wiki / 'raw/web').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            bridge.export(self.data, self.wiki)
        self.assertEqual(list(outside.iterdir()), [])
        (self.wiki / 'raw/web').unlink()
        (self.wiki / 'raw/web').mkdir()
        raw = self.wiki / ('raw/web/sns-x-' + version + '.md')
        victim = outside / 'victim'
        victim.write_bytes(b'protected')
        raw.symlink_to(victim)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            bridge.export(self.data, self.wiki)
        self.assertEqual(victim.read_bytes(), b'protected')

    def test_prepare_freezes_bounded_pending_without_acceptance_and_reuses_open(self):
        bridge = self.initialized()
        versions = {self.version('first evidence'), self.version('second evidence')}
        self.assertTrue(hasattr(bridge, 'prepare'), 'prepare API is missing')
        result = bridge.prepare(self.data, self.wiki, limit=1)
        self.assertEqual(result['status'], 'prepared')
        self.assertEqual(result['pending'], 2)
        manifest = Path(result['manifest'])
        frozen = json.loads(manifest.read_text())
        self.assertEqual(len(frozen['sources']), 1)
        self.assertIn(frozen['sources'][0]['version_id'], versions)
        self.assertEqual(frozen['wiki_dir'], str(self.wiki))
        self.assertIn('index_sha256', frozen['before'])
        self.assertIn('log_sha256', frozen['before'])
        self.assertEqual(frozen['before']['canonical'], {})
        self.assertEqual(manifest.stat().st_mode & 0o777, 0o600)
        self.assertEqual(manifest.parent.stat().st_mode & 0o777, 0o700)
        prompt = Path(result['prompt']).read_text()
        for instruction in ('omh-wiki', 'SCHEMA.md', 'untrusted', 'deferred',
                            'created', 'updated', 'index.md', 'log.md', 'credentials',
                            'two', 'dummy', 'synonym', 'sha256'):
            self.assertIn(instruction, prompt)
        captured = manifest.read_bytes()
        self.version('third evidence')
        repeated = bridge.prepare(self.data, self.wiki)
        self.assertEqual(repeated['batch_id'], result['batch_id'])
        self.assertEqual(repeated['pending'], 3)
        self.assertEqual(manifest.read_bytes(), captured)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT status FROM compile_batches').fetchone()[0], 'prepared')
        with self.assertRaisesRegex(ValueError, 'limit'):
            bridge.prepare(self.data, self.wiki, limit=0)

    def test_finish_without_covered_canonical_stays_prepared(self):
        bridge = self.initialized()
        self.version()
        result = bridge.prepare(self.data, self.wiki)
        self.assertTrue(hasattr(bridge, 'finish'), 'finish API is missing')
        with self.assertRaisesRegex(ValueError, 'covered'):
            bridge.finish(self.data, self.wiki, result['batch_id'])
        self.assertEqual(self.db.execute('SELECT status FROM compile_batches').fetchone()[0], 'prepared')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)
        self.assertEqual(bridge.prepare(self.data, self.wiki)['pending'], 1)

    def test_abort_preserves_pending_and_history_but_releases_batch(self):
        bridge = self.initialized()
        self.version()
        prepared = bridge.prepare(self.data, self.wiki)
        manifest = Path(prepared['manifest']).read_bytes()
        self.assertTrue(hasattr(bridge, 'abort'), 'abort API required')
        result = bridge.abort(self.data, self.wiki, prepared['batch_id'])
        self.assertEqual(result['status'], 'aborted')
        self.assertEqual(result['pending'], 1)
        self.assertEqual(Path(prepared['manifest']).read_bytes(), manifest)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)
        self.assertEqual(bridge.abort(self.data, self.wiki, prepared['batch_id'])['status'], 'noop')
        with self.assertRaisesRegex(ValueError, 'aborted'):
            bridge.finish(self.data, self.wiki, prepared['batch_id'])
        renewed = bridge.prepare(self.data, self.wiki)
        self.assertNotEqual(renewed['batch_id'], prepared['batch_id'])
        self.assertEqual(renewed['pending'], 1)

    def test_aborted_batches_rotate_all_pending_sources_without_acceptance(self):
        bridge = self.initialized()
        versions = {self.version('deferred UNIT evidence ' + str(i)) for i in range(101)}
        bridge.export(self.data, self.wiki)
        raw_before = {path: path.read_bytes() for path in (self.wiki / 'raw/web').glob('*.md')}
        exports_before = self.db.execute('SELECT * FROM raw_exports ORDER BY version_id').fetchall()
        log_before = (self.wiki / 'log.md').read_bytes()
        last_prepared, artifacts = {}, {}
        batches_before, sources_before = [], []
        for turn in range(4):
            prepared = bridge.prepare(self.data, self.wiki, limit=100)
            self.assertEqual(prepared['pending'], 101)
            selected = [source['version_id'] for source in
                        json.loads(Path(prepared['manifest']).read_text())['sources']]
            expected = sorted(versions, key=lambda version: (last_prepared.get(version, -1), version))[:100]
            self.assertEqual(selected[0], expected[0], 'unvisited or oldest-prepared source must lead')
            self.assertEqual(selected, expected)
            last_prepared.update((version, turn) for version in selected)
            # Preparing another batch must not rewrite any earlier history.
            self.assertEqual(self.db.execute('SELECT * FROM compile_batches ORDER BY rowid').fetchall()
                             [:len(batches_before)], batches_before)
            self.assertEqual(self.db.execute('SELECT * FROM batch_sources ORDER BY rowid').fetchall()
                             [:len(sources_before)], sources_before)
            for field in ('manifest', 'prompt'):
                path = Path(prepared[field])
                self.assertNotIn(path, artifacts)
                artifacts[path] = path.read_bytes()
            aborted = bridge.abort(self.data, self.wiki, prepared['batch_id'])
            self.assertEqual(aborted['status'], 'aborted')
            self.assertEqual(aborted['pending'], 101)
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM batch_sources WHERE accepted != 0')
                             .fetchone()[0], 0)
            batches_before = self.db.execute('SELECT * FROM compile_batches ORDER BY rowid').fetchall()
            sources_before = self.db.execute('SELECT * FROM batch_sources ORDER BY rowid').fetchall()
            self.assertEqual(len(batches_before), turn + 1)
            self.assertEqual(len(sources_before), (turn + 1) * 100)
            self.assertTrue(all(row[1] == 'aborted' for row in batches_before))
            for path, captured in artifacts.items():
                self.assertEqual(path.read_bytes(), captured)
            self.assertEqual({path: path.read_bytes() for path in (self.wiki / 'raw/web').glob('*.md')},
                             raw_before)
            self.assertEqual(self.db.execute('SELECT * FROM raw_exports ORDER BY version_id').fetchall(),
                             exports_before)
            self.assertEqual((self.wiki / 'log.md').read_bytes(), log_before)
        self.assertEqual(set(last_prepared), versions)
        self.assertTrue(all(turn > 0 for turn in last_prepared.values()), 'every source must be revisited')

    def test_partial_finish_prioritizes_unvisited_then_oldest_deferred_sources(self):
        bridge = self.initialized()
        versions = sorted(self.version('partial UNIT evidence ' + str(i)) for i in range(4))
        prepared = bridge.prepare(self.data, self.wiki, limit=3)
        frozen = json.loads(Path(prepared['manifest']).read_text())
        self.canonical_fixture(frozen['sources'][0]['raw_path'])
        completed = bridge.finish(self.data, self.wiki, prepared['batch_id'])
        self.assertEqual(completed['accepted'], 1)
        self.assertEqual(completed['pending'], 3)
        mappings_before = self.db.execute('SELECT * FROM wiki_sources ORDER BY canonical_path').fetchall()
        history_before = self.db.execute('SELECT * FROM batch_sources WHERE batch_id=? ORDER BY version_id',
                                         (prepared['batch_id'],)).fetchall()
        next_batch = bridge.prepare(self.data, self.wiki, limit=2)
        selected = json.loads(Path(next_batch['manifest']).read_text())['sources']
        self.assertEqual([source['version_id'] for source in selected], [versions[3], versions[1]])
        bridge.abort(self.data, self.wiki, next_batch['batch_id'])
        oldest_batch = bridge.prepare(self.data, self.wiki, limit=1)
        selected = json.loads(Path(oldest_batch['manifest']).read_text())['sources']
        self.assertEqual([source['version_id'] for source in selected], [versions[2]])
        self.assertEqual(oldest_batch['pending'], 3)
        self.assertEqual(self.db.execute('SELECT * FROM wiki_sources ORDER BY canonical_path').fetchall(),
                         mappings_before)
        self.assertEqual(self.db.execute('SELECT * FROM batch_sources WHERE batch_id=? ORDER BY version_id',
                                         (prepared['batch_id'],)).fetchall(), history_before)

    def test_cli_lifecycle_and_failure_exit_codes(self):
        self.version()
        script = LAB / 'wiki_pipeline.py'

        def invoke(action, *extra, expected=0):
            args = [sys.executable, '-B', str(script), action, '--wiki-dir', str(self.wiki)]
            if action != 'init':
                args += ['--data-dir', str(self.data)]
            result = subprocess.run(args + list(extra), capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            if not expected:
                self.assertTrue(result.stdout.strip(), 'CLI must execute and report JSON')
                return json.loads(result.stdout)
            self.assertTrue(result.stderr)
            return {}

        self.assertEqual(invoke('init', '--schema', str(SCHEMA), '--mode', 'demo')['status'], 'initialized')
        self.assertEqual(invoke('export')['exported'], 1)
        prepared = invoke('prepare', '--limit', '1')
        invoke('finish', '--batch-id', prepared['batch_id'], expected=2)
        self.assertEqual(invoke('abort', '--batch-id', prepared['batch_id'])['status'], 'aborted')
        invoke('finish', '--batch-id', prepared['batch_id'], expected=2)
        prepared = invoke('prepare')
        source = json.loads(Path(prepared['manifest']).read_text())['sources'][0]['raw_path']
        self.canonical_fixture(source)
        self.assertEqual(invoke('finish', '--batch-id', prepared['batch_id'])['accepted'], 1)
        self.assertEqual(invoke('prepare')['status'], 'noop')
        invoke('abort', '--batch-id', prepared['batch_id'], expected=2)

    def canonical_fixture(self, source):
        """Synthetic structural UNIT fixture, not fabricated model execution."""
        names = ['alpha', 'beta', 'gamma']
        for name in names:
            meta = {'title': name.title(), 'created': '2026-01-03', 'updated': '2026-01-03',
                    'type': 'concept', 'tags': ['provenance'], 'sources': [source],
                    'confidence': 'low', 'contested': False, 'contradictions': []}
            front = ''.join(k + ': ' + json.dumps(v) + '\n' for k, v in meta.items())
            body = '# UNIT fixture ' + name + '\n\nSynthetic assertion. ^[' + source + ']\n\n'
            body += ' '.join('[[concepts/' + other + ']]' for other in names if other != name) + '\n'
            (self.wiki / ('concepts/' + name + '.md')).write_text('---\n' + front + '---\n' + body)
        index = '# Wiki Index\n\n> Total pages: 3\n\n## Entities\n\n## Concepts\n\n'
        index += ''.join('- [[concepts/' + name + ']] — UNIT fixture summary\n' for name in names)
        index += '\n## Comparisons\n\n## Queries\n'
        (self.wiki / 'index.md').write_text(index)
        with (self.wiki / 'log.md').open('a') as log:
            log.write('\n## [2026-01-03] create | UNIT fixture\n\n')
            log.write('- `index.md`\n- `log.md`\n')
            log.write(''.join('- `concepts/' + name + '.md`\n' for name in names))

    def test_valid_finish_records_coverage_then_noop_and_new_content_pending(self):
        bridge = self.initialized()
        old = self.version('original version')
        result = bridge.prepare(self.data, self.wiki)
        source = json.loads(Path(result['manifest']).read_text())['sources'][0]['raw_path']
        self.canonical_fixture(source)
        completed = bridge.finish(self.data, self.wiki, result['batch_id'])
        self.assertEqual(completed['status'], 'finished')
        self.assertEqual(completed['accepted'], 1)
        self.assertEqual(completed['pending'], 0)
        mappings = self.db.execute('SELECT version_id,canonical_path,canonical_sha256,raw_sha256 FROM wiki_sources').fetchall()
        self.assertEqual(len(mappings), 3)
        for version, page, page_sha, raw_sha in mappings:
            self.assertEqual(version, old)
            self.assertEqual(page_sha, hashlib.sha256((self.wiki / page).read_bytes()).hexdigest())
            self.assertEqual(raw_sha, hashlib.sha256((self.wiki / source).read_bytes()).hexdigest())
        self.assertEqual(bridge.finish(self.data, self.wiki, result['batch_id'])['status'], 'noop')
        self.assertEqual(bridge.prepare(self.data, self.wiki)['status'], 'noop')
        new = self.version('edited content same post')
        prepared = bridge.prepare(self.data, self.wiki)
        self.assertEqual(prepared['pending'], 1)
        self.assertEqual([s['version_id'] for s in json.loads(Path(prepared['manifest']).read_text())['sources']], [new])

    def test_finish_rejects_invalid_schema_metadata_provenance_and_links(self):
        bridge = self.initialized()
        self.version()
        prepared = bridge.prepare(self.data, self.wiki)
        source = json.loads(Path(prepared['manifest']).read_text())['sources'][0]['raw_path']
        self.canonical_fixture(source)
        page = self.wiki / 'concepts/alpha.md'
        valid = page.read_text()
        cases = [
            valid.replace('title: "Alpha"\n', ''),
            valid.replace('type: "concept"', 'type: "entity"'),
            valid.replace('2026-01-03', '2026-99-03'),
            valid.replace('["provenance"]', '["unregistered"]'),
            valid.replace('confidence: "low"', 'confidence: "high"'),
            valid.replace('contested: false', 'contested: true'),
            valid.replace('contradictions: []', 'contradictions: ["missing"]'),
            valid.replace('title: "Alpha"', 'title: "Alpha"\ntitle: "Duplicate"'),
            valid.replace('title: "Alpha"', 'title: &anchor Alpha'),
            valid.replace('sources: ["' + source + '"]', 'sources: ["raw/web/../escape.md"]'),
            valid.replace('^[' + source + ']', '^[raw/web/unlisted.md]'),
            valid.replace('[[concepts/beta]]', '[[missing]]'),
            valid.replace('[[concepts/beta]]', '[[concepts/gamma]]'),
            valid + '<placeholder>\n',
            valid.replace('\n', '\r\n'),
            '\ufeff' + valid,
            valid.rstrip('\n'),
        ]
        for invalid in cases:
            page.write_bytes(invalid.encode())
            with self.assertRaises(ValueError):
                bridge.finish(self.data, self.wiki, prepared['batch_id'])
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)
        page.write_text(valid)
        page.rename(self.wiki / 'concepts/Uppercase.md')
        with self.assertRaises(ValueError):
            bridge.finish(self.data, self.wiki, prepared['batch_id'])
        (self.wiki / 'concepts/Uppercase.md').rename(page)
        self.assertEqual(bridge.finish(self.data, self.wiki, prepared['batch_id'])['status'], 'finished')

    def test_finish_checks_all_frozen_whole_raw_hashes_even_on_noop(self):
        bridge = self.initialized()
        self.version('used evidence')
        self.version('deferred evidence')
        prepared = bridge.prepare(self.data, self.wiki)
        sources = json.loads(Path(prepared['manifest']).read_text())['sources']
        self.canonical_fixture(sources[0]['raw_path'])
        unused = self.wiki / sources[1]['raw_path']
        captured = unused.read_bytes()
        unused.write_bytes(captured.replace(b'mode: "demo"', b'mode: "live"'))
        with self.assertRaisesRegex(ValueError, 'raw'):
            bridge.finish(self.data, self.wiki, prepared['batch_id'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)
        unused.write_bytes(captured)
        result = bridge.finish(self.data, self.wiki, prepared['batch_id'])
        self.assertEqual(result['accepted'], 1)
        self.assertEqual(result['pending'], 1)
        unused.write_bytes(captured + b'tamper\n')
        with self.assertRaisesRegex(ValueError, 'raw'):
            bridge.finish(self.data, self.wiki, prepared['batch_id'])
        unused.write_bytes(captured)
        next_batch = bridge.prepare(self.data, self.wiki)
        self.assertNotEqual(next_batch['batch_id'], prepared['batch_id'])
        self.assertEqual(next_batch['pending'], 1)

    def test_finish_rejects_schema_drift_until_batch_is_aborted(self):
        bridge = self.initialized()
        self.version()
        prepared = bridge.prepare(self.data, self.wiki)
        frozen = json.loads(Path(prepared['manifest']).read_text())
        self.canonical_fixture(frozen['sources'][0]['raw_path'])
        schema = self.wiki / 'SCHEMA.md'
        schema.write_bytes(schema.read_bytes() + b'\nChanged contract.\n')
        with self.assertRaisesRegex(ValueError, 'schema'):
            bridge.finish(self.data, self.wiki, prepared['batch_id'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)
        bridge.abort(self.data, self.wiki, prepared['batch_id'])
        newer = bridge.prepare(self.data, self.wiki)
        self.assertNotEqual(newer['batch_id'], prepared['batch_id'])

    def test_finish_does_not_accept_unchanged_preexisting_canonical(self):
        bridge = self.initialized()
        version = self.version()
        bridge.export(self.data, self.wiki)
        self.canonical_fixture('raw/web/sns-x-' + version + '.md')
        prepared = bridge.prepare(self.data, self.wiki)
        with (self.wiki / 'log.md').open('a') as log:
            log.write('\n## [2026-01-03] update | No actual source work\n\n- `log.md`\n')
        with self.assertRaisesRegex(ValueError, 'covered'):
            bridge.finish(self.data, self.wiki, prepared['batch_id'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)

    def test_updates_preserve_created_and_refresh_updated(self):
        import datetime as dt
        bridge = self.initialized()
        version = self.version()
        bridge.export(self.data, self.wiki)
        self.canonical_fixture('raw/web/sns-x-' + version + '.md')
        prepared = bridge.prepare(self.data, self.wiki)
        page = self.wiki / 'concepts/alpha.md'
        original = page.read_text()
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        with (self.wiki / 'log.md').open('a') as log:
            log.write('\n## [' + today + '] update | Reviewed fixture\n\n'
                      '- `concepts/alpha.md`\n- `log.md`\n')
        page.write_text(original.replace('created: "2026-01-03"', 'created: "2026-01-02"'))
        with self.assertRaisesRegex(ValueError, 'created'):
            bridge.finish(self.data, self.wiki, prepared['batch_id'])
        page.write_text(original + '\nReviewed evidence.\n')
        with self.assertRaisesRegex(ValueError, 'updated'):
            bridge.finish(self.data, self.wiki, prepared['batch_id'])
        page.write_text((original + '\nReviewed evidence.\n').replace(
            'updated: "2026-01-03"', 'updated: "' + today + '"'))
        self.assertEqual(bridge.finish(self.data, self.wiki, prepared['batch_id'])['accepted'], 1)

    def test_finish_requires_exact_index_and_append_only_affected_path_log(self):
        bridge = self.initialized()
        self.version()
        prepared = bridge.prepare(self.data, self.wiki)
        frozen = json.loads(Path(prepared['manifest']).read_text())
        self.canonical_fixture(frozen['sources'][0]['raw_path'])
        index, log = self.wiki / 'index.md', self.wiki / 'log.md'
        valid_index, valid_log = index.read_text(), log.read_text()
        invalid_indexes = [valid_index.replace('Total pages: 3', 'Total pages: 2'),
                           valid_index.replace('[[concepts/alpha]]', '[[raw/web/missing]]'),
                           valid_index.replace('[[concepts/alpha]]', '[[concepts/beta]]'),
                           valid_index.replace('## Concepts', '## Entities'),
                           valid_index.replace('alpha', 'TEMP').replace('gamma', 'alpha').replace('TEMP', 'gamma')]
        for invalid in invalid_indexes:
            index.write_text(invalid)
            with self.assertRaisesRegex(ValueError, 'index'):
                bridge.finish(self.data, self.wiki, prepared['batch_id'])
        index.write_text(valid_index)
        invalid_logs = [valid_log.replace('# Wiki Log', '# Rewritten'), frozen['before']['log'],
                        valid_log.replace(' create |', ' madeup |'),
                        valid_log.replace('2026-01-03', '2026-99-03'),
                        valid_log.replace('`concepts/alpha.md`', '`other.md`'),
                        valid_log.replace('`index.md`', '`other.md`')]
        for invalid in invalid_logs:
            log.write_text(invalid)
            with self.assertRaisesRegex(ValueError, 'log'):
                bridge.finish(self.data, self.wiki, prepared['batch_id'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)
        log.write_text(valid_log)
        self.assertEqual(bridge.finish(self.data, self.wiki, prepared['batch_id'])['status'], 'finished')


if __name__ == '__main__':
    unittest.main()
