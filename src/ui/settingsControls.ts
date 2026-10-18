import { SETTINGS_RANGES, type Settings } from "../app/settings";

/**
 * Binds every `[data-setting]` input inside container to the shared settings object.
 * Returns a function that refreshes the inputs from the settings (call before showing them).
 */
export function bindSettingsControls(container: HTMLElement, settings: Settings): () => void {
  const inputs = [...container.querySelectorAll<HTMLInputElement>("input[data-setting]")];

  for (const input of inputs) {
    const key = input.dataset.setting as keyof Settings;
    if (key === "reducedMotion") {
      input.addEventListener("change", () => (settings.reducedMotion = input.checked));
    } else {
      const range = SETTINGS_RANGES[key];
      input.min = String(range.min);
      input.max = String(range.max);
      input.step = String(range.step);
      input.addEventListener("input", () => (settings[key] = Number(input.value)));
    }
  }

  const sync = () => {
    for (const input of inputs) {
      const key = input.dataset.setting as keyof Settings;
      if (key === "reducedMotion") input.checked = settings.reducedMotion;
      else input.value = String(settings[key]);
    }
  };
  sync();
  return sync;
}
