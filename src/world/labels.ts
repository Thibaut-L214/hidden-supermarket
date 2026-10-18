// Canvas-drawn text and pictograms on flat panels: wording stays out of the GLB files.
import {
  Box3,
  CanvasTexture,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  PlaneGeometry,
  SRGBColorSpace,
  Vector3,
} from "three";
import type { Caption } from "../features/content/types";

/**
 * Flat label just in front of a sign panel's front face (+Z in glTF space); `twoSided` adds
 * the same label on the back face, for hanging signs seen from both aisles.
 */
export function createSignLabel(sign: Object3D, text: string): Mesh;
export function createSignLabel(sign: Object3D, text: string, twoSided: true): Mesh[];
export function createSignLabel(sign: Object3D, text: string, twoSided = false): Mesh | Mesh[] {
  const size = panelSize(sign);
  const faces = (twoSided ? [1, -1] : [1]).map((side) => {
    const label = createLabel(text, size.x * 0.95, size.y * 0.9, "#f7f4ec", "#3f5a3c");
    label.name = `${sign.name}_LABEL${side < 0 ? "_BACK" : ""}`;
    // Sign panels are unrotated boxes centred on their origin.
    label.position.set(0, 0, side * (size.z / 2 + 0.002));
    if (side < 0) label.rotation.y = Math.PI;
    return label;
  });
  return twoSided ? faces : faces[0]!;
}

export function createScanPictogram(plate: Object3D): Mesh {
  const size = panelSize(plate);
  const mesh = createPlate(size.x * 0.9, size.y * 0.9, "#f7f4ec", (ctx, w, h) => {
    // Viewfinder corners around a scan line: reads as « this shelf can be scanned ».
    const m = w * 0.18;
    const arm = w * 0.18;
    ctx.strokeStyle = "#3f5a3c";
    ctx.lineWidth = w * 0.06;
    ctx.lineCap = "round";
    for (const [x, y, dx, dy] of [
      [m, m, 1, 1],
      [w - m, m, -1, 1],
      [m, h - m, 1, -1],
      [w - m, h - m, -1, -1],
    ] as const) {
      ctx.beginPath();
      ctx.moveTo(x, y + dy * arm);
      ctx.lineTo(x, y);
      ctx.lineTo(x + dx * arm, y);
      ctx.stroke();
    }
    ctx.strokeStyle = "#6f8a68";
    ctx.beginPath();
    ctx.moveTo(m + w * 0.06, h / 2);
    ctx.lineTo(w - m - w * 0.06, h / 2);
    ctx.stroke();
  });
  mesh.name = `${plate.name}_ICON`;
  mesh.position.set(0, 0, size.z / 2 + 0.002);
  return mesh;
}

export function panelSize(panel: Object3D): Vector3 {
  panel.updateWorldMatrix(true, false);
  return new Box3().setFromObject(panel).getSize(new Vector3());
}

/** Text drawn on a canvas, shrunk to fit, mapped on a plane of the given size in metres. */
export function createLabel(
  text: string,
  width: number,
  height: number,
  background: string,
  ink: string,
): Mesh {
  return createPlate(width, height, background, (ctx, w, h) => {
    let px = Math.round(h * 0.6);
    ctx.font = `600 ${px}px system-ui, sans-serif`;
    const measured = ctx.measureText(text).width;
    if (measured > w * 0.9) {
      px = Math.floor((px * w * 0.9) / measured);
      ctx.font = `600 ${px}px system-ui, sans-serif`;
    }
    ctx.fillStyle = ink;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, w / 2, h / 2 + 4);
  });
}

function createPlate(
  width: number,
  height: number,
  background: string,
  draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void,
): Mesh {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = Math.round((512 * height) / width);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D indisponible");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  draw(ctx, canvas.width, canvas.height);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  texture.anisotropy = 4;
  return new Mesh(
    new PlaneGeometry(width, height),
    new MeshStandardMaterial({ map: texture, roughness: 0.8 }),
  );
}

/** Splits text into lines that fit `width` pixels with the context's current font. */
function wrap(ctx: CanvasRenderingContext2D, text: string, width: number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/)) {
    const next = line ? `${line} ${word}` : word;
    if (ctx.measureText(next).width > width && line) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/**
 * Reading stand panel (lot 2): mirrors the on-screen caption in the world. The DOM caption
 * stays the accessible source; this copy only helps the scene read as a documentary display.
 */
export class CaptionPanel {
  private face: Mesh | null = null;

  constructor(private readonly panel: Object3D) {}

  show(caption: Caption | null): void {
    this.face?.removeFromParent();
    (this.face?.material as MeshStandardMaterial | undefined)?.map?.dispose();
    this.face = null;
    const size = panelSize(this.panel);
    const width = size.x * 0.94;
    // The panel leans back, so its world box is taller than the face: use its local height.
    const height = width * (0.6 / 0.9);
    const face = createPlate(width, height, "#f7f4ec", (ctx, w, h) => {
      const pad = w * 0.06;
      ctx.fillStyle = "#4d5a4a";
      ctx.font = `600 ${Math.round(h * 0.07)}px system-ui, sans-serif`;
      const badge = caption
        ? `${caption.kind === "verified" ? "DONNÉE VÉRIFIÉE" : "ILLUSTRATION SCHÉMATIQUE"}${caption.status === "validated" ? "" : " · PROVISOIRE"}`
        : "DERRIÈRE LE RAYON";
      ctx.fillText(badge, pad, pad + h * 0.07);
      ctx.fillStyle = "#1f2420";
      ctx.font = `700 ${Math.round(h * 0.11)}px system-ui, sans-serif`;
      ctx.fillText(caption?.title ?? "Observez depuis le garde-corps", pad, pad + h * 0.22);
      ctx.font = `400 ${Math.round(h * 0.075)}px system-ui, sans-serif`;
      const body = caption?.short ?? "Les étapes s'affichent ici au fil de la chaîne.";
      wrap(ctx, body, w - 2 * pad).forEach((line, i) =>
        ctx.fillText(line, pad, pad + h * (0.36 + i * 0.1)),
      );
    });
    face.name = `${this.panel.name}_FACE`;
    face.position.set(0, 0, 0.017);
    this.panel.add(face);
    this.face = face;
  }
}
