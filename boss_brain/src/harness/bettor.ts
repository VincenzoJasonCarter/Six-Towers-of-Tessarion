import { ACTIONS, type Action } from "../engine/actions.ts";
import type { BeliefFactory } from "../engine/belief/types.ts";
import { decide, tempered, watched, type Option, type Watched } from "../engine/decision/decide.ts";
import type { Temperament } from "../engine/decision/temperament.ts";
import { Rng, seedFor } from "../engine/rng.ts";
import type { HeroSpec, SubclassId } from "../engine/subclasses.ts";
import { runFight, type FightRecord, type Prophecy, type Prophet } from "./fight.ts";
import type { Player, Style } from "./players.ts";
import { hash } from "./suite.ts";

/**
 * The M3 baseline module (DESIGN.md 8, "M3 protocol"): a minimal Prophet that
 * makes one bet a round, or none, chosen by the decision layer under a
 * temperament. It is a yardstick for temperament, not the Prophet (DESIGN.md 6.2).
 *
 * It reads `belief`, the same watched belief the fight observes into.
 */
export function bettor(step: Temperament, belief: Watched, rng: Rng): Prophet {
  let last: string | null = null;
  return {
    speak(round, heroes) {
      const view = tempered(belief, step);
      const named = step.disclosure !== "hidden";
      const options: Option<Prophecy | null>[] = [];
      for (const hero of heroes) {
        const context = { round, named };
        const odds = view.forecast(hero.id, context);
        const spread = last !== null && hero.id !== last ? 1 : 0;
        ACTIONS.forEach((_, a) => {
          const p = odds[a]!;
          options.push({
            move: { round, hero: hero.id, action: a as Action, p, hidden: !named },
            outcomes: [
              { p, utility: { tempo: 1, spread } },
              { p: 1 - p, utility: { spread } },
            ],
            about: { hero: hero.id, context },
          });
        });
      }
      // Silence last, so a bet wins a tie with it.
      options.push({ move: null, outcomes: [{ p: 1, utility: {} }] });
      const { chosen } = decide(options, step, belief, rng);
      last = chosen.move?.hero ?? null;
      return chosen.move ? [chosen.move] : [];
    },
  };
}

export interface BetSummary {
  readonly fights: number;
  readonly betsPerFight: number;
  /** How often a bet came true. */
  readonly success: number;
  /** Per fight, the share of bets on the hero bet on most; averaged over fights with a bet. */
  readonly fixation: number;
  /** The share of bets (after a fight's first) that repeat the most common bet so far. */
  readonly predictability: number;
}

/** Scores the bets of many fights. */
export class BetScore {
  #fights = 0;
  #bets = 0;
  #hits = 0;
  #fixation = 0;
  #fixationFights = 0;
  #repeats = 0;
  #repeatable = 0;

  addFight(fight: FightRecord): void {
    this.addBets(fight.prophecies);
  }

  /** One fight's bets, in the order they were made. */
  addBets(bets: readonly { readonly hero: string; readonly action: number; readonly fulfilled: boolean }[]): void {
    this.#fights += 1;
    this.#bets += bets.length;
    this.#hits += bets.filter((b) => b.fulfilled).length;
    if (bets.length > 0) {
      const perHero = new Map<string, number>();
      for (const b of bets) perHero.set(b.hero, (perHero.get(b.hero) ?? 0) + 1);
      this.#fixation += Math.max(...perHero.values()) / bets.length;
      this.#fixationFights += 1;
    }
    const seen = new Map<string, number>();
    for (const b of bets) {
      const key = `${b.hero}|${b.action}`;
      if (seen.size > 0) {
        const top = Math.max(...seen.values());
        this.#repeatable += 1;
        if (seen.get(key) === top) this.#repeats += 1;
      }
      seen.set(key, (seen.get(key) ?? 0) + 1);
    }
  }

  summary(): BetSummary {
    return {
      fights: this.#fights,
      betsPerFight: this.#bets / this.#fights,
      success: this.#bets ? this.#hits / this.#bets : 0,
      fixation: this.#fixationFights ? this.#fixation / this.#fixationFights : 0,
      predictability: this.#repeatable ? this.#repeats / this.#repeatable : 0,
    };
  }
}

export interface BetSuiteOptions {
  readonly seed: number;
  readonly trials: number;
  readonly rounds: number;
  readonly party: readonly SubclassId[];
  readonly styles: readonly Style[];
  readonly belief: BeliefFactory;
  readonly step: Temperament;
}

export interface BetSuiteResult {
  readonly step: Temperament;
  readonly styles: readonly ({ readonly style: string; readonly name: string } & BetSummary)[];
}

/**
 * Plays every style through `trials` fights against a temperament. Players
 * are seeded exactly as in `runSuite`, and the boss gets a stream of its own,
 * so the same style meets the same players under every step.
 */
export function runBetSuite(opts: BetSuiteOptions): BetSuiteResult {
  const heroes: HeroSpec[] = opts.party.map((subclass, i) => ({ id: `${subclass}#${i + 1}`, subclass }));
  const styles = opts.styles.map((style) => {
    const styleKey = hash(style.id);
    const score = new BetScore();
    for (let trial = 0; trial < opts.trials; trial++) {
      const players = new Map<string, Player>(
        heroes.map((h, i) => [h.id, style.make(h.subclass, new Rng(seedFor(opts.seed, styleKey, trial, i)))]),
      );
      const boss = new Rng(seedFor(opts.seed, styleKey, trial, BOSS_STREAM));
      const belief = watched(opts.belief(heroes));
      score.addFight(
        runFight({
          heroes,
          players,
          belief,
          rounds: opts.rounds,
          prophet: bettor(opts.step, belief, boss),
          rewindCost: Infinity,
        }),
      );
    }
    return { style: style.id, name: style.name, ...score.summary() };
  });
  return { step: opts.step, styles };
}

/** The boss's seed path, clear of the heroes' (0, 1, 2, ...). */
export const BOSS_STREAM = 1_000_003;
