import type { ModuleFactory } from "../../engine/module.ts";
import { announceRead, readOptions, SILENT, spreadFor, type Read } from "./common.ts";

/**
 * Bet (DESIGN.md 6.1): each round, bet that a hero will take an action, or
 * stay quiet. `tempo` 1 if right. M3's baseline module on the module
 * interface; it makes exactly the choices `bettor` did.
 */
export type BetMove = Read | null;

export const bet: ModuleFactory<BetMove> = () => {
  let last: string | null = null;
  return {
    id: "bet",
    options(moment, ctx) {
      if (moment.kind !== "round") return [];
      const options = readOptions(moment.round, ctx, last, () => ({ tempo: 1 }), (read): BetMove => read);
      // Silence last, so a bet wins a tie with it.
      options.push({ move: null, outcomes: [{ p: 1, utility: {} }] });
      return options;
    },
    announce: (move, step) => (move ? announceRead(move, step.disclosure, "has foretold it") : SILENT),
    resolve(move, _moment, { actions }) {
      if (!move) {
        last = null;
        return { kind: "silence", utility: {}, bets: [] };
      }
      const spread = spreadFor(last, move.hero);
      last = move.hero;
      const fulfilled = actions.get(move.hero) === move.action;
      return {
        kind: "bet",
        utility: { tempo: fulfilled ? 1 : 0, spread },
        bets: [{ hero: move.hero, action: move.action, fulfilled }],
      };
    },
  };
};
