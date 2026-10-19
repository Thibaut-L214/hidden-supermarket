// Recap of a shelf (docs/GDD.md §03.8, §06.5): at most three captions, sources reachable from
// the keyboard, replay, and a free return. Nothing forces reading to go on.
import type { ChainConfig } from "../features/chains/ChainModule";
import { captionById } from "../features/chains/ChainModule";

export interface RecapActions {
  onReplay(): void;
  onReturn(): void;
  onStay(): void;
}

export class RecapPanel {
  constructor(
    private readonly root: HTMLElement,
    actions: RecapActions,
  ) {
    const bind = (id: string, action: () => void) =>
      root.querySelector<HTMLButtonElement>(id)!.addEventListener("click", action);
    bind("#recap-replay", () => actions.onReplay());
    bind("#recap-return", () => actions.onReturn());
    bind("#recap-stay", () => actions.onStay());
    root.addEventListener("keydown", (event) => {
      if (event.key === "Escape") actions.onStay();
    });
  }

  get visible(): boolean {
    return !this.root.hidden;
  }

  show(config: ChainConfig): void {
    this.root.querySelector("#recap-title")!.textContent = `Rayon ${config.label} : récapitulatif`;

    const cards = this.root.querySelector(".recap-cards")!;
    cards.replaceChildren(
      ...config.recap.map((id) => {
        const caption = captionById(config, id);
        const item = document.createElement("li");
        const title = document.createElement("strong");
        title.textContent = caption.title;
        const text = document.createElement("p");
        text.textContent = caption.short;
        const badge = document.createElement("p");
        badge.className = "recap-badge";
        badge.textContent = [
          caption.kind === "verified" ? "Donnée vérifiée" : "Illustration schématique",
          caption.status === "validated" ? null : "provisoire",
        ]
          .filter(Boolean)
          .join(" · ");
        item.append(title, text, badge);
        return item;
      }),
    );

    const transcript = this.root.querySelector(".recap-transcript-body")!;
    const captionIds = new Set([
      config.terraceCaption,
      config.revealCaption,
      ...config.timeline.map((step) => step.captionId),
    ]);
    transcript.replaceChildren(
      ...[...captionIds].map((id) => {
        const caption = captionById(config, id);
        const item = document.createElement("li");
        const title = document.createElement("strong");
        title.textContent = caption.title;
        const text = document.createElement("p");
        text.textContent = caption.detail;
        item.append(title, text);
        return item;
      }),
    );

    const body = this.root.querySelector(".recap-sources-body")!;
    if (config.sources.length === 0) {
      const empty = document.createElement("p");
      empty.textContent =
        "Aucune source n'est encore associée à ce rayon : les contenus sont des brouillons en attente de validation éditoriale.";
      body.replaceChildren(empty);
    } else {
      const list = document.createElement("ul");
      list.append(
        ...config.sources.map((source) => {
          const item = document.createElement("li");
          const link = Object.assign(document.createElement("a"), {
            href: source.url,
            target: "_blank",
            rel: "noopener noreferrer",
            textContent: source.label,
          });
          item.append(link, ` (${source.publisher}, consulté le ${source.consultedAt})`);
          return item;
        }),
      );
      body.replaceChildren(list);
    }
    this.root.querySelectorAll("details").forEach((details) => (details.open = false));

    this.root.hidden = false;
    this.root.querySelector<HTMLButtonElement>("#recap-replay")!.focus();
  }

  hide(): void {
    this.root.hidden = true;
  }
}
