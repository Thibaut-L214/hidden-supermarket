import {
  Box3,
  CanvasTexture,
  DirectionalLight,
  Euler,
  HemisphereLight,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  PlaneGeometry,
  Quaternion,
  SRGBColorSpace,
  Scene,
  Vector3,
} from "three";
import type { AssetManager } from "../core/AssetManager";
import { STORE_CONTRACT } from "../core/assetContract";

/** Eye height of the player above the floor, in metres. */
export const EYE_HEIGHT = 1.6;

// Sign labels are drawn at runtime so that wording stays out of the GLB.
const SIGN_LABELS: Record<string, string> = { SIGN_EGGS: "Œufs" };

export class StoreWorld {
  readonly root: Object3D;

  private constructor(root: Object3D) {
    this.root = root;
  }

  static async load(assets: AssetManager, scene: Scene): Promise<StoreWorld> {
    const root = await assets.load(STORE_CONTRACT);
    scene.add(root, ...createStoreLights());
    for (const [name, label] of Object.entries(SIGN_LABELS)) {
      const sign = root.getObjectByName(name);
      if (sign) sign.add(createSignLabel(sign, label));
    }
    return new StoreWorld(root);
  }

  /** Player spawn on the floor plane; the player faces the spawn's local -Z. */
  spawnPose(): { position: { x: number; z: number }; yaw: number } {
    const spawn = this.root.getObjectByName("SPAWN_PLAYER");
    if (!spawn) throw new Error("SPAWN_PLAYER absent");
    const position = spawn.getWorldPosition(new Vector3());
    const yaw = new Euler().setFromQuaternion(spawn.getWorldQuaternion(new Quaternion()), "YXZ").y;
    return { position: { x: position.x, z: position.z }, yaw };
  }
}

function createStoreLights(): Object3D[] {
  // Broad, even store lighting (docs/DA.md §02A); ceiling panels are emissive only.
  const hemisphere = new HemisphereLight("#fff8ec", "#b9ab90", 1.3);
  const key = new DirectionalLight("#fffaf0", 1.4);
  key.position.set(3, 10, 4);
  return [hemisphere, key];
}

/** Flat label laid just in front of the sign panel's front face (+Z in glTF space). */
function createSignLabel(sign: Object3D, text: string): Mesh {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 144;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D indisponible");
  ctx.fillStyle = "#f7f4ec";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#3f5a3c";
  ctx.font = "600 88px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 4);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.anisotropy = 4;

  sign.updateWorldMatrix(true, false);
  const bounds = new Box3().setFromObject(sign);
  const size = bounds.getSize(new Vector3());
  const label = new Mesh(
    new PlaneGeometry(size.x * 0.95, size.y * 0.9),
    new MeshStandardMaterial({ map: texture, roughness: 0.8 }),
  );
  label.name = `${sign.name}_LABEL`;
  // Sign panels are unrotated boxes centred on their origin.
  label.position.set(0, 0, size.z / 2 + 0.002);
  return label;
}
