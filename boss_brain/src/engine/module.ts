import type { Action } from "./actions.ts";
import type { BeliefModel, Bet } from "./belief/types.ts";
import type { Option } from "./decision/decide.ts";
import type { Temperament, Utility } from "./decision/temperament.ts";
import type { Rng } from "./rng.ts";
import type { HeroSpec } from "./subclasses.ts";

/**
 * The module interface (DESIGN.md 4.3, 6): what a boss supplies to the
 * engine. The engine owns belief, decision and temperament; a module owns
 * its moves, what they might lead to, and what it counts as winning.
 */

/**
 * When the boss gets to decide: at the start of a round, or right after a
 * hero's turn (the Prophet's rewind). A module offers no options at moments
 * it doesn't act in.
 */
export type Moment =
  | { readonly kind: "round"; readonly round: number }
  | { readonly kind: "turn"; readonly round: number; readonly hero: string; readonly action: Action };

/** What the heroes are told before they act. */
export interface Announcement {
  /** Heroes the boss has spoken about: what it read of them, at the step's disclosure. */
  readonly named: readonly string[];
  /** Heroes who can see something coming at them, whatever was said (a raised axe). */
  readonly warned: readonly string[];
  /** For the proclaim view; empty when nothing is said. */
  readonly text: string;
}

/**
 * Something the DM records that isn't one of the five action categories
 * (the party took the Hoardwyrm's coin). Its meaning is the module's.
 */
export interface ModuleEvent {
  readonly kind: string;
  readonly hero?: string;
  readonly value?: number;
}

/** What happened once the heroes acted, as the move's resolver sees it. */
export interface Observed {
  /** Each hero's action this round so far. */
  readonly actions: ReadonlyMap<string, Action>;
  readonly events: readonly ModuleEvent[];
}

export interface Resolution {
  /** A short label for the kind of move, for reports ("cut", "hold"). */
  readonly kind: string;
  /** The utility actually realised. */
  readonly utility: Utility;
  /** The bets about heroes' actions the table now learns of, for the belief and the players. */
  readonly bets: readonly (Bet & { readonly hero: string })[];
  /** Module-specific numbers for reports. */
  readonly detail?: Readonly<Record<string, number>>;
}

export interface ModuleContext {
  readonly heroes: readonly HeroSpec[];
  /** The belief as the temperament sees it (sharpness, rashness): for scoring options. */
  readonly view: BeliefModel;
  /** The belief untempered: for a module's own learning, which should be honest. */
  readonly belief: BeliefModel;
  readonly step: Temperament;
}

export interface Module<M> {
  readonly id: string;
  /** The moves open at this moment, each with its outcomes and their utility. */
  options(moment: Moment, ctx: ModuleContext): Option<M>[];
  announce(move: M, step: Temperament): Announcement;
  /** For the DM view: what the move is, in a few words ("interrupt Kael's Mend"). */
  describe?(move: M): string;
  /** Settles a chosen move: a round's move once every hero has acted, a turn's move at once. */
  resolve(move: M, moment: Moment, observed: Observed): Resolution;
}

/** One module per fight, since a module may keep state (charges, its own outcome models). */
export type ModuleFactory<M> = (heroes: readonly HeroSpec[], rng: Rng) => Module<M>;
