// Simplified walking collisions (docs/TECH.md §01, docs/GDD.md §02: no physics engine).
// Floors are flat, so the player is a circle on the XZ plane and colliders are the XZ
// footprints of COL_* meshes that overlap the player's height.
import { Box3, type Object3D } from "three";

export interface Vec2 {
  x: number;
  z: number;
}

export interface Rect {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), hi);

/** Smallest displacement of circle (p, r) out of rect, or null when they do not overlap. */
export function pushOut(p: Vec2, r: number, rect: Rect): Vec2 | null {
  const dx = p.x - clamp(p.x, rect.minX, rect.maxX);
  const dz = p.z - clamp(p.z, rect.minZ, rect.maxZ);
  const d2 = dx * dx + dz * dz;
  if (d2 >= r * r) return null;
  if (d2 > 1e-12) {
    const d = Math.sqrt(d2);
    const k = (r - d) / d;
    return { x: dx * k, z: dz * k };
  }
  // Centre inside the rect: leave through the nearest side.
  const exits: Vec2[] = [
    { x: rect.minX - r - p.x, z: 0 },
    { x: rect.maxX + r - p.x, z: 0 },
    { x: 0, z: rect.minZ - r - p.z },
    { x: 0, z: rect.maxZ + r - p.z },
  ];
  return exits.reduce((best, e) => (Math.abs(e.x + e.z) < Math.abs(best.x + best.z) ? e : best));
}

/** Pushes the circle out of every rect; a few passes settle corners. */
export function resolve(p: Vec2, r: number, rects: readonly Rect[], passes = 4): Vec2 {
  let { x, z } = p;
  for (let i = 0; i < passes; i++) {
    let moved = false;
    for (const rect of rects) {
      const push = pushOut({ x, z }, r, rect);
      if (push) {
        x += push.x;
        z += push.z;
        moved = true;
      }
    }
    if (!moved) break;
  }
  return { x, z };
}

/** Moves in sub-steps no longer than half the radius, so fast moves cannot cross thin walls. */
export function moveCircle(from: Vec2, delta: Vec2, r: number, rects: readonly Rect[]): Vec2 {
  const length = Math.hypot(delta.x, delta.z);
  const steps = Math.max(1, Math.ceil(length / (r * 0.5)));
  let p = from;
  for (let i = 0; i < steps; i++) {
    p = resolve({ x: p.x + delta.x / steps, z: p.z + delta.z / steps }, r, rects);
  }
  return p;
}

interface Collider {
  object: Object3D;
  rect: Rect | null;
}

export class CollisionWorld {
  private colliders: Collider[] = [];
  private readonly box = new Box3();

  /**
   * @param radius player radius in metres
   * @param minY,maxY vertical band of the player's body; colliders outside it are ignored
   */
  constructor(
    readonly radius = 0.3,
    private readonly minY = 0.05,
    private readonly maxY = 1.9,
  ) {}

  /** Registers every COL_* descendant of root. */
  addFrom(root: Object3D): void {
    root.traverse((object) => {
      if (object.name.startsWith("COL_")) this.colliders.push({ object, rect: null });
    });
    this.refresh();
  }

  /** Forgets the colliders that belong to root (e.g. an unloaded chain module). */
  removeFrom(root: Object3D): void {
    this.colliders = this.colliders.filter(({ object }) => {
      let node: Object3D | null = object;
      while (node && node !== root) node = node.parent;
      return node !== root;
    });
  }

  /** Recomputes footprints from current world transforms (call after moving a collider). */
  refresh(): void {
    for (const collider of this.colliders) {
      collider.object.updateWorldMatrix(true, false);
      const { min, max } = this.box.setFromObject(collider.object);
      collider.rect =
        max.y < this.minY || min.y > this.maxY
          ? null
          : { minX: min.x, maxX: max.x, minZ: min.z, maxZ: max.z };
    }
  }

  get rects(): Rect[] {
    return this.colliders.flatMap(({ rect }) => (rect ? [rect] : []));
  }

  move(from: Vec2, delta: Vec2): Vec2 {
    return moveCircle(from, delta, this.radius, this.rects);
  }
}
