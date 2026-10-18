import type { Settings } from "../app/settings";
import { bindSettingsControls } from "./settingsControls";

/** Pause dialog: resume button and comfort settings (docs/DA.md §08). */
export class PauseMenu {
  private readonly resume: HTMLButtonElement;
  private readonly returnButton: HTMLButtonElement;
  private readonly sync: () => void;

  constructor(
    private readonly root: HTMLElement,
    settings: Settings,
    onResume: () => void,
    onReturn: () => void,
    onSettingsChange: () => void,
  ) {
    this.resume = root.querySelector<HTMLButtonElement>("#pause-resume")!;
    this.returnButton = root.querySelector<HTMLButtonElement>("#pause-return")!;
    this.returnButton.addEventListener("click", onReturn);
    this.sync = bindSettingsControls(root, settings, onSettingsChange);
    this.resume.addEventListener("click", onResume);
  }

  get visible(): boolean {
    return !this.root.hidden;
  }

  /** @param canReturn offer « Revenir au magasin » (a terrace is open, docs/GDD.md §05) */
  show(canReturn: boolean): void {
    this.sync();
    this.returnButton.hidden = !canReturn;
    this.root.hidden = false;
    this.resume.focus();
  }

  hide(): void {
    this.root.hidden = true;
  }
}
