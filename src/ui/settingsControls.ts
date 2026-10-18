import { SETTINGS_RANGES, type Settings, isRangeSetting } from "../app/settings";

/**
 * Binds every `[data-setting]` input inside container to the shared settings object; ranges
 * for numeric settings, checkboxes for toggles. Returns a function that refreshes the inputs
 * from the settings (call before showing them).
 */
export function bindSettingsControls(
  container: HTMLElement,
  settings: Settings,
  onChange: () => void = () => {},
): () => void {
  const inputs = [...container.querySelectorAll<HTMLInputElement>("input[data-setting]")];

  for (const input of inputs) {
    const key = input.dataset.setting as keyof Settings;
    if (isRangeSetting(key)) {
      const range = SETTINGS_RANGES[key];
      input.min = String(range.min);
      input.max = String(range.max);
      input.step = String(range.step);
      input.addEventListener("input", () => {
        settings[key] = Number(input.value);
        onChange();
      });
    } else {
      input.addEventListener("change", () => {
        settings[key] = input.checked;
        onChange();
      });
    }
  }

  const sync = () => {
    for (const input of inputs) {
      const key = input.dataset.setting as keyof Settings;
      if (isRangeSetting(key)) input.value = String(settings[key]);
      else input.checked = settings[key];
    }
  };
  sync();
  return sync;
}
