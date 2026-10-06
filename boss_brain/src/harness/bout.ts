import { CAST, SHOOT, STRIKE, type Action } from "../engine/actions.ts";
import type { BeliefFactory } from "../engine/belief/types.ts";
import { BOSS_HP, Brain } from "../engine/brain.ts";
import { TemperamentTrack, type Shift, type Trigger } from "../engine/decision/shift.ts";
import { AXES, STEPS, type Axis, type Temperament } from "../engine/decision/temperament.ts";
import type { ModuleFactory, Moment, Resolution } from "../engine/module.ts";
import { Rng, seedFor } from "../engine/rng.ts";
import type { HeroSpec, SubclassId } from "../engine/subclasses.ts";
import { BetScore, BOSS_STREAM, type BetSummary } from "./bettor.ts";
import { heeding, type Player, type Style, type Told } from "./players.ts";
import { hash } from "./suite.ts";

/** One settled move: when it was chosen, under which step, and what came of it. */
export interface Settled {
  readonly moment: Moment;
  readonly step: string;
  readonly resolution: Resolution;
}

export interface BoutRecord {
  readonly settled: readonly Settled[];
  readonly shifts: readonly Shift[];
}

/** The harness's crude HP clock: each Strike, Shoot or Cast a hero takes deals the boss 1. */
const ATTACKS: ReadonlySet<Action> = new Set([STRIKE, SHOOT, CAST]);

/**
 * One fight against any module (DESIGN.md 4): each round the boss may move,
 * then every hero acts once in party order, the boss may move again after
 * each turn, and a round's move is settled once everyone has acted. What a
 * move reveals about a hero's action is told to that hero when it settles.
 */
export function runBout<M>({
  heroes,
  players,
  brain,
  rounds,
  bossHp,
}: {
  readonly heroes: readonly HeroSpec[];
  readonly players: ReadonlyMap<string, Player>;
  readonly brain: Brain<M>;
  readonly rounds: number;
  /** The boss's HP on the crude clock; without it, the boss's HP is never recorded. */
  readonly bossHp?: number;
}): BoutRecord {
  const settled: Settled[] = [];
  const history = new Map<string, Action[]>(heroes.map((h) => [h.id, []]));
  const told = new Map<string, Told[]>(heroes.map((h) => [h.id, []]));
  let hp = bossHp ?? 0;
  const settle = (move: M, step: string, moment: Moment, actions: ReadonlyMap<string, Action>) => {
    const resolution = brain.resolve(move, moment, { actions, events: [] });
    settled.push({ moment, step, resolution });
    for (const b of resolution.bets) told.get(b.hero)!.push({ round: moment.round, action: b.action, fulfilled: b.fulfilled });
  };

  for (let round = 1; round <= rounds; round++) {
    const start: Moment = { kind: "round", round };
    const choice = brain.choose(start);
    const named = new Set(choice?.announcement.named ?? []);
    const warned = new Set(choice?.announcement.warned ?? []);
    const actions = new Map<string, Action>();
    for (const hero of heroes) {
      const context = { round, named: named.has(hero.id) };
      const own = history.get(hero.id)!;
      const action = players.get(hero.id)!.act({ ...context, warned: warned.has(hero.id), history: own, told: told.get(hero.id)! });
      brain.observe(hero.id, action, context);
      own.push(action);
      actions.set(hero.id, action);
      const turn: Moment = { kind: "turn", round, hero: hero.id, action };
      const reaction = brain.choose(turn);
      if (reaction) settle(reaction.move, reaction.step.id, turn, actions);
    }
    if (choice) settle(choice.move, choice.step.id, start, actions);
    if (bossHp !== undefined) {
      hp = Math.max(0, hp - [...actions.values()].filter((a) => ATTACKS.has(a)).length);
      brain.record({ kind: BOSS_HP, value: hp / bossHp });
    }
  }
  return { settled, shifts: brain.shifts };
}

/** How the boss played under one step, over the rounds it was in force. */
export interface PhaseSummary {
  readonly moves: number;
  readonly lethalPerMove: number;
  /** Each kind's share of the phase's moves. */
  readonly kinds: Readonly<Record<string, number>>;
  readonly betSuccess: number | null;
  /** Per fight, the share of the phase's bets on the hero bet on most; averaged over fights with a bet in it. */
  readonly fixation: number | null;
}

export interface ModuleSummary {
  readonly fights: number;
  /** The bets the moves made about heroes' actions, scored as in M3. */
  readonly bets: BetSummary;
  /** Utility realised per fight, by axis. */
  readonly perFight: Readonly<Record<Axis, number>>;
  /** Moves per fight, by kind. */
  readonly kinds: Readonly<Record<string, number>>;
  /** Module detail per fight, summed by key. */
  readonly detail: Readonly<Record<string, number>>;
  /** Per step the boss was in at some point. */
  readonly phases: Readonly<Record<string, PhaseSummary>>;
  /** Per step shifted to: the share of fights that got there, and the mean round it happened. */
  readonly shifts: Readonly<Record<string, { readonly rate: number; readonly round: number }>>;
  readonly shiftsPerFight: number;
}

interface PhaseTally {
  moves: number;
  lethal: number;
  kinds: Map<string, number>;
  bets: number;
  hits: number;
  fixation: number;
  fixationFights: number;
}

/** Scores the moves of many bouts. */
export class ModuleScore {
  #fights = 0;
  readonly #bets = new BetScore();
  readonly #axes = Object.fromEntries(AXES.map((a) => [a, 0])) as Record<Axis, number>;
  readonly #kinds = new Map<string, number>();
  readonly #detail = new Map<string, number>();
  readonly #phases = new Map<string, PhaseTally>();
  readonly #shifts = new Map<string, { fights: number; rounds: number }>();
  #shiftCount = 0;

