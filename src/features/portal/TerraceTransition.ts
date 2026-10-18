// Passage between the store and a chain's terrace (docs/GDD.md §03.4–9, §05 invariants):
// loads the module after a scan, opens the doors once the player is clear, tracks the
// threshold, closes behind the player on return, and restores a safe state after an error.
import { Box3, type Object3D, Quaternion, type Scene, Vector3 } from "three";
import { shelfNodes } from "../../core/assetContract";
import type { AssetManager } from "../../core/AssetManager";
import type { ChainId } from "../../core/chain";
import type { EventBus } from "../../core/EventBus";
import type { GameEvents, GameState, GameStateId } from "../../core/GameState";
import type { CollisionWorld, Rect, Vec2 } from "../../world/CollisionWorld";
import type { ChainConfig } from "../chains/ChainModule";
import { type DoorTarget, ShelfDoor, inSwingZone } from "./ShelfDoor";

export type Side = "store" | "terrace";

const IN_MODULE: readonly GameStateId[] = ["TERRACE", "REVEAL", "CHAIN", "RECAP"];
/** Distance in front of the shelf where a safe return places the player, in metres. */
const SAFE_DISTANCE = 2.5;

export interface Threshold {
  /** XZ footprint of TRIGGER_*_ENTRY: inside it, the side does not change. */
  zone: Rect;
  centre: Vec2;
  /** Unit vector towards the store. */
  storeNormal: Vec2;
}

/** Side of the threshold the player stands on; unchanged while inside the threshold zone. */
export function sideOf(p: Vec2, t: Threshold, previous: Side): Side {
  const { zone } = t;
  if (p.x >= zone.minX && p.x <= zone.maxX && p.z >= zone.minZ && p.z <= zone.maxZ) {
    return previous;
  }
  const along = (p.x - t.centre.x) * t.storeNormal.x + (p.z - t.centre.z) * t.storeNormal.z;
  return along >= 0 ? "store" : "terrace";
}

/** Where the doors should go. They never move while the player stands in their sweep. */
export function doorTarget(state: GameStateId, side: Side, inSwing: boolean): DoorTarget {
  if (IN_MODULE.includes(state)) return "open";
  if (state === "RETURN" && side === "terrace") return "open";
  if (inSwing) return "hold";
  return state === "OPENING" ? "open" : "closed";
}

export interface Player {
  readonly radius: number;
  position(): Vec2;
  teleport(position: Vec2, yaw: number): void;
}

export interface TransitionHud {
  setHint(text: string | null): void;
  alert(text: string): void;
}

interface Portal {
  chain: ChainId;
  door: ShelfDoor;
  threshold: Threshold;
  anchor: Object3D;
  side: Side;
}

export interface TerraceTransitionDeps {
  game: GameState;
  bus: EventBus<GameEvents>;
  assets: AssetManager;
  scene: Scene;
  collisions: CollisionWorld;
  storeRoot: Object3D;
  chains: Partial<Record<ChainId, ChainConfig>>;
  player: Player;
  hud: TransitionHud;
}

export class TerraceTransition {
  private readonly portals = new Map<ChainId, Portal>();
  private module: { chain: ChainId; root: Object3D } | null = null;
  /** Notified when a terrace module enters (root) or leaves (null) the scene. */
  onModuleChange: (chain: ChainId, root: Object3D | null) => void = () => {};

  constructor(private readonly deps: TerraceTransitionDeps) {
    for (const chain of Object.keys(deps.chains) as ChainId[]) {
      const portal = createPortal(deps.storeRoot, chain);
      if (portal) this.portals.set(chain, portal);
    }
    deps.bus.on("stateChanged", ({ from, to, snapshot }) => {
      if (to === "SCANNING" && snapshot.activeChain) void this.load(snapshot.activeChain);
      // Deferred so every listener sees ERROR before the recovery transitions.
      if (to === "ERROR") queueMicrotask(() => this.safeRestore(snapshot.error));
      if (from === "RETURN" && to === "STORE") this.unload();
    });
  }

  /** Whether a terrace is open and the pause menu can offer a return to the store. */
  get canReturn(): boolean {
    const { state } = this.deps.game.snapshot;
    return IN_MODULE.includes(state) || state === "RETURN";
  }

  /**
   * How much of the outdoor light should reach the player, in [0, 1]: full on the terrace,
   * a little through the opening doors (docs/GDD.md §06.1: exposure rises progressively).
   */
  get outdoorTarget(): number {
    const portal = this.activePortal();
    if (!portal || !this.module) return 0;
    return portal.side === "terrace" ? 1 : 0.35 * portal.door.openness;
  }

  update(dt: number): void {
    const { game, player, collisions, hud } = this.deps;
    const { state, activeChain } = game.snapshot;
    const portal = activeChain ? this.portals.get(activeChain) : undefined;
    if (!portal) {
      hud.setHint(null);
      return;
    }

    const p = player.position();
    const side = sideOf(p, portal.threshold, portal.side);
    if (side !== portal.side) {
      portal.side = side;
      if (side === "terrace" && state === "RETURN") game.send({ type: "TERRACE_ENTERED" });
      if (side === "store" && IN_MODULE.includes(state)) game.send({ type: "RETURN_REQUESTED" });
    }

    const current = game.snapshot.state;
    const inSwing = inSwingZone(p, portal.door.geometry, player.radius);
    if (portal.door.update(dt, doorTarget(current, portal.side, inSwing))) collisions.refresh();
    if (current === "OPENING" && portal.door.isOpen) game.send({ type: "DOORS_OPEN" });
    if (current === "RETURN" && portal.door.isClosed) game.send({ type: "DOORS_CLOSED" });

    hud.setHint(hintFor(current, inSwing && portal.side === "store"));
  }

