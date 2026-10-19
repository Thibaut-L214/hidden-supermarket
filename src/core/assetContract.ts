// Naming contract between Blender exports and the runtime (docs/TECH.md §03, docs/DECISIONS.md).
// Used at runtime to validate a loaded GLB and by tests/assets.test.ts on the exported files.
import type { ChainId } from "./chain";

/** Helper volumes: exported in the GLB, never rendered. */
export const HIDDEN_PREFIXES = ["COL_", "SCAN_", "TRIGGER_"] as const;

export interface AssetContract {
  /** URL served by Vite (files live under public/). */
  url: string;
  /** Node names that must exist. */
  required: readonly string[];
  /** child name → expected direct parent name. */
  parents: Readonly<Record<string, string>>;
  /** Name prefixes that must match at least `min` nodes. */
  prefixes: readonly { prefix: string; min: number }[];
}

/** Node names of a scannable shelf in the store GLB. */
export function shelfNodes(chain: ChainId) {
  const id = chain.toUpperCase();
  return {
    root: `SHELF_${id}_ROOT`,
    hingeL: `HINGE_${id}_L`,
    hingeR: `HINGE_${id}_R`,
    doorL: `DOOR_${id}_L`,
    doorR: `DOOR_${id}_R`,
    scan: `SCAN_${id}`,
    entry: `TRIGGER_${id}_ENTRY`,
    terraceAnchor: `ANCHOR_${id}_TERRACE`,
    sign: `SIGN_${id}`,
    /** « Scannable » pictogram beside the sign (docs/GDD.md §06.0). */
    picto: `PICTO_SCAN_${id}`,
  } as const;
}

/** Node names of a chain's terrace module GLB. */
export function terraceNodes(chain: ChainId) {
  const id = chain.toUpperCase();
  return {
    root: `TERRACE_${id}_ROOT`,
    view: `ANCHOR_${id}_VIEW`,
    focus: `ANCHOR_${id}_FOCUS`,
    roof: `ROOF_${id}`,
    interior: `INTERIOR_${id}`,
    /** Animals of the farm building, shown once the roof is off. */
    hens: `HENS_${id}`,
  } as const;
}

function shelfContract(chain: ChainId): Pick<AssetContract, "required" | "parents"> {
  const n = shelfNodes(chain);
  return {
    required: Object.values(n),
    parents: {
      [n.hingeL]: n.root,
      [n.hingeR]: n.root,
      [n.doorL]: n.hingeL,
      [n.doorR]: n.hingeR,
      [n.scan]: n.root,
      [n.entry]: n.root,
      [n.terraceAnchor]: n.root,
    },
  };
}

/** Store exit: sliding entrance leaves, exit zone inside, forecourt zone outside. */
export const EXIT_NODES = {
  doorL: "STORE_ENTRANCE_DOOR_L",
  doorR: "STORE_ENTRANCE_DOOR_R",
  exitZone: "TRIGGER_EXIT",
  parvisZone: "TRIGGER_PARVIS",
  parvis: "PARVIS_ROOT",
} as const;

const eggsShelf = shelfContract("eggs");

export const STORE_CONTRACT: AssetContract = {
  url: "/assets/store/store.glb",
  required: ["STORE_ROOT", "SPAWN_PLAYER", ...Object.values(EXIT_NODES), ...eggsShelf.required],
  parents: {
    ...eggsShelf.parents,
    COL_ENTRANCE_DOOR_L: EXIT_NODES.doorL,
    COL_ENTRANCE_DOOR_R: EXIT_NODES.doorR,
  },
  prefixes: [
    { prefix: "COL_", min: 1 },
    { prefix: "VOLUNTEER_", min: 2 },
  ],
};

const eggsTerrace = terraceNodes("eggs");

export const TERRACE_EGGS_CONTRACT: AssetContract = {
  url: "/assets/eggs/terrace_eggs.glb",
  required: [
    ...Object.values(eggsTerrace),
    "BUILDING_EGGS_FARM",
    "PACKING_EGGS_CENTER",
    "TRUCK_EGGS_ANIMALS",
    "HENCRATES_EGGS_HALL",
    "HENCRATES_EGGS_TRUCK",
  ],
  parents: {
    [eggsTerrace.view]: eggsTerrace.root,
    [eggsTerrace.focus]: eggsTerrace.root,
    [eggsTerrace.roof]: eggsTerrace.root,
  },
  // Guardrails on three sides of the terrace.
  prefixes: [{ prefix: "COL_RAIL_", min: 3 }],
};

/** First-person scanner: hand and handheld terminal (docs/DA.md §05). */
export const SCANNER_CONTRACT: AssetContract = {
  url: "/assets/shared/scanner_hand.glb",
  required: ["SCANNER_ROOT", "SCANNER_BODY", "SCANNER_SCREEN", "SCANNER_WINDOW", "SCANNER_HAND"],
  parents: {
    SCANNER_BODY: "SCANNER_ROOT",
    SCANNER_SCREEN: "SCANNER_ROOT",
    SCANNER_WINDOW: "SCANNER_ROOT",
    SCANNER_HAND: "SCANNER_ROOT",
  },
  prefixes: [],
};

export interface ContractNode {
  name: string;
  parentName: string | null;
}

/** Returns human-readable violations; an empty list means the asset honours the contract. */
export function checkContract(nodes: readonly ContractNode[], contract: AssetContract): string[] {
  const byName = new Map<string, ContractNode>();
  const errors: string[] = [];
  for (const node of nodes) {
    if (byName.has(node.name)) errors.push(`nom dupliqué : ${node.name}`);
    byName.set(node.name, node);
  }
  for (const name of contract.required) {
    if (!byName.has(name)) errors.push(`nœud manquant : ${name}`);
  }
  for (const [child, parent] of Object.entries(contract.parents)) {
    const node = byName.get(child);
    if (node && node.parentName !== parent) {
      errors.push(
        `${child} doit être enfant de ${parent} (trouvé : ${node.parentName ?? "racine"})`,
      );
    }
  }
  for (const { prefix, min } of contract.prefixes) {
    const count = nodes.filter((n) => n.name.startsWith(prefix)).length;
    if (count < min) errors.push(`au moins ${min} nœud(s) ${prefix}* attendus, ${count} trouvé(s)`);
  }
  return errors;
}

export function isHiddenHelper(name: string): boolean {
  return HIDDEN_PREFIXES.some((prefix) => name.startsWith(prefix));
}
