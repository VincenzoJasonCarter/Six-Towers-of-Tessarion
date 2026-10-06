import { K, type Action, type Distribution } from "../engine/actions.ts";
import { ArchetypesBelief } from "../engine/belief/archetypes.ts";
import { EnsembleBelief } from "../engine/belief/ensemble.ts";
import type { BeliefModel } from "../engine/belief/types.ts";
import { BOSS_HP, Brain, type Choice } from "../engine/brain.ts";
import type { Scored } from "../engine/decision/decide.ts";
import { ENRAGE, INSULT, TemperamentTrack, type Shift, type Trigger } from "../engine/decision/shift.ts";
import { STEPS } from "../engine/decision/temperament.ts";
import type { Announcement, Moment, Resolution } from "../engine/module.ts";
import { Rng } from "../engine/rng.ts";
import type { HeroSpec, SubclassId } from "../engine/subclasses.ts";
import { makeC, TUNED_C } from "../harness/candidates.ts";
import { placeholderWith, type PlaceholderConfig, type PlaceholderMove } from "../modules/placeholder.ts";

/**
 * The table tool's core (DESIGN.md 7): a fight as an append-only event log,
 * and everything else rebuilt by replaying it (4.1). Undo is dropping the
 * last event. The brain is seeded from the setup, so replaying the same log
 * makes the same choices: what the DM saw is what the log says.
 */

export interface TableHero {
  /** What the DM calls them; also their id in the engine. */
  readonly name: string;
  readonly subclass: SubclassId;
}

export interface TableSetup {
  readonly heroes: readonly TableHero[];
  /** How the Placeholder Boss fits the monster at the table (DESIGN.md 6.2). */
  readonly fitting: Partial<PlaceholderConfig>;
  /** The step the boss starts at. */
  readonly start: string;
  /** Shift to Wrathful below half HP and Bloodlusted below a quarter (needs `maxHp`). */
  readonly enrage: boolean;
  /** Each third bet foiled in a row, one step hotter. */
  readonly insult: boolean;
  /** The boss's maximum HP, for recording HP; null if the DM doesn't track it here. */
  readonly maxHp: number | null;
  readonly seed: number;
}

export type TableEvent =
  /** A hero's main action on their turn, in party order: the one tap per turn. */
  | { readonly type: "action"; readonly action: Action }
  /** The boss's HP now, as the DM reads it off their sheet. */
  | { readonly type: "hp"; readonly hp: number }
  /** The DM overrules this round's move with another of the ranked options (DESIGN.md 2: the DM can always overrule). */
  | { readonly type: "overrule"; readonly option: number }
  /** The DM sets the step by hand; it takes hold from the next round's choice. */
  | { readonly type: "step"; readonly step: string };

export interface FightLog {
  readonly version: 1;
  readonly setup: TableSetup;
  readonly events: readonly TableEvent[];
}

/** One round as it happened. */
export interface RoundRecord {
  readonly round: number;
  readonly step: string;
  readonly move: PlaceholderMove | null;
  readonly described: string;
  readonly announcement: Announcement | null;
  readonly overruled: boolean;
  readonly actions: ReadonlyMap<string, Action>;
  readonly resolution: Resolution | null;
  /** Moves made right after a hero's turn (none for the Placeholder; a Prophet's rewind would be one). */
  readonly reactions: readonly { readonly hero: string; readonly described: string; readonly resolution: Resolution }[];
}

export interface HeroView {
  readonly hero: TableHero;
  /** What the brain expects them to do this turn, untempered. */
  readonly forecast: Distribution;
  /** One line from the archetype model ("72% favours Shoot, 40% defies when named"). */
  readonly explanation: string;
  /** Their action this round, once taken. */
  readonly acted: Action | null;
  readonly named: boolean;
  readonly warned: boolean;
}

export interface TableState {
  readonly setup: TableSetup;
  readonly round: number;
  readonly step: string;
  /** The next hero to act this round, by index in the party; equals the party size when everyone has. */
  readonly turn: number;
  /** This round's move, its announcement and the options it was chosen from. */
  readonly plan: {
    readonly move: PlaceholderMove;
    readonly described: string;
    readonly announcement: Announcement;
    readonly ranked: readonly { readonly described: string; readonly eu: number; readonly chosen: boolean }[];
    readonly overruled: boolean;
  } | null;
  readonly heroes: readonly HeroView[];
  readonly history: readonly RoundRecord[];
  readonly shifts: readonly Shift[];
  readonly hp: number | null;
}

export const DEFAULT_SETUP: TableSetup = {
  heroes: [],
  fitting: {},
  start: "ruthless",
  enrage: true,
  insult: false,
  maxHp: null,
  seed: 1,
};

