import { argmax, type Action, type Distribution } from "../engine/actions.ts";
import type { BeliefModel } from "../engine/belief/types.ts";
import type { HeroSpec } from "../engine/subclasses.ts";
import type { Player, Told } from "./players.ts";

/**
 * The spike's prophecy policy: each round, name whoever the belief reads most
 * clearly and foretell their most likely action, unless nobody clears the
 * threshold. It has no temperament and no defiance model; it is the fixed
 * policy the harness measures belief models against.
 */
export interface BaselineProphet {
  /** Stay silent unless some forecast is at least this sure. */
  readonly threshold: number;
  readonly perRound: number;
  /** Echo Charges that make a rewind available. */
  readonly rewindCost: number;
}

export const SPIKE_PROPHET: BaselineProphet = { threshold: 0.4, perRound: 1, rewindCost: 3 };

export interface Prophecy {
  readonly round: number;
  readonly hero: string;
  readonly action: Action;
  readonly p: number;
  /** Sealed: the hero isn't told until the round is over (DESIGN.md 5.1, disclosure). */
  readonly hidden?: boolean;
}

/** Whoever makes the prophecies: the spike's fixed policy, or a temperament (M3). */
export interface Prophet {
  speak(round: number, heroes: readonly HeroSpec[], belief: BeliefModel): Prophecy[];
}

export const spikeProphet = (policy: BaselineProphet): Prophet => ({
  speak: (round, heroes, belief) => chooseProphecies(heroes, belief, round, policy),
});

export interface TurnRecord {
  readonly round: number;
  readonly hero: string;
  readonly named: boolean;
  /** The belief's forecast just before the action. */
  readonly forecast: Distribution;
  readonly action: Action;
}

export interface FightRecord {
  readonly turns: readonly TurnRecord[];
  readonly prophecies: readonly (Prophecy & { readonly fulfilled: boolean })[];
  readonly charges: number;
  /** The round in which charges first reached the rewind cost, if they did. */
  readonly firstRewindRound: number | null;
}

export function chooseProphecies(
  heroes: readonly HeroSpec[],
  belief: BeliefModel,
  round: number,
  policy: BaselineProphet,
): Prophecy[] {
  const picks: Prophecy[] = [];
  for (const hero of heroes) {
    // Forecast each hero as if named, since naming them is what the prophecy does.
    const odds = belief.forecast(hero.id, { round, named: true });
    const action = argmax(odds);
    if (odds[action]! >= policy.threshold) picks.push({ round, hero: hero.id, action, p: odds[action]! });
  }
  picks.sort((x, y) => y.p - x.p); // stable, so ties go to the earlier hero
  return picks.slice(0, policy.perRound);
}

export interface FightSetup {
  readonly heroes: readonly HeroSpec[];
  readonly players: ReadonlyMap<string, Player>;
  readonly belief: BeliefModel;
  readonly rounds: number;
  readonly prophet: Prophet;
  /** Echo Charges that make a rewind available. */
  readonly rewindCost: number;
}

/**
 * One fight: each round the Prophet speaks, then every hero acts once in
 * party order, and each prophecy is revealed to its hero when the round ends.
 * A hidden prophecy doesn't name its hero, so they act as if unnamed.
 */
export function runFight({ heroes, players, belief, rounds, prophet, rewindCost }: FightSetup): FightRecord {
  const turns: TurnRecord[] = [];
  const prophecies: (Prophecy & { fulfilled: boolean })[] = [];
  const history = new Map<string, Action[]>(heroes.map((h) => [h.id, []]));
  const told = new Map<string, Told[]>(heroes.map((h) => [h.id, []]));
  let charges = 0;
  let firstRewindRound: number | null = null;

  for (let round = 1; round <= rounds; round++) {
    const spoken = prophet.speak(round, heroes, belief);
    for (const hero of heroes) {
      const prophecy = spoken.find((p) => p.hero === hero.id);
      const context = { round, named: prophecy !== undefined && !prophecy.hidden };
      const forecast = belief.forecast(hero.id, context);
      const own = history.get(hero.id)!;
      const action = players.get(hero.id)!.act({ ...context, warned: false, history: own, told: told.get(hero.id)! });
      turns.push({ round, hero: hero.id, named: context.named, forecast, action });
      belief.observe(hero.id, action, context);
      own.push(action);
      if (prophecy) {
        const fulfilled = prophecy.action === action;
        prophecies.push({ ...prophecy, fulfilled });
        if (fulfilled) {
          charges += 1;
          if (firstRewindRound === null && charges >= rewindCost) firstRewindRound = round;
        }
      }
    }
    for (const p of prophecies) {
      if (p.round !== round) continue;
      told.get(p.hero)!.push({ round, action: p.action, fulfilled: p.fulfilled });
      belief.reveal(p.hero, { action: p.action, fulfilled: p.fulfilled });
    }
  }
  return { turns, prophecies, charges, firstRewindRound };
}
