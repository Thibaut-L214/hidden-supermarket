// Builds blockout .blend files (only when missing), exports every .blend to GLB and optimises it.
// Usage: pnpm assets [--rebuild] [--no-ao]
//   --rebuild regenerates blockouts, overwriting the .blend; --no-ao skips the occlusion and
//   lightmap bakes (the store reuses its last lightmap if the layout has not changed).
// BLENDER env var overrides the Blender executable path.
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const BLENDER = process.env.BLENDER ?? "/Applications/Blender.app/Contents/MacOS/Blender";
const rebuild = process.argv.includes("--rebuild");
const noAo = process.argv.includes("--no-ao");

const ASSETS = [
  {
    blend: "blender/store.blend",
    builder: "blender/scripts/build_store.py",
    glb: "public/assets/store/store.glb",
    lightmap: "store",
    // Panorama of the interior: image-based light of the store zone (blender/scripts/bake_env.py).
    env: "public/assets/shared/env_store.hdr",
  },
  {
    blend: "blender/scanner_hand.blend",
    builder: "blender/scripts/build_scanner_hand.py",
    glb: "public/assets/shared/scanner_hand.glb",
  },
  {
    blend: "blender/terrace_eggs.blend",
    builder: "blender/scripts/build_terrace_eggs.py",
    glb: "public/assets/eggs/terrace_eggs.glb",
    lightmap: "terrace",
  },
];

function blender(args) {
  execFileSync(BLENDER, ["-b", "--factory-startup", "--python-exit-code", "1", ...args], {
    stdio: ["ignore", "inherit", "inherit"],
  });
}

if (!existsSync(BLENDER)) {
  console.error(`Blender introuvable : ${BLENDER} (définir BLENDER=...)`);
  process.exit(1);
}

for (const asset of ASSETS) {
  const blend = resolve(asset.blend);
  if (rebuild || !existsSync(blend)) {
    console.log(`→ blockout ${asset.blend}`);
    blender(["-P", resolve(asset.builder), "--", blend]);
  }
  // Raw export kept out of the repository, then optimised into public/.
  const raw = resolve("blender/out", asset.glb.split("/").pop());
  console.log(`→ export ${raw}`);
  const flags = [...(noAo ? ["--no-ao"] : []), ...(asset.lightmap ? [`--lightmap=${asset.lightmap}`] : [])];
  blender([blend, "-P", resolve("blender/scripts/export.py"), "--", raw, ...flags]);
  if (asset.env && !noAo) {
    console.log(`→ panorama ${asset.env}`);
    blender([blend, "-P", resolve("blender/scripts/bake_env.py"), "--", resolve(asset.env)]);
  }
  console.log(`→ optimise ${asset.glb}`);
  // With --no-ao the lightmap is not rebaked: the last one is reused when it exists.
  const lightmap = resolve(raw.replace(/\.glb$/, ".lightmap.jpg"));
  const extra = asset.lightmap && existsSync(lightmap) ? [lightmap] : [];
  execFileSync(process.execPath, [resolve("scripts/optimize-glb.mjs"), raw, resolve(asset.glb), ...extra], {
    stdio: "inherit",
  });
}
