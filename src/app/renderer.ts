import { NeutralToneMapping, SRGBColorSpace, WebGLRenderer } from "three";

// Colour chain (docs/DA.md §03, docs/TECH.md §07): sRGB output, explicit tone mapping and
// exposure. Neutral tone mapping keeps the store palette's hues close to their authored values.
export const DEFAULT_EXPOSURE = 1.0;

export function createRenderer(canvas: HTMLCanvasElement): WebGLRenderer {
  const renderer = new WebGLRenderer({
    canvas,
    antialias: true,
    powerPreference: "high-performance",
  });
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = NeutralToneMapping;
  renderer.toneMappingExposure = DEFAULT_EXPOSURE;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  return renderer;
}
