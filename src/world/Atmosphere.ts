// Store and outdoor lighting blended by one factor (docs/DA.md §03–04, docs/GDD.md §06.1):
// the store stays broad and even; outside, a low sun and a hazy sky take over gradually.
// Changes are damped, so crossing the threshold never flashes.
import {
  Color,
  DirectionalLight,
  HemisphereLight,
  Mesh,
  type Object3D,
  PCFShadowMap,
  type Scene,
  type Texture,
  Vector3,
  type WebGLRenderer,
} from "three";
import { DEFAULT_EXPOSURE } from "../app/renderer";

/** Time constant of the blend, in seconds. */
const BLEND_SECONDS = 0.9;
const OUTDOOR_EXPOSURE = 0.92;
/** Image-based light of each zone (the baked store panorama, the terrace sky). */
const STORE_ENVIRONMENT = 0.5;
/**
 * Store ambient light. The baked lightmap and GTAO darken it (values below 1 under shelves and
 * in corners), so it sits above the 1.3 of the unbaked store to keep the high-key ivory look.
 */
const STORE_SKY = 1.9;
const OUTDOOR_ENVIRONMENT = 0.6;
/** The environment never fades below this share while it is swapped, so the swap is not a flash. */
const SWAP_FLOOR = 0.35;
/** Time constant of the "industrial" mood, in seconds: slower than the zone blend. */
const MOOD_SECONDS = 1.6;
const COLD_SKY = new Color("#c3d2dc");
const COLD_GROUND = new Color("#8a8a80");
const COLD_SUN = new Color("#f2f0ea");

/**
 * Which environment is lit at blend `f`, and how strongly (0 = store, 1 = outdoors). A cube
 * texture cannot be cross-faded, so the intensity dips to SWAP_FLOOR at the midpoint, where the
 * texture changes, while the hemisphere lights carry the transition.
 */
export function environmentBlend(f: number): { outdoor: boolean; weight: number } {
  const t = Math.min(1, Math.max(0, f));
  return { outdoor: t >= 0.5, weight: SWAP_FLOOR + (1 - SWAP_FLOOR) * Math.abs(1 - 2 * t) };
}

export class Atmosphere {
  /** Current blend: 0 = store lighting, 1 = outdoor lighting. */
  outdoor = 0;
  /** Current mood: 0 = natural light, 1 = cooler, flatter light over an industrial site. */
  mood = 0;
  private moodTarget = 0;

  private readonly storeSky = new HemisphereLight("#fff8ec", "#b9ab90", STORE_SKY);
  private readonly storeKey = new DirectionalLight("#fffaf0", 1.4);
  private readonly sky = new HemisphereLight("#dde5ea", "#9c947f", 1.1);
  private readonly sun = new DirectionalLight("#fff1dc", 2.4);
  private readonly skyColor = new Color("#dde5ea");
  private readonly groundColor = new Color("#9c947f");
  private readonly sunColor = new Color("#fff1dc");
  private environments: { store: Texture; outdoor: Texture } | null = null;

  constructor(
    private readonly scene: Scene,
    private readonly renderer: WebGLRenderer,
  ) {
    // The key light is flat and shadowless except for the swinging doors of the eggs shelf: a
    // small shadow frustum over the aisle in front of them (see shadeStore).
    this.storeKey.position.set(3, 10, -3.5);
    this.storeKey.target.position.set(0, 0, -7.5);
    this.storeKey.castShadow = true;
    this.storeKey.shadow.mapSize.set(1024, 1024);
    Object.assign(this.storeKey.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: 1, far: 30 });
    this.storeKey.shadow.camera.updateProjectionMatrix();
    this.storeKey.shadow.bias = -0.0005;
    this.storeKey.shadow.normalBias = 0.03;
    this.storeKey.shadow.radius = 3;
    // Low, slightly ahead and to the left of the view over the farm: controlled backlight.
    // Building-scale shadows only give the outdoor volumes their directional contrast.
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = PCFShadowMap;
    this.sun.target.position.set(0, -23, -55);
    this.sun.position.set(-80, 60, -150);
    this.sun.castShadow = true;
    const shadow = this.sun.shadow;
    shadow.mapSize.set(2048, 2048);
    Object.assign(shadow.camera, { left: -80, right: 80, top: 80, bottom: -80, near: 1, far: 300 });
    shadow.camera.updateProjectionMatrix();
    shadow.bias = -0.0004;
    shadow.normalBias = 0.08;
    scene.add(this.storeSky, this.storeKey, this.storeKey.target, this.sky, this.sun, this.sun.target);
    this.apply();
  }

  /** Unit vector from the scene towards the sun, for the sky dome. */
  get sunDirection(): Vector3 {
    return this.sun.position.clone().sub(this.sun.target.position).normalize();
  }

  /** Image-based lighting per zone; the store one is used until the player is outdoors. */
  setEnvironments(store: Texture, outdoor: Texture): void {
    this.environments = { store, outdoor };
    this.apply();
  }

  /** Building-scale sun shadows and the doors' shadow; off in reduced quality. */
  setShadows(enabled: boolean): void {
    this.sun.castShadow = enabled;
    this.storeKey.castShadow = enabled;
  }

  /** The doors that swing open cast the store's only dynamic shadow, on the floor in front. */
  shadeStore(root: Object3D): void {
    root.traverse((object) => {
      if (!(object instanceof Mesh)) return;
      if (/^DOOR_EGGS_[LR]/.test(object.name) || object.parent?.name.startsWith("DOOR_EGGS_")) {
        object.castShadow = true;
      }
      if (object.name === "STORE_FLOOR") object.receiveShadow = true;
    });
  }

  /** Lets an outdoor module cast and receive the sun's shadows. */
  shade(root: Object3D): void {
    root.traverse((object) => {
      if (object instanceof Mesh) object.castShadow = object.receiveShadow = true;
    });
  }

  /** Cools and flattens the daylight (0–1) while an intensive site is on show; damped. */
  setMood(amount: number): void {
    this.moodTarget = Math.min(1, Math.max(0, amount));
  }

  update(dt: number, target: number): void {
    if (dt <= 0) return;
    this.outdoor += (target - this.outdoor) * (1 - Math.exp(-dt / BLEND_SECONDS));
    this.mood += (this.moodTarget - this.mood) * (1 - Math.exp(-dt / MOOD_SECONDS));
    this.apply();
  }

  private apply(): void {
    const f = this.outdoor;
    this.storeSky.intensity = STORE_SKY * (1 - 0.55 * f);
    this.storeKey.intensity = 1.4 * (1 - 0.55 * f);
    const m = this.mood * f;
    this.sky.intensity = 1.1 * f;
    this.sky.color.copy(this.skyColor).lerp(COLD_SKY, m);
    this.sky.groundColor.copy(this.groundColor).lerp(COLD_GROUND, m);
    this.sun.intensity = 2.4 * f * (1 - 0.3 * this.mood);
    this.sun.color.copy(this.sunColor).lerp(COLD_SUN, m);
    this.renderer.toneMappingExposure =
      DEFAULT_EXPOSURE + (OUTDOOR_EXPOSURE - DEFAULT_EXPOSURE) * f - 0.04 * m;
    if (this.environments) {
      const { outdoor, weight } = environmentBlend(f);
      this.scene.environment = outdoor ? this.environments.outdoor : this.environments.store;
      this.scene.environmentIntensity = (outdoor ? OUTDOOR_ENVIRONMENT : STORE_ENVIRONMENT) * weight;
    }
  }
}
