"""Export the opened .blend to GLB with the project's standard settings.

Usage (headless):
  Blender -b <file.blend> -P blender/scripts/export.py -- <out.glb> [--no-ao] [--lightmap=<profile>]

On the in-memory copy only (the .blend on disk is left untouched), before exporting:
  1. modifiers are applied (chamfers, weighted normals);
  2. UV0 is projected for the tileable surface sets and the goods normal atlas (surfaces.py);
  3. --lightmap=store|terrace: lighting is baked (profiles in lightmap.py) into an atlas on a second UV layer (lightmap.py),
     written next to the GLB as <name>.lightmap.jpg; --no-ao also skips it (quick iterations);
  4. ambient occlusion is baked into vertex colours (COLOR_0) on the meshes the lightmap does
     not cover. --no-ao skips it.
Textures and the lightmap are bound to the materials afterwards by scripts/optimize-glb.mjs.

Naming and hierarchy are checked afterwards by tests/assets.test.ts against
src/core/assetContract.ts, so the contract lives in one place.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from common import apply_modifiers, bake_ambient_occlusion, export_glb, rendered_meshes  # noqa: E402
from lightmap import PROFILES, bake_lightmap, build_lightmap_uvs, isolation_key  # noqa: E402
from surfaces import project_brand_uvs, project_goods_uvs, project_surface_uvs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
paths = [a for a in argv if not a.startswith("--")]
if not paths:
    raise SystemExit("usage: export.py -- <out.glb> [--no-ao] [--lightmap=<profile>]")
out = os.path.abspath(paths[0])
os.makedirs(os.path.dirname(out), exist_ok=True)

meshes = rendered_meshes()
apply_modifiers(meshes)
print(f"UV0 projected on {project_surface_uvs(meshes)} textured meshes, {project_goods_uvs(meshes)} product parts")
print(f"{project_brand_uvs(meshes)} printed faces mapped")
lit = set()
profile = None
profile_name = next((a.split("=", 1)[1] for a in argv if a.startswith("--lightmap=")), None)
if profile_name:
    profile = PROFILES[profile_name]
    layout = build_lightmap_uvs(meshes, profile)
    print(f"lightmap UVs: {layout['islands']} islands, {layout['density']:.1f} texels/m")
    lit = {o.name for o in layout["baked"]}
    if "--no-ao" not in argv:
        bake_lightmap(layout["baked"], layout["floor"], os.path.splitext(out)[0] + ".lightmap.jpg", profile)
if "--no-ao" not in argv:
    started = time.time()
    # Parts that move at runtime are baked alone, so they carry no shadow of where they start.
    isolate = (lambda o: isolation_key(o.name) if profile.moving.search(o.name) else None) if profile else None
    ground = (lambda o: o.name == profile.floor or o.name.startswith(("TERRAIN_", "ROAD_", "DOCK_"))) if profile else None
    count = bake_ambient_occlusion([o for o in meshes if o.name not in lit], isolate=isolate, ground=ground)
    print(f"AO baked on {count} meshes in {time.time() - started:.1f} s")
export_glb(out)
