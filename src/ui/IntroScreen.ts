import type { Settings } from "../app/settings";
import { bindSettingsControls } from "./settingsControls";

/** Welcome dialog (docs/GDD.md §03.1): intent, controls, content notice, reduced motion, start. */
export class IntroScreen {
  private readonly start: HTMLButtonElement;
  private retry: (() => void) | null = null;

  constructor(
    private readonly root: HTMLElement,
    settings: Settings,
    onStart: () => void,
  ) {
    this.start = root.querySelector<HTMLButtonElement>("#intro-start")!;
    bindSettingsControls(root, settings);
    this.start.addEventListener("click", () => {
      if (this.retry) {
        const retry = this.retry;
        this.retry = null;
        this.start.disabled = true;
        this.start.textContent = "Chargement…";
        retry();
        return;
      }
      this.root.hidden = true;
      onStart();
    });
  }

  setReady(): void {
    this.start.disabled = false;
    this.start.textContent = "Commencer";
    this.start.focus();
  }

  /** Offers a retry instead of a dead end (the asset cache forgets failed loads). */
  setFailed(retry: () => void): void {
    this.start.textContent = "Réessayer le chargement";
    this.start.disabled = false;
    this.retry = retry;
    this.start.focus();
  }
}
