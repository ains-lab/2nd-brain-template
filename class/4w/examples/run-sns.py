"""Copy this wrapper into the owning Hermes profile's scripts directory.

The lab and keywords.json must first be copied to ~/.local/share/hermes-sns/.
Initialize live-wiki separately. This script exports raw, never compiles knowledge.
No secrets are read from files by this wrapper. Hermes supplies allowed env vars.
"""
from pathlib import Path
import subprocess
import sys

root = Path.home() / ".local" / "share" / "hermes-sns"
script = root / "lab" / "pipeline.py"
config = root / "keywords.json"
bridge = root / "lab" / "wiki_pipeline.py"
wiki = root / "live-wiki"
if not all(path.is_file() for path in (script, bridge, config)) or not wiki.is_dir():
    print("SNS setup incomplete: install both lab scripts and config, initialize live-wiki", file=sys.stderr)
    raise SystemExit(2)
collected = subprocess.run([
    sys.executable, str(script), "--config", str(config),
    "--data-dir", str(root / "live-data"), "--mode", "live",
], check=False)
if collected.returncode not in (0, 1):
    raise SystemExit(collected.returncode)
# A partial run may contain useful committed observations; preserve its exit code.
exported = subprocess.run([
    sys.executable, str(bridge), "export",
    "--data-dir", str(root / "live-data"), "--wiki-dir", str(wiki),
], check=False)
raise SystemExit(exported.returncode or collected.returncode)
