// Eggs shelf (docs/GDD.md §06). Every caption is a schematic description awaiting editorial
// validation; none states a figure. Unknown facts stay TODO_SOURCE.
import { TERRACE_EGGS_CONTRACT } from "../../core/assetContract";
import type { ChainConfig } from "../../features/chains/ChainModule";
import { TODO_SOURCE, type Caption } from "../../features/content/types";

const schematic = (caption: Omit<Caption, "kind" | "status" | "scope"> & { scope?: string }) =>
  ({ kind: "schematic", status: "draft", scope: "Illustration", ...caption }) satisfies Caption;

export const eggs: ChainConfig = {
  id: "eggs",
  label: "Œufs",
  terrace: TERRACE_EGGS_CONTRACT,
  // Cages, floor or free range: editorial choice pending (docs/DECISIONS.md).
  systemType: TODO_SOURCE,
  terraceCaption: "eggs.terrace",
  revealCaption: "eggs.system",
  captions: [
    schematic({
      id: "eggs.terrace",
      title: "Représentation schématique",
      short:
        "Distances et durées sont compressées : ce paysage illustre des étapes, pas un site réel.",
      detail:
        "Les bâtiments, la route et le centre de conditionnement sont rapprochés pour être visibles depuis la terrasse. Leur disposition ne reproduit aucune exploitation existante.",
    }),
    schematic({
      id: "eggs.system",
      title: "Système d'élevage",
      short:
        "Intérieur provisoire : le système représenté (cages, sol ou plein air) reste à choisir et à sourcer.",
      detail:
        "L'aménagement intérieur sera modélisé d'après un système d'élevage documenté, choisi et validé par L214. D'ici là, ces volumes neutres ne décrivent aucune installation.",
      source: TODO_SOURCE,
      scope: "À définir",
    }),
    schematic({
      id: "eggs.collect",
      title: "Collecte",
      short: "Les œufs sont rassemblés au bout du bâtiment, puis placés en caisses.",
      detail:
        "Étape illustrée : la collecte est représentée par des caisses qui s'accumulent à la sortie du bâtiment. Le mode de collecte précis dépendra du système retenu.",
    }),
    schematic({
      id: "eggs.transport",
      title: "Transport",
      short: "Un camion emporte les caisses vers un centre de tri et de conditionnement.",
      detail:
        "Le trajet est raccourci pour rester visible. Il s'agit d'un transport d'œufs, pas d'animaux.",
    }),
    schematic({
      id: "eggs.process",
      title: "Tri et conditionnement",
      short: "Au centre, les œufs sont triés puis emballés pour la vente.",
      detail:
        "L'intérieur du centre n'est pas montré : seules les caisses qui entrent et les palettes qui sortent illustrent cette étape.",
    }),
    schematic({
      id: "eggs.delivery",
      title: "Livraison",
      short: "Les boîtes partent en camion vers le magasin, jusqu'au rayon.",
      detail: "Le camion de livraison rejoint le magasin d'où vous êtes parti.",
    }),
    schematic({
      id: "eggs.recap.system",
      title: "Le système représenté",
      short: "Le système d'élevage montré reste à choisir et à documenter avant toute diffusion.",
      detail:
        "Les conditions de vie des poules pondeuses diffèrent fortement selon le système. Ce cartel sera rédigé à partir de sources vérifiées une fois le système choisi.",
      source: TODO_SOURCE,
      scope: "À définir",
    }),
    schematic({
      id: "eggs.recap.steps",
      title: "Les étapes",
      short:
        "Collecte au bâtiment, transport en caisses, tri et conditionnement, puis livraison au magasin.",
      detail:
        "La filière des œufs passe par un centre de conditionnement entre l'élevage et le magasin : elle ne suit pas le même parcours que les filières de viande.",
    }),
    schematic({
      id: "eggs.recap.scope",
      title: "Un cas, pas toute la filière",
      short:
        "Cette scène illustre un parcours type : les pratiques varient selon les exploitations.",
      detail:
        "Le parcours montré ne prétend pas représenter toutes les exploitations. Les sources consultables préciseront le pays, la période et le système concernés.",
    }),
  ],
  timeline: [
    {
      id: "collect",
      event: "collect",
      durationSec: 7,
      captionId: "eggs.collect",
      to: "CRATES_EGGS_COLLECT",
    },
    {
      id: "load-farm",
      event: "load",
      durationSec: 4,
      captionId: "eggs.collect",
      from: "CRATES_EGGS_COLLECT",
      to: "CARGO_EGGS_FARM",
    },
    {
      id: "to-packing",
      event: "drive",
      durationSec: 11,
      captionId: "eggs.transport",
      vehicle: "TRUCK_EGGS_FARM",
      pathId: "PATH_EGGS_FARM",
    },
    {
      id: "process",
      event: "process",
      durationSec: 9,
      captionId: "eggs.process",
      from: "CARGO_EGGS_FARM",
      to: "CARTONS_EGGS_PACKED",
    },
    {
      id: "load-delivery",
      event: "load",
      durationSec: 4,
      captionId: "eggs.process",
      from: "CARTONS_EGGS_PACKED",
      to: "CARGO_EGGS_DELIVERY",
    },
    {
      id: "to-store",
      event: "drive",
      durationSec: 8,
      captionId: "eggs.delivery",
      vehicle: "TRUCK_EGGS_DELIVERY",
      pathId: "PATH_EGGS_DELIVERY",
    },
    {
      id: "deliver",
      event: "deliver",
      durationSec: 2,
      captionId: "eggs.delivery",
      from: "CARGO_EGGS_DELIVERY",
    },
  ],
  recap: ["eggs.recap.system", "eggs.recap.steps", "eggs.recap.scope"],
  // No source attached yet: every caption is a draft (docs/CONTENT_SCHEMA.md).
  sources: [],
};
