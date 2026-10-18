// Optimises a Blender export for the web (docs/TECH.md §07): dedup, prune (empties kept:
// anchors, paths and spawn points are leaves), weld, reorder, then meshopt compression with
// filters. No quantisation: it would move dequantisation scales into node transforms, and
// the runtime relies on node pivots and unit scale (naming contract, doors, roof).
// Usage: node scripts/optimize-glb.mjs <in.glb> <out.glb> [lightmap.jpg]
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { Logger, NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS, EXTMeshoptCompression } from "@gltf-transform/extensions";
import { dedup, prune, quantize, reorder, weld } from "@gltf-transform/functions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";
import { applyLightmap, applySurfaces } from "./lib/surfaces.mjs";

const [input, output, lightmap] = process.argv.slice(2);
if (!input || !output) {
  console.error("usage: optimize-glb.mjs <in.glb> <out.glb> [lightmap.jpg]");
  process.exit(1);
}

await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ "meshopt.encoder": MeshoptEncoder, "meshopt.decoder": MeshoptDecoder });

const doc = await io.read(input);
doc.setLogger(new Logger(Logger.Verbosity.WARN));
const surfaces = applySurfaces(doc);
console.log(`  ${surfaces} matériau(x) texturé(s)`);
if (lightmap) console.log(`  lightmap sur ${applyLightmap(doc, lightmap)} matériau(x)`);
await doc.transform(
  dedup(),
  prune({ keepLeaves: true, keepExtras: true }),
  weld(),
  // Baked occlusion (COLOR_0) on 8 bits is plenty; positions are left alone (see above).
  quantize({ pattern: /^COLOR_0$/, quantizeColor: 8 }),
  reorder({ encoder: MeshoptEncoder }),
);
doc
  .createExtension(EXTMeshoptCompression)
  .setRequired(true)
  .setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.FILTER });

// KTX2 needs KTX-Software (toktx). Blockout assets carry no texture; textured assets from the
// artists are compressed once toktx is installed (see CLAUDE.md, pipeline d'assets).
const textures = doc.getRoot().listTextures().length;
if (textures > 0) {
  let toktx = false;
  try {
    execFileSync("toktx", ["--version"], { stdio: "ignore" });
    toktx = true;
  } catch {
    // not installed
  }
  console.warn(
    toktx
      ? `⚠ ${textures} texture(s) : lancer « npx @gltf-transform/cli etc1s|uastc » pour KTX2.`
      : `⚠ ${textures} texture(s) non compressée(s) : installer KTX-Software (toktx) pour KTX2.`,
  );
}

mkdirSync(dirname(output), { recursive: true });
await io.write(output, doc);
