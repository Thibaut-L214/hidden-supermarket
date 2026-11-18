// Height fog (docs/DA.md §03, terrace: « horizon brumeux »). The haze pools in the valley and
// thins with altitude, so the site below the terrace stays crisp while distant fields dissolve
// and hilltops emerge. It replaces three's FogExp2 formula in every built-in material by
// patching the fog shader chunks once, before any material is compiled; `scene.fog` stays a
// FogExp2 and its `density` still drives the distance term.
import { ShaderChunk } from "three";

export const HEIGHT_FOG = {
  /** Density of the low haze at `floor`, per metre. */
  density: 0.0009,
  /** Altitude where the low haze is densest: the valley floor under the terrace, in metres. */
  floor: -24,
  /** Exponential falloff with altitude, per metre (the haze halves every ~15 m). */
  falloff: 0.045,
} as const;

/**
 * Fog amount in [0, 1] between an eye at altitude `eyeY` and a point at altitude `pointY`,
 * `distance` metres away. `exp2Density` is the FogExp2 density of the scene (distance term).
 * Mirrors the GLSL below; kept in TypeScript for tests and tuning.
 */
export function heightFogAmount(
  distance: number,
  eyeY: number,
  pointY: number,
  exp2Density: number,
): number {
  const { density, floor, falloff } = HEIGHT_FOG;
  const rise = falloff * (pointY - eyeY);
  // Average of exp(-falloff·y) along the ray; tends to 1 for a level ray.
  const slab = Math.abs(rise) < 1e-4 ? 1 - rise / 2 : (1 - Math.exp(-rise)) / rise;
  const low = density * Math.exp(-falloff * (eyeY - floor)) * slab * distance;
  const far = exp2Density * exp2Density * distance * distance;
  return 1 - Math.exp(-(low + far));
}

const glsl = (value: number): string => value.toFixed(6);

let installed = false;

/** Idempotent; must run before the first material compiles (see src/app/renderer.ts). */
export function installHeightFog(): void {
  if (installed) return;
  installed = true;
  ShaderChunk.fog_pars_vertex = /* glsl */ `
#ifdef USE_FOG
  varying float vFogDepth;
  varying float vFogRise;
#endif`;
  // World altitude from the view-space position: valid for meshes, instances, sprites and lines.
  ShaderChunk.fog_vertex = /* glsl */ `
#ifdef USE_FOG
  vFogDepth = length( mvPosition.xyz );
  vFogRise = dot( vec3( viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1] ), mvPosition.xyz );
#endif`;
  ShaderChunk.fog_pars_fragment = /* glsl */ `
#ifdef USE_FOG
  uniform vec3 fogColor;
  varying float vFogDepth;
  varying float vFogRise;
  #ifdef FOG_EXP2
    uniform float fogDensity;
  #else
    uniform float fogNear;
    uniform float fogFar;
  #endif
#endif`;
  ShaderChunk.fog_fragment = /* glsl */ `
#ifdef USE_FOG
  #ifdef FOG_EXP2
    float fogRise = ${glsl(HEIGHT_FOG.falloff)} * vFogRise;
    float fogSlab = abs( fogRise ) < 1e-4 ? 1.0 - 0.5 * fogRise : ( 1.0 - exp( - fogRise ) ) / fogRise;
    float fogLow = ${glsl(HEIGHT_FOG.density)}
      * exp( - ${glsl(HEIGHT_FOG.falloff)} * ( cameraPosition.y - ( ${glsl(HEIGHT_FOG.floor)} ) ) )
      * fogSlab * vFogDepth;
    float fogFactor = 1.0 - exp( - fogLow - fogDensity * fogDensity * vFogDepth * vFogDepth );
  #else
    float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
  #endif
  gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, clamp( fogFactor, 0.0, 1.0 ) );
#endif`;
}