/** Rebuilds the fight from its log. Throws on an event that can't happen (an action after everyone acted, say). */
export function replay(log: FightLog): TableState {
  const { setup } = log;
  const heroes: HeroSpec[] = setup.heroes.map((h) => ({ id: h.name, subclass: h.subclass }));
  const belief = makeC(TUNED_C)(heroes);
  const triggers: Trigger[] = [...(setup.enrage && setup.maxHp !== null ? ENRAGE : []), ...(setup.insult ? [INSULT] : [])];
  const track = new TemperamentTrack(STEPS, setup.start, triggers);
  const module = placeholderWith(setup.fitting)(heroes, new Rng(setup.seed ^ 0x5bd1e995));
  const brain = new Brain(belief, track, module, heroes, new Rng(setup.seed));
  const describe = (m: PlaceholderMove) => module.describe!(m);

  const history: RoundRecord[] = [];
  let round = 1;
  let hp: number | null = setup.maxHp;
  let pendingStep: string | null = null;
  let actions = new Map<string, Action>();
  let reactions: RoundRecord["reactions"][number][] = [];
  let choice: Choice<PlaceholderMove> | null = null;
  let move: PlaceholderMove | null = null;
  let announcement: Announcement | null = null;
  let overruled = false;

  const startRound = () => {
    if (pendingStep) {
      track.set(pendingStep, round);
      pendingStep = null;
    }
    choice = brain.choose({ kind: "round", round });
    move = choice?.move ?? null;
    announcement = choice?.announcement ?? null;
    overruled = false;
    actions = new Map();
    reactions = [];
  };
  const endRound = () => {
    const moment: Moment = { kind: "round", round };
    const resolution = move ? brain.resolve(move, moment, { actions, events: [] }) : null;
    history.push({
      round,
      step: choice?.step.id ?? brain.step.id,
      move,
      described: move ? describe(move) : "nothing",
      announcement,
      overruled,
      actions,
      resolution,
      reactions,
    });
    round += 1;
    startRound();
  };

  startRound();
  for (const e of log.events) {
    switch (e.type) {
      case "action": {
        const hero = heroes[actions.size];
        if (!hero) throw new Error("replay: an action after every hero has acted");
        const named = announcement?.named.includes(hero.id) ?? false;
        const context = { round, named };
        brain.observe(hero.id, e.action, context);
        actions.set(hero.id, e.action);
        const turn: Moment = { kind: "turn", round, hero: hero.id, action: e.action };
        const reaction = brain.choose(turn);
        if (reaction) {
          const resolution = brain.resolve(reaction.move, turn, { actions, events: [] });
          reactions.push({ hero: hero.id, described: describe(reaction.move), resolution });
        }
        if (actions.size === heroes.length) endRound();
        break;
      }
      case "hp": {
        hp = e.hp;
        if (setup.maxHp) brain.record({ kind: BOSS_HP, value: Math.max(0, e.hp) / setup.maxHp });
        break;
      }
      case "overrule": {
        if (actions.size > 0) throw new Error("replay: a move can only be overruled before anyone acts");
        const ranked = (choice as Choice<PlaceholderMove> | null)?.decision.ranked;
        const picked = ranked?.[e.option];
        if (!picked) throw new Error(`replay: no option ${e.option} to overrule with`);
        move = picked.option.move;
        announcement = module.announce(move, brain.step);
        overruled = true;
        break;
      }
      case "step": {
        pendingStep = e.step;
        break;
      }
    }
  }

  const c = choice as Choice<PlaceholderMove> | null;
  const plan =
    c && move && announcement
      ? {
          move,
          described: describe(move),
          announcement,
          ranked: c.decision.ranked.map((s: Scored<PlaceholderMove>) => ({ described: describe(s.option.move), eu: s.eu, chosen: s.option.move === move })),
          overruled,
        }
      : null;
  const named = new Set(announcement?.named ?? []);
  const warned = new Set(announcement?.warned ?? []);
  return {
    setup,
    round,
    step: brain.step.id,
    turn: actions.size,
    plan,
    heroes: setup.heroes.map((h) => ({
      hero: h,
      forecast: brain.belief.forecast(h.name, { round, named: named.has(h.name) }),
      explanation: explain(belief, h.name),
      acted: actions.get(h.name) ?? null,
      named: named.has(h.name),
      warned: warned.has(h.name),
    })),
    history,
    shifts: track.shifts,
    hp,
  };
}

/** The archetype model's one line about a hero, if the belief has one. */
function explain(belief: BeliefModel, hero: string): string {
  const members = belief instanceof EnsembleBelief ? belief.members : [belief];
  const archetypes = members.find((m): m is ArchetypesBelief => m instanceof ArchetypesBelief);
  return archetypes ? archetypes.explain(hero) : "";
}

/** A log with one more event, if replaying it works; otherwise the error. */
export function append(log: FightLog, event: TableEvent): { log: FightLog; state: TableState } {
  const next: FightLog = { ...log, events: [...log.events, event] };
  return { log: next, state: replay(next) };
}

export function undo(log: FightLog): FightLog {
  return { ...log, events: log.events.slice(0, -1) };
}

export function newFight(setup: TableSetup): FightLog {
  if (setup.heroes.length === 0) throw new Error("A fight needs at least one hero");
  if (new Set(setup.heroes.map((h) => h.name)).size !== setup.heroes.length) throw new Error("Heroes need different names");
  return { version: 1, setup, events: [] };
}

/** Parses an exported log, checking its shape. */
export function parseLog(text: string): FightLog {
  const log = JSON.parse(text) as FightLog;
  if (log?.version !== 1 || !log.setup || !Array.isArray(log.events)) throw new Error("Not a boss-brain fight log");
  replay(log);
  return log;
}

export const ACTION_COUNT = K;
