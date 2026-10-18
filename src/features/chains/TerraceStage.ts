// Terrace staging (docs/GDD.md §03.5–6, §06.2–3): first contextualisation on the terrace,
// viewpoint at the guardrail, roof reveal with a short caption on the system shown.
import { type Object3D, Vector3 } from "three";
import { terraceNodes } from "../../core/assetContract";
import type { EventBus } from "../../core/EventBus";
import type { GameEvents, GameState } from "../../core/GameState";
import type { Vec2 } from "../../world/CollisionWorld";
import type { Caption } from "../content/types";
import type { ChainConfig } from "./ChainModule";
import { RoofReveal } from "./RoofReveal";

/** Distance to ANCHOR_*_VIEW, in metres, at which the player counts as at the viewpoint. */
export const VIEW_RADIUS = 1.6;
/** How far past the threshold, in metres, the player must be to stand on the terrace. */
const ON_TERRACE = 0.5;

export interface StageHud {
  setHint(text: string | null): void;
  showCaption(caption: Caption | null): void;
}

export interface TerraceStageDeps {
  game: GameState;
  bus: EventBus<GameEvents>;
  player: { position(): Vec2 };
  hud: StageHud;
  reducedMotion: () => boolean;
  /** Optional framing towards a world point; skipped under reduced motion. */
  glance: (target: Vector3) => void;
}

interface Stage {
  config: ChainConfig;
  root: Object3D;
  view: Object3D;
  focus: Object3D;
  roof: RoofReveal;
  welcomed: boolean;
}

export class TerraceStage {
  private stage: Stage | null = null;
  private readonly local = new Vector3();
  private readonly reveals = new WeakMap<Object3D, RoofReveal>();

  constructor(private readonly deps: TerraceStageDeps) {
    deps.bus.on("stateChanged", ({ to }) => {
      const stage = this.stage;
      if (!stage) return;
      if (to === "REVEAL") {
        if (!deps.reducedMotion()) deps.glance(stage.focus.getWorldPosition(new Vector3()));
        deps.hud.showCaption(stage.config.captions.reveal);
      }
      if (to === "RETURN") deps.hud.showCaption(null);
    });
  }

  /** Binds a freshly loaded terrace module; its roof starts closed. */
  attach(config: ChainConfig, root: Object3D): void {
    const n = terraceNodes(config.id);
    const find = (name: string) => {
      const object = root.getObjectByName(name);
      if (!object) throw new Error(`${name} absent`);
      return object;
    };
    this.stage?.roof.reset();
    // Modules are cached by the asset manager: reuse the reveal (and its material copies).
    let roof = this.reveals.get(root);
    if (!roof) {
      roof = new RoofReveal(find(n.roof), this.deps.reducedMotion);
      this.reveals.set(root, roof);
    }
    roof.reset();
    this.stage = { config, root, view: find(n.view), focus: find(n.focus), roof, welcomed: false };
  }

  detach(): void {
    this.stage?.roof.reset();
    this.stage = null;
    this.deps.hud.setHint(null);
    this.deps.hud.showCaption(null);
  }

  update(dt: number): void {
    const { game, hud } = this.deps;
    const stage = this.stage;
    if (!stage) return;
    const { state } = game.snapshot;

    if (state === "TERRACE") {
      const onTerrace = this.isOnTerrace(stage);
      if (onTerrace && !stage.welcomed) {
        stage.welcomed = true;
        hud.showCaption(stage.config.captions.terrace);
      }
      if (this.atViewpoint(stage)) {
        hud.setHint(null);
        game.send({ type: "VIEWPOINT_REACHED" });
        return;
      }
      hud.setHint(onTerrace ? "Avancez jusqu'au garde-corps pour observer." : null);
      return;
    }
    hud.setHint(null);
    if (state === "REVEAL" && stage.roof.update(dt)) game.send({ type: "ROOF_REVEALED" });
  }

  private playerLocal(stage: Stage): Vector3 {
    const p = this.deps.player.position();
    return stage.root.worldToLocal(this.local.set(p.x, stage.root.position.y, p.z));
  }

  /** The module's local -Z points from the threshold out over the terrace. */
  private isOnTerrace(stage: Stage): boolean {
    return this.playerLocal(stage).z < -ON_TERRACE;
  }

  private atViewpoint(stage: Stage): boolean {
    const p = this.playerLocal(stage);
    const v = stage.view.position;
    return Math.hypot(p.x - v.x, p.z - v.z) < VIEW_RADIUS;
  }
}
