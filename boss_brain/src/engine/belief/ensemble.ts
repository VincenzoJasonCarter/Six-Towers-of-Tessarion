import { normalize, type Action, type Distribution } from "../actions.ts";
import type { HeroSpec } from "../subclasses.ts";
import type { BeliefFactory, BeliefModel, Bet, ObservationContext } from "./types.ts";

/**
 * Belief model C, "ensemble" (DESIGN.md 8, M2 protocol): Bayesian model
 * averaging over several belief models. Each player has their own weights,
 * and each turn every member is credited by the probability it gave the
 * action taken, so the ensemble leans on whichever member reads this player
 * best. Forgetting relaxes the weights toward even, as in model B.
 */
export interface EnsembleConfig {
  /** Each turn, the evidence so far counts this much (1 = never forgets). */
  readonly memory: number;
}

export const ENSEMBLE_DEFAULTS: EnsembleConfig = { memory: 0.95 };

export class EnsembleBelief implements BeliefModel {
  readonly id: string;
  readonly config: EnsembleConfig;
  readonly members: readonly BeliefModel[];
  readonly #logWeights = new Map<string, number[]>();

  constructor(members: readonly BeliefModel[], heroes: readonly HeroSpec[], config: Partial<EnsembleConfig> = {}) {
    if (members.length === 0) throw new Error("EnsembleBelief needs at least one member");
    this.members = members;
    this.config = { ...ENSEMBLE_DEFAULTS, ...config };
    this.id = `ensemble(${members.map((m) => m.id).join(", ")})`;
    for (const h of heroes) this.#logWeights.set(h.id, members.map(() => 0));
  }

  /** How much each member is trusted for this player, in member order. */
  weights(hero: string): number[] {
    return normalize(this.#log(hero).map(Math.exp));
  }

  forecast(hero: string, context: ObservationContext): Distribution {
    const w = this.weights(hero);
    const forecasts = this.members.map((m) => m.forecast(hero, context));
    return forecasts[0]!.map((_, i) => forecasts.reduce((s, f, j) => s + w[j]! * f[i]!, 0));
  }

  observe(hero: string, action: Action, context: ObservationContext): void {
    const { memory } = this.config;
    const lw = this.#log(hero);
    const updated = this.members.map((m, j) => memory * lw[j]! + Math.log(Math.max(m.forecast(hero, context)[action]!, 1e-12)));
    const top = Math.max(...updated);
    this.#logWeights.set(hero, updated.map((x) => x - top));
    for (const m of this.members) m.observe(hero, action, context);
  }

  reveal(hero: string, bet: Bet): void {
    for (const m of this.members) m.reveal(hero, bet);
  }

  #log(hero: string): number[] {
    const lw = this.#logWeights.get(hero);
    if (!lw) throw new Error(`EnsembleBelief: unknown hero ${hero}`);
    return lw;
  }
}

export function ensembleBelief(members: readonly BeliefFactory[], config: Partial<EnsembleConfig> = {}): BeliefFactory {
  return (heroes) => new EnsembleBelief(members.map((f) => f(heroes)), heroes, config);
}
