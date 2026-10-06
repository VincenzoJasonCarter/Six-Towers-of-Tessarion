import { argmax, type Action, type Distribution } from "./actions.ts";

/**
 * What the brain assumes about a hero before it has watched them: the usual
 * shape of each subclass's turn, in ACTIONS order (strike, shoot, cast, mend,
 * guard). These are hand-set from ../lore-book/05-subclasses-skill.md and are
 * meant to be replaced by numbers from playtest logs (DESIGN.md 9).
 */
export const SUBCLASSES = {
  verdant: { name: "Verdant Mage", shape: [0.05, 0.05, 0.55, 0.25, 0.10] },
  warbound: { name: "Warbound Mage", shape: [0.45, 0.05, 0.35, 0.05, 0.10] },
  stonewarden: { name: "Stonewarden Mage", shape: [0.10, 0.05, 0.45, 0.15, 0.25] },
  hellbound: { name: "Hellbound Mage", shape: [0.05, 0.05, 0.70, 0.05, 0.15] },
  sanguine_mage: { name: "Sanguine Mage", shape: [0.05, 0.05, 0.55, 0.25, 0.10] },
  aether: { name: "Aether Mage", shape: [0.05, 0.05, 0.35, 0.45, 0.10] },
  sanguine_aegis: { name: "Sanguine Aegis", shape: [0.70, 0.05, 0.05, 0.10, 0.10] },
  bulwark: { name: "Bulwark Aegis", shape: [0.50, 0.05, 0.05, 0.05, 0.35] },
  warden: { name: "Warden Aegis", shape: [0.55, 0.05, 0.05, 0.05, 0.30] },
  crystal_archer: { name: "Crystal Archer", shape: [0.05, 0.75, 0.05, 0.05, 0.10] },
  gunman: { name: "Gunman", shape: [0.10, 0.70, 0.05, 0.05, 0.10] },
  unknown: { name: "Unknown", shape: [0.20, 0.20, 0.20, 0.20, 0.20] },
} as const satisfies Record<string, { name: string; shape: Distribution }>;

export type SubclassId = keyof typeof SUBCLASSES;

export function isSubclass(id: string): id is SubclassId {
  return Object.hasOwn(SUBCLASSES, id);
}

export function shapeOf(subclass: SubclassId): Distribution {
  return SUBCLASSES[subclass].shape;
}

/** The action a subclass takes most often. */
export function mainAction(subclass: SubclassId): Action {
  return argmax(shapeOf(subclass));
}

/** A hero at the table, as the brain knows them. */
export interface HeroSpec {
  readonly id: string;
  readonly subclass: SubclassId;
}
