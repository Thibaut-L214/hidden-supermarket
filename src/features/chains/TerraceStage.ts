// Terrace staging (docs/GDD.md §03.5–7, §06.2–4): first contextualisation on the terrace,
// viewpoint at the guardrail, roof reveal with a caption on the system shown, then the
// chain's schematic timeline with one caption per step.
import { Mesh, type Object3D, Vector3 } from "three";
import { terraceNodes } from "../../core/assetContract";
import type { EventBus } from "../../core/EventBus";
import type { GameEvents, GameState } from "../../core/GameState";
import type { Vec2 } from "../../world/CollisionWorld";
import type { Caption } from "../content/types";
import { type ChainConfig, captionById } from "./ChainModule";
import { ChainTimeline } from "./ChainTimeline";
import { RoofReveal } from "./RoofReveal";
import { TimelineDirector } from "./TimelineDirector";

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
  /** Animals of the farm building: drawn once the roof starts to lift. */
  animals: Object3D;
  scene: ChainTimeline;
  director: TimelineDirector;
  caption: string | null;
  welcomed: boolean;
}

export class TerraceStage {
  private stage: Stage | null = null;
  private readonly local = new Vector3();
  // Modules are cached by the asset manager: reuse what is built on them (material copies,
  // timeline state) instead of rebuilding it on every visit.
  private readonly built = new WeakMap<Object3D, { roof: RoofReveal; scene: ChainTimeline }>();

  constructor(private readonly deps: TerraceStageDeps) {
    deps.bus.on("stateChanged", ({ to }) => {
      const stage = this.stage;
      if (!stage) return;
      if (to === "REVEAL") {
        if (!deps.reducedMotion()) deps.glance(stage.focus.getWorldPosition(new Vector3()));
        this.showCaption(stage, stage.config.revealCaption);
      }
      if (to === "CHAIN") {
        stage.director.restart();
        stage.scene.apply(stage.director.state);
      }
      if (to === "RETURN") this.showCaption(stage, null);
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
    this.detach();
    let built = this.built.get(root);
    if (!built) {
      built = {
        roof: new RoofReveal(find(n.roof), this.deps.reducedMotion),
        scene: new ChainTimeline(root, config.timeline, this.deps.reducedMotion),
      };
      this.built.set(root, built);
    }
    built.roof.reset();
    built.scene.apply(null);
    const animals = find(n.animals);
    // Far from the terrace and numerous: they take part in neither the sun's shadow nor ground it.
    animals.traverse((object) => {
      if (object instanceof Mesh) object.castShadow = false;
    });
    animals.visible = false;
    this.stage = {
      config,
      root,
      view: find(n.view),
      focus: find(n.focus),
      animals,
      ...built,
      director: new TimelineDirector(config.timeline),
      caption: null,
      welcomed: false,
    };
  }

  detach(): void {
    if (!this.stage) return;
    this.stage.roof.reset();
    this.stage.scene.apply(null);
    this.stage.animals.visible = false;
    this.stage = null;
    this.deps.hud.setHint(null);
    this.deps.hud.showCaption(null);
  }

  update(dt: number): void {
    const { game, hud } = this.deps;
    const stage = this.stage;
    if (!stage) return;
    const { state } = game.snapshot;
    stage.animals.visible = stage.roof.progress > 0;

    if (state === "TERRACE") {
      const onTerrace = this.isOnTerrace(stage);
      if (onTerrace && !stage.welcomed) {
        stage.welcomed = true;
        this.showCaption(stage, stage.config.terraceCaption);
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
    if (state === "CHAIN") {
      const timeline = stage.director.update(dt);
      stage.scene.apply(timeline);
      this.showCaption(stage, stage.config.timeline[timeline.active]?.captionId ?? null);
      if (timeline.done) game.send({ type: "TIMELINE_DONE" });
    }
  }

  private showCaption(stage: Stage, id: string | null): void {
    if (stage.caption === id) return;
    stage.caption = id;
    this.deps.hud.showCaption(id ? captionById(stage.config, id) : null);
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
