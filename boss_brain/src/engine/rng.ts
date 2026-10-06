/**
 * A small seeded random number generator (mulberry32), so every harness run
 * can be reproduced exactly from its seed.
 */
export class Rng {
  #state: number;

  constructor(seed: number) {
    this.#state = seed >>> 0;
  }

  /** A float in [0, 1). */
  next(): number {
    let t = (this.#state = (this.#state + 0x6d2b79f5) >>> 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /** An integer in [0, n). */
  int(n: number): number {
    return Math.floor(this.next() * n);
  }

  /** An index drawn in proportion to the (non-negative) weights. */
  weighted(weights: readonly number[]): number {
    const total = weights.reduce((a, b) => a + b, 0);
    let r = this.next() * total;
    for (let i = 0; i < weights.length; i++) {
      r -= weights[i]!;
      if (r < 0) return i;
    }
    return weights.length - 1;
  }
}

/**
 * A seed derived from a base seed and a path of integers, so a sub-run (one
 * style, one trial) gets the same stream whichever other sub-runs happen.
 */
export function seedFor(base: number, ...path: number[]): number {
  let h = base >>> 0;
  for (const p of path) {
    h = Math.imul(h ^ (p >>> 0), 0x9e3779b1) >>> 0;
    h ^= h >>> 16;
    h = Math.imul(h, 0x85ebca6b) >>> 0;
    h ^= h >>> 13;
  }
  return h >>> 0;
}
