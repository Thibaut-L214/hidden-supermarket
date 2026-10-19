// Indoor finishing is one selected scenario. Sources support claims; editorial review remains due.
import { BEEF_MARKER_ANCHORS, TERRACE_BEEF_CONTRACT } from "../../core/assetContract";
import type { ChainConfig } from "../../features/chains/ChainModule";
import type { Caption, SourceRef } from "../../features/content/types";

const FR_BEEF: SourceRef = {
  id: "fr-beef-farming",
  label: "Le bien-être et la protection des vaches à viande",
  url: "https://agriculture.gouv.fr/le-bien-etre-et-la-protection-des-vaches-viande",
  publisher: "Ministère de l’Agriculture",
  consultedAt: "2026-10-19",
};

const EFSA_BEEF: SourceRef = {
  id: "efsa-beef-welfare-2025",
  label: "Bien-être des bovins de boucherie",
  url: "https://www.efsa.europa.eu/fr/plain-language-summary/welfare-beef-cattle",
  publisher: "Autorité européenne de sécurité des aliments (EFSA)",
  consultedAt: "2026-10-19",
};

const EFSA_TRANSPORT: SourceRef = {
  id: "efsa-cattle-transport-2022",
  label: "Bien-être des bovins pendant le transport",
  url: "https://www.efsa.europa.eu/fr/plain-language-summary/welfare-cattle-during-transport",
  publisher: "Autorité européenne de sécurité des aliments (EFSA)",
  consultedAt: "2026-10-19",
};

const EFSA_SLAUGHTER: SourceRef = {
  id: "efsa-cattle-slaughter-2020",
  label: "Welfare of cattle at slaughter — bien-être des bovins à l’abattoir",
  url: "https://www.efsa.europa.eu/en/efsajournal/pub/6275",
  publisher: "Autorité européenne de sécurité des aliments (EFSA)",
  consultedAt: "2026-10-19",
};

const FR_SLAUGHTER: SourceRef = {
  id: "fr-slaughterhouse-protection",
  label: "La protection des animaux à l’abattoir",
  url: "https://agriculture.gouv.fr/la-protection-des-animaux-labattoir",
  publisher: "Ministère de l’Agriculture",
  consultedAt: "2026-10-19",
};

const EU_HYGIENE: SourceRef = {
  id: "eu-food-hygiene-853-2004",
  label: "Règlement (CE) 853/2004 — hygiène des denrées alimentaires d’origine animale",
  url: "https://eur-lex.europa.eu/legal-content/FR/ALL/?uri=celex%3A32004R0853",
  publisher: "Parlement européen et Conseil de l’Union européenne",
  consultedAt: "2026-10-19",
};

const schematic = (caption: Omit<Caption, "kind" | "status" | "scope">) =>
  ({ kind: "schematic", status: "draft", scope: "Illustration", ...caption }) satisfies Caption;

const verified = (caption: Omit<Caption, "kind" | "status">) =>
  ({ kind: "verified", status: "review", ...caption }) satisfies Caption;

