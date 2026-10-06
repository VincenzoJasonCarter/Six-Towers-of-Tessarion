import { ACTIONS, K, normalize, type Action, type Distribution } from "../actions.ts";
import { shapeOf, type HeroSpec } from "../subclasses.ts";
import { dodge } from "./dodge.ts";
import type { BeliefFactory, BeliefModel, Bet, ObservationContext } from "./types.ts";

/**
 * Belief model B, "archetypes" (DESIGN.md 4.2): Akinator's approach. A fixed
 * set of hypotheses about what kind of player this is, each a complete model
 * of their turn, and an exact Bayesian posterior over them. Every hypothesis
 * is a habit crossed with a reaction to being named and, from M2b, with a
 * reaction to the boss's revealed bets:
 *
 *   habits     follows the subclass · favours one action (×5) · chaotic ·
 *              repeats itself · avoids repeating itself
 *   reactions  complies when named · defies when named (dodges their usual action)
 *   wariness   ignores the boss's bets · wary of them (steers away from what
 *              the boss has bet on, named or not)
 *
 * The forecast is the posterior-weighted average of the hypotheses, and the
 * posterior is the explanation ("72% favours Shoot, 64% defies when named").
 * Forgetting is done by tempering: each turn the log-posterior relaxes toward
 * the prior by a factor `memory`, so a player who changes is followed.
 */
export interface ArchetypesConfig {
  /** Prior weight on "follows the subclass"; the other habits share the rest. */
  readonly subclassPrior: number;
  /** Prior probability that a player defies when named. */
  readonly defiantPrior: number;
  /** Prior probability that a player is wary of the boss's bets. At 0 the model is M2's exactly. */
  readonly waryPrior: number;
  /** Each turn, the evidence so far counts this much (1 = never forgets). */
  readonly memory: number;
  /** Share of the forecast spread evenly, so nothing is ever impossible. */
  readonly floor: number;
}

export const ARCHETYPES_DEFAULTS: ArchetypesConfig = {
  subclassPrior: 0.4,
  defiantPrior: 0.25,
  waryPrior: 0,
  memory: 0.9,
  floor: 0.01,
};

interface Habit {
  readonly id: string;
  readonly label: string;
  /** Share of the non-subclass prior this habit gets. */
  readonly share: number;
  predict(shape: Distribution, last: Action | null): number[];
}

const FAVOURED = 0.75;
const REPEAT = 0.7;
const AVOID = 0.05;
/** How hard a wary player steers away from an action, per bet on it: e^-1.2 ≈ 0.3. */
const WARY = 1.2;
/** Each of its own turns, a wary player's memory of the bets fades by this. */
const WARY_FADE = 0.8;

const HABITS: readonly Habit[] = [
  { id: "subclass", label: "follows the subclass", share: 0, predict: (shape) => [...shape] },
  ...ACTIONS.map(
    (a, x): Habit => ({
      id: `favours-${a.id}`,
      label: `favours ${a.label}`,
      share: 0.1,
      predict: () => Array.from({ length: K }, (_, i) => (i === x ? FAVOURED : (1 - FAVOURED) / (K - 1))),
    }),
  ),
  { id: "chaotic", label: "chaotic", share: 1 / 6, predict: () => new Array<number>(K).fill(1 / K) },
  {
    id: "repeater",
    label: "repeats itself",
    share: 1 / 6,
    predict: (shape, last) => (last === null ? [...shape] : shape.map((p, i) => REPEAT * (i === last ? 1 : 0) + (1 - REPEAT) * p)),
  },
  {
    id: "shifter",
    label: "avoids repeating itself",
    share: 1 / 6,
    predict: (shape, last) => (last === null ? [...shape] : normalize(shape.map((p, i) => (i === last ? p * AVOID : p)))),
  },
];

export interface Hypothesis {
  readonly habit: string;
  readonly label: string;
  readonly defies: boolean;
  readonly wary: boolean;
  readonly p: number;
}

interface Mind {
  readonly shape: Distribution;
  readonly logPrior: number[];
  logPost: number[];
  last: Action | null;
  /** The boss's revealed bets on each action, fading. */
  bets: number[];
}

export class ArchetypesBelief implements BeliefModel {
  readonly id = "archetypes";
  readonly config: ArchetypesConfig;
  readonly #minds = new Map<string, Mind>();
  /** Every (habit, reaction, wariness) hypothesis, in a fixed order. */
  readonly #pairs: readonly { habit: Habit; defies: boolean; wary: boolean; prior: number }[];

