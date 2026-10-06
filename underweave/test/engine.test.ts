import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CAST, GUARD, K, SHOOT, STRIKE, argmax } from "../src/engine/actions.ts";
import { CountsBelief } from "../src/engine/belief/counts.ts";
import { Rng, seedFor } from "../src/engine/rng.ts";
import { SUBCLASSES, mainAction, shapeOf } from "../src/engine/subclasses.ts";

const close = (a: number, b: number, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} vs ${b}`);
const ctx = { round: 1, named: false };

describe("subclasses", () => {
  it("every shape is a distribution over the five actions", () => {
    for (const [id, { shape }] of Object.entries(SUBCLASSES)) {
      assert.equal(shape.length, K, id);
      close(shape.reduce((a, b) => a + b, 0), 1);
    }
  });

  it("knows each subclass's main action", () => {
    assert.equal(mainAction("gunman"), SHOOT);
    assert.equal(mainAction("bulwark"), STRIKE);
    assert.equal(mainAction("hellbound"), CAST);
  });
});

describe("Rng", () => {
  it("repeats itself for the same seed", () => {
    const a = new Rng(42);
    const b = new Rng(42);
    for (let i = 0; i < 100; i++) assert.equal(a.next(), b.next());
  });

  it("draws in proportion to the weights", () => {
    const rng = new Rng(1);
    const counts = [0, 0, 0];
    for (let i = 0; i < 30000; i++) counts[rng.weighted([1, 2, 7])]! += 1;
    close(counts[0]! / 30000, 0.1, 0.01);
    close(counts[2]! / 30000, 0.7, 0.01);
  });

  it("derives different seeds for different paths", () => {
    assert.notEqual(seedFor(1, 0, 0), seedFor(1, 0, 1));
    assert.notEqual(seedFor(1, 0, 1), seedFor(1, 1, 0));
    assert.equal(seedFor(1, 2, 3), seedFor(1, 2, 3));
  });
});

describe("CountsBelief", () => {
  const hero = { id: "g", subclass: "gunman" } as const;

  it("starts at the subclass shape", () => {
    const belief = new CountsBelief([hero]);
    belief.forecast("g", ctx).forEach((p, i) => close(p, shapeOf("gunman")[i]!));
  });

  it("is a Dirichlet posterior when it never forgets", () => {
    const belief = new CountsBelief([hero], { memory: 1, patternPrior: 0, doubt: 0 });
    for (let i = 0; i < 6; i++) belief.observe("g", STRIKE, ctx);
    // prior 4 × shape, plus 6 strikes, out of 10
    close(belief.forecast("g", ctx)[STRIKE]!, (4 * 0.1 + 6) / 10, 1e-6);
  });

  it("always forecasts a distribution", () => {
    const belief = new CountsBelief([hero]);
    const rng = new Rng(3);
    for (let i = 0; i < 50; i++) {
      belief.observe("g", rng.int(K) as 0, ctx);
      close(belief.forecast("g", ctx).reduce((a, b) => a + b, 0), 1);
    }
  });

  it("moves toward what it sees", () => {
    const belief = new CountsBelief([hero]);
    const before = belief.forecast("g", ctx)[GUARD]!;
    belief.observe("g", GUARD, ctx);
    assert.ok(belief.forecast("g", ctx)[GUARD]! > before);
  });

  it("shifts its trust to the pattern model for an alternating player", () => {
    const belief = new CountsBelief([{ id: "b", subclass: "bulwark" }]);
    for (let i = 0; i < 10; i++) belief.observe("b", i % 2 ? GUARD : STRIKE, ctx);
    assert.ok(belief.weights("b")[1] > 0.8, `pattern weight ${belief.weights("b")[1]}`);
    assert.equal(argmax(belief.forecast("b", ctx)), STRIKE); // last was Guard, so Strike is next
  });

  it("rejects heroes it wasn't told about", () => {
    assert.throws(() => new CountsBelief([hero]).forecast("nobody", ctx));
  });
});
