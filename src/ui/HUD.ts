/** Reticle with scan progress, contextual prompt, and transient alerts. */
export class HUD {
  private aimText: string | null = null;
  private hintText: string | null = null;
  private alertTimer: number | undefined;

  constructor(
    private readonly reticle: HTMLElement,
    private readonly prompt: HTMLElement,
    private readonly status: HTMLElement,
  ) {}

  setVisible(visible: boolean): void {
    this.reticle.hidden = !visible;
    this.prompt.hidden = !visible;
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
  setHint(text: string | null): void {
    this.hintText = text;
    this.renderPrompt();
  }

  alert(text: string, seconds = 6): void {
    window.clearTimeout(this.alertTimer);
    this.status.textContent = text;
    this.status.dataset.kind = "info";
    this.alertTimer = window.setTimeout(() => (this.status.textContent = ""), seconds * 1000);
  }

  private renderPrompt(): void {
    const text = this.hintText ?? this.aimText ?? "";
    if (this.prompt.textContent !== text) this.prompt.textContent = text;
  }
}
