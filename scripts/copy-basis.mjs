// Copies three.js's Basis Universal transcoder next to the app, for KTX2 textures.
import { cpSync, mkdirSync } from "node:fs";

mkdirSync("public/basis", { recursive: true });
for (const file of ["basis_transcoder.js", "basis_transcoder.wasm"]) {
  cpSync(`node_modules/three/examples/jsm/libs/basis/${file}`, `public/basis/${file}`);
}
