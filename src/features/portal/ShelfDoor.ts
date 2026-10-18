// Two rigid shelf halves rotating around their hinges (docs/DA.md §05, docs/DECISIONS.md).
// Poses are computed from the reference transforms captured at load, never accumulated, so
// any number of open/close cycles ends on exactly the same pose (docs/TECH.md §05).
import { Box3, type Object3D, Quaternion, Vector3 } from "three";
import { shelfNodes } from "../../core/assetContract";
import { ease } from "../../core/easing";
import type { ChainId } from "../../core/chain";
import type { Vec2 } from "../../world/CollisionWorld";

export const DOOR_SECONDS = 2.5;
export const DOOR_ANGLE = Math.PI / 2;
/** Extra clearance around the swept area, in metres. */
export const SWING_MARGIN = 0.15;

export type DoorTarget = "open" | "closed" | "hold";

export interface SwingGeometry {
  /** Hinge positions on the XZ plane (front outer corners of the shelf). */
  hinges: readonly Vec2[];
  /** Unit vector on the XZ plane from the shelf towards the store. */
  storeNormal: Vec2;
  /** Width of one door, from hinge to the shelf centre. */
  width: number;
  /** Shelf depth, from its front to the wall. */
  depth: number;
}

/**
 * True when a player of the given radius stands where a door sweeps or rests: within reach of
 * a hinge and in front of the wall. Conservative on purpose (whole half-disc, not the arc).
 */
export function inSwingZone(p: Vec2, g: SwingGeometry, radius: number): boolean {
  const reach = g.width + radius + SWING_MARGIN;
  const behind = g.depth + radius + SWING_MARGIN;
  return g.hinges.some((h) => {
    const dx = p.x - h.x;
    const dz = p.z - h.z;
    const along = dx * g.storeNormal.x + dz * g.storeNormal.z;
    return Math.hypot(dx, dz) < reach && along > -behind;
  });
}

interface Leaf {
  door: Object3D;
  reference: Quaternion;
  /** +1 or -1: rotation sign that swings this leaf towards the store. */
  sign: number;
}

const UP = new Vector3(0, 1, 0);

export class ShelfDoor {
  /** Linear progress in [0, 1]; the pose uses its eased value. */
  openness = 0;
  readonly geometry: SwingGeometry;
  private readonly leaves: Leaf[];
  private readonly turn = new Quaternion();

  constructor(shelfRoot: Object3D, chain: ChainId) {
    const n = shelfNodes(chain);
    const find = (name: string) => {
      const object = shelfRoot.getObjectByName(name);
      if (!object) throw new Error(`${name} absent`);
      return object;
    };
    shelfRoot.updateWorldMatrix(true, true);

    // Left hinge rotates clockwise seen from above (negative angle), right hinge the opposite.
    this.leaves = [
      { door: find(n.doorL), reference: find(n.doorL).quaternion.clone(), sign: -1 },
      { door: find(n.doorR), reference: find(n.doorR).quaternion.clone(), sign: 1 },
    ];

    const hinges = [n.hingeL, n.hingeR].map((name) => {
      const w = find(name).getWorldPosition(new Vector3());
      return { x: w.x, z: w.z };
    });
    const normal = new Vector3(0, 0, 1).applyQuaternion(
      shelfRoot.getWorldQuaternion(new Quaternion()),
    );
    const [l, r] = hinges as [Vec2, Vec2];
    const size = new Box3().setFromObject(find(n.scan)).getSize(new Vector3());
    this.geometry = {
      hinges,
      storeNormal: { x: normal.x, z: normal.z },
      width: Math.hypot(r.x - l.x, r.z - l.z) / 2,
      depth: Math.abs(size.x * normal.x) + Math.abs(size.z * normal.z),
    };
  }

  get isOpen(): boolean {
    return this.openness === 1;
  }

  get isClosed(): boolean {
    return this.openness === 0;
  }

  /** Moves towards the target; returns true when the pose changed. */
  update(dt: number, target: DoorTarget): boolean {
    if (target === "hold" || dt <= 0) return false;
    const goal = target === "open" ? 1 : 0;
    if (this.openness === goal) return false;
    const step = dt / DOOR_SECONDS;
    this.openness =
      goal > this.openness ? Math.min(this.openness + step, 1) : Math.max(this.openness - step, 0);
    this.apply();
    return true;
  }

  /** Immediate closing, for the safe return after an error. */
  snapClosed(): void {
    this.openness = 0;
    this.apply();
  }

  private apply(): void {
    const angle = DOOR_ANGLE * ease(this.openness);
    for (const leaf of this.leaves) {
      this.turn.setFromAxisAngle(UP, leaf.sign * angle);
      leaf.door.quaternion.copy(leaf.reference).multiply(this.turn);
    }
  }
}
