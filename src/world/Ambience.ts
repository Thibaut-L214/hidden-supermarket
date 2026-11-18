// Small outdoor life (docs/DA.md §04: discreet animation): dust motes that catch the backlight
// and a few distant birds gliding over the fields. Both are single draw calls driven by the
// shared WorldFx clock, fade in with the outdoor light and stand still under reduced motion.
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  DoubleSide,
  Group,
  Mesh,
  Points,
  ShaderMaterial,
  Vector3,
} from "three";
import { FX_UNIFORMS } from "./WorldFx";

const MOTES = 420;
/** Side of the cube of motes that follows the camera, in metres. */
const MOTE_SPAN = 28;
const BIRDS = 7;

/** Deterministic pseudo-random number in [0, 1) (docs: « état déterministe »). */
export function seeded(index: number, salt: number): number {
  const x = Math.sin(index * 127.1 + salt * 311.7) * 43758.5453;
  return x - Math.floor(x);
}

function motes(uniforms: Record<string, { value: unknown }>): Points {
  const base = new Float32Array(MOTES * 3);
  const seed = new Float32Array(MOTES);
  for (let i = 0; i < MOTES; i++) {
    base[i * 3] = seeded(i, 1) * MOTE_SPAN;
    base[i * 3 + 1] = seeded(i, 2) * MOTE_SPAN;
    base[i * 3 + 2] = seeded(i, 3) * MOTE_SPAN;
    seed[i] = seeded(i, 4);
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(base, 3));
  geometry.setAttribute("seed", new BufferAttribute(seed, 1));
  const material = new ShaderMaterial({
    uniforms,
    vertexShader: /* glsl */ `
      uniform float uFxTime;
      uniform vec3 uFxSun;
      uniform float uOutdoor;
      uniform float uPixels;
      attribute float seed;
      varying float vGlow;
      void main() {
        // Slow drift, wrapped into a cube centred on the camera.
        vec3 drift = uFxTime * vec3(0.11, 0.025 + 0.03 * seed, 0.07);
        drift.y += 0.25 * sin(uFxTime * 0.3 + seed * 40.0);
        vec3 p = mod(position + drift - cameraPosition, ${MOTE_SPAN.toFixed(1)}) - ${(MOTE_SPAN / 2).toFixed(1)};
        vec4 mv = viewMatrix * vec4(p + cameraPosition, 1.0);
        float distance = length(mv.xyz);
        // Forward scattering: motes light up towards the sun and vanish elsewhere.
        float towardsSun = max(dot(normalize(p), uFxSun), 0.0);
        vGlow = uOutdoor * (0.05 + 0.95 * pow(towardsSun, 6.0))
          * smoothstep(1.2, 4.0, distance) * (1.0 - smoothstep(9.0, 14.0, distance))
          * (0.5 + 0.5 * seed);
        gl_PointSize = uPixels * (0.012 + 0.014 * seed) / distance;
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColour;
      varying float vGlow;
      void main() {
        float d = length(gl_PointCoord - 0.5);
        gl_FragColor = vec4(uColour * vGlow * smoothstep(0.5, 0.1, d), 1.0);
      }
    `,
    blending: AdditiveBlending,
    transparent: true,
    depthWrite: false,
    fog: false,
  });
  const points = new Points(geometry, material);
  points.name = "FX_MOTES";
  points.frustumCulled = false;
  return points;
}

function birds(uniforms: Record<string, { value: unknown }>, centre: Vector3): Mesh {
  // Each bird: two triangles sharing the body edge; `wing` is 0 on the body, ±1 on the tips.
  const position: number[] = [];
  const orbit: number[] = [];
  const wing: number[] = [];
  for (let i = 0; i < BIRDS; i++) {
    const radius = 45 + 80 * seeded(i, 5);
    const height = -8 + 22 * seeded(i, 6);
    const phase = 6.2832 * seeded(i, 7);
    const speed = (0.05 + 0.04 * seeded(i, 8)) * (i % 2 === 0 ? 1 : -1);
    for (const side of [-1, 1]) {
      position.push(0, 0, -0.22, 0, 0, 0.22, side * 0.75, 0, 0.05);
      wing.push(0, 0, side);
      for (let v = 0; v < 3; v++) orbit.push(radius, height, phase, speed);
    }
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(position), 3));
  geometry.setAttribute("orbit", new BufferAttribute(new Float32Array(orbit), 4));
  geometry.setAttribute("wing", new BufferAttribute(new Float32Array(wing), 1));
  const material = new ShaderMaterial({
    uniforms: { ...uniforms, uCentre: { value: centre } },
    vertexShader: /* glsl */ `
      uniform float uFxTime;
      uniform vec3 uCentre;
      attribute vec4 orbit;
      attribute float wing;
      void main() {
        float angle = orbit.z + uFxTime * orbit.w;
        // Heading along the circle; a slow beat with glides in between.
        vec2 heading = vec2(cos(angle), sin(angle)) * sign(orbit.w);
        float beat = sin(uFxTime * 5.0 + orbit.z * 3.0) * smoothstep(-0.2, 0.6, sin(uFxTime * 0.5 + orbit.z));
        vec3 local = position;
        local.y += abs(wing) * (0.12 + 0.3 * beat);
        vec3 world = uCentre + vec3(sin(angle) * orbit.x, orbit.y, cos(angle) * orbit.x);
        world += vec3(heading.x * local.z + heading.y * local.x, local.y, -heading.y * local.z + heading.x * local.x);
        gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uBird;
      uniform float uOutdoor;
      void main() {
        gl_FragColor = vec4(uBird, uOutdoor);
      }
    `,
    transparent: true,
    side: DoubleSide,
    depthWrite: false,
    fog: false,
  });
  const mesh = new Mesh(geometry, material);
  mesh.name = "FX_BIRDS";
  mesh.frustumCulled = false;
  return mesh;
}

export class Ambience extends Group {
  private readonly uniforms = {
    uFxTime: FX_UNIFORMS.uFxTime,
    uFxSun: FX_UNIFORMS.uFxSun,
    uOutdoor: { value: 0 },
    /** Drawing-buffer height: point sizes are in metres, converted in the shader. */
    uPixels: { value: 1 },
    uColour: { value: new Color("#fff0d6").multiplyScalar(0.9) },
    /** Birds are silhouettes already half lost in the haze. */
    uBird: { value: new Color("#5d646b") },
  };

  /** @param birdsCentre point the birds circle around: over the fields, beyond the site. */
  constructor(birdsCentre: Vector3) {
    super();
    this.name = "FX_AMBIENCE";
    this.add(motes(this.uniforms), birds(this.uniforms, birdsCentre));
  }

  /** `outdoor` in [0, 1] (Atmosphere); `bufferHeight` in device pixels; `fov` in degrees. */
  update(outdoor: number, bufferHeight: number, fov: number): void {
    this.uniforms.uOutdoor.value = outdoor;
    this.uniforms.uPixels.value = bufferHeight / (2 * Math.tan((fov * Math.PI) / 360));
    this.visible = outdoor > 0.02;
  }
}
