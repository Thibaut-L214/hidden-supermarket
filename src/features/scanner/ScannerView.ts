// First-person scanner (docs/DA.md §05: readable foreground tool, non-militarised): the hand
// and terminal from scanner_hand.glb, drawn in their own pass over the scene so they never
// clip into shelves or walls. The terminal's screen shows the shelf aimed at and the hold
// progress; its scan window glows while a shelf is aimed at.
import {
  BufferGeometry,
  CanvasTexture,
  Color,
  DirectionalLight,
  Euler,
  HemisphereLight,
  Line,
  LineBasicMaterial,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  type Object3D,
  PerspectiveCamera,
  PlaneGeometry,
  SRGBColorSpace,
  Scene,
  type Texture,
  Vector3,
  type WebGLRenderer,
} from "three";
import type { AssetManager } from "../../core/AssetManager";
import { SCANNER_CONTRACT } from "../../core/assetContract";
import { ease } from "../../core/easing";
import type { GameStateId } from "../../core/GameState";

/** Seconds to raise or lower the scanner (instant with reduced motion). */
const RAISE_SECONDS = 0.35;
/** Seconds the screen shows « Scanné » after a confirmation. */
const CONFIRM_SECONDS = 1.2;

// Placement in front of the camera: lower right, screen turned towards the player.
const REST = new Vector3(0.11, -0.12, -0.4);
// Pitch the scan head away, then yaw the screen back towards the camera (it sits to the right).
const TILT = new Euler(-0.5, -0.32, -0.04, "YXZ");
const LOWERED_DROP = 0.32;

export interface ScannerViewInput {
  /** False under dialogs, on the intro and in the end menu. */
  visible: boolean;
  /** Held up in the store; lowered on the terrace and on the way out. */
  raised: boolean;
  /** Shelf label aimed at, or null. */
  label: string | null;
  /** Hold progress in [0, 1]. */
  progress: number;
}

/** The scanner is held up only in the store, where it can be used. */
export function scannerRaised(state: GameStateId): boolean {
  return state === "STORE" || state === "SCANNING" || state === "OPENING";
}

export interface ScreenText {
  title: string;
  subtitle: string;
  /** Progress bar in [0, 1], or null when there is nothing to scan. */
  progress: number | null;
}

/** What the terminal's screen says (pure, tested). */
export function screenText(label: string | null, progress: number, confirmed: boolean): ScreenText {
  if (confirmed) return { title: "Scanné", subtitle: label ?? "", progress: 1 };
  if (label) return { title: label, subtitle: "Maintenir pour scanner", progress };
  return { title: "Prêt", subtitle: "Visez un rayon", progress: null };
}

export class ScannerView {
  readonly scene = new Scene();
  readonly camera = new PerspectiveCamera(50, 1, 0.01, 5);
  private lowered = 1;
  private confirmTimer = 0;
  private visible = false;
  private lastScreen = "";
  private readonly screenCanvas = document.createElement("canvas");
  private readonly screenTexture: CanvasTexture;
  private readonly window: MeshStandardMaterial | null;
  private readonly beam: Line;
  private readonly tip = new Vector3();

  private constructor(
    private readonly root: Object3D,
    environment: Texture | null,
    private readonly reducedMotion: () => boolean,
  ) {
    this.scene.environment = environment;
    this.scene.environmentIntensity = 0.6;
    const key = new DirectionalLight("#fffaf0", 1.6);
    key.position.set(-0.6, 1, 0.8);
    this.scene.add(new HemisphereLight("#fff8ec", "#8a8070", 1.5), key, root);

    // Screen: a canvas on the front face of SCANNER_SCREEN (+Z in glTF space).
    this.screenCanvas.width = 256;
    this.screenCanvas.height = 328;
    this.screenTexture = new CanvasTexture(this.screenCanvas);
    this.screenTexture.colorSpace = SRGBColorSpace;
    const screen = root.getObjectByName("SCANNER_SCREEN")!;
    const face = new Mesh(
      new PlaneGeometry(0.056, 0.072),
      new MeshBasicMaterial({ map: this.screenTexture }),
    );
    face.position.z = 0.0005;
    screen.add(face);

    // Scan window: own material copy whose glow follows the aim.
    const windowMesh = root.getObjectByName("SCANNER_WINDOW");
    const material =
      windowMesh instanceof Mesh ? (windowMesh.material as MeshStandardMaterial).clone() : null;
    if (material && windowMesh instanceof Mesh) {
      material.emissive = new Color("#9be3a6");
      material.emissiveIntensity = 0;
      windowMesh.material = material;
    }
    this.window = material;

    // Faint guide from the scan window towards the centre of view, only while aiming.
    this.beam = new Line(
      new BufferGeometry().setFromPoints([new Vector3(), new Vector3(0, 0, -3)]),
      new LineBasicMaterial({ color: "#9be3a6", transparent: true, opacity: 0.35 }),
    );
    this.beam.visible = false;
    this.scene.add(this.beam);
    this.drawScreen(screenText(null, 0, false));
    this.applyPose();
  }

