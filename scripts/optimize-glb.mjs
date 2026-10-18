// Optimises a Blender export for the web (docs/TECH.md §07): dedup, prune (empties kept:
// anchors, paths and spawn points are leaves), weld, reorder, then meshopt compression with
// filters. No quantisation: it would move dequantisation scales into node transforms, and
// the runtime relies on node pivots and unit scale (naming contract, doors, roof).
// Usage: node scripts/optimize-glb.mjs <in.glb> <out.glb>
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { Logger, NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS, EXTMeshoptCompression } from "@gltf-transform/extensions";
import { dedup, prune, reorder, weld } from "@gltf-transform/functions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error("usage: optimize-glb.mjs <in.glb> <out.glb>");
  process.exit(1);
}

await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ "meshopt.encoder": MeshoptEncoder, "meshopt.decoder": MeshoptDecoder });

const doc = await io.read(input);
doc.setLogger(new Logger(Logger.Verbosity.WARN));
await doc.transform(
  dedup(),
  prune({ keepLeaves: true, keepExtras: true }),
  weld(),
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
