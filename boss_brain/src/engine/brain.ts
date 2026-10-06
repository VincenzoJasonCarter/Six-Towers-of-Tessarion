import type { Action } from "./actions.ts";
import type { BeliefModel, ObservationContext } from "./belief/types.ts";
import { decide, tempered, watched, type Decision, type Watched } from "./decision/decide.ts";
import type { Temperament } from "./decision/temperament.ts";
import type { Announcement, Module, Moment, Observed, Resolution } from "./module.ts";
import type { Rng } from "./rng.ts";
import type { HeroSpec } from "./subclasses.ts";

export interface Choice<M> {
  readonly move: M;
  readonly announcement: Announcement;
  /** Every option with its score, for the explanation (DESIGN.md 4.5). */
  readonly decision: Decision<M>;
}

/**
 * One boss in one fight: a belief, a temperament and a module, wired the way
 * DESIGN.md 4 draws them. Observe each turn, ask for a choice at each moment,
 * and resolve what was chosen; the brain tells the belief what the table has
 * seen.
 */
export class Brain<M> {
  readonly belief: Watched;
  readonly step: Temperament;
  readonly module: Module<M>;
  readonly #heroes: readonly HeroSpec[];
  readonly #rng: Rng;

  constructor(belief: BeliefModel, step: Temperament, module: Module<M>, heroes: readonly HeroSpec[], rng: Rng) {
    this.belief = watched(belief);
    this.step = step;
    this.module = module;
    this.#heroes = heroes;
    this.#rng = rng;
  }

  /** The boss's choice at this moment, or null if its module doesn't act now. */
  choose(moment: Moment): Choice<M> | null {
    const view = tempered(this.belief, this.step);
    const options = this.module.options(moment, { heroes: this.#heroes, view, belief: this.belief, step: this.step });
    if (options.length === 0) return null;
    const decision = decide(options, this.step, this.belief, this.#rng);
    const move = decision.chosen.move;
    return { move, announcement: this.module.announce(move, this.step), decision };
  }

  observe(hero: string, action: Action, context: ObservationContext): void {
    this.belief.observe(hero, action, context);
  }

  resolve(move: M, moment: Moment, observed: Observed): Resolution {
    const resolution = this.module.resolve(move, moment, observed);
    for (const { hero, ...bet } of resolution.bets) this.belief.reveal(hero, bet);
    return resolution;
  }
}
