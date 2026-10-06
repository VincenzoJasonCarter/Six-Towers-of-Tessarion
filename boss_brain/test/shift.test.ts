import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { STRIKE } from "../src/engine/actions.ts";
import { CountsBelief } from "../src/engine/belief/counts.ts";
import { BOSS_HP, Brain } from "../src/engine/brain.ts";
import { ENRAGE, INSULT, TemperamentTrack, type FightSignals } from "../src/engine/decision/shift.ts";
import { STEPS } from "../src/engine/decision/temperament.ts";
import { Rng } from "../src/engine/rng.ts";
import { runBout } from "../src/harness/bout.ts";
import { placeholder } from "../src/modules/placeholder.ts";

const signals = (over: Partial<FightSignals> = {}): FightSignals => ({
  round: 1,
  bossHp: null,
  betsSeen: 0,
  betsFulfilled: 0,
  foiledInARow: 0,
  events: {},
  ...over,
});
const gunman = { id: "g", subclass: "gunman" } as const;

describe("TemperamentTrack", () => {
  it("enrages at half and a quarter HP, once each, in order", () => {
    const t = new TemperamentTrack(STEPS, "ruthless", ENRAGE);
    t.update(signals({ round: 2, bossHp: 0.8 }));
    assert.equal(t.current.id, "ruthless");
    t.update(signals({ round: 4, bossHp: 0.45 }));
    assert.equal(t.current.id, "wrathful");
    t.update(signals({ round: 7, bossHp: 0.2 }));
    assert.equal(t.current.id, "bloodlusted");
    assert.deepEqual(
      t.shifts.map((s) => [s.round, s.from, s.to, s.reason]),
      [
        [4, "ruthless", "wrathful", "below half HP"],
        [7, "wrathful", "bloodlusted", "below a quarter HP"],
      ],
    );
  });

  it("fires a repeating trigger when its condition turns true, not every round it stays true", () => {
    const t = new TemperamentTrack(STEPS, "curious", [INSULT]);
    for (const foiled of [1, 2, 3, 3, 3, 4, 5, 6]) t.update(signals({ foiledInARow: foiled }));
    assert.equal(t.current.id, "ruthless", "two insults: curious → hunting → ruthless");
    assert.equal(t.shifts.length, 2);
  });

  it("stops at the ends of the dial", () => {
    const t = new TemperamentTrack(STEPS, "bloodlusted", [{ id: "x", reason: "", when: () => true, to: "hotter" }]);
    t.update(signals());
    assert.equal(t.current.id, "bloodlusted");
    assert.deepEqual(t.shifts, []);
    assert.throws(() => new TemperamentTrack(STEPS, "playful"));
  });
});

describe("Brain with a track", () => {
  it("shifts at the start of a round when the DM records its HP, and keeps its belief", () => {
    const belief = new CountsBelief([gunman]);
    const brain = new Brain(belief, new TemperamentTrack(STEPS, "ruthless", ENRAGE), placeholder([gunman], new Rng(1)), [gunman], new Rng(1));
    for (let i = 0; i < 5; i++) brain.observe("g", STRIKE, { round: 1, named: false });
    const read = brain.belief.forecast("g", { round: 2, named: false });
    brain.record({ kind: BOSS_HP, value: 0.4 });
    const choice = brain.choose({ kind: "round", round: 2 })!;
    assert.equal(choice.step.id, "wrathful");
    assert.deepEqual(brain.belief.forecast("g", { round: 2, named: false }), read, "the belief carries through the shift");
  });

  it("runs a bout on the HP clock, recording which step each move was made under", () => {
    const heroes = [gunman, { id: "b", subclass: "bulwark" }] as const;
    const brain = new Brain(new CountsBelief(heroes), new TemperamentTrack(STEPS, "ruthless", ENRAGE), placeholder(heroes, new Rng(1)), heroes, new Rng(1));
    const players = new Map(heroes.map((h) => [h.id, { act: () => STRIKE }]));
    const bout = runBout({ heroes, players, brain, rounds: 10, bossHp: 8 });
    // Two strikes a round: half left after round 2 (not below it), a quarter after round 3, none after 4.
    assert.deepEqual(bout.shifts.map((s) => [s.round, s.to]), [
      [4, "wrathful"],
      [5, "bloodlusted"],
    ]);
    assert.deepEqual(bout.settled.map((s) => s.step).slice(0, 5), ["ruthless", "ruthless", "ruthless", "wrathful", "bloodlusted"]);
  });
});

describe("Patience", () => {
  it("keeps waiting moves from a step that won't wait: Bloodlusted neither readies a reaction nor winds up", () => {
    const heroes = [gunman] as const;
    const kinds = (step: string) => {
      const brain = new Brain(new CountsBelief(heroes), new TemperamentTrack(STEPS, step), placeholder(heroes, new Rng(1)), heroes, new Rng(1));
      return new Set(brain.choose({ kind: "round", round: 1 })!.decision.ranked.map((s) => (s.option.move as { kind: string }).kind));
    };
    assert.deepEqual([...kinds("wrathful")].sort(), ["interrupt", "signature", "strike", "wind-up"]);
    assert.deepEqual([...kinds("bloodlusted")].sort(), ["signature", "strike"]);
  });
});
