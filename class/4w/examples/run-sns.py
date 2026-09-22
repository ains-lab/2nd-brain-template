"""Copy this wrapper into the owning Hermes profile's scripts directory.

The lab and keywords.json must first be copied to ~/.local/share/hermes-sns/.
No secrets are read from files by this wrapper. Hermes supplies allowed env vars.
"""
import os
from pathlib import Path
import sys

root = Path.home() / ".local" / "share" / "hermes-sns"
script = root / "lab" / "pipeline.py"
config = root / "keywords.json"
if not script.is_file() or not config.is_file():
    print("SNS setup incomplete: install lab/pipeline.py and keywords.json", file=sys.stderr)
    raise SystemExit(2)
os.execv(sys.executable, [
    sys.executable, str(script), "--config", str(config),
    "--data-dir", str(root / "live-data"), "--mode", "live",
])
