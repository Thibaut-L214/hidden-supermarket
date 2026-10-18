"""Export the opened .blend to GLB with the project's standard settings.

Usage (headless):
  Blender -b <file.blend> -P blender/scripts/export.py -- <out.glb> [--no-ao]

Before exporting, modifiers are applied and ambient occlusion is baked into vertex colours
(COLOR_0), on the in-memory copy only: the .blend on disk is left untouched. --no-ao skips
the bake for quick iterations.

Naming and hierarchy are checked afterwards by tests/assets.test.ts against
src/core/assetContract.ts, so the contract lives in one place.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from common import bake_ambient_occlusion, export_glb  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
paths = [a for a in argv if not a.startswith("--")]
if not paths:
    raise SystemExit("usage: export.py -- <out.glb> [--no-ao]")
out = os.path.abspath(paths[0])
os.makedirs(os.path.dirname(out), exist_ok=True)
if "--no-ao" not in argv:
    started = time.time()
    count = bake_ambient_occlusion()
    print(f"AO baked on {count} meshes in {time.time() - started:.1f} s")
export_glb(out)
