// Post-processing chain (docs/TECH.md §07: sparing effects, off in reduced quality):
//   scene (half-float, linear) → GTAO → bloom → tone mapping + sRGB → SMAA
// Tone mapping and exposure stay owned by the renderer (OutputPass reads them each frame, so the
// Atmosphere's exposure blend keeps working). The hand-held scanner is drawn afterwards,
// straight to the screen, as before.
import {
  type Camera,
  type Object3D,
  type Scene,
  Vector2,
  type WebGLRenderer,
} from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { GTAOPass } from "three/addons/postprocessing/GTAOPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { SMAAPass } from "three/addons/postprocessing/SMAAPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

/**
 * Tuning, in linear units. The store already carries baked occlusion (lightmap), so GTAO only
 * adds contact shadows for what moves and for fine detail; the bloom threshold sits above the lit
 * surfaces so that only emitters (ceiling panels, signs, the sun disc) glow.
 */
export const POST_SETTINGS = {
  ao: { radius: 0.45, distanceExponent: 1.5, thickness: 1.2, scale: 1.0, samples: 12, distanceFallOff: 1.0 },
  aoIntensity: 0.55,
  bloom: { strength: 0.32, radius: 0.55, threshold: 1.05 },
  /** Bloom threshold in full sun: sunlit white paint and road markings stay below it, the sun disc does not. */
  bloomThresholdOutdoor: 2.6,
} as const;

export class PostProcessing {
  enabled = true;
  private readonly composer: EffectComposer;
  private readonly ao: GTAOPass;
  private readonly bloom: UnrealBloomPass;

  /**
   * @param hiddenForAO objects drawn by the scene pass but kept out of the AO depth/normal
   *   pass (the sky dome: it is not geometry).
   */
  constructor(
    private readonly renderer: WebGLRenderer,
    scene: Scene,
    camera: Camera,
    hiddenForAO: Object3D[] = [],
  ) {
    this.composer = new EffectComposer(renderer);
    this.composer.addPass(new RenderPass(scene, camera));

    this.ao = new GTAOPass(scene, camera, 512, 512);
    this.ao.updateGtaoMaterial({ ...POST_SETTINGS.ao });
    this.ao.blendIntensity = POST_SETTINGS.aoIntensity;
    const render = this.ao.render.bind(this.ao) as (...args: unknown[]) => void;
    this.ao.render = ((...args: unknown[]) => {
      for (const object of hiddenForAO) object.visible = false;
      render(...args);
      for (const object of hiddenForAO) object.visible = true;
    }) as GTAOPass["render"];
    this.composer.addPass(this.ao);

    const { strength, radius, threshold } = POST_SETTINGS.bloom;
    this.bloom = new UnrealBloomPass(new Vector2(512, 512), strength, radius, threshold);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());
    this.composer.addPass(new SMAAPass());
  }

  /** `outdoor` in [0, 1] (Atmosphere): in the sun, lit surfaces exceed the store's bloom threshold. */
  setOutdoor(outdoor: number): void {
    const { threshold } = POST_SETTINGS.bloom;
    this.bloom.threshold = threshold + (POST_SETTINGS.bloomThresholdOutdoor - threshold) * outdoor;
  }

  /** Size in CSS pixels; the pixel ratio comes from the renderer. */
  setSize(width: number, height: number): void {
    this.composer.setPixelRatio(this.renderer.getPixelRatio());
    this.composer.setSize(width, height);
  }

  render(deltaSeconds: number): void {
    this.composer.render(deltaSeconds);
  }
}
