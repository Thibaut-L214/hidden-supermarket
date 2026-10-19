import { type Caption, captionBadge } from "../features/content/types";

/** Contextual prompt, captions and transient alerts (the scanner itself is drawn in 3D). */
export class HUD {
  private aimText: string | null = null;
  /** Hints by source; the first non-empty one in insertion order is shown. */
  private readonly hints = new Map<string, string | null>();
  private alertTimer: number | undefined;
  private current: Caption | null = null;

  /** Caption currently on screen, for the detail panel. */
  get currentCaption(): Caption | null {
    return this.current;
  }

  constructor(
    private readonly prompt: HTMLElement,
    private readonly status: HTMLElement,
    private readonly caption: HTMLElement,
  ) {}

  setVisible(visible: boolean): void {
    this.prompt.hidden = !visible;
    this.caption.classList.toggle("dimmed", !visible);
  }

  /** Shelf aimed at (label), for the text prompt; progress shows on the scanner's screen. */
  setAim(label: string | null): void {
    this.aimText = label
      ? `Rayon ${label} : maintenez le clic ou appuyez sur E pour scanner.`
      : null;
    this.renderPrompt();
  }

  /** Guidance that takes precedence over the aim prompt (doors waiting, loading…). */
  setHint(source: string, text: string | null): void {
    if (this.hints.get(source) === text) return;
    this.hints.set(source, text);
    this.renderPrompt();
  }

  /** Immersive caption (docs/GDD.md §08): one idea, its nature, and its validation status. */
  showCaption(caption: Caption | null): void {
    this.current = caption;
    if (!caption) {
      this.caption.hidden = true;
      return;
    }
    this.caption.querySelector(".caption-badge")!.textContent = captionBadge(caption);
    this.caption.querySelector(".caption-title")!.textContent = caption.title;
    this.caption.querySelector(".caption-text")!.textContent = caption.short;
    this.caption.hidden = false;
  }

  alert(text: string, seconds = 6): void {
    window.clearTimeout(this.alertTimer);
    this.status.textContent = text;
    this.status.dataset.kind = "info";
    this.alertTimer = window.setTimeout(() => (this.status.textContent = ""), seconds * 1000);
  }

  private renderPrompt(): void {
    const hint = [...this.hints.values()].find((t) => t);
    const text = hint ?? this.aimText ?? "";
    if (this.prompt.textContent !== text) this.prompt.textContent = text;
  }
}
