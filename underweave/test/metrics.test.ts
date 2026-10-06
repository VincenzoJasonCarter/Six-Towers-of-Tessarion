import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CAST, SHOOT, STRIKE } from "../src/engine/actions.ts";
import { ForecastScore, ProphecyScore } from "../src/harness/metrics.ts";

const close = (a: number, b: number, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} vs ${b}`);
const UNIFORM = [0.2, 0.2, 0.2, 0.2, 0.2];

describe("ForecastScore", () => {
  it("scores a blind guess at the known baselines", () => {
    const score = new ForecastScore();
    score.add(UNIFORM, CAST, 1);
    const s = score.summary();
    close(s.logLoss, Math.log(5));
    close(s.brier, 0.8);
  });

  it("counts a hit when the most likely action happens", () => {
    const score = new ForecastScore();
    score.add([0.6, 0.1, 0.1, 0.1, 0.1], STRIKE, 1);
    score.add([0.6, 0.1, 0.1, 0.1, 0.1], SHOOT, 5);
    const s = score.summary();
    close(s.accuracy, 0.5);
    assert.deepEqual(s.accuracyByPhase, [1, 0, null]);
  });

  it("finds no calibration error when confidence matches outcomes", () => {
    const score = new ForecastScore();
    // 60% sure, right 3 times in 5
    for (const a of [STRIKE, STRIKE, STRIKE, SHOOT, CAST]) score.add([0.6, 0.1, 0.1, 0.1, 0.1], a, 1);
    close(score.summary().calibrationError, 0);
  });

  it("measures overconfidence", () => {
    const score = new ForecastScore();
    // 90% sure, right half the time
    score.add([0.9, 0.025, 0.025, 0.025, 0.025], STRIKE, 1);
    score.add([0.9, 0.025, 0.025, 0.025, 0.025], SHOOT, 1);
    close(score.summary().calibrationError, 0.4);
  });
});

describe("ProphecyScore", () => {
  it("averages over fights, and over rewinds only where they happened", () => {
    const score = new ProphecyScore();
    const p = (fulfilled: boolean) => ({ round: 1, hero: "h", action: STRIKE, p: 0.5, fulfilled });
    score.addFight({ turns: [], prophecies: [p(true), p(true), p(true), p(false)], charges: 3, firstRewindRound: 4 });
    score.addFight({ turns: [], prophecies: [p(false), p(false)], charges: 0, firstRewindRound: null });
    const s = score.summary();
    close(s.spokenPerFight, 3);
    close(s.hitRate, 0.5);
    close(s.chargesPerFight, 1.5);
    close(s.rewindReached, 0.5);
    assert.equal(s.firstRewindRound, 4);
  });
});
