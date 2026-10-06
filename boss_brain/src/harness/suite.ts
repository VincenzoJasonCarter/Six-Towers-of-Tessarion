import type { BeliefFactory } from "../engine/belief/types.ts";
import { Rng, seedFor } from "../engine/rng.ts";
import type { HeroSpec, SubclassId } from "../engine/subclasses.ts";
import { runFight, spikeProphet, type BaselineProphet } from "./fight.ts";
import { ForecastScore, ProphecyScore, type ForecastSummary, type ProphecySummary } from "./metrics.ts";
import type { Player, Style } from "./players.ts";

export interface SuiteOptions {
  readonly seed: number;
  /** Fights per player style. */
  readonly trials: number;
  readonly rounds: number;
  readonly party: readonly SubclassId[];
  readonly styles: readonly Style[];
  readonly belief: BeliefFactory;
  readonly policy: BaselineProphet;
}

export interface StyleResult {
  readonly style: string;
  readonly name: string;
  readonly plays: string;
  readonly forecast: ForecastSummary;
  /** Forecasts on the turns where the boss had named this hero. */
  readonly named: ForecastSummary;
  readonly prophecy: ProphecySummary;
}

export interface SuiteResult {
  readonly belief: string;
  readonly seed: number;
  readonly trials: number;
  readonly rounds: number;
  readonly party: readonly SubclassId[];
  readonly policy: BaselineProphet;
  readonly styles: readonly StyleResult[];
  /** Forecast scores over every style together. */
  readonly pooled: ForecastSummary;
}

/**
 * Plays every style through `trials` fights, the whole party playing that
 * style. Each (style, fight, hero) gets its own seed, keyed by the style's id,
 * so a style's numbers don't change when other styles are added, reordered
 * or left out.
 */
export function runSuite(opts: SuiteOptions): SuiteResult {
  const heroes: HeroSpec[] = opts.party.map((subclass, i) => ({ id: `${subclass}#${i + 1}`, subclass }));
  const pooled = new ForecastScore();
  let beliefId = "";

  const styles = opts.styles.map((style): StyleResult => {
    const styleKey = hash(style.id);
    const forecast = new ForecastScore();
    const named = new ForecastScore();
    const prophecy = new ProphecyScore();
    for (let trial = 0; trial < opts.trials; trial++) {
      const players = new Map<string, Player>(
        heroes.map((h, i) => [h.id, style.make(h.subclass, new Rng(seedFor(opts.seed, styleKey, trial, i)))]),
      );
      const belief = opts.belief(heroes);
      beliefId = belief.id;
      const fight = runFight({
        heroes,
        players,
        belief,
        rounds: opts.rounds,
        prophet: spikeProphet(opts.policy),
        rewindCost: opts.policy.rewindCost,
      });
      forecast.addFight(fight);
      named.addFight(fight, (t) => t.named);
      pooled.addFight(fight);
      prophecy.addFight(fight);
    }
    return {
      style: style.id,
      name: style.name,
      plays: style.plays,
      forecast: forecast.summary(),
      named: named.summary(),
      prophecy: prophecy.summary(),
    };
  });

  return {
    belief: beliefId,
    seed: opts.seed,
    trials: opts.trials,
    rounds: opts.rounds,
    party: opts.party,
    policy: opts.policy,
    styles,
    pooled: pooled.summary(),
  };
}

/** A stable number for a style's id, to key its seeds. */
export function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619) >>> 0;
  return h;
}
