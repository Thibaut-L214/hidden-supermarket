import {
  Box3,
  CanvasTexture,
  Euler,
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
import { STORE_CONTRACT, shelfNodes } from "../core/assetContract";
import type { ChainId } from "../core/chain";
import { CHAINS } from "../data/chains";

/** Eye height of the player above the floor, in metres. */
export const EYE_HEIGHT = 1.6;

export class StoreWorld {
  readonly root: Object3D;

  private constructor(root: Object3D) {
    this.root = root;
  }

  static async load(assets: AssetManager, scene: Scene): Promise<StoreWorld> {
    const root = await assets.load(STORE_CONTRACT);
    scene.add(root);
    // Sign labels are drawn at runtime so that wording stays out of the GLB.
    for (const chain of Object.values(CHAINS)) {
      const sign = root.getObjectByName(shelfNodes(chain.id).sign);
      if (sign) sign.add(createSignLabel(sign, chain.label));
    }
    return new StoreWorld(root);
  }

  /** Discreet « exploré » plate under the shelf's sign (docs/GDD.md §06.6); idempotent. */
  markExplored(chain: ChainId): void {
    const sign = this.root.getObjectByName(shelfNodes(chain).sign);
    if (!sign || sign.getObjectByName(`${sign.name}_EXPLORED`)) return;
    const size = new Box3().setFromObject(sign).getSize(new Vector3());
    const plate = createLabel("✓ Exploré", 0.7, 0.18, "#e4ebdf", "#3f5a3c");
    plate.name = `${sign.name}_EXPLORED`;
    plate.position.set(0, -size.y / 2 - 0.14, size.z / 2 + 0.004);
    sign.add(plate);
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

/** Flat label laid just in front of the sign panel's front face (+Z in glTF space). */
function createSignLabel(sign: Object3D, text: string): Mesh {
  sign.updateWorldMatrix(true, false);
  const size = new Box3().setFromObject(sign).getSize(new Vector3());
  const label = createLabel(text, size.x * 0.95, size.y * 0.9, "#f7f4ec", "#3f5a3c");
  label.name = `${sign.name}_LABEL`;
  // Sign panels are unrotated boxes centred on their origin.
  label.position.set(0, 0, size.z / 2 + 0.002);
  return label;
}

/** Text drawn on a canvas and mapped on a plane of the given size in metres. */
function createLabel(
  text: string,
  width: number,
  height: number,
  background: string,
  ink: string,
): Mesh {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = Math.round((512 * height) / width);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D indisponible");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = ink;
  ctx.font = `600 ${Math.round(canvas.height * 0.6)}px system-ui, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 4);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.anisotropy = 4;
  return new Mesh(
    new PlaneGeometry(width, height),
    new MeshStandardMaterial({ map: texture, roughness: 0.8 }),
  );
}
