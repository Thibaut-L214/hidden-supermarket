// On-demand detail of the current caption (docs/GDD.md §08: short text in the view, detailed
// text in a panel on demand), with its nature, scope and source.
import type { Caption } from "../features/content/types";
import { TODO_SOURCE } from "../features/content/types";

export class SourcePanel {
  constructor(
    private readonly root: HTMLElement,
    onClose: () => void,
  ) {
    root.querySelector("#source-close")!.addEventListener("click", onClose);
    root.addEventListener("keydown", (event) => {
      if (event.key === "Escape" || event.code === "KeyI") onClose();
    });
  }

  get visible(): boolean {
    return !this.root.hidden;
  }

  show(caption: Caption): void {
    const set = (selector: string, text: string) =>
      (this.root.querySelector(selector)!.textContent = text);
    set("#source-title", caption.title);
    set(
      ".source-badge",
      `${caption.kind === "verified" ? "Donnée vérifiée" : "Illustration schématique"} · ${
        caption.status === "validated" ? "validé" : "contenu provisoire, à valider"
      }`,
    );
    set(".source-detail", caption.detail);
    set(".source-scope", `Portée : ${caption.scope}`);

    const source = this.root.querySelector(".source-ref")!;
    if (caption.source && caption.source !== TODO_SOURCE) {
      const link = Object.assign(document.createElement("a"), {
        href: caption.source.url,
        target: "_blank",
        rel: "noopener noreferrer",
        textContent: caption.source.label,
      });
      source.replaceChildren(
        "Source : ",
        link,
        ` (${caption.source.publisher}, consulté le ${caption.source.consultedAt})`,
      );
    } else if (caption.source === TODO_SOURCE) {
      source.replaceChildren("Source : à compléter avant publication.");
    } else {
      source.replaceChildren("Illustration : aucune affirmation factuelle à sourcer.");
    }

    this.root.hidden = false;
    this.root.querySelector<HTMLButtonElement>("#source-close")!.focus();
  }

  hide(): void {
    this.root.hidden = true;
  }
}
