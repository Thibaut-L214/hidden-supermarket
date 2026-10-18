import type { ChainId } from "../core/chain";
import type { EventBus } from "../core/EventBus";
import type { GameEvents } from "../core/GameState";

/**
 * Per-visit memory, kept in memory only (docs/TECH.md §05: sessionStorage stays optional
 * pending the privacy policy).
 */
export class Session {
  private readonly explored = new Set<ChainId>();

  markExplored(chain: ChainId): void {
    this.explored.add(chain);
  }

  hasExplored(chain: ChainId): boolean {
    return this.explored.has(chain);
  }

  get exploredChains(): ChainId[] {
    return [...this.explored];
  }
}

/** A shelf counts as explored once its chain has played to the recap. */
export function trackExploration(bus: EventBus<GameEvents>, session: Session): () => void {
  return bus.on("stateChanged", ({ to, snapshot }) => {
    if (to === "RECAP" && snapshot.activeChain) session.markExplored(snapshot.activeChain);
  });
}
