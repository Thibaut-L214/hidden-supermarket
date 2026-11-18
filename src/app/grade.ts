// Colour grade per zone (docs/DA.md §03): ivory and warm in the store, natural and warmer still
// in daylight, cold and desaturated while an industrial site is on show. Applied after tone
// mapping, on display-referred colour, as the last step before anti-aliasing.
import type { ShaderMaterialParameters } from "three";

export interface Grade {
  /** Multiplier of each channel: the tint of the lights. */
  gain: [number, number, number];
  /** Colour added to the darks: the tint of the shadows. */
  lift: [number, number, number];
  saturation: number;
  /** 0 leaves the tone curve alone, 1 applies a full S-curve. */
  contrast: number;
  /** Darkening of the corners, in [0, 1]. */
  vignette: number;
}

export const GRADES = {
  store: {
    gain: [1.02, 1.0, 0.965],
    lift: [0.012, 0.01, 0.004],
    saturation: 1.05,
    contrast: 0.1,
    vignette: 0.1,
  },
  daylight: {
    gain: [1.03, 1.0, 0.955],
    lift: [0.0, 0.006, 0.016],
    saturation: 1.1,
    contrast: 0.26,
    vignette: 0.16,
  },
  industrial: {
    gain: [0.985, 0.995, 1.02],
    lift: [0.002, 0.007, 0.016],
    saturation: 0.92,
    contrast: 0.34,
    vignette: 0.2,
  },
} as const satisfies Record<string, Grade>;

const mix = (a: number, b: number, t: number): number => a + (b - a) * t;

function blend(a: Grade, b: Grade, t: number): Grade {
  const triple = (x: readonly number[], y: readonly number[]): [number, number, number] => [
    mix(x[0]!, y[0]!, t),
    mix(x[1]!, y[1]!, t),
    mix(x[2]!, y[2]!, t),
  ];
  return {
    gain: triple(a.gain, b.gain),
    lift: triple(a.lift, b.lift),
    saturation: mix(a.saturation, b.saturation, t),
    contrast: mix(a.contrast, b.contrast, t),
    vignette: mix(a.vignette, b.vignette, t),
  };
}

/** Grade for the Atmosphere's blends: `outdoor` 0 = store, 1 = daylight; `mood` 1 = industrial. */
export function gradeFor(outdoor: number, mood: number): Grade {
  const clamp = (x: number) => Math.min(1, Math.max(0, x));
  const outside = blend(GRADES.daylight, GRADES.industrial, clamp(mood));
  return blend(GRADES.store, outside, clamp(outdoor));
}

export const GRADE_SHADER = {
  uniforms: {
    tDiffuse: { value: null },
    gain: { value: [1, 1, 1] },
    lift: { value: [0, 0, 0] },
    saturation: { value: 1 },
    contrast: { value: 0 },
    vignette: { value: 0 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform vec3 gain;
    uniform vec3 lift;
    uniform float saturation;
    uniform float contrast;
    uniform float vignette;
    varying vec2 vUv;
    void main() {
      vec4 texel = texture2D(tDiffuse, vUv);
      vec3 c = texel.rgb * gain;
      c += lift * (1.0 - c);
      c = mix(vec3(dot(c, vec3(0.2126, 0.7152, 0.0722))), c, saturation);
      c = clamp(c, 0.0, 1.0);
      c = mix(c, c * c * (3.0 - 2.0 * c), contrast);
      vec2 centred = (vUv - 0.5) * vec2(1.0, 0.85);
      c *= 1.0 - vignette * smoothstep(0.3, 0.75, length(centred));
      gl_FragColor = vec4(c, texel.a);
    }
  `,
} satisfies ShaderMaterialParameters;
