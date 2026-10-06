import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CAST, GUARD, K, SHOOT, STRIKE, type Action } from "../src/engine/actions.ts";
import { Rng } from "../src/engine/rng.ts";
import { mainAction } from "../src/engine/subclasses.ts";
import {
  ADAPTIVE,
  ALTERNATOR,
  CONTRARIAN,
  HABITUAL,
  RANDOM,
  SECOND_GUESSER,
  STYLES,
  SWITCHER,
  TELL_READER,
  styleById,
  type PlayerView,
  type Told,
} from "../src/harness/players.ts";

const view = (over: Partial<PlayerView> = {}): PlayerView => ({ round: 1, named: false, warned: false, history: [], told: [], ...over });

function frequencies(act: () => Action, n = 20000): number[] {
  const counts = new Array<number>(K).fill(0);
  for (let i = 0; i < n; i++) counts[act()]! += 1;
  return counts.map((c) => c / n);
}

describe("synthetic players", () => {
  it("have unique ids and can be looked up", () => {
    assert.equal(new Set(STYLES.map((s) => s.id)).size, STYLES.length);
    for (const s of STYLES) assert.equal(styleById(s.id), s);
    assert.throws(() => styleById("nope"));
  });

  it("Habitual plays its main action 9 times in 13", () => {
    const player = HABITUAL.make("gunman", new Rng(1));
    const f = frequencies(() => player.act(view()));
    assert.ok(Math.abs(f[SHOOT]! - 9 / 13) < 0.01, String(f[SHOOT]));
  });

  it("Random is uniform", () => {
    const player = RANDOM.make("gunman", new Rng(1));
    for (const p of frequencies(() => player.act(view()))) assert.ok(Math.abs(p - 0.2) < 0.01);
  });

  it("Alternator cycles Strike and Guard", () => {
    const player = ALTERNATOR.make("bulwark", new Rng(1));
    const history: Action[] = [];
    for (let i = 0; i < 6; i++) history.push(player.act(view({ history })));
    assert.deepEqual(history, [STRIKE, GUARD, STRIKE, GUARD, STRIKE, GUARD]);
  });

  it("Switcher shoots four times, then strikes", () => {
    const player = SWITCHER.make("gunman", new Rng(1));
    const history: Action[] = [];
    for (let i = 0; i < 6; i++) history.push(player.act(view({ history })));
    assert.deepEqual(history, [SHOOT, SHOOT, SHOOT, SHOOT, STRIKE, STRIKE]);
  });

  it("Contrarian never plays its main action when named", () => {
    const player = CONTRARIAN.make("hellbound", new Rng(1));
    const f = frequencies(() => player.act(view({ named: true })), 5000);
    assert.equal(f[mainAction("hellbound")], 0);
    const unnamed = frequencies(() => player.act(view()), 5000);
    assert.ok(unnamed[CAST]! > 0.6);
  });

  it("Second-guesser avoids what it has done most when named", () => {
    const player = SECOND_GUESSER.make("gunman", new Rng(1));
    const history = [STRIKE, STRIKE, SHOOT] as Action[];
    const f = frequencies(() => player.act(view({ named: true, history })), 5000);
    assert.equal(f[STRIKE], 0);
    assert.ok(f[SHOOT]! > 0.5, "it still shoots, since it has struck more");
  });

  it("Adaptive shies away from an action a prophecy caught", () => {
    // Count Shoot on the turn right after being caught, over many fresh players.
    let shots = 0;
    const n = 4000;
    const caught: Told[] = [{ round: 1, action: SHOOT, fulfilled: true }];
    for (let i = 0; i < n; i++) {
      const player = ADAPTIVE.make("gunman", new Rng(i));
      if (player.act(view({ told: caught })) === SHOOT) shots += 1;
    }
    // Shoot is 0.70 of the shape; burned to ×0.3 it becomes 0.21 / 0.51 ≈ 0.41.
    assert.ok(Math.abs(shots / n - 0.21 / 0.51) < 0.03, String(shots / n));
  });

  it("Tell-reader steers away from what the boss bet on, named or not, hit or miss", () => {
    const player = TELL_READER.make("gunman", new Rng(1));
    const free = frequencies(() => player.act(view()), 5000);
    assert.ok(Math.abs(free[SHOOT]! - 0.7) < 0.03, "with no bets seen, it plays by the book");
    const told: Told[] = [
      { round: 1, action: SHOOT, fulfilled: true },
      { round: 2, action: SHOOT, fulfilled: false },
    ];
    const f = frequencies(() => player.act(view({ told })), 5000);
    // Shoot is 0.70 of the shape; two bets make it ×0.25: 0.175 / 0.475 ≈ 0.37.
    assert.ok(Math.abs(f[SHOOT]! - 0.175 / 0.475) < 0.03, String(f[SHOOT]));
  });
});
