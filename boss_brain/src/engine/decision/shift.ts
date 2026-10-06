import type { Temperament } from "./temperament.ts";

/**
 * Temperament shifting mid-fight (DESIGN.md 5.3): a module declares triggers,
 * and the dial moves when one fires. Only the temperament changes; the belief
 * carries on, so a boss that loses its temper still remembers what it read.
 */

/** What triggers can see, all of it generic: no trigger needs to know the module. */
export interface FightSignals {
  readonly round: number;
  /** The boss's remaining HP as a share of its maximum, if the DM tracks it. */
  readonly bossHp: number | null;
  /** Bets the table has seen, and how many came true. */
  readonly betsSeen: number;
  readonly betsFulfilled: number;
  /** Bets foiled one after another, up to the latest. */
  readonly foiledInARow: number;
  /** Module events so far, by kind. */
  readonly events: Readonly<Record<string, number>>;
}

/** Where a trigger moves the dial: to a step, or one step hotter or cooler. */
export type ShiftTarget = string | "hotter" | "cooler";

export interface Trigger {
  readonly id: string;
  /** For the DM: why the boss changed ("below half HP"). */
  readonly reason: string;
  readonly when: (signals: FightSignals) => boolean;
  readonly to: ShiftTarget;
  /** Fire once a fight (the default), or each time the condition becomes true again. */
  readonly repeat?: boolean;
}

export interface Shift {
  readonly round: number;
  readonly from: string;
  readonly to: string;
  readonly trigger: string;
  readonly reason: string;
}

/**
 * The dial over one fight. Checked at the start of each round, before the
 * boss chooses: triggers are tried in order, and each one that fires moves
 * the dial. A trigger that doesn't repeat is spent once it has fired; one
 * that repeats fires each time its condition turns from false to true, so a
 * condition that simply stays true doesn't fire round after round.
 */
export class TemperamentTrack {
  readonly #steps: readonly Temperament[];
  readonly #triggers: readonly Trigger[];
  readonly #spent = new Set<string>();
  readonly #held = new Map<string, boolean>();
  readonly shifts: Shift[] = [];
  #index: number;

  constructor(steps: readonly Temperament[], start: string, triggers: readonly Trigger[] = []) {
    this.#steps = steps;
    this.#triggers = triggers;
    this.#index = this.#indexOf(start);
  }

  get current(): Temperament {
    return this.#steps[this.#index]!;
  }

  update(signals: FightSignals): void {
    for (const t of this.#triggers) {
      if (this.#spent.has(t.id)) continue;
      const holds = t.when(signals);
      const was = this.#held.get(t.id) ?? false;
      this.#held.set(t.id, holds);
      if (!holds || (t.repeat && was)) continue;
      if (!t.repeat) this.#spent.add(t.id);
      const to = this.#target(t.to);
      if (to === this.#index) continue;
      this.shifts.push({ round: signals.round, from: this.current.id, to: this.#steps[to]!.id, trigger: t.id, reason: t.reason });
      this.#index = to;
    }
  }

  #target(to: ShiftTarget): number {
    if (to === "hotter") return Math.min(this.#steps.length - 1, this.#index + 1);
    if (to === "cooler") return Math.max(0, this.#index - 1);
    return this.#indexOf(to);
  }

  #indexOf(id: string): number {
    const i = this.#steps.findIndex((s) => s.id === id);
    if (i < 0) throw new Error(`No temperament step "${id}". Known: ${this.#steps.map((s) => s.id).join(", ")}`);
    return i;
  }
}

/** The classic enrage (DESIGN.md 5.3): cold above half HP, Wrathful below it, Bloodlusted below a quarter. */
export const ENRAGE: readonly Trigger[] = [
  { id: "half", reason: "below half HP", when: (s) => s.bossHp !== null && s.bossHp < 0.5, to: "wrathful" },
  { id: "quarter", reason: "below a quarter HP", when: (s) => s.bossHp !== null && s.bossHp < 0.25, to: "bloodlusted" },
];

/** An insult: each third bet foiled in a row, the boss loses a step of its cool. */
export const INSULT: Trigger = {
  id: "insult",
  reason: "foiled three times running",
  when: (s) => s.foiledInARow >= 3 && s.foiledInARow % 3 === 0,
  to: "hotter",
  repeat: true,
};
