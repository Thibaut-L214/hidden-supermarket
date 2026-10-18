// Binds the tileable PBR sets of blender/textures/ to the materials of an exported GLB, by
// material name (blender/textures/surfaces.json). UV0 comes from the export-time box projection
// (blender/scripts/surfaces.py). The colour and roughness textures only modulate the authored
// factors: their values sit just under 1 (COLOUR_CENTRE, ROUGH_CENTRE in make_textures.py), so
// the factors are scaled up by the same amount and the material keeps its authored average.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// Keep in sync with blender/scripts/make_textures.py.
const COLOUR_CENTRE = 0.93;
const ROUGH_CENTRE = 0.85;

const TEXTURES = resolve("blender/textures");

/** Loads each image once per document, however many materials share it. */
function textureCache(doc) {
  const cache = new Map();
  return (file, name) => {
    let texture = cache.get(file);
    if (!texture) {
      texture = doc
        .createTexture(name)
        .setImage(new Uint8Array(readFileSync(resolve(TEXTURES, file))))
        .setMimeType("image/jpeg");
      cache.set(file, texture);
    }
    return texture;
  };
}

/** Returns how many materials received a surface set. */
export function applySurfaces(doc) {
  const { sets, goods, materials: mapping } = JSON.parse(
    readFileSync(resolve(TEXTURES, "surfaces.json"), "utf8"),
  );
  const texture = textureCache(doc);
  let bound = 0;
  for (const material of doc.getRoot().listMaterials()) {
    const name = sets[mapping[material.getName()]] ? mapping[material.getName()] : null;
    if (!name) continue;
    const set = sets[name];
    const [r, g, b, a] = material.getBaseColorFactor();
    material
      .setBaseColorFactor([r, g, b].map((c) => Math.min(1, c / COLOUR_CENTRE)).concat(a))
      .setBaseColorTexture(texture(`${name}_color.jpg`, `${name}_color`))
      .setNormalTexture(texture(`${name}_normal.jpg`, `${name}_normal`))
      .setNormalScale(set.normalScale)
      .setMetallicRoughnessTexture(texture(`${name}_orm.jpg`, `${name}_orm`))
      .setRoughnessFactor(Math.min(1, material.getRoughnessFactor() / ROUGH_CENTRE));
    bound += 1;
  }
  // Products: colours stay as authored, their rounded edges and grooves come from one normal atlas.
  for (const material of doc.getRoot().listMaterials()) {
    if (!material.getName().startsWith(goods.prefix)) continue;
    material
      .setNormalTexture(texture(goods.normal, "goods_normal"))
      .setNormalScale(goods.normalScale);
    bound += 1;
  }
  // UV0 is dead weight on primitives whose material took no texture.
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const primitive of mesh.listPrimitives()) {
      const material = primitive.getMaterial();
      if (!material?.getBaseColorTexture() && !material?.getNormalTexture()) {
        primitive.setAttribute("TEXCOORD_0", null);
      }
    }
  }
  return bound;
}

/**
 * Binds the baked lightmap (blender/scripts/lightmap.py) as occlusionTexture on TEXCOORD_1.
 * three.js multiplies it into the indirect light, so the baked soft shadows and light pools
 * modulate the hemisphere and environment lighting. Returns how many materials received it.
 */
export function applyLightmap(doc, path) {
  const texture = doc
    .createTexture("lightmap")
    .setImage(new Uint8Array(readFileSync(path)))
    .setMimeType("image/jpeg");
  const materials = new Set();
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const primitive of mesh.listPrimitives()) {
      const material = primitive.getMaterial();
      if (material && primitive.getAttribute("TEXCOORD_1")) materials.add(material);
    }
  }
  for (const material of materials) {
    material.setOcclusionTexture(texture).setOcclusionStrength(1);
    material.getOcclusionTextureInfo().setTexCoord(1);
  }
  return materials.size;
}
