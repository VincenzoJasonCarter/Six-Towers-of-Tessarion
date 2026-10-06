import type { Action } from "../engine/actions.ts";
import type { BeliefFactory } from "../engine/belief/types.ts";
import { Brain } from "../engine/brain.ts";
import { AXES, type Axis, type Temperament } from "../engine/decision/temperament.ts";
import type { ModuleFactory, Moment, Resolution } from "../engine/module.ts";
import { Rng, seedFor } from "../engine/rng.ts";
import type { HeroSpec, SubclassId } from "../engine/subclasses.ts";
import { BetScore, BOSS_STREAM, type BetSummary } from "./bettor.ts";
import { heeding, type Player, type Style, type Told } from "./players.ts";
import { hash } from "./suite.ts";

/** One settled move: when it was chosen and what came of it. */
export interface Settled {
  readonly moment: Moment;
  readonly resolution: Resolution;
}

export interface BoutRecord {
  readonly settled: readonly Settled[];
}

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
}: {
  readonly heroes: readonly HeroSpec[];
  readonly players: ReadonlyMap<string, Player>;
  readonly brain: Brain<M>;
  readonly rounds: number;
}): BoutRecord {
  const settled: Settled[] = [];
  const history = new Map<string, Action[]>(heroes.map((h) => [h.id, []]));
  const told = new Map<string, Told[]>(heroes.map((h) => [h.id, []]));
  const settle = (move: M, moment: Moment, actions: ReadonlyMap<string, Action>) => {
    const resolution = brain.resolve(move, moment, { actions, events: [] });
    settled.push({ moment, resolution });
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
      if (reaction) settle(reaction.move, turn, actions);
    }
    if (choice) settle(choice.move, start, actions);
  }
  return { settled };
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
}

/** Scores the moves of many bouts. */
export class ModuleScore {
  #fights = 0;
  readonly #bets = new BetScore();
  readonly #axes = Object.fromEntries(AXES.map((a) => [a, 0])) as Record<Axis, number>;
  readonly #kinds = new Map<string, number>();
  readonly #detail = new Map<string, number>();

  addBout(bout: BoutRecord): void {
    this.#fights += 1;
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
      const brain = new Brain(opts.belief(heroes), opts.step, module, heroes, new Rng(seedFor(opts.seed, styleKey, trial, BOSS_STREAM)));
      score.addBout(runBout({ heroes, players, brain, rounds: opts.rounds }));
    }
    return { style: style.id, name: style.name, ...score.summary() };
  });
  return { step: opts.step, styles };
}
