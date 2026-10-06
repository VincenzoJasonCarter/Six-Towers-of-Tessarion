import type { ModuleFactory } from "../../engine/module.ts";
import { announceRead, FIGHT_VALUE, readOptions, SILENT, spreadFor, type Read } from "./common.ts";

/** Press: a plain blow on a hero, `lethal` 0.5 and sure. */
export const PRESS = 0.5;

/**
 * Punish (DESIGN.md 6.1): each round, ready a cut against a hero's action
 * (if they take it, it is cut: `lethal` by its fight value), press a hero
 * with a plain blow, or do nothing. Reading, weighted by what an action is
 * worth.
 */
export type PunishMove = ({ readonly kind: "cut" } & Read) | { readonly kind: "press"; readonly hero: string } | null;

export const punish: ModuleFactory<PunishMove> = () => {
  let last: string | null = null;
  return {
    id: "punish",
    options(moment, ctx) {
      if (moment.kind !== "round") return [];
      const cuts = readOptions(
        moment.round,
        ctx,
        last,
        (action) => ({ lethal: FIGHT_VALUE[action]! }),
        (read): PunishMove => ({ kind: "cut", ...read }),
      );
      const presses = ctx.heroes.map((h) => ({
        move: { kind: "press", hero: h.id } as PunishMove,
        outcomes: [{ p: 1, utility: { lethal: PRESS, spread: spreadFor(last, h.id) } }],
      }));
      return [...cuts, ...presses, { move: null, outcomes: [{ p: 1, utility: {} }] }];
    },
    announce: (move, step) => (move?.kind === "cut" ? announceRead(move, step.disclosure, "will cut it") : SILENT),
    resolve(move, _moment, { actions }) {
      if (!move) {
        last = null;
        return { kind: "nothing", utility: {}, bets: [] };
      }
      const spread = spreadFor(last, move.hero);
      last = move.hero;
      if (move.kind === "press") return { kind: "press", utility: { lethal: PRESS, spread }, bets: [] };
      const fulfilled = actions.get(move.hero) === move.action;
      return {
        kind: "cut",
        utility: { lethal: fulfilled ? FIGHT_VALUE[move.action]! : 0, spread },
        bets: [{ hero: move.hero, action: move.action, fulfilled }],
      };
    },
  };
};
