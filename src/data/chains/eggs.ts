import { TERRACE_EGGS_CONTRACT } from "../../core/assetContract";
import type { ChainConfig } from "../../features/chains/ChainModule";
import { TODO_SOURCE } from "../../features/content/types";

export const eggs: ChainConfig = {
  id: "eggs",
  label: "Œufs",
  terrace: TERRACE_EGGS_CONTRACT,
  // Cages, floor or free range: editorial choice pending (docs/DECISIONS.md).
  systemType: TODO_SOURCE,
  captions: {
    terrace: {
      id: "eggs.terrace",
      title: "Représentation schématique",
      short:
        "Distances et durées sont compressées : ce paysage illustre des étapes, pas un site réel.",
      detail:
        "Les bâtiments, la route et le centre de conditionnement sont rapprochés pour être visibles depuis la terrasse. Leur disposition ne reproduit aucune exploitation existante.",
      kind: "schematic",
      scope: "Illustration",
      status: "draft",
    },
    reveal: {
      id: "eggs.system",
      title: "Système d'élevage",
      short:
        "Intérieur provisoire : le système représenté (cages, sol ou plein air) reste à choisir et à sourcer.",
      detail:
        "L'aménagement intérieur sera modélisé d'après un système d'élevage documenté, choisi et validé par L214. D'ici là, ces volumes neutres ne décrivent aucune installation.",
      kind: "schematic",
      source: TODO_SOURCE,
      scope: "À définir",
      status: "draft",
    },
  },
};