export const beef: ChainConfig = {
  id: "beef",
  label: "Viande bovine",
  terrace: TERRACE_BEEF_CONTRACT,
  systemType: "Engraissement en bâtiment",
  terraceCaption: "beef.terrace",
  revealCaption: "beef.system",
  captions: [
    schematic({
      id: "beef.terrace",
      title: "Représentation schématique",
      short:
        "Ce parcours illustre un engraissement en bâtiment, puis l’abattoir et la livraison de viande au magasin.",
      detail:
        "Le rayon propose des steaks et de la viande hachée. Le paysage rapproche les étapes et réduit leurs durées. Les animaux, bâtiments et véhicules ne reproduisent aucun site réel. Les effectifs visibles ne donnent aucune densité d’élevage.",
    }),
    schematic({
      id: "beef.site",
      title: "Un site, plusieurs bâtiments",
      short:
        "Les bâtiments d’engraissement se répètent pour figurer l’échelle d’un site. Leur nombre est schématique.",
      detail:
        "Plusieurs bâtiments identiques se succèdent pour montrer l’aspect répétitif d’un site d’engraissement. Cette scène ne donne ni le nombre de bâtiments ni l’effectif d’un élevage réel.",
    }),
    verified({
      id: "beef.system",
      title: "Engraissement en bâtiment",
      short:
        "L’engraissement peut avoir lieu en bâtiment, en prairie ou dans un système mixte. Ici, nous montrons le bâtiment.",
      detail:
        "L’engraissement vise à développer la masse musculaire du bovin par son alimentation. Ce scénario commence pendant cette phase : il ne décrit pas toute sa vie ni tous les élevages bovins.",
      source: FR_BEEF,
      scope: "France, présentation du ministère publiée en 2019",
    }),
    verified({
      id: "beef.load",
      title: "Chargement des bovins",
      short:
        "Les bovins rejoignent le camion à pied. Le chargement comporte des risques de stress et de blessures.",
      detail:
        "L’EFSA identifie des risques liés aux manipulations et aux installations pendant le chargement et le déchargement. La marche visible schématise ces déplacements ; elle ne mesure pas leur difficulté.",
      source: EFSA_TRANSPORT,
      scope: "Union européenne, avis scientifique de 2022",
    }),
    verified({
      id: "beef.transport",
      title: "Transport vers l’abattoir",
      short:
        "Le camion transporte des bovins vivants. Chaleur, mouvements et durée du trajet peuvent affecter leur bien-être.",
      detail:
        "L’EFSA décrit notamment des risques de stress thermique, de soif et de fatigue. Leur survenue dépend des conditions du transport. La scène ne représente ni une distance ni une durée réelle.",
      source: EFSA_TRANSPORT,
      scope: "Union européenne, avis scientifique de 2022",
    }),
    verified({
      id: "beef.waiting",
      title: "Déchargement et attente",
      short:
        "À l’abattoir, les bovins quittent le camion à pied, puis attendent dans un espace d’hébergement.",
      detail:
        "L’EFSA distingue le déchargement, l’attente et la conduite vers l’étourdissement. La scène rapproche ces étapes ; elle ne fixe pas la durée d’attente.",
      source: EFSA_SLAUGHTER,
      scope: "Union européenne, avis scientifique de 2020",
    }),
    verified({
      id: "beef.approach",
      title: "Vers la zone d’étourdissement",
      short: "Les bovins avancent à pied dans le couloir vers la zone d’étourdissement.",
      detail:
        "La conduite des animaux précède l’étourdissement dans le scénario choisi. L’EFSA identifie des risques de peur et de restriction des mouvements lors de cette phase.",
      source: EFSA_SLAUGHTER,
      scope: "Union européenne, avis scientifique de 2020",
    }),
    verified({
      id: "beef.slaughter",
      title: "Étourdissement et mise à mort",
      short:
        "Hors champ : étourdissement, puis saignée pour la mise à mort dans le scénario présenté.",
      detail:
        "L’étourdissement vise la perte de conscience. La saignée provoque ensuite la mort. L’étourdissement peut échouer ; l’animal peut aussi reprendre conscience avant sa mort. Les opérateurs doivent surveiller ces risques. La scène ne décrit pas toutes les pratiques d’abattage et garde ces opérations hors champ, sans image sanglante.",
      source: EFSA_SLAUGHTER,
      scope: "Union européenne, avis scientifique de 2020 ; scénario avec étourdissement préalable",
    }),
    verified({
      id: "beef.chill",
      title: "Chambre froide",
      short: "Après la mise à mort et la préparation, les carcasses passent en chambre froide.",
      detail:
        "Le ministère décrit la préparation des carcasses, leur inspection vétérinaire et leur réfrigération. La scène omet les opérations de préparation et montre des volumes de viande simplifiés.",
      source: FR_SLAUGHTER,
      scope: "France, présentation du ministère publiée en 2019",
    }),
    verified({
      id: "beef.cut",
      title: "Découpe",
      short: "L’atelier découpe la viande en morceaux en maîtrisant sa température.",
      detail:
        "Les règles européennes d’hygiène encadrent la température pendant la découpe. La scène illustre cette étape sans reproduire les gestes de travail.",
      source: EU_HYGIENE,
      scope: "Union européenne, règles d’hygiène des viandes d’ongulés domestiques",
    }),
    verified({
      id: "beef.pack",
      title: "Conditionnement",
      short: "L’atelier conditionne les morceaux, puis prépare les colis pour la livraison.",
      detail:
        "Le règlement encadre le conditionnement, l’emballage et la maîtrise de la température des viandes. Les cartons visibles simplifient les colis ; ils ne montrent pas tous les emballages.",
      source: EU_HYGIENE,
      scope: "Union européenne, règles d’hygiène des viandes d’ongulés domestiques",
    }),
    verified({
      id: "beef.delivery",
      title: "Livraison réfrigérée",
      short: "Le camion réfrigéré transporte les colis de viande jusqu’au magasin.",
      detail:
        "La température de la viande doit rester maîtrisée pendant le transport. Ce camion représente un circuit de livraison possible jusqu’au rayon.",
      source: EU_HYGIENE,
      scope: "Union européenne, règles d’hygiène des viandes d’ongulés domestiques",
    }),
    verified({
      id: "beef.recap.welfare",
      title: "Des besoins à respecter",
      short:
        "Le manque d’espace et un sol inconfortable peuvent gêner le repos des bovins en bâtiment.",
      detail:
        "L’EFSA recommande de l’espace, une litière souple, de l’eau salubre et l’accès au fourrage. Ces besoins permettent d’évaluer les conditions d’élevage. Les risques décrits ne constituent pas un constat sur chaque exploitation.",
      source: EFSA_BEEF,
      scope: "Union européenne, avis scientifique de 2025",
    }),
    schematic({
      id: "beef.recap.steps",
      title: "Des animaux à la viande",
      short: "Le parcours suit les bovins jusqu’à la mise à mort, puis la viande jusqu’au magasin.",
      detail:
        "Chargement, transport, attente et approche précèdent l’étourdissement et la saignée hors champ. Viennent ensuite la chambre froide, la découpe, le conditionnement et la livraison réfrigérée.",
    }),
    verified({
      id: "beef.recap.scope",
      title: "Un parcours parmi d’autres",
      short:
        "La viande bovine peut provenir de troupeaux allaitants ou laitiers. Ce bâtiment ne représente pas toute la filière.",
      detail:
        "Le ministère distingue ces origines et les engraissements en prairie, en bâtiment ou mixtes. Ce parcours choisit un engraissement en bâtiment sans prétendre représenter toute la viande rouge.",
      source: FR_BEEF,
      scope: "France, présentation du ministère publiée en 2019",
    }),
  ],
  timeline: [
    {
      id: "load-cattle",
      event: "walk",
      durationSec: 10,
      captionId: "beef.load",
      from: "CATTLE_BEEF_FARM",
      to: "CATTLE_BEEF_TRUCK",
      pathId: "PATH_BEEF_LOAD",
    },
    {
      id: "to-slaughterhouse",
      event: "drive",
      durationSec: 11,
      captionId: "beef.transport",
      vehicle: "TRUCK_BEEF_ANIMALS",
      pathId: "PATH_BEEF_ANIMALS",
    },
    {
      id: "unload-cattle",
      event: "walk",
      durationSec: 9,
      captionId: "beef.waiting",
      from: "CATTLE_BEEF_TRUCK",
      to: "CATTLE_BEEF_WAITING",
      pathId: "PATH_BEEF_UNLOAD",
    },
    {
      id: "approach",
      event: "walk",
      durationSec: 9,
      captionId: "beef.approach",
      from: "CATTLE_BEEF_WAITING",
      to: "CATTLE_BEEF_APPROACH",
      pathId: "PATH_BEEF_APPROACH",
    },
    {
      id: "slaughter",
      event: "process",
      durationSec: 9,
      captionId: "beef.slaughter",
      from: "CATTLE_BEEF_APPROACH",
    },
    {
      id: "chill",
      event: "collect",
      durationSec: 7,
      captionId: "beef.chill",
      to: "MEAT_BEEF_CHILLED",
    },
    {
      id: "cut",
      event: "process",
      durationSec: 7,
      captionId: "beef.cut",
      from: "MEAT_BEEF_CHILLED",
      to: "MEAT_BEEF_CUT",
    },
    {
      id: "pack",
      event: "process",
      durationSec: 6,
      captionId: "beef.pack",
      from: "MEAT_BEEF_CUT",
      to: "CARTONS_BEEF_PACKED",
    },
    {
      id: "load-delivery",
      event: "load",
      durationSec: 4,
      captionId: "beef.delivery",
      from: "CARTONS_BEEF_PACKED",
      to: "CARGO_BEEF_DELIVERY",
    },
    {
      id: "to-store",
      event: "drive",
      durationSec: 9,
      captionId: "beef.delivery",
      vehicle: "TRUCK_BEEF_DELIVERY",
      pathId: "PATH_BEEF_DELIVERY",
    },
    {
      id: "deliver",
      event: "deliver",
      durationSec: 3,
      captionId: "beef.delivery",
      from: "CARGO_BEEF_DELIVERY",
    },
  ],
  markers: [
    { anchor: BEEF_MARKER_ANCHORS[0], captionId: "beef.recap.welfare" },
    { anchor: BEEF_MARKER_ANCHORS[1], captionId: "beef.site" },
  ],
  recap: ["beef.recap.welfare", "beef.recap.steps", "beef.recap.scope"],
  sources: [FR_BEEF, EFSA_BEEF, EFSA_TRANSPORT, EFSA_SLAUGHTER, FR_SLAUGHTER, EU_HYGIENE],
};
