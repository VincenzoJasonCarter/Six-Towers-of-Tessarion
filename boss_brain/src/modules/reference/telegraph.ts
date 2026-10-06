import { GUARD } from "../../engine/actions.ts";
import type { Option } from "../../engine/decision/decide.ts";
import type { ModuleFactory } from "../../engine/module.ts";
import { heedModel, SILENT, spreadFor } from "../common.ts";

export const WIND_UP = 1.5;
export const QUICK = 1;

/**
 * Telegraph (DESIGN.md 6.1): each round, wind up a big blow on a hero, who
 * sees it coming (`lethal` 1.5 unless they Guard, and `show` 1 either way), or
 * strike quickly and unseen (`lethal` 1 unless they Guard), or do nothing.
 * Drama against efficiency.
 *
 * How likely each blow is to be guarded comes from `heedModel`.
 */
export type TelegraphMove = { readonly kind: "wind-up" | "quick"; readonly hero: string } | null;

export const telegraph: ModuleFactory<TelegraphMove> = (heroes) => {
  let last: string | null = null;
  const heed = heedModel(heroes);
  return {
    id: "telegraph",
    options(moment, ctx) {
      if (moment.kind !== "round") return [];
      const options: Option<TelegraphMove>[] = [];
      for (const hero of ctx.heroes) {
        const spread = spreadFor(last, hero.id);
        const guards = heed.look(hero.id, moment.round, ctx);
        options.push({
          move: { kind: "wind-up", hero: hero.id },
          outcomes: [
            { p: 1 - guards.warned, utility: { lethal: WIND_UP, show: 1, spread } },
            { p: guards.warned, utility: { show: 1, spread } },
          ],
        });
        options.push({
          move: { kind: "quick", hero: hero.id },
          outcomes: [
            { p: 1 - guards.unwarned, utility: { lethal: QUICK, spread } },
            { p: guards.unwarned, utility: { spread } },
          ],
        });
      }
      options.push({ move: null, outcomes: [{ p: 1, utility: {} }] });
      return options;
    },
    announce: (move) =>
      move?.kind === "wind-up" ? { named: [], warned: [move.hero], text: `The boss winds up a blow at ${move.hero}.` } : SILENT,
    resolve(move, _moment, { actions }) {
      if (!move) {
        last = null;
        return { kind: "nothing", utility: {}, bets: [] };
      }
      const spread = spreadFor(last, move.hero);
      last = move.hero;
      const guard = actions.get(move.hero) === GUARD;
      if (move.kind === "quick") return { kind: "quick", utility: { lethal: guard ? 0 : QUICK, spread }, bets: [] };
      heed.learn(move.hero, guard);
      return { kind: "wind-up", utility: { lethal: guard ? 0 : WIND_UP, show: 1, spread }, bets: [] };
    },
  };
};
