import type { Settings } from "../app/settings";
import { bindSettingsControls } from "./settingsControls";

/** Welcome dialog (docs/GDD.md §03.1): intent, controls, content notice, reduced motion, start. */
export class IntroScreen {
  private readonly start: HTMLButtonElement;

  constructor(
    private readonly root: HTMLElement,
    settings: Settings,
    onStart: () => void,
  ) {
    this.start = root.querySelector<HTMLButtonElement>("#intro-start")!;
    bindSettingsControls(root, settings);
    this.start.addEventListener("click", () => {
      this.root.hidden = true;
      onStart();
    });
  }

  setReady(): void {
    this.start.disabled = false;
    this.start.textContent = "Commencer";
    this.start.focus();
  }

  setFailed(): void {
    this.start.textContent = "Magasin indisponible";
  }
}