  addBout(bout: BoutRecord): void {
    this.#fights += 1;
    const perHero = new Map<string, Map<string, number>>();
    for (const { step, resolution: r } of bout.settled) {
      let t = this.#phases.get(step);
      if (!t) this.#phases.set(step, (t = { moves: 0, lethal: 0, kinds: new Map(), bets: 0, hits: 0, fixation: 0, fixationFights: 0 }));
      t.moves += 1;
      t.lethal += r.utility.lethal ?? 0;
      t.kinds.set(r.kind, (t.kinds.get(r.kind) ?? 0) + 1);
      for (const b of r.bets) {
        t.bets += 1;
        if (b.fulfilled) t.hits += 1;
        if (!perHero.has(step)) perHero.set(step, new Map());
        const m = perHero.get(step)!;
        m.set(b.hero, (m.get(b.hero) ?? 0) + 1);
      }
    }
    for (const [step, m] of perHero) {
      const t = this.#phases.get(step)!;
      const counts = [...m.values()];
      t.fixation += Math.max(...counts) / counts.reduce((a, b) => a + b, 0);
      t.fixationFights += 1;
    }
    this.#shiftCount += bout.shifts.length;
    const reached = new Set<string>();
    for (const sh of bout.shifts) {
      if (reached.has(sh.to)) continue;
      reached.add(sh.to);
      const x = this.#shifts.get(sh.to) ?? { fights: 0, rounds: 0 };
      x.fights += 1;
      x.rounds += sh.round;
      this.#shifts.set(sh.to, x);
    }
    this.#bets.addBets(bout.settled.flatMap((s) => s.resolution.bets));
    for (const { resolution: r } of bout.settled) {
      for (const axis of AXES) this.#axes[axis] += r.utility[axis] ?? 0;
      this.#kinds.set(r.kind, (this.#kinds.get(r.kind) ?? 0) + 1);
      for (const [k, v] of Object.entries(r.detail ?? {})) this.#detail.set(k, (this.#detail.get(k) ?? 0) + v);
    }
  }

  summary(): ModuleSummary {
    const per = (x: number) => x / this.#fights;
    return {
      fights: this.#fights,
      bets: this.#bets.summary(),
      perFight: Object.fromEntries(AXES.map((a) => [a, per(this.#axes[a])])) as Record<Axis, number>,
      kinds: Object.fromEntries([...this.#kinds].map(([k, v]) => [k, per(v)])),
      detail: Object.fromEntries([...this.#detail].map(([k, v]) => [k, per(v)])),
      phases: Object.fromEntries(
        [...this.#phases].map(([step, t]) => [
          step,
          {
            moves: t.moves,
            lethalPerMove: t.lethal / t.moves,
            kinds: Object.fromEntries([...t.kinds].map(([k, v]) => [k, v / t.moves])),
            betSuccess: t.bets ? t.hits / t.bets : null,
            fixation: t.fixationFights ? t.fixation / t.fixationFights : null,
          },
        ]),
      ),
      shifts: Object.fromEntries([...this.#shifts].map(([to, x]) => [to, { rate: x.fights / this.#fights, round: x.rounds / x.fights }])),
      shiftsPerFight: per(this.#shiftCount),
    };
  }
}

export interface ModuleSuiteOptions {
  readonly seed: number;
  readonly trials: number;
  readonly rounds: number;
  readonly party: readonly SubclassId[];
  readonly styles: readonly Style[];
  readonly belief: BeliefFactory;
  readonly step: Temperament;
  readonly module: ModuleFactory<unknown>;
  /** Triggers that shift the dial mid-fight, starting from `step` (DESIGN.md 5.3). */
  readonly triggers?: readonly Trigger[];
  /** The boss's HP on the crude clock, for triggers that read it. */
  readonly bossHp?: number;
}

export interface ModuleSuiteResult {
  readonly step: Temperament;
  readonly styles: readonly ({ readonly style: string; readonly name: string } & ModuleSummary)[];
}

/** The heroes' warning streams, clear of theirs and the boss's. */
const WARN_STREAM = 2_000_003;
const MODULE_STREAM = 3_000_017;

/**
 * Plays every style through `trials` bouts against a module under a
 * temperament. Seeds as in `runBetSuite`, so Bet here meets the same players
 * and makes the same draws as M3's bettor did.
 */
export function runModuleSuite(opts: ModuleSuiteOptions): ModuleSuiteResult {
  const heroes: HeroSpec[] = opts.party.map((subclass, i) => ({ id: `${subclass}#${i + 1}`, subclass }));
  const styles = opts.styles.map((style) => {
    const styleKey = hash(style.id);
    const score = new ModuleScore();
    for (let trial = 0; trial < opts.trials; trial++) {
      const players = new Map<string, Player>(
        heroes.map((h, i) => [
          h.id,
          heeding(
            style,
            style.make(h.subclass, new Rng(seedFor(opts.seed, styleKey, trial, i))),
            new Rng(seedFor(opts.seed, styleKey, trial, WARN_STREAM + i)),
          ),
        ]),
      );
      const module = opts.module(heroes, new Rng(seedFor(opts.seed, styleKey, trial, MODULE_STREAM)));
      const temperament = opts.triggers ? new TemperamentTrack(STEPS, opts.step.id, opts.triggers) : opts.step;
      const brain = new Brain(opts.belief(heroes), temperament, module, heroes, new Rng(seedFor(opts.seed, styleKey, trial, BOSS_STREAM)));
      score.addBout(runBout({ heroes, players, brain, rounds: opts.rounds, bossHp: opts.bossHp }));
    }
    return { style: style.id, name: style.name, ...score.summary() };
  });
  return { step: opts.step, styles };
}
