import { archetypesBelief, type ArchetypesConfig } from "../engine/belief/archetypes.ts";
import { countsBelief, type CountsConfig } from "../engine/belief/counts.ts";
import { withDefiance, type DefianceConfig } from "../engine/belief/defiance.ts";
import { ensembleBelief, type EnsembleConfig } from "../engine/belief/ensemble.ts";
import type { BeliefFactory } from "../engine/belief/types.ts";

/**
 * The M2 candidates (DESIGN.md 8, "M2 protocol") and the grids they are tuned
 * on. `ad` is tuned on top of the best `a`, and `c` combines the best `ad` and
 * the best `b`, so their grids are built from earlier winners.
 */
export type ParamsA = Partial<CountsConfig>;
export interface ParamsAD {
  readonly counts: ParamsA;
  readonly defiance: Partial<DefianceConfig>;
}
export type ParamsB = Partial<ArchetypesConfig>;
export interface ParamsC {
  readonly ad: ParamsAD;
  readonly b: ParamsB;
  readonly ensemble: Partial<EnsembleConfig>;
}

export const makeA = (p: ParamsA): BeliefFactory => countsBelief(p);
export const makeAD = (p: ParamsAD): BeliefFactory => withDefiance(countsBelief(p.counts), p.defiance);
export const makeB = (p: ParamsB): BeliefFactory => archetypesBelief(p);
export const makeC = (p: ParamsC): BeliefFactory => ensembleBelief([makeAD(p.ad), makeB(p.b)], p.ensemble);

/** Every combination of the listed values. */
export function product<T extends Record<string, readonly unknown[]>>(axes: T): { [K in keyof T]: T[K][number] }[] {
  let out: Record<string, unknown>[] = [{}];
  for (const [key, values] of Object.entries(axes)) {
    out = out.flatMap((partial) => values.map((v) => ({ ...partial, [key]: v })));
  }
  return out as { [K in keyof T]: T[K][number] }[];
}

export const gridA = (): ParamsA[] =>
  product({ priorStrength: [2, 4, 8], memory: [0.8, 0.9, 1], patternPrior: [0.2, 0.35, 0.5, 0.65, 0.8] });

export const gridAD = (counts: ParamsA): ParamsAD[] =>
  product({
    prior: [[1, 9], [1, 3], [1, 1], [2, 1], [3, 1]] as const,
    teachInner: ["all", "unnamed"] as const,
    memory: [0.9, 1],
  }).map((defiance) => ({ counts, defiance }));

export const gridB = (): ParamsB[] =>
  product({
    subclassPrior: [0.25, 0.4, 0.6, 0.75, 0.9],
    defiantPrior: [0.1, 0.25, 0.4, 0.55, 0.7],
    memory: [0.8, 0.9, 0.95, 1],
  });

// Memory is capped at 1 (never forgets), so C's grid can't be widened past it.
export const gridC = (ad: ParamsAD, b: ParamsB): ParamsC[] =>
  product({ memory: [0.9, 0.95, 1] }).map((ensemble) => ({ ad, b, ensemble }));

/** The winning settings from the M2 run (reports/m2-belief.md). */
export const M2_TUNED = {
  a: { priorStrength: 4, memory: 0.8, patternPrior: 0.65 },
  b: { subclassPrior: 0.4, defiantPrior: 0.55, memory: 0.9 },
} as const;
const TUNED_AD: ParamsAD = { counts: M2_TUNED.a, defiance: { prior: [1, 1], teachInner: "all", memory: 0.9 } };
const TUNED_C: ParamsC = { ad: TUNED_AD, b: M2_TUNED.b, ensemble: { memory: 0.9 } };

/**
 * The candidates for `npm run harness -- --belief <id>`. Model A keeps the
 * spike's settings so the M1 baseline stays reproducible; the others use
 * their M2 tuning.
 */
export const DEFAULT_CANDIDATES: Record<string, { readonly name: string; readonly make: () => BeliefFactory }> = {
  a: { name: "A: counts (spike settings)", make: () => makeA({}) },
  ad: { name: "A + defiance (M2 tuning)", make: () => makeAD(TUNED_AD) },
  b: { name: "B: archetypes (M2 tuning)", make: () => makeB(M2_TUNED.b) },
  c: { name: "C: ensemble (M2 tuning, the chosen model)", make: () => makeC(TUNED_C) },
};
