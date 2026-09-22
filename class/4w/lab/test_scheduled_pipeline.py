"""Wrapper contract with harmless local script fixtures, not SNS requests."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ScheduledPipelineTests(unittest.TestCase):
    def test_missing_wiki_setup_stops_before_collection(self):
        wrapper = Path(__file__).resolve().parents[1] / 'examples/run-sns.py'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / '.local/share/hermes-sns'
            (root / 'lab').mkdir(parents=True)
            (root / 'keywords.json').write_text('{}', encoding='utf-8')
            (root / 'lab/pipeline.py').write_text(
                'from pathlib import Path\n'
                'Path(__file__).parents[1].joinpath("collected").touch()\n', encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', str(wrapper)],
                                    env={**os.environ, 'HOME': temp},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((root / 'collected').exists())

    def test_wrapper_exports_committed_data_without_hiding_partial(self):
        wrapper = Path(__file__).resolve().parents[1] / 'examples/run-sns.py'
        for code in (0, 1, 2):
            with self.subTest(collection_exit=code), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / '.local/share/hermes-sns'
                (root / 'lab').mkdir(parents=True)
                (root / 'live-wiki').mkdir()
                (root / 'keywords.json').write_text('{}', encoding='utf-8')
                (root / 'lab/pipeline.py').write_text(
                    'raise SystemExit(' + str(code) + ')\n', encoding='utf-8')
                (root / 'lab/wiki_pipeline.py').write_text(
                    'import json, sys\nfrom pathlib import Path\n'
                    'Path(__file__).parents[1].joinpath("called.json").write_text(json.dumps(sys.argv[1:]))\n',
                    encoding='utf-8')
                result = subprocess.run([sys.executable, '-B', str(wrapper)],
                                        env={**os.environ, 'HOME': temp},
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stderr)
                marker = root / 'called.json'
                self.assertEqual(marker.exists(), code in (0, 1), 'export committed partial data too')
                if marker.exists():
                    self.assertEqual(json.loads(marker.read_text()), [
                        'export', '--data-dir', str(root / 'live-data'),
                        '--wiki-dir', str(root / 'live-wiki')])


if __name__ == '__main__':
    unittest.main()
