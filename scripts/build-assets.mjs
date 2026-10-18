// Builds blockout .blend files (only when missing), exports every .blend to GLB and optimises it.
// Usage: pnpm assets [--rebuild]   (--rebuild regenerates blockouts, overwriting the .blend)
// BLENDER env var overrides the Blender executable path.
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const BLENDER = process.env.BLENDER ?? "/Applications/Blender.app/Contents/MacOS/Blender";
const rebuild = process.argv.includes("--rebuild");

const ASSETS = [
  {
    blend: "blender/store.blend",
    builder: "blender/scripts/build_store.py",
    glb: "public/assets/store/store.glb",
  },
  {
    blend: "blender/terrace_eggs.blend",
    builder: "blender/scripts/build_terrace_eggs.py",
    glb: "public/assets/eggs/terrace_eggs.glb",
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
  blender([blend, "-P", resolve("blender/scripts/export.py"), "--", raw]);
  console.log(`→ optimise ${asset.glb}`);
  execFileSync(process.execPath, [resolve("scripts/optimize-glb.mjs"), raw, resolve(asset.glb)], {
    stdio: "inherit",
  });
}
