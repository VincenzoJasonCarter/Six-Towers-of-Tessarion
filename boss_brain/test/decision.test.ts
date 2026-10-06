import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { GUARD, SHOOT, STRIKE, type Action } from "../src/engine/actions.ts";
import { CountsBelief } from "../src/engine/belief/counts.ts";
import type { BeliefModel } from "../src/engine/belief/types.ts";
import { decide, temper, tempered, uncertainty, watched, type Option } from "../src/engine/decision/decide.ts";
import { PLACEHOLDER_STEPS, STEPS, stepById, type Temperament } from "../src/engine/decision/temperament.ts";
import { Rng } from "../src/engine/rng.ts";
import { BetScore, bettor } from "../src/harness/bettor.ts";
import type { FightRecord } from "../src/harness/fight.ts";

const close = (a: number, b: number, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} vs ${b}`);
const sum = (xs: readonly number[]) => xs.reduce((a, b) => a + b, 0);
const ctx = { round: 1, named: true };
const gunman = { id: "g", subclass: "gunman" } as const;
const ruthless = PLACEHOLDER_STEPS.find((s) => s.id === "ruthless")!;

/** A temperament that only cares about `tempo`, with the given levers. */
const plain = (over: Partial<Temperament> = {}): Temperament => ({
  ...ruthless,
  slack: 0,
  mixing: 0,
  weights: { lethal: 0, spread: 0, show: 0, tempo: 1 },
  sharpness: 1,
  rashness: 0,
  explore: 0,
  ...over,
});

/** A bet that comes true with probability p, worth one `tempo`. */
const bet = (move: string, p: number, hero?: string): Option<string> => ({
  move,
  outcomes: [
    { p, utility: { tempo: 1 } },
    { p: 1 - p, utility: {} },
  ],
  ...(hero ? { about: { hero, context: ctx } } : {}),
});

const fixedBelief = (forecasts: Record<string, number[]>): BeliefModel => ({
  id: "fixed",
  forecast: (hero) => forecasts[hero]!,
  observe: () => {},
  reveal: () => {},
});

describe("temper", () => {
  it("leaves β = 1 alone, flattens below 1 and sharpens above, keeping the order", () => {
    const d = [0.6, 0.3, 0.05, 0.03, 0.02];
    assert.deepEqual(temper(d, 1), d);
    const soft = temper(d, 0.5);
    const sharp = temper(d, 2);
    close(sum(soft), 1);
    close(sum(sharp), 1);
    assert.ok(soft[0]! < d[0]! && sharp[0]! > d[0]!);
    assert.deepEqual([...sharp].sort((a, b) => b - a), sharp, "the order of the actions is kept");
  });
});

describe("uncertainty", () => {
  it("is 0 when sure and 1 when blind", () => {
    close(uncertainty([1, 0, 0, 0, 0]), 0);
    close(uncertainty([0.2, 0.2, 0.2, 0.2, 0.2]), 1);
  });
});

describe("decide", () => {
  const belief = fixedBelief({});
  const options = [bet("low", 0.2), bet("best", 0.6), bet("near", 0.58)];

  it("at mixing 0 takes the best, without touching the rng", () => {
    const rng = new Rng(1);
    const before = new Rng(1).next();
    assert.equal(decide(options, plain(), belief, rng).chosen.move, "best");
    assert.equal(rng.next(), before);
  });

  it("ranks every option for the explanation", () => {
    const { ranked } = decide(options, plain(), belief, new Rng(1));
    assert.deepEqual(ranked.map((s) => s.option.move), ["best", "near", "low"]);
    close(ranked[0]!.eu, 0.6);
  });

  it("mixes only among the options within the slack of the best", () => {
    const picks = new Set<string>();
    const rng = new Rng(3);
    for (let i = 0; i < 200; i++) picks.add(decide(options, plain({ slack: 0.1, mixing: 1 }), belief, rng).chosen.move);
    assert.deepEqual([...picks].sort(), ["best", "near"]);
  });

  it("adds an exploration bonus for betting where the forecast is unsure", () => {
    const unsure = fixedBelief({ sure: [0.9, 0.025, 0.025, 0.025, 0.025], blind: [0.2, 0.2, 0.2, 0.2, 0.2] });
    const opts = [bet("sure", 0.5, "sure"), bet("blind", 0.5, "blind")];
    assert.equal(decide(opts, plain(), unsure, new Rng(1)).chosen.move, "sure", "ties go to the first");
    assert.equal(decide(opts, plain({ explore: 0.1 }), unsure, new Rng(1)).chosen.move, "blind");
  });
});

describe("tempered", () => {
  it("stakes a rash boss's forecast on the player doing their last action again", () => {
    const belief = watched(new CountsBelief([gunman]));
    const calm = tempered(belief, plain()).forecast("g", ctx);
    assert.deepEqual(tempered(belief, plain({ rashness: 0.8 })).forecast("g", ctx), calm, "no last action yet");
    belief.observe("g", GUARD, ctx);
    const usual = belief.forecast("g", ctx);
    const rash = tempered(belief, plain({ rashness: 0.8 })).forecast("g", ctx);
    close(sum(rash), 1);
    close(rash[GUARD]!, 0.2 * usual[GUARD]! + 0.8);
    close(rash[SHOOT]!, 0.2 * usual[SHOOT]!);
  });
});

describe("bettor", () => {
  const heroes = [gunman, { id: "b", subclass: "bulwark" }] as const;

  it("makes one bet a round, disclosed at the step's level", () => {
    const belief = watched(new CountsBelief(heroes));
    const [p] = bettor(ruthless, belief, new Rng(1)).speak(1, heroes, belief);
    assert.equal(p!.hidden, true);
    const curious = PLACEHOLDER_STEPS.find((s) => s.id === "curious")!;
    const [q] = bettor(curious, belief, new Rng(1)).speak(1, heroes, belief);
    assert.equal(q!.hidden, false);
  });

  it("doesn't count spread in the first round, so a fixated boss still speaks", () => {
    const fixated = plain({ weights: { lethal: 0, spread: -5, show: 0, tempo: 1 } });
    const belief = watched(new CountsBelief(heroes));
    const boss = bettor(fixated, belief, new Rng(1));
    const first = boss.speak(1, heroes, belief);
    assert.equal(first.length, 1);
    assert.equal(boss.speak(2, heroes, belief)[0]!.hero, first[0]!.hero, "then it sticks to its target");
  });
});

describe("BetScore", () => {
  it("measures success, fixation and predictability", () => {
    const p = (round: number, hero: string, action: Action, fulfilled: boolean) => ({ round, hero, action, p: 0.5, fulfilled });
    const fight: FightRecord = {
      turns: [],
      charges: 0,
      firstRewindRound: null,
      prophecies: [
        p(1, "g", SHOOT, true),
        p(2, "g", SHOOT, false), // repeats the most common bet so far
        p(3, "b", STRIKE, true), // doesn't
        p(4, "g", SHOOT, true), // does
      ],
    };
    const score = new BetScore();
    score.addFight(fight);
    score.addFight({ ...fight, prophecies: [] });
    const s = score.summary();
    close(s.success, 3 / 4);
    close(s.betsPerFight, 2);
    close(s.fixation, 3 / 4, 1e-9);
    close(s.predictability, 2 / 3);
  });
});

describe("STEPS", () => {
  it("keep each step on its side of the curve, as the M3 protocol requires", () => {
    const [curious, hunting, ruthless, wrathful, bloodlusted] = ["curious", "hunting", "ruthless", "wrathful", "bloodlusted"].map(stepById);
    assert.deepEqual(STEPS.map((s) => s.id), PLACEHOLDER_STEPS.map((s) => s.id));
    assert.ok(curious!.sharpness <= hunting!.sharpness && hunting!.sharpness <= 1);
    assert.equal(ruthless!.sharpness, 1);
    assert.equal(ruthless!.rashness, 0);
    assert.ok(bloodlusted!.rashness > wrathful!.rashness);
    assert.ok(bloodlusted!.weights.spread < wrathful!.weights.spread && wrathful!.weights.spread < 0);
    assert.deepEqual(STEPS.map((s) => s.disclosure), ["full", "name", "hidden", "name", "full"]);
    assert.throws(() => stepById("playful"));
  });
});
