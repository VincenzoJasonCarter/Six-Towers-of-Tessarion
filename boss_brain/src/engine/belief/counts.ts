import { K, normalize, type Action, type Distribution } from "../actions.ts";
import { shapeOf, type HeroSpec } from "../subclasses.ts";
import type { BeliefFactory, BeliefModel, Bet, ObservationContext } from "./types.ts";

/**
 * Belief model A, "counts" (DESIGN.md 4.2), ported from the spike in
 * ../../../prophet/model.js with the same maths.
 *
 * Each hero gets two competing models of their turn:
 *   habit    a Dirichlet over the five actions, seeded with the subclass shape
 *   pattern  one Dirichlet per previous action, seeded with the habit model,
 *            so the two agree until a hero's turns depend on the turn before
 * The forecast mixes them, weighted by Bayes: each observed action credits
 * each model by the probability it gave that action.
 */
export interface CountsConfig {
  /** How many turns' worth of trust the subclass shape gets. */
  readonly priorStrength: number;
  /** Each new turn, older evidence is multiplied by this (1 = never forgets). */
  readonly memory: number;
  /** Starting belief that a hero's turns follow on from each other. */
  readonly patternPrior: number;
  /** Floor kept under each model's weight so neither is ruled out for good. */
  readonly doubt: number;
}

export const COUNTS_DEFAULTS: CountsConfig = {
  priorStrength: 4,
  memory: 0.9,
  patternPrior: 0.35,
  doubt: 0.02,
};

interface Mind {
  readonly prior: number[];
  habit: number[];
  pattern: number[][];
  last: Action | null;
  weights: [number, number];
}

const zeros = (): number[] => new Array<number>(K).fill(0);

export class CountsBelief implements BeliefModel {
  readonly id = "counts";
  readonly config: CountsConfig;
  readonly #minds = new Map<string, Mind>();

  constructor(heroes: readonly HeroSpec[], config: Partial<CountsConfig> = {}) {
    this.config = { ...COUNTS_DEFAULTS, ...config };
    for (const hero of heroes) {
      this.#minds.set(hero.id, {
        prior: shapeOf(hero.subclass).map((p) => p * this.config.priorStrength),
        habit: zeros(),
        pattern: Array.from({ length: K }, zeros),
        last: null,
        weights: [1 - this.config.patternPrior, this.config.patternPrior],
      });
    }
  }

  // Model A ignores the context; defiance comes in M2.
  forecast(hero: string, _context?: ObservationContext): Distribution {
    const m = this.#mind(hero);
    const h = this.#habitOdds(m);
    const p = this.#patternOdds(m);
    return h.map((x, i) => m.weights[0] * x + m.weights[1] * p[i]!);
  }

  observe(hero: string, action: Action, _context?: ObservationContext): void {
    const m = this.#mind(hero);
    const { memory, doubt } = this.config;
    const h = this.#habitOdds(m);
    const p = this.#patternOdds(m);
    const w = normalize([m.weights[0] * h[action]!, m.weights[1] * p[action]!]);
    m.weights = [w[0]! * (1 - doubt) + doubt / 2, w[1]! * (1 - doubt) + doubt / 2];
    m.habit = m.habit.map((c) => c * memory);
    m.habit[action]! += 1;
    m.pattern = m.pattern.map((row) => row.map((c) => c * memory));
    if (m.last !== null) m.pattern[m.last]![action]! += 1;
    m.last = action;
  }

  // Model A doesn't model players who read the boss.
  reveal(_hero: string, _bet: Bet): void {}

  /** The weight on [habit, pattern], for reports and tests. */
  weights(hero: string): readonly [number, number] {
    return this.#mind(hero).weights;
  }

  #mind(hero: string): Mind {
    const m = this.#minds.get(hero);
    if (!m) throw new Error(`CountsBelief: unknown hero ${hero}`);
    return m;
  }

  #habitOdds(m: Mind): number[] {
    return normalize(m.prior.map((p, i) => p + m.habit[i]!));
  }

  #patternOdds(m: Mind): number[] {
    const base = this.#habitOdds(m);
    if (m.last === null) return base;
    const row = m.pattern[m.last]!;
    return normalize(base.map((p, i) => p * this.config.priorStrength + row[i]!));
  }
}

export function countsBelief(config: Partial<CountsConfig> = {}): BeliefFactory {
  return (heroes) => new CountsBelief(heroes, config);
}
