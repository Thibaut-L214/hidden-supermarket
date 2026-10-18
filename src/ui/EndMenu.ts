// End of visit (docs/GDD.md §03.10, §09): explored shelves, optional L214 links opened only on
// an explicit click in a new tab, free return to the store, and a way to finish with nothing
// asked. No logo, no payment field.
import type { ExitLink } from "../data/exitLinks";

export interface EndMenuActions {
  onBack(): void;
  onFinish(): void;
}

export class EndMenu {
  constructor(
    private readonly menu: HTMLElement,
    private readonly finale: HTMLElement,
    links: readonly ExitLink[],
    actions: EndMenuActions,
  ) {
    menu.querySelector(".end-links")!.replaceChildren(
      ...links.map((link) => {
        const item = document.createElement("li");
        if (link.url) {
          const a = Object.assign(document.createElement("a"), {
            href: link.url,
            target: "_blank",
            rel: "noopener noreferrer",
            textContent: link.label,
          });
          const note = document.createElement("span");
          note.className = "end-note";
          note.textContent = " (nouvel onglet, lien à confirmer)";
          a.append(note);
          item.append(a);
        } else {
          item.textContent = `${link.label} `;
          const note = document.createElement("span");
          note.className = "end-note";
          note.textContent = "(lien à confirmer)";
          item.append(note);
          item.setAttribute("aria-disabled", "true");
        }
        return item;
      }),
    );
    menu.querySelector("#end-back")!.addEventListener("click", () => actions.onBack());
    menu.querySelector("#end-finish")!.addEventListener("click", () => actions.onFinish());
    finale.querySelector("#end-restart")!.addEventListener("click", () => location.reload());
  }

  get visible(): boolean {
    return !this.menu.hidden || !this.finale.hidden;
  }

  show(exploredLabels: readonly string[]): void {
    this.menu.querySelector(".end-explored")!.textContent =
      exploredLabels.length > 0
        ? `Rayon${exploredLabels.length > 1 ? "s" : ""} exploré${exploredLabels.length > 1 ? "s" : ""} : ${exploredLabels.join(", ")}.`
        : "Vous n'avez exploré aucun rayon. Vous pouvez revenir dans le magasin à tout moment.";
    this.finale.hidden = true;
    this.menu.hidden = false;
    this.menu.querySelector<HTMLButtonElement>("#end-back")!.focus();
  }

  hide(): void {
    this.menu.hidden = true;
  }

  finish(): void {
    this.menu.hidden = true;
    this.finale.hidden = false;
    this.finale.querySelector<HTMLButtonElement>("#end-restart")!.focus();
  }
}
