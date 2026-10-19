// Eggs shelf (docs/GDD.md §06). Verified statements cite their source; scene-specific movements
// remain explicitly schematic. Editorial review is still required before publication.
import { TERRACE_EGGS_CONTRACT } from "../../core/assetContract";
import type { ChainConfig } from "../../features/chains/ChainModule";
import type { Caption, SourceRef } from "../../features/content/types";

const EU_LAYING_HENS: SourceRef = {
  id: "eu-laying-hens-1999-74",
  label: "Directive 1999/74/CE — normes minimales pour les poules pondeuses",
  url: "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:31999L0074",
  publisher: "Conseil de l’Union européenne",
  consultedAt: "2026-10-19",
};

const EU_EGGS_MARKETING: SourceRef = {
  id: "eu-eggs-marketing-2023-2465",
  label: "Règlement (UE) 2023/2465 — normes de commercialisation des œufs",
  url: "https://eur-lex.europa.eu/eli/reg_del/2023/2465/oj?locale=fr",
  publisher: "Commission européenne",
  consultedAt: "2026-10-19",
};

const FR_EGGS_PRODUCTION: SourceRef = {
  id: "fr-eggs-production-2024",
  label: "La production d’œufs française — données 2024",
  url: "https://agriculture.gouv.fr/la-production-doeufs-francaise",
  publisher: "Ministère de l’Agriculture",
  consultedAt: "2026-10-19",
};

const EFSA_POULTRY_TRANSPORT: SourceRef = {
  id: "efsa-poultry-transport-2022",
  label: "Avis scientifique sur le transport des oiseaux en conteneurs",
  url: "https://www.efsa.europa.eu/en/efsajournal/pub/7441",
  publisher: "Autorité européenne de sécurité des aliments (EFSA)",
  consultedAt: "2026-10-19",
};

const schematic = (caption: Omit<Caption, "kind" | "status" | "scope"> & { scope?: string }) =>
  ({ kind: "schematic", status: "draft", scope: "Illustration", ...caption }) satisfies Caption;

const verified = (caption: Omit<Caption, "kind" | "status">) =>
  ({ kind: "verified", status: "review", ...caption }) satisfies Caption;

