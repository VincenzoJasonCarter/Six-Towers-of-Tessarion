import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import { GUARD, MEND, SHOOT, STRIKE, type Action } from "../src/engine/actions.ts";
import { CountsBelief, countsBelief } from "../src/engine/belief/counts.ts";
import { Brain } from "../src/engine/brain.ts";
import { STEPS, stepById } from "../src/engine/decision/temperament.ts";
import type { Module } from "../src/engine/module.ts";
import { Rng } from "../src/engine/rng.ts";
import { runBetSuite } from "../src/harness/bettor.ts";
import { runBout, runModuleSuite } from "../src/harness/bout.ts";
import { heeding, HABITUAL, RANDOM, STYLES, type Player, type PlayerView } from "../src/harness/players.ts";
import { bet, punish, spendOrHold, telegraph } from "../src/modules/reference/index.ts";
import { FIGHT_VALUE } from "../src/modules/reference/common.ts";
import { PRESS } from "../src/modules/reference/punish.ts";
import { BUDGET } from "../src/modules/reference/spend.ts";

const here = dirname(fileURLToPath(import.meta.url));
const gunman = { id: "g", subclass: "gunman" } as const;
const view = (over: Partial<PlayerView> = {}): PlayerView => ({ round: 1, named: false, warned: false, history: [], told: [], ...over });
const always = (action: Action): Player => ({ act: () => action });
const ruthless = stepById("ruthless");
const brainOf = <M>(module: Module<M>, step = ruthless) => new Brain(new CountsBelief([gunman]), step, module, [gunman], new Rng(1));
const actions = (a: Action) => new Map([["g", a]]);

describe("the engine", () => {
  it("imports nothing from outside src/engine (M4 interface target 1)", () => {
    const engine = resolve(here, "../src/engine");
    const files = (readdirSync(engine, { recursive: true }) as string[]).filter((f) => f.endsWith(".ts"));
    for (const f of files) {
      const path = join(engine, f);
      for (const [, spec] of readFileSync(path, "utf8").matchAll(/from "(\.[^"]+)"/g)) {
        const target = relative(engine, resolve(dirname(path), spec!));
        assert.ok(!target.startsWith(".."), `${f} imports ${spec}`);
      }
    }
  });
});

describe("heeding", () => {
  it("makes a warned player Guard half the time; Random ignores warnings", () => {
    const player = heeding(HABITUAL, always(SHOOT), new Rng(1));
    let guards = 0;
    for (let i = 0; i < 4000; i++) if (player.act(view({ warned: true })) === GUARD) guards += 1;
    assert.ok(Math.abs(guards / 4000 - 0.5) < 0.03, String(guards / 4000));
    assert.equal(player.act(view()), SHOOT);
    const random = always(SHOOT);
    assert.equal(heeding(RANDOM, random, new Rng(1)), random);
  });
});

describe("runBout", () => {
  it("asks the module after every turn, and settles a turn's move at once", () => {
    const seen: string[] = [];
    const module: Module<string> = {
      id: "probe",
      options: (moment) =>
        moment.kind === "turn" ? [{ move: `react ${moment.round}`, outcomes: [{ p: 1, utility: { tempo: 1 } }] }] : [],
      announce: () => ({ named: [], warned: [], text: "" }),
      resolve: (move, moment) => {
        seen.push(`${move} ${moment.kind}`);
        return { kind: "react", utility: { tempo: 1 }, bets: [] };
      },
    };
    const bout = runBout({ heroes: [gunman], players: new Map([["g", always(STRIKE)]]), brain: brainOf(module), rounds: 2 });
    assert.deepEqual(seen, ["react 1 turn", "react 2 turn"]);
    assert.equal(bout.settled.length, 2);
  });
});

describe("Bet", () => {
  it("is M3's bettor on the module interface: the same draws, the same numbers", () => {
    const base = { seed: 5, trials: 15, rounds: 10, party: ["gunman", "bulwark"] as const, styles: STYLES, belief: countsBelief() };
    for (const step of STEPS) {
      const before = runBetSuite({ ...base, step });
      const after = runModuleSuite({ ...base, step, module: bet as never });
      before.styles.forEach((s, i) => {
        const { fights: _, ...want } = s;
        const { fights: __, ...got } = after.styles[i]!.bets;
        assert.deepEqual({ ...got, style: s.style, name: s.name }, { ...want }, `${step.id}, ${s.style}`);
      });
    }
  });
});

describe("Punish", () => {
  it("cuts a read action by its fight value, and presses for a sure half", () => {
    const m = punish([gunman], new Rng(1));
    const round = { kind: "round", round: 1 } as const;
    const cut = m.resolve({ kind: "cut", hero: "g", action: MEND }, round, { actions: actions(MEND), events: [] });
    assert.equal(cut.utility.lethal, FIGHT_VALUE[MEND]);
    assert.deepEqual(cut.bets, [{ hero: "g", action: MEND, fulfilled: true }]);
    const press = m.resolve({ kind: "press", hero: "g" }, round, { actions: actions(MEND), events: [] });
    assert.equal(press.utility.lethal, PRESS);
    assert.deepEqual(press.bets, []);
  });
});

describe("Spend or hold", () => {
  it("values holding less as the fight runs out, and stops when the charges are spent", () => {
    const m = spendOrHold([gunman], new Rng(1));
    const ctx = { heroes: [gunman], view: new CountsBelief([gunman]), belief: new CountsBelief([gunman]), step: ruthless };
    const hold = (round: number) => m.options({ kind: "round", round }, ctx).at(-1)!.outcomes[0]!.utility.tempo;
    assert.deepEqual([hold(1), hold(5), hold(10)], [0.9, 0.5, 0]);
    assert.equal(m.options({ kind: "round", round: 1 }, ctx).some((o) => o.about), false, "a spend is no probe");
    for (let round = 1; round <= BUDGET; round++) {
      const spent = m.resolve({ kind: "spend", hero: "g", action: MEND }, { kind: "round", round }, { actions: actions(STRIKE), events: [] });
      assert.equal(spent.utility.lethal, 0);
      assert.deepEqual(spent.detail, { aimedValue: FIGHT_VALUE[MEND], round });
    }
    assert.deepEqual(m.options({ kind: "round", round: 4 }, ctx), []);
  });
});

describe("Telegraph", () => {
  it("warns its target, and learns how often warned heroes heed it", () => {
    const m = telegraph([gunman], new Rng(1));
    const windUp = { kind: "wind-up", hero: "g" } as const;
    assert.deepEqual(m.announce(windUp, ruthless).warned, ["g"]);
    const ctx = { heroes: [gunman], view: new CountsBelief([gunman]), belief: new CountsBelief([gunman]), step: ruthless };
    const lands = () => m.options({ kind: "round", round: 1 }, ctx)[0]!.outcomes[0]!.p;
    const guardsAnyway = ctx.view.forecast("g", { round: 1, named: false })[GUARD]!;
    assert.ok(Math.abs(lands() - (1 - (0.5 + 0.5 * guardsAnyway))) < 1e-12, "half heed, the rest guard as usual");
    const r = m.resolve(windUp, { kind: "round", round: 1 }, { actions: actions(GUARD), events: [] });
    assert.equal(r.utility.lethal, 0);
    assert.equal(r.utility.show, 1);
    assert.ok(lands() < 0.5, "after a guard, it expects fewer wind-ups to land");
  });
});