  /** Manual return (pause menu): back in front of the shelf, then the doors close normally. */
  returnToStore(): void {
    const { game } = this.deps;
    const portal = this.activePortal();
    if (!portal || !this.canReturn) return;
    this.placeInFront(portal);
    if (IN_MODULE.includes(game.snapshot.state)) game.send({ type: "RETURN_REQUESTED" });
  }

  private activePortal(): Portal | undefined {
    const chain = this.deps.game.snapshot.activeChain;
    return chain ? this.portals.get(chain) : undefined;
  }

  private async load(chain: ChainId): Promise<void> {
    const { game, assets, scene, collisions, chains } = this.deps;
    const config = chains[chain];
    const portal = this.portals.get(chain);
    if (!config || !portal) {
      game.send({ type: "FAILURE", reason: "Ce rayon n'est pas encore disponible." });
      return;
    }
    portal.side = "store";

    let root: Object3D;
    try {
      root = await assets.load(config.terrace);
    } catch (error) {
      console.error(error);
      if (this.isLoading(chain)) {
        game.send({ type: "FAILURE", reason: "La filière n'a pas pu être chargée." });
      }
      return;
    }
    if (!this.isLoading(chain)) return;

    portal.anchor.getWorldPosition(root.position);
    portal.anchor.getWorldQuaternion(root.quaternion);
    scene.add(root);
    root.updateMatrixWorld(true);
    collisions.addFrom(root);
    this.module = { chain, root };
    try {
      this.onModuleChange(chain, root);
    } catch (error) {
      // A module that loads but cannot be staged must not block the session either.
      console.error(error);
      game.send({ type: "FAILURE", reason: "La filière n'a pas pu être préparée." });
      return;
    }
    game.send({ type: "MODULE_READY" });
  }

  private isLoading(chain: ChainId): boolean {
    const { state, activeChain } = this.deps.game.snapshot;
    return state === "SCANNING" && activeChain === chain;
  }

  private unload(): void {
    if (!this.module) return;
    this.deps.scene.remove(this.module.root);
    this.deps.collisions.removeFrom(this.module.root);
    this.onModuleChange(this.module.chain, null);
    this.module = null;
  }

  /** ERROR → SAFE_RETURN → STORE: player in front of the shelf, doors shut, module gone. */
  private safeRestore(reason?: string): void {
    const { game, collisions, hud } = this.deps;
    const portal = this.activePortal();
    if (portal) {
      const p = this.deps.player.position();
      if (
        portal.side === "terrace" ||
        inSwingZone(p, portal.door.geometry, this.deps.player.radius)
      ) {
        this.placeInFront(portal);
      }
      portal.door.snapClosed();
      collisions.refresh();
    }
    this.unload();
    hud.alert(`${reason ?? "Une erreur est survenue."} Retour au magasin.`);
    game.send({ type: "ERROR_ACKNOWLEDGED" });
    game.send({ type: "SAFE_RESTORED" });
  }

  private placeInFront(portal: Portal): void {
    const [l, r] = portal.door.geometry.hinges as [Vec2, Vec2];
    const n = portal.door.geometry.storeNormal;
    const position = {
      x: (l.x + r.x) / 2 + n.x * SAFE_DISTANCE,
      z: (l.z + r.z) / 2 + n.z * SAFE_DISTANCE,
    };
    // Facing the shelf: forward (-sin yaw, -cos yaw) = -normal.
    this.deps.player.teleport(position, Math.atan2(n.x, n.z));
    portal.side = "store";
  }
}

function hintFor(state: GameStateId, blocking: boolean): string | null {
  if (state === "SCANNING") return "Chargement de la filière…";
  if (state === "OPENING" && blocking) return "Reculez pour laisser le rayon s'ouvrir.";
  if (state === "RETURN" && blocking) return "Écartez-vous pour laisser le rayon se refermer.";
  return null;
}

function createPortal(storeRoot: Object3D, chain: ChainId): Portal | null {
  const n = shelfNodes(chain);
  const shelfRoot = storeRoot.getObjectByName(n.root);
  const entry = shelfRoot?.getObjectByName(n.entry);
  const anchor = shelfRoot?.getObjectByName(n.terraceAnchor);
  if (!shelfRoot || !entry || !anchor) return null;

  const door = new ShelfDoor(shelfRoot, chain);
  entry.updateWorldMatrix(true, false);
  const box = new Box3().setFromObject(entry);
  const centre = box.getCenter(new Vector3());
  const normal = new Vector3(0, 0, 1).applyQuaternion(
    shelfRoot.getWorldQuaternion(new Quaternion()),
  );
  return {
    chain,
    door,
    anchor,
    side: "store",
    threshold: {
      zone: { minX: box.min.x, maxX: box.max.x, minZ: box.min.z, maxZ: box.max.z },
      centre: { x: centre.x, z: centre.z },
      storeNormal: { x: normal.x, z: normal.z },
    },
  };
}