  static async load(
    assets: AssetManager,
    environment: Texture | null,
    reducedMotion: () => boolean,
  ): Promise<ScannerView> {
    return new ScannerView(await assets.load(SCANNER_CONTRACT), environment, reducedMotion);
  }

  setAspect(aspect: number): void {
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
  }

  /** Shows « Scanné » on the screen for a moment. */
  confirm(): void {
    this.confirmTimer = CONFIRM_SECONDS;
  }

  /** @param realDt wall-clock seconds: the tool keeps answering even while game time stops */
  update(realDt: number, input: ScannerViewInput): void {
    this.visible = input.visible;
    const target = input.raised ? 0 : 1;
    if (this.reducedMotion()) this.lowered = target;
    else {
      const step = realDt / RAISE_SECONDS;
      this.lowered =
        target > this.lowered ? Math.min(this.lowered + step, 1) : Math.max(this.lowered - step, 0);
    }
    this.confirmTimer = Math.max(this.confirmTimer - realDt, 0);
    this.applyPose();

    const aiming = input.raised && input.label !== null;
    if (this.window) this.window.emissiveIntensity = aiming ? 1.2 + 1.5 * input.progress : 0;
    this.beam.visible = aiming && this.lowered < 0.05;
    if (this.beam.visible) {
      this.root.getObjectByName("SCANNER_WINDOW")!.getWorldPosition(this.tip);
      const points = this.beam.geometry.attributes.position!;
      points.setXYZ(0, this.tip.x, this.tip.y, this.tip.z);
      points.needsUpdate = true;
    }

    const text = screenText(input.label, input.progress, this.confirmTimer > 0);
    const key = `${text.title}|${text.subtitle}|${text.progress === null ? "-" : Math.round(text.progress * 20)}`;
    if (key !== this.lastScreen) {
      this.lastScreen = key;
      this.drawScreen(text);
    }
  }

  /** Draws the tool over the scene, after the scene pass (clears depth only). */
  render(renderer: WebGLRenderer): void {
    if (!this.visible || this.lowered >= 1) return;
    renderer.clearDepth();
    renderer.render(this.scene, this.camera);
  }

  private applyPose(): void {
    const t = ease(this.lowered);
    this.root.position.set(REST.x, REST.y - LOWERED_DROP * t, REST.z);
    this.root.rotation.set(TILT.x + 0.5 * t, TILT.y, TILT.z, TILT.order);
  }

  private drawScreen(text: ScreenText): void {
    const ctx = this.screenCanvas.getContext("2d");
    if (!ctx) return;
    const { width: w, height: h } = this.screenCanvas;
    ctx.fillStyle = "#1d2326";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#6f8a68";
    ctx.fillRect(0, 0, w, 34);
    ctx.fillStyle = "#f7f4ec";
    ctx.font = "600 20px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("SCAN", w / 2, 24);
    ctx.font = `700 ${text.title.length > 10 ? 34 : 44}px system-ui, sans-serif`;
    ctx.fillText(text.title, w / 2, 130);
    ctx.fillStyle = "#c9d6c4";
    ctx.font = "400 22px system-ui, sans-serif";
    ctx.fillText(text.subtitle, w / 2, 172);
    if (text.progress !== null) {
      ctx.fillStyle = "#33403a";
      ctx.fillRect(28, 222, w - 56, 22);
      ctx.fillStyle = "#9be3a6";
      ctx.fillRect(28, 222, (w - 56) * text.progress, 22);
    }
    this.screenTexture.needsUpdate = true;
  }
}
