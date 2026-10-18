import { NodeIO, type Document } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";
import { resolve } from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import {
  SCANNER_CONTRACT,
  STORE_CONTRACT,
  TERRACE_EGGS_CONTRACT,
  checkContract,
  type AssetContract,
  type ContractNode,
} from "../src/core/assetContract";
import { eggs } from "../src/data/chains/eggs";

/** Reader for the optimised GLBs (meshopt-compressed, quantised). */
async function reader(): Promise<NodeIO> {
  await MeshoptDecoder.ready;
  return new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ "meshopt.decoder": MeshoptDecoder });
}

function contractNodes(doc: Document): ContractNode[] {
  return doc
    .getRoot()
    .listNodes()
    .map((node) => ({ name: node.getName(), parentName: node.getParentNode()?.getName() ?? null }));
}

describe("checkContract", () => {
  const contract: AssetContract = {
    url: "",
    required: ["ROOT", "DOOR"],
    parents: { DOOR: "HINGE" },
    prefixes: [{ prefix: "COL_", min: 1 }],
  };

  it("accepts a conforming hierarchy", () => {
    const nodes = [
      { name: "ROOT", parentName: null },
      { name: "HINGE", parentName: "ROOT" },
      { name: "DOOR", parentName: "HINGE" },
      { name: "COL_DOOR", parentName: "DOOR" },
    ];
    expect(checkContract(nodes, contract)).toEqual([]);
  });

  it("reports missing nodes, wrong parents, duplicates and missing prefixes", () => {
    const nodes = [
      { name: "DOOR", parentName: "ROOT" },
      { name: "DOOR", parentName: "ROOT" },
    ];
    expect(checkContract(nodes, contract)).toEqual([
      "nom dupliqué : DOOR",
      "nœud manquant : ROOT",
      "DOOR doit être enfant de HINGE (trouvé : ROOT)",
      "au moins 1 nœud(s) COL_* attendus, 0 trouvé(s)",
    ]);
  });
});

describe.each([STORE_CONTRACT, TERRACE_EGGS_CONTRACT, SCANNER_CONTRACT])("$url", (contract) => {
  let doc: Document;

  beforeAll(async () => {
    doc = await (await reader()).read(resolve("public", `.${contract.url}`));
  });

  it("honours the naming contract", () => {
    expect(checkContract(contractNodes(doc), contract)).toEqual([]);
  });

  it("keeps every node at unit scale (transforms applied before export)", () => {
    const scaled = doc
      .getRoot()
      .listNodes()
      .filter((node) => node.getScale().some((s) => Math.abs(s - 1) > 1e-6))
      .map((node) => node.getName());
    expect(scaled).toEqual([]);
  });
});

describe("eggs timeline objects", () => {
  it("exist in the terrace GLB, with at least two points per path", async () => {
    const doc = await (await reader()).read(resolve("public", `.${TERRACE_EGGS_CONTRACT.url}`));
    const names = new Set(
      doc
        .getRoot()
        .listNodes()
        .map((n) => n.getName()),
    );
    const missing: string[] = [];
    for (const step of eggs.timeline) {
      for (const name of [step.from, step.to, step.vehicle]) {
        if (name && !names.has(name)) missing.push(name);
      }
      if (step.pathId) {
        const points = [...names].filter((n) => n.startsWith(`${step.pathId}_`));
        if (points.length < 2) missing.push(`${step.pathId}_NN (${points.length})`);
      }
    }
    expect(missing).toEqual([]);
  });
});
