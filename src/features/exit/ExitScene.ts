// Way out (docs/GDD.md §03.10, §09): at the entrance, E opens the sliding doors onto the
// forecourt; walking past the volunteers opens the end menu. Walking back in cancels. The
// doors never close on the player, and nobody blocks the way.
import { Box3, type Object3D } from "three";
import { EXIT_NODES } from "../../core/assetContract";
import type { GameState } from "../../core/GameState";
import type { Rect, Vec2 } from "../../world/CollisionWorld";

export const EXIT_DOOR_SECONDS = 1.2;
/** How far each leaf slides into the wall, in metres. */
const SLIDE = 1.45;

export interface ExitHud {
  setHint(text: string | null): void;
}

export interface ExitSceneDeps {
  game: GameState;
  storeRoot: Object3D;
  player: { readonly radius: number; position(): Vec2 };
  hud: ExitHud;
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
  /** World Z of the outer face of the entrance: beyond it the player is outdoors. */
  private readonly outsideZ: number;
  private pressed = false;

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
  }

  /** Records an E press; consumed on the next update. */
  press(): void {
    this.pressed = true;
  }

  /** Outdoor light share, like the terrace: full on the forecourt, some through the doors. */
  get outdoorTarget(): number {
    const p = this.deps.player.position();
    if (p.z > this.outsideZ) return 1;
    return this.deps.game.snapshot.state === "EXIT" ? 0.3 * this.openness : 0;
  }

  update(dt: number): void {
    const { game, hud, player } = this.deps;
    const pressed = this.pressed;
    this.pressed = false;
    const p = player.position();
    const { state } = game.snapshot;

    const atDoor = inside(p, this.exitZone);
    if (state === "STORE" && atDoor) {
      hud.setHint("Appuyez sur E pour sortir du magasin.");
      if (pressed) game.send({ type: "EXIT_REQUESTED" });
    } else if (state === "EXIT" && p.z < this.exitZone.minZ) {
      game.send({ type: "EXIT_CANCELLED" });
      hud.setHint(null);
    } else if (state === "EXIT" && inside(p, this.parvisZone)) {
      game.send({ type: "PARVIS_REACHED" });
      hud.setHint(null);
    } else {
      hud.setHint(null);
    }

    const open = game.snapshot.state === "EXIT";
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
