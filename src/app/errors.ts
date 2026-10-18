// Runtime failures must never trap the visitor (docs/GDD.md §05 invariants).
import type { GameState } from "../core/GameState";

export const RUNTIME_FAILURE = "Un problème est survenu pendant la visite.";

/**
 * Routes an unexpected error to the safe return when a shelf is open. Returns true when a
 * recovery was started; in the store itself there is nothing to unwind.
 */
export function recoverFromError(game: GameState): boolean {
  const { state, activeChain } = game.snapshot;
  if (!activeChain || state === "ERROR" || state === "SAFE_RETURN") return false;
  return game.send({ type: "FAILURE", reason: RUNTIME_FAILURE });
}

/** Logs an error once per distinct message, so a failure repeated every frame stays readable. */
export function createErrorLog(log: (error: unknown) => void = console.error) {
  let last = "";
  return (error: unknown) => {
    const message = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
    if (message === last) return;
    last = message;
    log(error);
  };
}
