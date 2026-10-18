// Prints triangle and vertex counts of a GLB, total and per node (heaviest first).
// Usage: node scripts/inspect-glb.mjs public/assets/store/store.glb
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.decoder": MeshoptDecoder });
const doc = await io.read(process.argv[2]);
const rows = [];
let total = 0, verts = 0;
for (const node of doc.getRoot().listNodes()) {
  const mesh = node.getMesh(); if (!mesh) continue;
  let t = 0, v = 0;
  for (const p of mesh.listPrimitives()) { const i = p.getIndices(); const pos = p.getAttribute("POSITION"); v += pos.getCount(); t += (i ? i.getCount() : pos.getCount()) / 3; }
  total += t; verts += v; rows.push([node.getName(), Math.round(t), v]);
}
rows.sort((a, b) => b[1] - a[1]);
console.log("total tris", Math.round(total), "verts", verts);
for (const r of rows.slice(0, 18)) console.log(r.join("\t"));
