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
      // « Scannable » pictogram beside the sign (docs/GDD.md §06.0).
      const picto = root.getObjectByName(shelfNodes(chain.id).picto);
      if (picto) picto.add(createScanPictogram(picto));
    }
    // Hanging aisle signs carry their generic category in glTF extras (no brand, no price).
    root.traverse((object) => {
      const label = object.userData.label;
      if (/^AISLE_SIGN_\d+$/.test(object.name) && typeof label === "string") {
        createSignLabel(object, label, true).forEach((face) => object.add(face));
      }
    });
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

/**
 * Flat label just in front of a sign panel's front face (+Z in glTF space); `twoSided` adds
 * the same label on the back face, for hanging signs seen from both aisles.
 */
function createSignLabel(sign: Object3D, text: string): Mesh;
function createSignLabel(sign: Object3D, text: string, twoSided: true): Mesh[];
function createSignLabel(sign: Object3D, text: string, twoSided = false): Mesh | Mesh[] {
  const size = panelSize(sign);
  const faces = (twoSided ? [1, -1] : [1]).map((side) => {
    const label = createLabel(text, size.x * 0.95, size.y * 0.9, "#f7f4ec", "#3f5a3c");
    label.name = `${sign.name}_LABEL${side < 0 ? "_BACK" : ""}`;
    // Sign panels are unrotated boxes centred on their origin.
    label.position.set(0, 0, side * (size.z / 2 + 0.002));
    if (side < 0) label.rotation.y = Math.PI;
    return label;
  });
  return twoSided ? faces : faces[0]!;
}

function createScanPictogram(plate: Object3D): Mesh {
  const size = panelSize(plate);
  const mesh = createPlate(size.x * 0.9, size.y * 0.9, "#f7f4ec", (ctx, w, h) => {
    // Viewfinder corners around a scan line: reads as « this shelf can be scanned ».
    const m = w * 0.18;
    const arm = w * 0.18;
    ctx.strokeStyle = "#3f5a3c";
    ctx.lineWidth = w * 0.06;
    ctx.lineCap = "round";
    for (const [x, y, dx, dy] of [
      [m, m, 1, 1],
      [w - m, m, -1, 1],
      [m, h - m, 1, -1],
      [w - m, h - m, -1, -1],
    ] as const) {
      ctx.beginPath();
      ctx.moveTo(x, y + dy * arm);
      ctx.lineTo(x, y);
      ctx.lineTo(x + dx * arm, y);
      ctx.stroke();
    }
    ctx.strokeStyle = "#6f8a68";
    ctx.beginPath();
    ctx.moveTo(m + w * 0.06, h / 2);
    ctx.lineTo(w - m - w * 0.06, h / 2);
    ctx.stroke();
  });
  mesh.name = `${plate.name}_ICON`;
  mesh.position.set(0, 0, size.z / 2 + 0.002);
  return mesh;
}

function panelSize(panel: Object3D): Vector3 {
  panel.updateWorldMatrix(true, false);
  return new Box3().setFromObject(panel).getSize(new Vector3());
}

/** Text drawn on a canvas, shrunk to fit, mapped on a plane of the given size in metres. */
function createLabel(
  text: string,
  width: number,
  height: number,
  background: string,
  ink: string,
): Mesh {
  return createPlate(width, height, background, (ctx, w, h) => {
    let px = Math.round(h * 0.6);
    ctx.font = `600 ${px}px system-ui, sans-serif`;
    const measured = ctx.measureText(text).width;
    if (measured > w * 0.9) {
      px = Math.floor((px * w * 0.9) / measured);
      ctx.font = `600 ${px}px system-ui, sans-serif`;
    }
    ctx.fillStyle = ink;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, w / 2, h / 2 + 4);
  });
}

function createPlate(
  width: number,
  height: number,
  background: string,
  draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void,
): Mesh {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = Math.round((512 * height) / width);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D indisponible");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  draw(ctx, canvas.width, canvas.height);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.anisotropy = 4;
  return new Mesh(
    new PlaneGeometry(width, height),
    new MeshStandardMaterial({ map: texture, roughness: 0.8 }),
  );
}