export const eggs: ChainConfig = {
  id: "eggs",
  label: "Œufs",
  terrace: TERRACE_EGGS_CONTRACT,
  // Stacked enriched cages: editorial choice documented in docs/DECISIONS.md.
  systemType: "Cages",
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
    verified({
      id: "eggs.system",
      title: "Cages aménagées",
      short:
        "Dans l’Union européenne, une cage aménagée offre au moins 750 cm² par poule.",
      detail:
        "Le minimum réglementaire est de 750 cm² par poule, dont 600 cm² utilisables. La cage doit aussi comporter un nid, une litière et au moins 15 cm de perchoir par poule. La vue schématise les rangées et ne montre pas tous ces équipements.",
      source: EU_LAYING_HENS,
      scope: "Union européenne, règles applicables aux cages aménagées",
    }),
    verified({
      id: "eggs.hens.load",
      title: "Fin de la période de ponte",
      short:
        "À la fin de la période de ponte, les poules sont chargées en conteneurs pour quitter l’élevage.",
      detail:
        "Cette séquence se déroule après le parcours des œufs. L’EFSA distingue la préparation, le chargement, le trajet, l’arrivée et la sortie des conteneurs. Elle relève notamment des risques de stress de manipulation et de blessures.",
      source: EFSA_POULTRY_TRANSPORT,
      scope: "Union européenne, avis scientifique adopté en 2022",
    }),
    verified({
      id: "eggs.hens.leave",
      title: "Transport vers l’abattoir",
      short: "Le camion conduit les poules en fin de ponte vers un abattoir, hors champ dans cette scène.",
      detail:
        "L’avis de l’EFSA examine spécifiquement le transport routier des poules en fin de ponte vers l’abattoir. La scène montre le départ du camion, mais pas le trajet ni l’arrivée.",
      source: EFSA_POULTRY_TRANSPORT,
      scope: "Union européenne, avis scientifique adopté en 2022",
    }),
    schematic({
      id: "eggs.collect",
      title: "Collecte",
      short: "Les œufs sont rassemblés au bout du bâtiment, puis placés en caisses.",
      detail:
        "Étape illustrée : la collecte est représentée par des caisses qui s'accumulent à la sortie du bâtiment. Le mode de collecte précis dépendra du système retenu.",
    }),
    verified({
      id: "eggs.transport",
      title: "Vers le centre d’emballage",
      short: "Dans le cas montré, un camion transporte les œufs vers un centre d’emballage agréé.",
      detail:
        "Le centre d’emballage peut être installé sur le même site que l’élevage. Le camion illustre donc un circuit possible. Il transporte des œufs ; le transport des poules intervient après.",
      source: EU_EGGS_MARKETING,
      scope: "Union européenne, circuit schématique soumis aux règles de commercialisation",
    }),
    verified({
      id: "eggs.process",
      title: "Tri et conditionnement",
      short: "Les œufs de catégorie A sont triés par qualité et poids, puis marqués et emballés sous 10 jours.",
      detail:
        "Dans l’Union européenne, un centre d’emballage classe les œufs de catégorie A par qualité et poids. Ils doivent être triés, marqués et emballés dans les 10 jours suivant la ponte. L’intérieur du centre n’est pas montré.",
      source: EU_EGGS_MARKETING,
      scope: "Union européenne, règlement applicable depuis 2023",
    }),
    schematic({
      id: "eggs.delivery",
      title: "Livraison",
      short: "Dans le cas montré, les boîtes partent en camion vers le magasin, jusqu’au rayon.",
      detail:
        "Le camion de livraison rejoint le magasin d’où vous êtes parti. Cette scène ne représente pas les circuits de vente directe.",
    }),
    verified({
      id: "eggs.recap.system",
      title: "Le système montré",
      short: "Une cage aménagée offre au moins 750 cm² par poule, dont 600 cm² utilisables.",
      detail:
        "La réglementation exige aussi un nid, une litière permettant le picotage et le grattage, et au moins 15 cm de perchoir par poule. Ces minima ne décrivent pas toutes les conditions d’un élevage.",
      source: EU_LAYING_HENS,
      scope: "Union européenne, règles applicables aux cages aménagées",
    }),
    verified({
      id: "eggs.recap.steps",
      title: "Du bâtiment au magasin",
      short:
        "Les œufs sont collectés, triés par qualité et poids, marqués, emballés, puis livrés au magasin.",
      detail:
        "Le centre d’emballage sépare la qualité des œufs et leur poids avant la vente. La séquence des poules en fin de ponte intervient ensuite : elle ne fait pas partie du transport des œufs.",
      source: EU_EGGS_MARKETING,
      scope: "Union européenne, règlement applicable depuis 2023",
    }),
    verified({
      id: "eggs.recap.scope",
      title: "Un système minoritaire en France",
      short:
        "En France, 72 % des poules pondeuses étaient élevées hors cage en 2024 : cette scène montre un autre système.",
      detail:
        "Le ministère de l’Agriculture indique que 72 % des poules pondeuses françaises étaient élevées hors cage en 2024. Le système en cages montré ici ne représente donc ni tous les élevages ni le système majoritaire en France.",
      source: FR_EGGS_PRODUCTION,
      scope: "France, données 2024 publiées en 2026",
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
    {
      id: "load-hens",
      event: "load",
      durationSec: 7,
      captionId: "eggs.hens.load",
      from: "HENCRATES_EGGS_HALL",
      to: "HENCRATES_EGGS_TRUCK",
      carry: true,
    },
    {
      id: "hens-leave",
      event: "drive",
      durationSec: 8,
      captionId: "eggs.hens.leave",
      vehicle: "TRUCK_EGGS_ANIMALS",
      pathId: "PATH_EGGS_ANIMALS",
    },
  ],
  recap: ["eggs.recap.system", "eggs.recap.steps", "eggs.recap.scope"],
  sources: [EU_LAYING_HENS, EU_EGGS_MARKETING, FR_EGGS_PRODUCTION, EFSA_POULTRY_TRANSPORT],
};
