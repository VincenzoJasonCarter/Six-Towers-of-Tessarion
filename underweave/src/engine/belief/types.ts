import type { Action, Distribution } from "../actions.ts";
import type { HeroSpec } from "../subclasses.ts";

/** What the brain knows about a turn besides the action itself. */
export interface ObservationContext {
  readonly round: number;
  /** The boss named this hero this round (DESIGN.md 4.2, "being named is evidence"). */
  readonly named: boolean;
}

/**
 * A model of the players (DESIGN.md 4.2): it forecasts each hero's next
 * action and learns from each one it sees. Candidate models are compared in
 * the harness by swapping the factory.
 */
export interface BeliefModel {
  /** Short name for reports. */
  readonly id: string;
  /** What the hero will do next, before seeing it. */
  forecast(hero: string, context: ObservationContext): Distribution;
  /** Learn from what the hero did. */
  observe(hero: string, action: Action, context: ObservationContext): void;
}

export type BeliefFactory = (heroes: readonly HeroSpec[]) => BeliefModel;
