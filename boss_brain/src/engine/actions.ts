/**
 * The five things a hero can do on their turn, as the DM records them
 * (DESIGN.md 4.1). An Action is an index into ACTIONS.
 */
export const ACTIONS = [
  { id: "strike", label: "Strike", covers: "melee weapon attack" },
  { id: "shoot", label: "Shoot", covers: "ranged weapon attack" },
  { id: "cast", label: "Cast", covers: "attack or control spell" },
  { id: "mend", label: "Mend", covers: "heal, buff, shield an ally" },
  { id: "guard", label: "Guard", covers: "dodge, dash, hold, anything else" },
] as const;

export type Action = 0 | 1 | 2 | 3 | 4;
export const K = ACTIONS.length;

export const STRIKE: Action = 0;
export const SHOOT: Action = 1;
export const CAST: Action = 2;
export const MEND: Action = 3;
export const GUARD: Action = 4;

/** A probability for each action, in ACTIONS order. Sums to 1. */
export type Distribution = readonly number[];

export function actionId(a: Action): string {
  return ACTIONS[a].id;
}

export function isAction(n: number): n is Action {
  return Number.isInteger(n) && n >= 0 && n < K;
}

/** The most likely action, the first one on a tie. */
export function argmax(d: Distribution): Action {
  let best = 0;
  for (let i = 1; i < d.length; i++) if (d[i]! > d[best]!) best = i;
  return best as Action;
}

export function normalize(xs: readonly number[]): number[] {
  const z = xs.reduce((a, b) => a + b, 0);
  return xs.map((x) => x / z);
}
