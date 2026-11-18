// Shader-level life for the outdoor modules (docs/DA.md §04: discreet animation): drifting cloud
// shadows on everything the sun lights, wind in the foliage and an idle motion for the animals.
// One set of uniforms is shared by every patched material and by the sky dome, so the shadows
// on the ground are those of the clouds drawn overhead.
import { type Material, Mesh, MeshStandardMaterial, type Object3D, Vector3 } from "three";

/** Altitude of the cloud layer, in metres. */
export const CLOUD_ALTITUDE = 700;

/**
 * Cloud cover in [0, 1] above a ground position (metres), shared by the sky dome and by the
 * shadows. `uFxTime` only moves the field: without motion the sky keeps its shape.
 */
export const CLOUD_GLSL = /* glsl */ `
  uniform float uFxTime;
  float fxHash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
  }
  float fxNoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(fxHash(i), fxHash(i + vec2(1.0, 0.0)), f.x),
      mix(fxHash(i + vec2(0.0, 1.0)), fxHash(i + vec2(1.0, 1.0)), f.x),
      f.y
    );
  }
  float fxClouds(vec2 xz) {
    vec2 p = xz / 520.0 + uFxTime * vec2(0.011, 0.004);
    float n = 0.5 * fxNoise(p) + 0.25 * fxNoise(p * 2.03 + 7.1)
      + 0.125 * fxNoise(p * 4.01 + 3.7) + 0.0625 * fxNoise(p * 8.1 + 1.3);
    return smoothstep(0.5, 0.74, n / 0.9375);
  }
`;

export const FX_UNIFORMS = {
  /** Seconds of game time; frozen under reduced motion. */
  uFxTime: { value: 0 },
  /** Share of the sunlight a cloud removes, already scaled by how far outdoors the player is. */
  uFxCloudShade: { value: 0 },
  /** Unit vector towards the sun. */
  uFxSun: { value: new Vector3(0, 1, 0) },
  /** 1 with motion, 0 under reduced motion: wind and idle animation stop. */
  uFxMotion: { value: 1 },
};

export interface FxOptions {
  /** Sway of the foliage, in metres; 0 leaves the vertices alone. */
  wind?: number;
  /** Idle motion of animals: needs the `_phase` vertex attribute. */
  idle?: boolean;
  /**
   * The mesh carries `_phase` (blender/scripts/lowpoly.py): x is a per-plant or per-animal phase,
   * y the height above its foot, z the weight of an animal's head, all in [0, 1].
   */
  phase?: boolean;
}

export const FOLIAGE_MATERIAL = /^M_FOLIAGE_/;
export const ANIMAL_MATERIAL = /^M_ANIMAL_/;

/** What a material gets from its name; pure, for tests. */
export function fxOptionsFor(
  materialName: string,
  hasPhase: boolean,
  wind: number,
): Required<FxOptions> {
  const sway = FOLIAGE_MATERIAL.test(materialName) ? wind : 0;
  const idle = hasPhase && ANIMAL_MATERIAL.test(materialName);
  return { wind: sway, idle, phase: hasPhase && (sway > 0 || idle) };
}

const patched = new WeakSet<Material>();

function patch(material: MeshStandardMaterial, options: Required<FxOptions>): void {
  if (patched.has(material)) return;
  patched.add(material);
  const { wind, idle, phase } = options;
  const previous = material.onBeforeCompile;
  material.onBeforeCompile = (shader, renderer) => {
    previous.call(material, shader, renderer);
    Object.assign(shader.uniforms, FX_UNIFORMS);
    const motion: string[] = [];
    if (wind > 0) {
      // Out-of-phase wobble across the canopy: reads as leaves moving, not as a rigid shake.
      // With a phase attribute, each plant has its own beat and its foot stays put.
      motion.push(/* glsl */ `
        float fxPhase = dot(position, vec3(0.37, 0.53, 0.29))${phase ? " + _phase.x * 6.2832" : ""};
        transformed += ${wind.toFixed(3)} * uFxMotion${phase ? " * _phase.y" : ""} * vec3(
          sin(uFxTime * 1.3 + fxPhase),
          0.35 * sin(uFxTime * 1.9 + fxPhase * 1.7),
          cos(uFxTime * 1.1 + fxPhase * 1.3));`);
    }
    if (idle) {
      // Breathing everywhere, and a slow, occasional nod of the head alone.
      motion.push(/* glsl */ `
        float fxBeat = uFxTime * 0.9 + _phase.x * 6.2832;
        float fxNod = _phase.z * max(0.0, sin(fxBeat * 0.6 + _phase.x * 40.0));
        transformed += uFxMotion * normal * (0.004 * sin(fxBeat * 2.0));
        transformed.y -= uFxMotion * 0.06 * fxNod * fxNod;`);
    }
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
        uniform float uFxTime;
        uniform float uFxMotion;
        varying vec3 vFxWorld;
        ${phase ? "attribute vec3 _phase;" : ""}`,
      )
      .replace("#include <begin_vertex>", `#include <begin_vertex>\n${motion.join("\n")}`)
      .replace(
        "#include <project_vertex>",
        `#include <project_vertex>
        vFxWorld = mvPosition.xyz * mat3(viewMatrix) + cameraPosition;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
        ${CLOUD_GLSL}
        uniform float uFxCloudShade;
        uniform vec3 uFxSun;
        varying vec3 vFxWorld;`,
      )
      // After the lights are summed and before they are combined: clouds dim the sun only.
      .replace(
        "#include <aomap_fragment>",
        `#include <aomap_fragment>
        float fxRise = (${CLOUD_ALTITUDE.toFixed(1)} - vFxWorld.y) / max(uFxSun.y, 0.05);
        float fxSunlight = 1.0 - uFxCloudShade * fxClouds(vFxWorld.xz + uFxSun.xz * fxRise);
        reflectedLight.directDiffuse *= fxSunlight;
        reflectedLight.directSpecular *= fxSunlight;`,
      );
  };
  const key = `fx:${wind.toFixed(3)}:${idle ? 1 : 0}:${phase ? 1 : 0}`;
  material.customProgramCacheKey = () => key;
  material.needsUpdate = true;
}

/**
 * Patches the lit materials under an outdoor root. `wind` is the sway given to foliage
 * (metres): larger for trees seen from the terrace than for those the player walks under.
 */
export function applyWorldFx(root: Object3D, wind: number): void {
  root.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    const hasPhase = object.geometry.hasAttribute("_phase");
    const materials: Material[] = Array.isArray(object.material)
      ? object.material
      : [object.material];
    for (const material of materials) {
      if (material instanceof MeshStandardMaterial) {
        patch(material, fxOptionsFor(material.name, hasPhase, wind));
      }
    }
  });
}

/** Advances the shared uniforms. `outdoor` in [0, 1] (Atmosphere). */
export function updateWorldFx(
  dt: number,
  outdoor: number,
  sunDirection: Vector3,
  reducedMotion: boolean,
): void {
  if (!reducedMotion) FX_UNIFORMS.uFxTime.value += dt;
  FX_UNIFORMS.uFxMotion.value = reducedMotion ? 0 : 1;
  FX_UNIFORMS.uFxCloudShade.value = 0.6 * outdoor;
  FX_UNIFORMS.uFxSun.value.copy(sunDirection);
}
