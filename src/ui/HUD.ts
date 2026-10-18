import type { Caption } from "../features/content/types";

/** Reticle with scan progress, contextual prompt, and transient alerts. */
export class HUD {
  private aimText: string | null = null;
  /** Hints by source; the first non-empty one in insertion order is shown. */
  private readonly hints = new Map<string, string | null>();
  private alertTimer: number | undefined;

  constructor(
    private readonly reticle: HTMLElement,
    private readonly prompt: HTMLElement,
    private readonly status: HTMLElement,
    private readonly caption: HTMLElement,
  ) {}

  setVisible(visible: boolean): void {
    this.reticle.hidden = !visible;
    this.prompt.hidden = !visible;
    this.caption.classList.toggle("dimmed", !visible);
  }

  /** Shelf under the reticle (label) and hold progress in [0, 1]. */
  setAim(label: string | null, progress: number): void {
    this.reticle.toggleAttribute("data-targeted", label !== null);
    this.reticle.style.setProperty("--progress", String(progress));
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
    if (!caption) {
      this.caption.hidden = true;
      return;
    }
    const badges = [caption.kind === "verified" ? "Donnée vérifiée" : "Illustration schématique"];
    if (caption.status !== "validated") badges.push("Contenu provisoire, à valider");
    this.caption.querySelector(".caption-badge")!.textContent = badges.join(" · ");
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
