// Sky dome for the terrace (docs/DA.md §03: hazy blue-grey horizon, controlled backlight). A
// gradient from the haze at the horizon to a pale zenith, a warm halo and a small sun disc
// towards the key light. The horizon colour is the fog colour, so distant hills dissolve into
// the sky instead of a flat backdrop. Values are linear and above 1 near the sun: with
// post-processing the disc blooms, without it tone mapping tames it.
import { BackSide, Color, Mesh, ShaderMaterial, SphereGeometry, Vector3 } from "three";

export interface SkyColours {
  /** Colour at the horizon; also used for the fog. */
  horizon: string;
  zenith: string;
  /** Below the horizon (the ground seen through gaps, reflections of the floor). */
  ground: string;
  sun: string;
}

export const TERRACE_SKY: SkyColours = {
  horizon: "#cdd6da",
  zenith: "#a9bccb",
  ground: "#b9b5a6",
  sun: "#fff0d6",
};

const VERTEX = /* glsl */ `
  varying vec3 vDirection;
  void main() {
    vDirection = position;
    vec4 clip = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    // Pinned just inside the far plane: the dome never clips, whatever the camera's far value.
    gl_Position = vec4(clip.xy, clip.w * 0.9999, clip.w);
  }
`;

const FRAGMENT = /* glsl */ `
  uniform vec3 horizon;
  uniform vec3 zenith;
  uniform vec3 ground;
  uniform vec3 sunColour;
  uniform vec3 sunDirection;
  varying vec3 vDirection;
  void main() {
    vec3 d = normalize(vDirection);
    float mu = max(dot(d, sunDirection), 0.0);
    float up = smoothstep(0.0, 0.85, d.y);
    vec3 sky = mix(horizon, zenith, pow(up, 0.55));
    // The haze warms and brightens around the sun, mostly low in the sky (backlight).
    float lowSky = 1.0 - smoothstep(0.0, 0.6, d.y);
    sky = mix(sky, sunColour * 0.9, pow(mu, 6.0) * 0.35 * (0.4 + 0.6 * lowSky));
    sky = mix(sky, ground, smoothstep(0.0, -0.3, d.y));
    float halo = pow(mu, 48.0) * 0.5;
    float disc = smoothstep(0.99955, 0.99985, mu) * 6.0;
    gl_FragColor = vec4(sky + sunColour * (halo + disc), 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

export class SkyDome extends Mesh<SphereGeometry, ShaderMaterial> {
  constructor(sunDirection: Vector3, colours: SkyColours = TERRACE_SKY) {
    super(
      new SphereGeometry(1, 32, 16),
      new ShaderMaterial({
        uniforms: {
          horizon: { value: new Color(colours.horizon) },
          zenith: { value: new Color(colours.zenith) },
          ground: { value: new Color(colours.ground) },
          sunColour: { value: new Color(colours.sun) },
          sunDirection: { value: sunDirection.clone().normalize() },
        },
        vertexShader: VERTEX,
        fragmentShader: FRAGMENT,
        side: BackSide,
        depthWrite: false,
        fog: false,
      }),
    );
    this.name = "SKY_DOME";
    this.frustumCulled = false;
    this.renderOrder = -1000;
  }

  /** The dome is centred on the camera: it has no parallax. */
  follow(position: Vector3): void {
    this.position.copy(position);
  }
}
