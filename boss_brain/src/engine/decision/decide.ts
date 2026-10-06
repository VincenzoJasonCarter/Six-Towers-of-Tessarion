import { K, normalize, type Action, type Distribution } from "../actions.ts";
import type { BeliefModel, Bet, ObservationContext } from "../belief/types.ts";
import type { Rng } from "../rng.ts";
import { AXES, type Temperament, type Utility } from "./temperament.ts";

/**
 * The decision layer (DESIGN.md 4.4): scores a module's options by expected
 * utility under a temperament and picks one. It knows nothing about any
 * particular boss: an option is just outcomes with probabilities and axis
 * scores, and perhaps the player it bets on.
 */
export interface Outcome {
  readonly p: number;
  readonly utility: Utility;
}

export interface Option<T> {
  /** What the module will do if this is chosen. */
  readonly move: T;
  readonly outcomes: readonly Outcome[];
  /** The player this option bets on, if any, for the exploration bonus. */
  readonly about?: { readonly hero: string; readonly context: ObservationContext };
  /** It waits for a trigger (a readied reaction, a wind-up): offered only to a step that waits. */
  readonly waiting?: boolean;
}

export interface Scored<T> {
  readonly option: Option<T>;
  readonly eu: number;
  /** The part of `eu` that is the exploration bonus. */
  readonly bonus: number;
}

export interface Decision<T> {
  readonly chosen: Option<T>;
  /** Every option with its score, best first, for the explanation (DESIGN.md 4.5). */
  readonly ranked: readonly Scored<T>[];
}

/** p^β, renormalised: β < 1 hedges, β > 1 jumps to conclusions. */
export function temper(d: Distribution, beta: number): Distribution {
  return beta === 1 ? d : normalize(d.map((p) => p ** beta));
}

/** Entropy divided by ln K: 0 when sure, 1 when blind. */
export function uncertainty(d: Distribution): number {
  return -d.reduce((s, p) => s + (p > 0 ? p * Math.log(p) : 0), 0) / Math.log(K);
}

/** A belief that also remembers each hero's last action, for rashness. */
export interface Watched extends BeliefModel {
  last(hero: string): Action | null;
}

/** Wraps a belief so the decision layer can see each hero's last action; everything else passes through. */
export function watched(belief: BeliefModel): Watched {
  const last = new Map<string, Action>();
  return {
    id: belief.id,
    forecast: (hero, context) => belief.forecast(hero, context),
    observe: (hero, action, context) => {
      last.set(hero, action);
      belief.observe(hero, action, context);
    },
    reveal: (hero: string, bet: Bet) => belief.reveal(hero, bet),
    last: (hero) => last.get(hero) ?? null,
  };
}

/**
 * The belief as the temperament sees it (DESIGN.md 5.1): tempered by its
 * sharpness, then, if it is rash, staked in part on each player doing their
 * last action again. Modules work out outcome probabilities from this view.
 */
export function tempered(belief: Watched, t: Temperament): BeliefModel {
  const view = (hero: string, context: ObservationContext): Distribution => {
    const d = temper(belief.forecast(hero, context), t.sharpness);
    const last = belief.last(hero);
    if (t.rashness === 0 || last === null) return d;
    return d.map((p, i) => (1 - t.rashness) * p + (i === last ? t.rashness : 0));
  };
  return { ...belief, id: `${belief.id}, as ${t.id} sees it`, forecast: view };
}

type About = NonNullable<Option<unknown>["about"]>;

/** Expected utility under the temperament's values, plus the exploration bonus. */
export function score<T>(option: Option<T>, t: Temperament, unsure: (about: About) => number): Scored<T> {
  const value = (u: Utility) => AXES.reduce((s, axis) => s + t.weights[axis] * (u[axis] ?? 0), 0);
  const expected = option.outcomes.reduce((s, o) => s + o.p * value(o.utility), 0);
  const bonus = option.about && t.explore !== 0 ? t.explore * unsure(option.about) : 0;
  return { option, eu: expected + bonus, bonus };
}

/**
 * Care, then mixing (DESIGN.md 5.1): keep the options within the slack of
 * the best, then draw among them by a softmax at the mixing temperature. At
 * temperature 0 the first best is taken and the rng is not touched.
 *
 * Exploration reads the untempered belief: what the brain really doesn't
 * know, whatever its temperament makes of it.
 */
export function decide<T>(options: readonly Option<T>[], t: Temperament, belief: BeliefModel, rng: Rng): Decision<T> {
  if (options.length === 0) throw new Error("decide: no options");
  const seen = new Map<string, number>();
  const unsure = ({ hero, context }: About) => {
    const key = `${hero}|${context.round}|${context.named}`;
    let u = seen.get(key);
    if (u === undefined) seen.set(key, (u = uncertainty(belief.forecast(hero, context))));
    return u;
  };
  const ranked = options.map((o) => score(o, t, unsure)).sort((x, y) => y.eu - x.eu);
  const best = ranked[0]!.eu;
  const floor = best - t.slack * Math.abs(best);
  const considered = ranked.filter((s) => s.eu >= floor);
  if (t.mixing === 0 || considered.length === 1) return { chosen: considered[0]!.option, ranked };
  const weights = considered.map((s) => Math.exp((s.eu - best) / t.mixing));
  return { chosen: considered[rng.weighted(weights)]!.option, ranked };
}
