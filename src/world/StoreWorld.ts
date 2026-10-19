import { Box3, Euler, type Object3D, Quaternion, type Scene, Vector3 } from "three";
import type { AssetManager } from "../core/AssetManager";
import { STORE_CONTRACT, shelfNodes } from "../core/assetContract";
import type { ChainId } from "../core/chain";
import { CHAINS } from "../data/chains";
import { createLabel, createScanPictogram, createSignLabel } from "./labels";

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
    // Aisle signs (hanging, two-sided) and the store sign carry a generic word in glTF
    // extras (no brand, no price); the text is drawn here.
    root.traverse((object) => {
      const label = object.userData.label;
      if (typeof label !== "string") return;
      if (/^AISLE_SIGN_\d+$/.test(object.name)) {
        createSignLabel(object, label, true).forEach((face) => object.add(face));
      } else if (object.name === "STORE_SIGN" || object.name.startsWith("PRODUCT_SIGN_")) {
        object.add(createSignLabel(object, label));
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
