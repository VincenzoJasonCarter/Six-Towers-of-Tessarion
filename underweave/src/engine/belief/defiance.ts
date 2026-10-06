import type { Action, Distribution } from "../actions.ts";
import type { HeroSpec } from "../subclasses.ts";
import { dodge } from "./dodge.ts";
import type { BeliefFactory, BeliefModel, ObservationContext } from "./types.ts";

/**
 * The defiance layer (DESIGN.md 4.2, "being named is evidence"), wrapped
 * around any belief model.
 *
 * Each player has a Beta belief over δ, how often they dodge when named. A
 * named player's forecast is
 *     (1 − δ) · usual  +  δ · dodge(usual)
 * where `usual` is the inner model's forecast as if they weren't named. After
 * each named turn, the Beta is updated by how much of the action each branch
 * explains (the responsibility r of the dodge branch: α += r, β += 1 − r).
 */
export interface DefianceConfig {
  /** Beta prior on dodging when named, as pseudo-counts [dodged, complied]. */
  readonly prior: readonly [number, number];
  /** Whether named turns also teach the inner model what the player usually does. */
  readonly teachInner: "all" | "unnamed";
  /** Each named turn, older evidence about dodging is multiplied by this. */
  readonly memory: number;
}

export const DEFIANCE_DEFAULTS: DefianceConfig = { prior: [1, 3], teachInner: "all", memory: 1 };

export class DefianceBelief implements BeliefModel {
  readonly id: string;
  readonly config: DefianceConfig;
  readonly #inner: BeliefModel;
  readonly #beta = new Map<string, [number, number]>();

  constructor(inner: BeliefModel, heroes: readonly HeroSpec[], config: Partial<DefianceConfig> = {}) {
    this.#inner = inner;
    this.config = { ...DEFIANCE_DEFAULTS, ...config };
    this.id = `${inner.id}+defiance`;
    for (const h of heroes) this.#beta.set(h.id, [0, 0]);
  }

  /** The current estimate of how often this player dodges when named. */
  defiance(hero: string): number {
    const [dodged, complied] = this.#evidence(hero);
    const [a, b] = this.config.prior;
    return (a + dodged) / (a + b + dodged + complied);
  }

  forecast(hero: string, context: ObservationContext): Distribution {
    const usual = this.#inner.forecast(hero, { ...context, named: false });
    if (!context.named) return usual;
    const d = this.defiance(hero);
    const away = dodge(usual);
    return usual.map((p, i) => (1 - d) * p + d * away[i]!);
  }

  observe(hero: string, action: Action, context: ObservationContext): void {
    if (context.named) {
      const usual = this.#inner.forecast(hero, { ...context, named: false });
      const d = this.defiance(hero);
      const comply = (1 - d) * usual[action]!;
      const defy = d * dodge(usual)[action]!;
      const r = defy / (comply + defy);
      const ev = this.#evidence(hero);
      ev[0] = ev[0] * this.config.memory + r;
      ev[1] = ev[1] * this.config.memory + (1 - r);
      if (this.config.teachInner === "unnamed") return;
    }
    this.#inner.observe(hero, action, context);
  }

  #evidence(hero: string): [number, number] {
    const ev = this.#beta.get(hero);
    if (!ev) throw new Error(`DefianceBelief: unknown hero ${hero}`);
    return ev;
  }
}

export function withDefiance(inner: BeliefFactory, config: Partial<DefianceConfig> = {}): BeliefFactory {
  return (heroes) => new DefianceBelief(inner(heroes), heroes, config);
}
