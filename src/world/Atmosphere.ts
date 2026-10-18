// Store and outdoor lighting blended by one factor (docs/DA.md §03–04, docs/GDD.md §06.1):
// the store stays broad and even; outside, a low sun and a hazy sky take over gradually.
// Changes are damped, so crossing the threshold never flashes.
import {
  DirectionalLight,
  HemisphereLight,
  Mesh,
  type Object3D,
  PCFSoftShadowMap,
  type Scene,
  type WebGLRenderer,
} from "three";
import { DEFAULT_EXPOSURE } from "../app/renderer";

/** Time constant of the blend, in seconds. */
const BLEND_SECONDS = 0.9;
const OUTDOOR_EXPOSURE = 0.92;

export class Atmosphere {
  /** Current blend: 0 = store lighting, 1 = outdoor lighting. */
  outdoor = 0;

  private readonly storeSky = new HemisphereLight("#fff8ec", "#b9ab90", 1.3);
  private readonly storeKey = new DirectionalLight("#fffaf0", 1.4);
  private readonly sky = new HemisphereLight("#dde5ea", "#9c947f", 1.1);
  private readonly sun = new DirectionalLight("#fff1dc", 2.4);

  constructor(
    scene: Scene,
    private readonly renderer: WebGLRenderer,
  ) {
    this.storeKey.position.set(3, 10, 4);
    // Low, slightly ahead and to the left of the view over the farm: controlled backlight.
    // Building-scale shadows only give the outdoor volumes their directional contrast.
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = PCFSoftShadowMap;
    this.sun.target.position.set(0, -23, -55);
    this.sun.position.set(-80, 60, -150);
    this.sun.castShadow = true;
    const shadow = this.sun.shadow;
    shadow.mapSize.set(2048, 2048);
    Object.assign(shadow.camera, { left: -80, right: 80, top: 80, bottom: -80, near: 1, far: 300 });
    shadow.camera.updateProjectionMatrix();
    shadow.bias = -0.0004;
    shadow.normalBias = 0.08;
    scene.add(this.storeSky, this.storeKey, this.sky, this.sun, this.sun.target);
    this.apply();
  }

  /** Building-scale sun shadows; off in reduced quality. */
  setShadows(enabled: boolean): void {
    this.sun.castShadow = enabled;
  }

  /** Lets an outdoor module cast and receive the sun's shadows. */
  shade(root: Object3D): void {
    root.traverse((object) => {
      if (object instanceof Mesh) object.castShadow = object.receiveShadow = true;
    });
  }

  update(dt: number, target: number): void {
    if (dt <= 0) return;
    this.outdoor += (target - this.outdoor) * (1 - Math.exp(-dt / BLEND_SECONDS));
    this.apply();
  }

  private apply(): void {
    const f = this.outdoor;
    this.storeSky.intensity = 1.3 * (1 - 0.55 * f);
    this.storeKey.intensity = 1.4 * (1 - 0.55 * f);
    this.sky.intensity = 1.1 * f;
    this.sun.intensity = 2.4 * f;
    this.renderer.toneMappingExposure =
      DEFAULT_EXPOSURE + (OUTDOOR_EXPOSURE - DEFAULT_EXPOSURE) * f;
  }
}
