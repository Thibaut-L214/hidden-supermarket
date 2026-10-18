/** One-line text track for sound cues (docs/DA.md §08). */
export class Subtitles {
  private timer: number | undefined;

  constructor(private readonly element: HTMLElement) {}

  show(text: string, seconds = 2.5): void {
    window.clearTimeout(this.timer);
    this.element.textContent = text;
    this.timer = window.setTimeout(() => (this.element.textContent = ""), seconds * 1000);
  }
}
