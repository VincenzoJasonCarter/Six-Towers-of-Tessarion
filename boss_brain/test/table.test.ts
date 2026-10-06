import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CAST, GUARD, MEND, SHOOT, STRIKE } from "../src/engine/actions.ts";
import { append, DEFAULT_SETUP, newFight, parseLog, replay, undo, type FightLog, type TableSetup } from "../src/table/session.ts";

const setup: TableSetup = {
  ...DEFAULT_SETUP,
  heroes: [
    { name: "Kael", subclass: "gunman" },
    { name: "Mira", subclass: "verdant" },
  ],
  maxHp: 40,
  seed: 7,
};

const play = (log: FightLog, ...events: Parameters<typeof append>[1][]) => events.reduce((l, e) => append(l, e).log, log);

describe("the table session", () => {
  it("starts with a plan for round 1 and the first hero to act", () => {
    const s = replay(newFight(setup));
    assert.equal(s.round, 1);
    assert.equal(s.turn, 0);
    assert.equal(s.step, "ruthless");
    assert.ok(s.plan, "the boss has a move");
    assert.ok(s.plan!.ranked.length > 1 && s.plan!.ranked.filter((r) => r.chosen).length === 1);
    assert.equal(s.heroes.length, 2);
    for (const h of s.heroes) assert.ok(Math.abs(h.forecast.reduce((a, b) => a + b, 0) - 1) < 1e-9);
    assert.match(s.heroes[0]!.explanation, /defies when named/);
  });

  it("takes one tap per hero, then settles the round and plans the next", () => {
    const log = play(newFight(setup), { type: "action", action: SHOOT }, { type: "action", action: CAST });
    const s = replay(log);
    assert.equal(s.round, 2);
    assert.equal(s.turn, 0);
    assert.equal(s.history.length, 1);
    assert.equal(s.history[0]!.actions.get("Kael"), SHOOT);
    assert.ok(s.history[0]!.resolution);
  });

  it("replays the same log to the same fight, and undo is dropping the last event", () => {
    const events = [STRIKE, MEND, SHOOT, MEND, SHOOT, CAST].map((action) => ({ type: "action", action }) as const);
    const log = play(newFight(setup), ...events);
    assert.deepEqual(replay(log), replay(JSON.parse(JSON.stringify(log))));
    const back = replay(undo(log));
    assert.equal(back.round, 3);
    assert.equal(back.turn, 1);
    assert.deepEqual(back.history, replay(play(newFight(setup), ...events.slice(0, 5))).history);
  });

  it("lets the DM overrule the move before anyone acts, and not after", () => {
    const log = newFight(setup);
    const first = replay(log);
    const other = first.plan!.ranked.findIndex((r) => !r.chosen);
    const s = replay(append(log, { type: "overrule", option: other }).log);
    assert.equal(s.plan!.overruled, true);
    assert.equal(s.plan!.described, first.plan!.ranked[other]!.described);
    const acted = play(log, { type: "action", action: STRIKE });
    assert.throws(() => append(acted, { type: "overrule", option: other }));
  });

  it("enrages when the DM records the boss below half HP", () => {
    const log = play(newFight(setup), { type: "hp", hp: 18 }, { type: "action", action: GUARD }, { type: "action", action: GUARD });
    const s = replay(log);
    assert.equal(s.hp, 18);
    assert.equal(s.step, "wrathful");
    assert.deepEqual(s.shifts.map((x) => [x.round, x.to, x.reason]), [[2, "wrathful", "below half HP"]]);
  });

  it("lets the DM set the step by hand from the next round", () => {
    const log = play(newFight(setup), { type: "step", step: "curious" });
    assert.equal(replay(log).step, "ruthless", "this round's move is already made");
    const next = play(log, { type: "action", action: STRIKE }, { type: "action", action: STRIKE });
    assert.equal(replay(next).step, "curious");
  });

  it("refuses what can't happen, and checks imported logs", () => {
    assert.throws(() => newFight({ ...setup, heroes: [] }));
    assert.throws(() => newFight({ ...setup, heroes: [setup.heroes[0]!, setup.heroes[0]!] }));
    assert.throws(() => parseLog("{}"));
    const log = play(newFight(setup), { type: "action", action: STRIKE });
    assert.deepEqual(parseLog(JSON.stringify(log)), log);
  });
});
