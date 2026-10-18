import type { Settings } from "../app/settings";
import { bindSettingsControls } from "./settingsControls";

/** Pause dialog: resume button and comfort settings (docs/DA.md §08). */
export class PauseMenu {
  private readonly resume: HTMLButtonElement;
  private readonly sync: () => void;

  constructor(
    private readonly root: HTMLElement,
    settings: Settings,
    onResume: () => void,
  ) {
    this.resume = root.querySelector<HTMLButtonElement>("#pause-resume")!;
    this.sync = bindSettingsControls(root, settings);
    this.resume.addEventListener("click", onResume);
  }

  get visible(): boolean {
    return !this.root.hidden;
  }

  show(): void {
    this.sync();
    this.root.hidden = false;
    this.resume.focus();
  }

  hide(): void {
    this.root.hidden = true;
  }
}
