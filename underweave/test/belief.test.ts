import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CAST, GUARD, K, MEND, SHOOT, STRIKE, argmax, type Action } from "../src/engine/actions.ts";
import { ArchetypesBelief } from "../src/engine/belief/archetypes.ts";
import { CountsBelief } from "../src/engine/belief/counts.ts";
import { DefianceBelief } from "../src/engine/belief/defiance.ts";
import { dodge } from "../src/engine/belief/dodge.ts";
import { EnsembleBelief } from "../src/engine/belief/ensemble.ts";
import type { BeliefModel } from "../src/engine/belief/types.ts";
import { shapeOf } from "../src/engine/subclasses.ts";
import { gridA, gridAD, gridB, gridC, product } from "../src/harness/candidates.ts";

const close = (a: number, b: number, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} vs ${b}`);
const sum = (xs: readonly number[]) => xs.reduce((a, b) => a + b, 0);
const free = { round: 1, named: false };
const named = { round: 1, named: true };
const gunman = { id: "g", subclass: "gunman" } as const;

/** A fixed forecast that never learns, for testing the layers around it. */
const fixed = (d: number[]): BeliefModel & { seen: Action[] } => {
  const seen: Action[] = [];
  return { id: "fixed", seen, forecast: () => d, observe: (_h, a) => void seen.push(a) };
};

describe("dodge", () => {
  it("moves the usual action's weight onto the others, keeping a little", () => {
    const d = dodge([0.7, 0.1, 0.1, 0.05, 0.05]);
    close(sum(d), 1);
    close(d[STRIKE]!, 0.02);
    close(d[SHOOT]! / d[MEND]!, 2);
  });
});

describe("DefianceBelief", () => {
  it("passes unnamed turns straight through", () => {
    const usual = [0.6, 0.1, 0.1, 0.1, 0.1];
    const belief = new DefianceBelief(fixed(usual), [gunman]);
    assert.deepEqual(belief.forecast("g", free), usual);
  });

  it("learns that a player dodges, and then foretells the dodge", () => {
    const belief = new DefianceBelief(fixed([0.6, 0.1, 0.1, 0.1, 0.1]), [gunman]);
    const before = belief.defiance("g");
    // Guard is 10% likely even for a player who complies, so each dodge is only partial evidence.
    for (let i = 0; i < 8; i++) belief.observe("g", GUARD, named);
    assert.ok(belief.defiance("g") > 0.4 && belief.defiance("g") > before + 0.15, String(belief.defiance("g")));
    assert.ok(belief.forecast("g", named)[STRIKE]! < 0.4, "named, Strike is much less likely than its usual 60%");
    close(sum(belief.forecast("g", named)), 1);
    // It keeps learning, but it can only learn *that* they dodge, not *where*
    // to: the dodge is spread over the other actions, so Guard never stands out.
    const after8 = belief.forecast("g", named)[STRIKE]!;
    for (let i = 0; i < 20; i++) belief.observe("g", GUARD, named);
    const f = belief.forecast("g", named);
    assert.ok(f[STRIKE]! < after8);
    close(f[GUARD]!, f[SHOOT]!);
  });

  it("learns that a player complies", () => {
    const belief = new DefianceBelief(fixed([0.6, 0.1, 0.1, 0.1, 0.1]), [gunman]);
    for (let i = 0; i < 8; i++) belief.observe("g", STRIKE, named);
    assert.ok(belief.defiance("g") < 0.1, String(belief.defiance("g")));
  });

  it("can keep named turns away from the inner model", () => {
    const inner = fixed([0.6, 0.1, 0.1, 0.1, 0.1]);
    const belief = new DefianceBelief(inner, [gunman], { teachInner: "unnamed" });
    belief.observe("g", GUARD, named);
    belief.observe("g", CAST, free);
    assert.deepEqual(inner.seen, [CAST]);
  });
});

describe("ArchetypesBelief", () => {
  it("forecasts a distribution leaning on the subclass at first", () => {
    const belief = new ArchetypesBelief([gunman]);
    const f = belief.forecast("g", free);
    close(sum(f), 1);
    assert.equal(argmax(f), argmax(shapeOf("gunman")));
  });

  it("works out that a Gunman who always casts favours Cast", () => {
    const belief = new ArchetypesBelief([gunman]);
    for (let i = 0; i < 6; i++) belief.observe("g", CAST, free);
    assert.equal(belief.posterior("g")[0]!.habit, "favours-cast");
    assert.equal(argmax(belief.forecast("g", free)), CAST);
    assert.match(belief.explain("g"), /^\d+% favours Cast, \d+% defies when named$/);
  });

  it("spots a defier and foretells the dodge", () => {
    const belief = new ArchetypesBelief([gunman]);
    for (let i = 0; i < 4; i++) {
      belief.observe("g", SHOOT, free);
      belief.observe("g", GUARD, named);
    }
    assert.ok(belief.defiance("g") > 0.6, String(belief.defiance("g"))); // from a prior of 0.25
    assert.equal(argmax(belief.forecast("g", free)), SHOOT);
    assert.notEqual(argmax(belief.forecast("g", named)), SHOOT);
  });

  it("never calls anything impossible", () => {
    const belief = new ArchetypesBelief([gunman]);
    for (let i = 0; i < 30; i++) belief.observe("g", SHOOT, free);
    for (const p of belief.forecast("g", named)) assert.ok(p >= 0.01 / K);
  });

  it("keeps a proper posterior", () => {
    const belief = new ArchetypesBelief([gunman]);
    for (const a of [SHOOT, STRIKE, GUARD, SHOOT] as Action[]) belief.observe("g", a, free);
    close(sum(belief.posterior("g").map((h) => h.p)), 1);
  });
});

describe("EnsembleBelief", () => {
  it("leans on whichever member reads the player better", () => {
    const good = fixed([0.8, 0.05, 0.05, 0.05, 0.05]);
    const bad = fixed([0.05, 0.8, 0.05, 0.05, 0.05]);
    const belief = new EnsembleBelief([good, bad], [gunman]);
    for (let i = 0; i < 5; i++) belief.observe("g", STRIKE, free);
    assert.ok(belief.weights("g")[0]! > 0.99);
    assert.equal(argmax(belief.forecast("g", free)), STRIKE);
    assert.equal(good.seen.length, 5, "members keep learning");
  });

  it("with one member is that member", () => {
    const counts = new CountsBelief([gunman]);
    const belief = new EnsembleBelief([counts], [gunman]);
    belief.observe("g", CAST, free);
    assert.deepEqual(belief.forecast("g", free), counts.forecast("g"));
  });
});

describe("M2 grids", () => {
  it("cover every combination", () => {
    assert.equal(product({ x: [1, 2], y: ["a", "b", "c"] }).length, 6);
    assert.equal(gridA().length, 45);
    assert.equal(gridAD({}).length, 20);
    assert.equal(gridB().length, 100);
    assert.equal(gridC({ counts: {}, defiance: {} }, {}).length, 3);
  });
});
