import type { Action } from "./actions.ts";
import type { BeliefModel, ObservationContext } from "./belief/types.ts";
import { decide, tempered, watched, type Decision, type Watched } from "./decision/decide.ts";
import { TemperamentTrack, type FightSignals, type Shift } from "./decision/shift.ts";
import type { Temperament } from "./decision/temperament.ts";
import type { Announcement, Module, ModuleEvent, Moment, Observed, Resolution } from "./module.ts";
import type { Rng } from "./rng.ts";
import type { HeroSpec } from "./subclasses.ts";

export interface Choice<M> {
  readonly move: M;
  readonly announcement: Announcement;
  /** Every option with its score, for the explanation (DESIGN.md 4.5). */
  readonly decision: Decision<M>;
  /** The step the choice was made under. */
  readonly step: Temperament;
}

/** The module event the DM records for the boss's HP: `value` is the share remaining. */
export const BOSS_HP = "boss-hp";

/**
 * One boss in one fight: a belief, a temperament and a module, wired the way
 * DESIGN.md 4 draws them. Observe each turn, ask for a choice at each moment,
 * and resolve what was chosen; the brain tells the belief what the table has
 * seen. Given a track rather than a single step, the temperament can shift
 * at the start of a round (5.3); the belief carries on through a shift.
 */
export class Brain<M> {
  readonly belief: Watched;
  readonly track: TemperamentTrack;
  readonly module: Module<M>;
  readonly #heroes: readonly HeroSpec[];
  readonly #rng: Rng;
  #bossHp: number | null = null;
  #betsSeen = 0;
  #betsFulfilled = 0;
  #foiledInARow = 0;
  readonly #events = new Map<string, number>();

  constructor(belief: BeliefModel, step: Temperament | TemperamentTrack, module: Module<M>, heroes: readonly HeroSpec[], rng: Rng) {
    this.belief = watched(belief);
    this.track = step instanceof TemperamentTrack ? step : new TemperamentTrack([step], step.id);
    this.module = module;
    this.#heroes = heroes;
    this.#rng = rng;
  }

  /** The step in force now. */
  get step(): Temperament {
    return this.track.current;
  }

  get shifts(): readonly Shift[] {
    return this.track.shifts;
  }

  /** The boss's choice at this moment, or null if its module doesn't act now. */
  choose(moment: Moment): Choice<M> | null {
    if (moment.kind === "round") this.track.update(this.#signals(moment.round));
    const step = this.step;
    const view = tempered(this.belief, step);
    const offered = this.module.options(moment, { heroes: this.#heroes, view, belief: this.belief, step });
    const options = step.waits ? offered : offered.filter((o) => !o.waiting);
    if (options.length === 0) return null;
    const decision = decide(options, step, this.belief, this.#rng);
    const move = decision.chosen.move;
    return { move, announcement: this.module.announce(move, step), decision, step };
  }

  observe(hero: string, action: Action, context: ObservationContext): void {
    this.belief.observe(hero, action, context);
  }

  /** Something the DM records outside a resolution: the boss's HP, a minion slain. */
  record(event: ModuleEvent): void {
    this.#events.set(event.kind, (this.#events.get(event.kind) ?? 0) + 1);
    if (event.kind === BOSS_HP && event.value !== undefined) this.#bossHp = event.value;
  }

  resolve(move: M, moment: Moment, observed: Observed): Resolution {
    for (const e of observed.events) this.record(e);
    const resolution = this.module.resolve(move, moment, observed);
    for (const { hero, ...bet } of resolution.bets) {
      this.belief.reveal(hero, bet);
      this.#betsSeen += 1;
      if (bet.fulfilled) {
        this.#betsFulfilled += 1;
        this.#foiledInARow = 0;
      } else {
        this.#foiledInARow += 1;
      }
    }
    return resolution;
  }

  #signals(round: number): FightSignals {
    return {
      round,
      bossHp: this.#bossHp,
      betsSeen: this.#betsSeen,
      betsFulfilled: this.#betsFulfilled,
      foiledInARow: this.#foiledInARow,
      events: Object.fromEntries(this.#events),
    };
  }
}
