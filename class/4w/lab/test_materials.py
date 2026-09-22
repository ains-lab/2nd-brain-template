"""Repeatable lesson checks; syntax checks never run API/cron examples."""
import ast
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class MaterialTests(unittest.TestCase):
    def test_text_format_and_code_fences(self):
        for path in sorted(ROOT.rglob('*')):
            if path.suffix not in ('.md', '.py', '.json'):
                continue
            with self.subTest(path=str(path.relative_to(ROOT))):
                data = path.read_bytes()
                text = data.decode('utf-8')
                self.assertFalse(data.startswith(b'\xef\xbb\xbf'))
                self.assertNotIn(b'\r', data)
                self.assertTrue(data.endswith(b'\n'))
                if path.suffix == '.md':
                    self.assertEqual(len(re.findall(r'^```', text, re.M)) % 2, 0)
                elif path.suffix == '.py':
                    ast.parse(text, filename=str(path))
                else:
                    json.loads(text)

    def test_markdown_local_links_resolve(self):
        for path in sorted(ROOT.glob('*.md')):
            for target in re.findall(r'\[[^\]\n]+\]\(([^\s)]+)\)', path.read_text(encoding='utf-8')):
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith('#'):
                    continue
                with self.subTest(path=path.name, link=target):
                    self.assertTrue((path.parent / unquote(parsed.path)).exists())

    @unittest.skipUnless(shutil.which('bash'), 'bash syntax checker unavailable')
    def test_bash_examples_have_valid_syntax(self):
        for path in sorted(ROOT.glob('*.md')):
            blocks = re.findall(r'^```bash\n(.*?)^```', path.read_text(encoding='utf-8'), re.M | re.S)
            for number, block in enumerate(blocks, 1):
                with self.subTest(path=path.name, block=number):
                    result = subprocess.run(['bash', '-n'], input=block, text=True,
                                            capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
