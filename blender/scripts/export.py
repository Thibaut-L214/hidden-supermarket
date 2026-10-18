"""Export the opened .blend to GLB with the project's standard settings.

Usage (headless):
  Blender -b <file.blend> -P blender/scripts/export.py -- <out.glb>

Naming and hierarchy are checked afterwards by tests/assets.test.ts against
src/core/assetContract.ts, so the contract lives in one place.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from common import export_glb  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
if not argv:
    raise SystemExit("usage: export.py -- <out.glb>")
out = os.path.abspath(argv[0])
os.makedirs(os.path.dirname(out), exist_ok=True)
export_glb(out)
