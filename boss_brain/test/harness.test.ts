import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CountsBelief, countsBelief } from "../src/engine/belief/counts.ts";
import { Rng } from "../src/engine/rng.ts";
import { chooseProphecies, runFight, spikeProphet, SPIKE_PROPHET } from "../src/harness/fight.ts";
import { ALTERNATOR, HABITUAL, RANDOM, STYLES, SWITCHER, BY_THE_BOOK, type Style } from "../src/harness/players.ts";
import { runSuite } from "../src/harness/suite.ts";
import type { SubclassId } from "../src/engine/subclasses.ts";

const SPIKE_PARTY: SubclassId[] = ["gunman", "bulwark", "verdant", "hellbound"];

const suite = (styles: readonly Style[], trials: number, seed = 1) =>
  runSuite({ seed, trials, rounds: 10, party: SPIKE_PARTY, styles, belief: countsBelief(), policy: SPIKE_PROPHET });

describe("chooseProphecies", () => {
  it("names the hero read most clearly, and stays silent below the threshold", () => {
    const heroes = [
      { id: "v", subclass: "verdant" },
      { id: "a", subclass: "crystal_archer" },
    ] as const;
    const belief = new CountsBelief(heroes);
    assert.deepEqual(
      chooseProphecies(heroes, belief, 1, SPIKE_PROPHET).map((p) => p.hero),
      ["a"],
    );
    assert.deepEqual(chooseProphecies(heroes, belief, 1, { ...SPIKE_PROPHET, threshold: 0.9 }), []);
    assert.equal(chooseProphecies(heroes, belief, 1, { ...SPIKE_PROPHET, perRound: 2 }).length, 2);
  });
});

describe("runFight", () => {
  it("gives every hero one turn a round and tells them their prophecies", () => {
    const heroes = [
      { id: "g", subclass: "gunman" },
      { id: "b", subclass: "bulwark" },
    ] as const;
    const players = new Map(heroes.map((h, i) => [h.id, HABITUAL.make(h.subclass, new Rng(i))]));
    const fight = runFight({ heroes, players, belief: new CountsBelief(heroes), rounds: 5, prophet: spikeProphet(SPIKE_PROPHET), rewindCost: 3 });
    assert.equal(fight.turns.length, 10);
    assert.equal(fight.prophecies.length, 5);
    assert.equal(fight.charges, fight.prophecies.filter((p) => p.fulfilled).length);
    for (const t of fight.turns) {
      assert.equal(t.named, fight.prophecies.some((p) => p.round === t.round && p.hero === t.hero));
    }
  });

  it("reveals every prophecy to the belief once its round is over", () => {
    const heroes = [{ id: "g", subclass: "gunman" }] as const;
    const players = new Map(heroes.map((h) => [h.id, HABITUAL.make(h.subclass, new Rng(1))]));
    const inner = new CountsBelief(heroes);
    const revealed: { hero: string; action: number; fulfilled: boolean }[] = [];
    const belief = {
      id: "spy",
      forecast: inner.forecast.bind(inner),
      observe: inner.observe.bind(inner),
      reveal: (hero: string, bet: { action: number; fulfilled: boolean }) => void revealed.push({ hero, ...bet }),
    };
    const fight = runFight({ heroes, players, belief, rounds: 6, prophet: spikeProphet(SPIKE_PROPHET), rewindCost: 3 });
    assert.deepEqual(
      revealed,
      fight.prophecies.map((p) => ({ hero: p.hero, action: p.action, fulfilled: p.fulfilled })),
    );
  });
});

describe("runSuite", () => {
  it("is reproducible from its seed", () => {
    assert.deepEqual(suite(STYLES, 20), suite(STYLES, 20));
    assert.notDeepEqual(suite([RANDOM], 50, 1), suite([RANDOM], 50, 2));
  });

  it("gives a style the same numbers whichever other styles run", () => {
    const alone = suite([RANDOM], 50).styles[0];
    const among = suite([HABITUAL, RANDOM], 50).styles[1];
    assert.deepEqual(alone, among);
  });

  // The spike's results (DESIGN.md, "Spike results"), at large sample sizes
  // so the bounds can be tight: [hit rate, charges / fight, share of fights
  // reaching a rewind, average round of the first rewind].
  it("reproduces the spike", () => {
    const expected: [Style, number, number, number, number][] = [
      [HABITUAL, 0.69, 6.9, 1.0, 4.3],
      [BY_THE_BOOK, 0.7, 7.0, 1.0, 4.3],
      [RANDOM, 0.2, 1.9, 0.31, 7.3],
      [ALTERNATOR, 0.6, 6.0, 1.0, 7.0],
      [SWITCHER, 0.7, 7.0, 1.0, 3.0],
    ];
    const result = suite(expected.map((e) => e[0]), 3000);
    expected.forEach(([style, hit, charges, reached, round], i) => {
      const p = result.styles[i]!.prophecy;
      const near = (got: number, want: number, eps: number, what: string) =>
        assert.ok(Math.abs(got - want) <= eps, `${style.name} ${what}: ${got.toFixed(3)}, spike ${want}`);
      near(p.hitRate, hit, 0.02, "hit rate");
      near(p.chargesPerFight, charges, 0.2, "charges per fight");
      near(p.rewindReached, reached, 0.03, "fights reaching a rewind");
      near(p.firstRewindRound!, round, 0.25, "round of first rewind");
    });
  });
});
