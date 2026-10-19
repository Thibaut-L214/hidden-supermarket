// Builds blockout .blend files (only when missing), exports every .blend to GLB and optimises it.
// Usage: pnpm assets [--rebuild] [--no-ao] [--only=store,beef]
//   --rebuild regenerates blockouts, overwriting the .blend; --no-ao skips the occlusion and
//   lightmap bakes (the store reuses its last lightmap if the layout has not changed).
// BLENDER env var overrides the Blender executable path.
import { execFileSync } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const BLENDER = process.env.BLENDER ?? "/Applications/Blender.app/Contents/MacOS/Blender";
const rebuild = process.argv.includes("--rebuild");
const noAo = process.argv.includes("--no-ao");

const only = process.argv
  .find((arg) => arg.startsWith("--only="))
  ?.slice(7)
  .split(",");

const ASSETS = [
  {
    id: "store",
    blend: "blender/store.blend",
    builder: "blender/scripts/build_store.py",
    glb: "public/assets/store/store.glb",
    lightmap: "store",
    // Panorama of the interior: image-based light of the store zone (blender/scripts/bake_env.py).
    env: "public/assets/shared/env_store.hdr",
  },
  {
    id: "scanner",
    blend: "blender/scanner_hand.blend",
    builder: "blender/scripts/build_scanner_hand.py",
    glb: "public/assets/shared/scanner_hand.glb",
  },
  {
    id: "eggs",
    blend: "blender/terrace_eggs.blend",
    builder: "blender/scripts/build_terrace_eggs.py",
    glb: "public/assets/eggs/terrace_eggs.glb",
    lightmap: "terrace",
  },
  {
    id: "beef",
    blend: "blender/terrace_beef.blend",
    builder: "blender/scripts/build_terrace_beef.py",
    glb: "public/assets/beef/terrace_beef.glb",
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

if (only?.some((id) => !ASSETS.some((asset) => asset.id === id))) {
  throw new Error("--only accepts store, scanner, eggs, beef");
}

for (const asset of ASSETS.filter((asset) => !only || only.includes(asset.id))) {
  const blend = resolve(asset.blend);
  const regenerated = rebuild || !existsSync(blend);
  if (regenerated) {
    console.log(`→ blockout ${asset.blend}`);
    blender(["-P", resolve(asset.builder), "--", blend]);
  }
  // Raw export kept out of the repository, then optimised into public/.
  const raw = resolve("blender/out", asset.glb.split("/").pop());
  console.log(`→ export ${raw}`);
  // Geometry changes invalidate the old atlas. Fast rebuilds export without it.
  const useLightmap = asset.lightmap && !(regenerated && noAo);
  if (regenerated && noAo && asset.lightmap) {
    rmSync(raw.replace(/\.glb$/, ".lightmap.jpg"), { force: true });
  }
  const flags = [
    ...(noAo ? ["--no-ao"] : []),
    ...(useLightmap ? [`--lightmap=${asset.lightmap}`] : []),
  ];
  blender([blend, "-P", resolve("blender/scripts/export.py"), "--", raw, ...flags]);
  if (asset.env && !noAo) {
    console.log(`→ panorama ${asset.env}`);
    blender([blend, "-P", resolve("blender/scripts/bake_env.py"), "--", resolve(asset.env)]);
  }
  console.log(`→ optimise ${asset.glb}`);
  // Reuse an atlas only while its geometry stays unchanged.
  const lightmap = resolve(raw.replace(/\.glb$/, ".lightmap.jpg"));
  const extra = useLightmap && existsSync(lightmap) ? [lightmap] : [];
  execFileSync(
    process.execPath,
    [resolve("scripts/optimize-glb.mjs"), raw, resolve(asset.glb), ...extra],
    {
      stdio: "inherit",
    },
  );
}