  constructor(heroes: readonly HeroSpec[], config: Partial<ArchetypesConfig> = {}) {
    this.config = { ...ARCHETYPES_DEFAULTS, ...config };
    const { subclassPrior, defiantPrior, waryPrior } = this.config;
    const habitPrior = (h: Habit) => (h.id === "subclass" ? subclassPrior : (1 - subclassPrior) * h.share);
    // With no prior on wariness, leave the wary hypotheses out, so the model is M2's exactly.
    const wariness = waryPrior > 0 ? [false, true] : [false];
    this.#pairs = HABITS.flatMap((habit) =>
      [false, true].flatMap((defies) =>
        wariness.map((wary) => ({
          habit,
          defies,
          wary,
          prior:
            habitPrior(habit) * (defies ? defiantPrior : 1 - defiantPrior) * (wary ? waryPrior : 1 - waryPrior),
        })),
      ),
    );
    for (const hero of heroes) {
      const logPrior = this.#pairs.map((h) => Math.log(h.prior));
      this.#minds.set(hero.id, {
        shape: shapeOf(hero.subclass),
        logPrior,
        logPost: [...logPrior],
        last: null,
        bets: new Array<number>(K).fill(0),
      });
    }
  }

  forecast(hero: string, context: ObservationContext): Distribution {
    const m = this.#mind(hero);
    const post = this.#posterior(m);
    const out = new Array<number>(K).fill(0);
    this.#predictions(m, context).forEach((pred, h) => pred.forEach((p, i) => (out[i]! += post[h]! * p)));
    const { floor } = this.config;
    return out.map((p) => (1 - floor) * p + floor / K);
  }

  observe(hero: string, action: Action, context: ObservationContext): void {
    const m = this.#mind(hero);
    const { memory } = this.config;
    const preds = this.#predictions(m, context);
    m.logPost = m.logPost.map(
      (lp, h) => memory * lp + (1 - memory) * m.logPrior[h]! + Math.log(Math.max(preds[h]![action]!, 1e-12)),
    );
    // Keep the numbers from drifting: subtract the largest.
    const top = Math.max(...m.logPost);
    m.logPost = m.logPost.map((lp) => lp - top);
    m.last = action;
    m.bets = m.bets.map((b) => b * WARY_FADE);
  }

  reveal(hero: string, bet: Bet): void {
    this.#mind(hero).bets[bet.action]! += 1;
  }

  /** The posterior over hypotheses, most likely first. */
  posterior(hero: string): Hypothesis[] {
    const m = this.#mind(hero);
    return this.#posterior(m)
      .map((p, h) => {
        const { habit, defies, wary } = this.#pairs[h]!;
        return { habit: habit.id, label: habit.label, defies, wary, p };
      })
      .sort((x, y) => y.p - x.p);
  }

  /** How likely this player is to defy when named, summed over habits. */
  defiance(hero: string): number {
    return this.posterior(hero).reduce((s, h) => s + (h.defies ? h.p : 0), 0);
  }

  /** How likely this player is to be wary of the boss's bets, summed over the rest. */
  wariness(hero: string): number {
    return this.posterior(hero).reduce((s, h) => s + (h.wary ? h.p : 0), 0);
  }

  /** One line for the DM: the most likely habit, the chance of defiance and, if modelled, of wariness. */
  explain(hero: string): string {
    const byHabit = new Map<string, number>();
    for (const h of this.posterior(hero)) byHabit.set(h.label, (byHabit.get(h.label) ?? 0) + h.p);
    const [label, p] = [...byHabit].sort((x, y) => y[1] - x[1])[0]!;
    const pct = (x: number) => `${Math.round(x * 100)}%`;
    const wary = this.config.waryPrior > 0 ? `, ${pct(this.wariness(hero))} wary of the boss` : "";
    return `${pct(p)} ${label}, ${pct(this.defiance(hero))} defies when named${wary}`;
  }

  #mind(hero: string): Mind {
    const m = this.#minds.get(hero);
    if (!m) throw new Error(`ArchetypesBelief: unknown hero ${hero}`);
    return m;
  }

  #posterior(m: Mind): number[] {
    return normalize(m.logPost.map(Math.exp));
  }

  #predictions(m: Mind, context: ObservationContext): number[][] {
    const steer = m.bets.map((b) => Math.exp(-WARY * b));
    return this.#pairs.map(({ habit, defies, wary }) => {
      const habitual = habit.predict(m.shape, m.last);
      const usual = wary ? normalize(habitual.map((p, i) => p * steer[i]!)) : habitual;
      return defies && context.named ? dodge(usual) : usual;
    });
  }
}

export function archetypesBelief(config: Partial<ArchetypesConfig> = {}): BeliefFactory {
  return (heroes) => new ArchetypesBelief(heroes, config);
}
