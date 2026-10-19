// Way out (docs/GDD.md §03.10, §09): automatic sliding doors. Both leaves slide into the wall
// as the player approaches, from inside or from the forecourt, and close once nobody is near.
// Stepping outside starts the exit; walking past the volunteers opens the end menu; walking
// back in cancels. The doors never close on the player, and nobody blocks the way.
import { Box3, type Object3D } from "three";
import { EXIT_NODES } from "../../core/assetContract";
import type { GameState } from "../../core/GameState";
import type { Rect, Vec2 } from "../../world/CollisionWorld";

export const EXIT_DOOR_SECONDS = 0.8;
/** Approach distances that open the doors, in metres: inside the store, and on the forecourt. */
const REACH_INSIDE = 0.8;
const REACH_OUTSIDE = 3.0;
const REACH_SIDE = 1.0;
/**
 * Wider zone in which walking towards the doors already opens them, so they are open by the time
 * the player arrives (they take EXIT_DOOR_SECONDS; walking is about 2 m/s). Standing still or
 * turning away there does nothing: the spawn point lies inside it.
 */
const EARLY_INSIDE = 3.6;
const EARLY_OUTSIDE = 6.0;
const EARLY_SIDE = 1.5;
/** Speed towards the doors, in m/s, that counts as approaching; faster than this is a teleport. */
const APPROACH_SPEED = 0.25;
const TELEPORT_SPEED = 8;
/** How far each leaf slides into the wall, in metres. */
const SLIDE = 1.45;

export interface ExitSceneDeps {
  game: GameState;
  storeRoot: Object3D;
  player: { readonly radius: number; position(): Vec2 };
  /** Called after the doors moved, so colliders follow. */
  onDoorsMoved: () => void;
}

function footprint(object: Object3D, grow = 0): Rect {
  object.updateWorldMatrix(true, false);
  const box = new Box3().setFromObject(object);
  return {
    minX: box.min.x - grow,
    maxX: box.max.x + grow,
    minZ: box.min.z - grow,
    maxZ: box.max.z + grow,
  };
}

export function inside(p: Vec2, r: Rect): boolean {
  return p.x >= r.minX && p.x <= r.maxX && p.z >= r.minZ && p.z <= r.maxZ;
}

interface Leaf {
  object: Object3D;
  baseX: number;
  direction: number;
}

export class ExitScene {
  /** Door opening in [0, 1]. */
  openness = 0;
  private readonly leaves: Leaf[];
  private readonly exitZone: Rect;
  private readonly parvisZone: Rect;
  /** Where the sliding leaves stand, grown by the player's radius: no closing while occupied. */
  private readonly doorway: Rect;
  /** Where standing opens the doors: in front of the entrance on both sides. */
  private readonly approach: Rect;
  /** Wider zone where walking towards the doors opens them early. */
  private readonly early: Rect;
  /** World Z of the outer face of the entrance: beyond it the player is outdoors. */
  private readonly outsideZ: number;
  private previous: Vec2 | null = null;
  private approaching = false;

  constructor(private readonly deps: ExitSceneDeps) {
    const find = (name: string) => {
      const object = deps.storeRoot.getObjectByName(name);
      if (!object) throw new Error(`${name} absent`);
      return object;
    };
    const left = find(EXIT_NODES.doorL);
    const right = find(EXIT_NODES.doorR);
    this.leaves = [
      { object: left, baseX: left.position.x, direction: -1 },
      { object: right, baseX: right.position.x, direction: 1 },
    ];
    this.exitZone = footprint(find(EXIT_NODES.exitZone));
    this.parvisZone = footprint(find(EXIT_NODES.parvisZone));
    const doors = [footprint(left), footprint(right)];
    const grow = deps.player.radius + 0.1;
    this.doorway = {
      minX: Math.min(...doors.map((d) => d.minX)) - grow,
      maxX: Math.max(...doors.map((d) => d.maxX)) + grow,
      minZ: Math.min(...doors.map((d) => d.minZ)) - grow,
      maxZ: Math.max(...doors.map((d) => d.maxZ)) + grow,
    };
    this.outsideZ = Math.max(...doors.map((d) => d.maxZ));
    this.approach = {
      minX: this.doorway.minX - REACH_SIDE,
      maxX: this.doorway.maxX + REACH_SIDE,
      minZ: this.exitZone.minZ - REACH_INSIDE,
      maxZ: this.outsideZ + REACH_OUTSIDE,
    };
    this.early = {
      minX: this.doorway.minX - EARLY_SIDE,
      maxX: this.doorway.maxX + EARLY_SIDE,
      minZ: this.exitZone.minZ - EARLY_INSIDE,
      maxZ: this.outsideZ + EARLY_OUTSIDE,
    };
  }

  /** True while the player walks towards the doorway inside the early zone. */
  private updateApproach(p: Vec2, dt: number): void {
    const last = this.previous;
    this.previous = { ...p };
    if (!inside(p, this.early)) {
      this.approaching = false;
      return;
    }
    if (!last || dt <= 0) return;
    const doorZ = (this.exitZone.minZ + this.outsideZ) / 2;
    const towards = Math.sign(doorZ - p.z) * ((p.z - last.z) / dt);
    if (Math.abs(p.z - last.z) / dt > TELEPORT_SPEED) this.approaching = false;
    else if (towards > APPROACH_SPEED) this.approaching = true;
    else if (towards < -APPROACH_SPEED) this.approaching = false;
  }

  /** Outdoor light share, like the terrace: full on the forecourt, some through the doors. */
  get outdoorTarget(): number {
    const p = this.deps.player.position();
    if (p.z > this.outsideZ) return 1;
    return this.deps.game.snapshot.state === "EXIT" ? 0.3 * this.openness : 0;
  }

  update(dt: number): void {
    const { game, player } = this.deps;
    const p = player.position();
    const { state } = game.snapshot;

    if (state === "STORE" && p.z > this.outsideZ) {
      game.send({ type: "EXIT_REQUESTED" });
    } else if (state === "EXIT" && p.z < this.exitZone.minZ) {
      game.send({ type: "EXIT_CANCELLED" });
    } else if (state === "EXIT" && inside(p, this.parvisZone)) {
      game.send({ type: "PARVIS_REACHED" });
    }

    // Automatic doors serve the store and the way out only: while a shelf is open, the
    // visit continues behind it.
    const current = game.snapshot.state;
    const serving = current === "STORE" || current === "EXIT";
    this.updateApproach(p, dt);
    const open = serving && (inside(p, this.approach) || this.approaching);
    const goal = open ? 1 : 0;
    // Never slide a leaf back while someone stands in the doorway.
    if (!open && inside(p, this.doorway)) return;
    if (this.openness === goal || dt <= 0) return;
    const step = dt / EXIT_DOOR_SECONDS;
    this.openness =
      goal > this.openness ? Math.min(this.openness + step, 1) : Math.max(this.openness - step, 0);
    for (const leaf of this.leaves) {
      leaf.object.position.x = leaf.baseX + leaf.direction * SLIDE * this.openness;
    }
    this.deps.onDoorsMoved();
  }
}
