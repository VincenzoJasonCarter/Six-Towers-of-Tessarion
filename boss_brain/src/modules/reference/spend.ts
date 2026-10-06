import type { ModuleFactory } from "../../engine/module.ts";
import { announceRead, FIGHT_VALUE, readOptions, SILENT, spreadFor, type Read } from "../common.ts";

/** Charges the boss starts a fight with; they don't come back. */
export const BUDGET = 3;
/** How long the module expects a fight to last; at the table, the DM's guess. */
export const EXPECTED_ROUNDS = 10;

/**
 * Spend or hold (DESIGN.md 6.1): the boss starts with a few charges that
 * don't come back. Each round it holds them (`tempo`, worth the share of the
 * fight still to come, so a charge is worth less as the fight runs out) or
 * spends one on a cut, as in Punish. Timing: patience against impatience.
 *
 * A spend commits a scarce charge, so it is not a probe: it carries no
 * exploration bonus.
 */
export type SpendMove = ({ readonly kind: "spend" } & Read) | null;

const holdValue = (round: number) => Math.max(0, EXPECTED_ROUNDS - round) / EXPECTED_ROUNDS;

export const spendOrHold: ModuleFactory<SpendMove> = () => {
  let last: string | null = null;
  let charges = BUDGET;
  return {
    id: "spend-or-hold",
    options(moment, ctx) {
      if (moment.kind !== "round" || charges === 0) return [];
      const spends = readOptions(
        moment.round,
        ctx,
        last,
        (action) => ({ lethal: FIGHT_VALUE[action]! }),
        (read): SpendMove => ({ kind: "spend", ...read }),
        { probe: false },
      );
      return [...spends, { move: null, outcomes: [{ p: 1, utility: { tempo: holdValue(moment.round) } }] }];
    },
    announce: (move, step) => (move ? announceRead(move, step.disclosure, "will spend a charge to cut it") : SILENT),
    resolve(move, moment, { actions }) {
      if (!move) {
        last = null;
        return { kind: "hold", utility: { tempo: holdValue(moment.round) }, bets: [] };
      }
      const spread = spreadFor(last, move.hero);
      last = move.hero;
      charges -= 1;
      const fulfilled = actions.get(move.hero) === move.action;
      return {
        kind: "spend",
        utility: { lethal: fulfilled ? FIGHT_VALUE[move.action]! : 0, spread },
        bets: [{ hero: move.hero, action: move.action, fulfilled }],
        detail: { aimedValue: FIGHT_VALUE[move.action]!, round: moment.round },
      };
    },
  };
};
