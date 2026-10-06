import { ACTIONS, type Action } from "../../engine/actions.ts";
import type { Option } from "../../engine/decision/decide.ts";
import type { Disclosure, Utility } from "../../engine/decision/temperament.ts";
import type { Announcement, ModuleContext } from "../../engine/module.ts";

/**
 * What each action is worth to the party (DESIGN.md 6.1), standing in for a
 * combat model the harness doesn't have. Denying a heal is `lethal` (4.3).
 * Placeholders, to come from playtests.
 */
export const FIGHT_VALUE: readonly number[] = [
  1, // Strike
  1, // Shoot
  1, // Cast
  1.5, // Mend
  0.25, // Guard
];

/** `spread` for going after a different hero from last round's target; none in the first round or after a quiet one. */
export const spreadFor = (last: string | null, hero: string): number => (last !== null && hero !== last ? 1 : 0);

/** A move that reads a hero's action: a bet, or a cut. */
export interface Read {
  readonly hero: string;
  readonly action: Action;
}

/**
 * One option per (hero, action): a read that pays `onHit` if the hero takes
 * that action. The forecast is made as if named unless the disclosure is
 * hidden, and the read carries the exploration bonus unless it is no probe.
 */
export function readOptions<M>(
  round: number,
  ctx: ModuleContext,
  last: string | null,
  onHit: (action: Action) => Utility,
  move: (read: Read) => M,
  { probe = true }: { readonly probe?: boolean } = {},
): Option<M>[] {
  const named = ctx.step.disclosure !== "hidden";
  const options: Option<M>[] = [];
  for (const hero of ctx.heroes) {
    const context = { round, named };
    const odds = ctx.view.forecast(hero.id, context);
    const spread = spreadFor(last, hero.id);
    ACTIONS.forEach((_, a) => {
      const action = a as Action;
      const p = odds[action]!;
      options.push({
        move: move({ hero: hero.id, action }),
        outcomes: [
          { p, utility: { ...onHit(action), spread } },
          { p: 1 - p, utility: { spread } },
        ],
        ...(probe ? { about: { hero: hero.id, context } } : {}),
      });
    });
  }
  return options;
}

/** What the table hears of a read, at the step's disclosure. */
export function announceRead(read: Read, disclosure: Disclosure, verb: string): Announcement {
  const label = ACTIONS[read.action]!.label;
  switch (disclosure) {
    case "full":
      return { named: [read.hero], warned: [], text: `${read.hero} will ${label}; the boss ${verb}.` };
    case "name":
      return { named: [read.hero], warned: [], text: `The boss has seen what ${read.hero} will do.` };
    case "hidden":
      return { named: [], warned: [], text: "" };
  }
}

export const SILENT: Announcement = { named: [], warned: [], text: "" };
