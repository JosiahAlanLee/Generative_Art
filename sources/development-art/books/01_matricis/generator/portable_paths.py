"""Local paths for the original Matricis artwork generators."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
FONTS = ROOT / "sources/codex-intervallorum/common/fonts"
OUTPUT = Path(os.environ.get("MATRICIS_OUTPUT", ROOT / "examples/out/matricis"))
PREVIEW = OUTPUT / "previews"
OUTPUT.mkdir(parents=True, exist_ok=True)
PREVIEW.mkdir(parents=True, exist_ok=True)
