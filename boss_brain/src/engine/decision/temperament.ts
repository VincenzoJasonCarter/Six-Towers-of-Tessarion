/**
 * Temperament (DESIGN.md 5): the dial that turns expected utility into a
 * choice. It runs from cool interest to rage, and the boss plays best in the
 * middle; the two ends fall short for different reasons, never by rolling
 * dice.
 */

/** The shared utility axes (DESIGN.md 4.3), so a step means the same for every boss. */
export const AXES = ["lethal", "spread", "show", "tempo"] as const;
export type Axis = (typeof AXES)[number];
export type Utility = Readonly<Partial<Record<Axis, number>>>;

/**
 * How much the players are told (DESIGN.md 5.1): what and who, who only, or
 * nothing until it is over. A rule of character, not a choice made for profit.
 */
export type Disclosure = "full" | "name" | "hidden";

export interface Temperament {
  readonly id: string;
  readonly name: string;
  /** Care: only options within this share of the best EU are considered. */
  readonly slack: number;
  /** Mixing: the softmax temperature among them; 0 always takes the best. */
  readonly mixing: number;
  /** Values: the weight on each utility axis. */
  readonly weights: Readonly<Record<Axis, number>>;
  /** Sharpness: the belief is tempered to p^β before use; β < 1 hedges. */
  readonly sharpness: number;
  /** Rashness: the share of the forecast staked on the player doing their last action again. */
  readonly rashness: number;
  /** Exploration: the bonus for betting where the forecast is unsure. */
  readonly explore: number;
  readonly disclosure: Disclosure;
}

const step = (
  id: string,
  name: string,
  slack: number,
  mixing: number,
  [lethal, spread, show, tempo]: readonly [number, number, number, number],
  sharpness: number,
  rashness: number,
  explore: number,
  disclosure: Disclosure,
): Temperament => ({ id, name, slack, mixing, weights: { lethal, spread, show, tempo }, sharpness, rashness, explore, disclosure });

/** The five steps with the placeholder values of DESIGN.md 5.2, before M3 calibrates them. */
export const PLACEHOLDER_STEPS: readonly Temperament[] = [
  step("curious", "Curious", 0.3, 0.3, [0.2, 1.0, 1.0, 0.5], 0.6, 0, 0.5, "full"),
  step("hunting", "Hunting", 0.15, 0.15, [0.5, 0.5, 0.4, 0.8], 0.85, 0, 0.2, "name"),
  step("ruthless", "Ruthless", 0.05, 0.15, [0.8, 0.2, 0, 1.0], 1.0, 0, 0.1, "hidden"),
  step("wrathful", "Wrathful", 0.02, 0.05, [0.9, -0.1, 0.3, 1.0], 1.0, 0.4, 0, "name"),
  step("bloodlusted", "Bloodlusted", 0, 0, [1.0, -0.6, 0.5, 0.8], 1.0, 0.8, 0, "full"),
];

const calibrated = (id: string, levers: Partial<Temperament>): Temperament => ({
  ...PLACEHOLDER_STEPS.find((s) => s.id === id)!,
  ...levers,
});

/**
 * The five steps as M3 calibrated them (reports/m3-temperament.md): the
 * placeholders with their tuned levers. Calibrated against model C at its M2
 * settings; they hold only at its defiance prior (DESIGN.md, "M3 results").
 */
export const STEPS: readonly Temperament[] = [
  calibrated("curious", { sharpness: 0.9, mixing: 0.15 }),
  calibrated("hunting", { sharpness: 0.95, mixing: 0.15, slack: 0.4 }),
  calibrated("ruthless", { mixing: 0.03 }),
  calibrated("wrathful", { rashness: 0.6 }),
  // Any rashness from 0.5 up makes the same bets (DESIGN.md, "M3 results, first run", point 1).
  calibrated("bloodlusted", { rashness: 0.8 }),
];

export function stepById(id: string): Temperament {
  const step = STEPS.find((s) => s.id === id);
  if (!step) throw new Error(`No temperament step "${id}". Known: ${STEPS.map((s) => s.id).join(", ")}`);
  return step;
}
