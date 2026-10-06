/**
 * M4: the module interface and the reference modules (DESIGN.md 8, "M4
 * protocol").
 *
 * Usage, from boss_brain/:
 *
 *     npm run compare:m4              # the full protocol, about half an hour
 *     npm run compare:m4 -- --quick   # a smoke test with few fights; its verdict means nothing
 *
 * Checks the interface targets, runs the M3 steps (with the placeholder
 * `lethal` and `show` weights) through Punish, Spend or hold and Telegraph on
 * the tuning data, and stops there if a value target fails: the protocol's
 * fix is a written change to those weights before the held-out run. If they
 * all hold, evaluates every module on held-out data, checks Bet against M3's
 * report, and writes reports/m4-modules.md and reports/m4-modules.json.
 */
import { readdirSync, readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { STEPS, type Temperament } from "../engine/decision/temperament.ts";
import { SUBCLASSES, type SubclassId } from "../engine/subclasses.ts";
import { REFERENCE_MODULES } from "../modules/reference/index.ts";
import { runModuleSuite, type ModuleSuiteResult } from "./bout.ts";
import { makeC, TUNED_C } from "./candidates.ts";
import { ADAPTIVE, BY_THE_BOOK, HABITUAL, STYLES } from "./players.ts";
import { num, pct, table } from "./report.ts";

const SPIKE_PARTY: SubclassId[] = ["gunman", "bulwark", "verdant", "hellbound"];
const SECOND_PARTY: SubclassId[] = ["warbound", "sanguine_aegis", "crystal_archer", "aether"];
const ORDINARY = ["habitual", "by-the-book", "adaptive"];
const LETHAL_MODULES = ["punish", "spend-or-hold", "telegraph"];
/** The modules whose moves are reads, where the bell of reading applies (target 1, as amended). */
const READING_MODULES = ["punish", "spend-or-hold"];
/** Target 4, as amended: the cold boss and the enraged ones don't stop to wind up. */
const WIND_UP_CEILING = 0.1;

const { values: args } = parseArgs({ options: { quick: { type: "boolean", default: false } } });
const TUNE = { seed: 1, trials: args.quick ? 30 : 300, party: SPIKE_PARTY, styles: [HABITUAL, BY_THE_BOOK, ADAPTIVE] };
const EVAL = { seed: 2, trials: args.quick ? 60 : 1000, parties: [SPIKE_PARTY, SECOND_PARTY] };
const ROUNDS = 10;
const BELIEF = makeC(TUNED_C);

const moduleById = (id: string) => REFERENCE_MODULES.find((m) => m.id === id)!;

/** One module under one step: the per-style results on each party run. */
interface Cell {
  readonly module: string;
  readonly step: string;
  readonly byParty: readonly ModuleSuiteResult[];
}

function run(module: string, step: Temperament, seed: number, trials: number, parties: readonly (readonly SubclassId[])[], styles = STYLES): Cell {
  const byParty = parties.map((party) =>
    runModuleSuite({ seed, trials, rounds: ROUNDS, party, styles, belief: BELIEF, step, module: moduleById(module).make }),
  );
  return { module, step: step.id, byParty };
}

/** A per-style number, averaged over the given styles and then over the parties. */
function mean(cell: Cell, styles: readonly string[], f: (s: ModuleSuiteResult["styles"][number]) => number): number {
  const perParty = cell.byParty.map((r) => {
    const picked = r.styles.filter((s) => styles.includes(s.style));
    return picked.reduce((sum, s) => sum + f(s), 0) / picked.length;
  });
  return perParty.reduce((a, b) => a + b, 0) / perParty.length;
}

interface Measures {
  readonly lethal: number;
  readonly spends: number;
  readonly aimed: number;
  /** The mean round of a spend. */
  readonly spendRound: number;
  readonly windUps: number;
}

function measures(cell: Cell): Measures {
  const spends = mean(cell, ORDINARY, (s) => s.kinds["spend"] ?? 0);
  return {
    lethal: mean(cell, ORDINARY, (s) => s.perFight.lethal),
    spends,
    aimed: spends ? mean(cell, ORDINARY, (s) => s.detail["aimedValue"] ?? 0) / spends : 0,
    spendRound: spends ? mean(cell, ORDINARY, (s) => s.detail["round"] ?? 0) / spends : 0,
    windUps: mean(cell, ORDINARY, (s) => (s.kinds["wind-up"] ?? 0) / ROUNDS),
  };
}

interface Check {
  readonly target: string;
  readonly passed: boolean;
  readonly detail: string;
}

const ids = STEPS.map((s) => s.id);
const names = Object.fromEntries(STEPS.map((s) => [s.id, s.name]));

function valueChecks(cells: readonly Cell[]): Check[] {
  const m = (module: string, step: string) => measures(cells.find((c) => c.module === module && c.step === step)!);
  const series = (module: string, f: (x: Measures) => number) => ids.map((id) => f(m(module, id)));
  // As amended after the tuning check: up to Ruthless, then Ruthless above both hot steps (a plateau, M3 point 4).
  const bell = (xs: readonly number[]) => xs[0]! < xs[1]! && xs[1]! < xs[2]! && xs[2]! > xs[3]! && xs[2]! > xs[4]!;
  const argmax = (xs: readonly number[]) => xs.indexOf(Math.max(...xs));
  const argmin = (xs: readonly number[]) => xs.indexOf(Math.min(...xs));
  const show = (xs: readonly number[], f: (x: number) => string) => xs.map(f).join(" → ");

  const checks: Check[] = [];
  for (const module of READING_MODULES) {
    const lethal = series(module, (x) => x.lethal);
    checks.push({ target: `1. Bell carries over: ${moduleById(module).name}`, passed: bell(lethal), detail: show(lethal, (x) => num(x, 2)) });
  }
  for (const module of LETHAL_MODULES) {
    const lethal = series(module, (x) => x.lethal);
    checks.push({
      target: `2. Rage is frightening: ${moduleById(module).name}`,
      passed: lethal[4]! > lethal[0]!,
      detail: `Bloodlusted ${num(lethal[4]!, 2)} against Curious ${num(lethal[0]!, 2)}`,
    });
  }
  const spendRound = series("spend-or-hold", (x) => x.spendRound);
  const aimed = series("spend-or-hold", (x) => x.aimed);
  const yieldPerSpend = series("spend-or-hold", (x) => (x.spends ? x.lethal / x.spends : 0));
  checks.push({
    target: "3. Patience: Bloodlusted spends earliest",
    passed: argmin(spendRound) === 4,
    detail:
      `mean round of a spend ${show(spendRound, (x) => num(x, 1))} ` +
      `(reported, not targets: aimed value ${show(aimed, (x) => num(x, 2))}; \`lethal\` per spend ${show(yieldPerSpend, (x) => num(x, 2))})`,
  });
  const windUps = series("telegraph", (x) => x.windUps);
  checks.push({
    target: `4. Wind-ups: highest at Curious, under ${pct(WIND_UP_CEILING)} from Ruthless on`,
    passed: argmax(windUps) === 0 && windUps.slice(2).every((x) => x < WIND_UP_CEILING),
    detail: show(windUps, pct),
  });
  return checks;
}

/** Interface target 1: nothing in src/engine imports from outside it. */
function engineIsClean(): Check {
  const engine = resolve(dirname(fileURLToPath(import.meta.url)), "../engine");
  const bad: string[] = [];
  for (const f of (readdirSync(engine, { recursive: true }) as string[]).filter((x) => x.endsWith(".ts"))) {
    const path = join(engine, f);
    for (const [, spec] of readFileSync(path, "utf8").matchAll(/from "(\.[^"]+)"/g)) {
      if (relative(engine, resolve(dirname(path), spec!)).startsWith("..")) bad.push(`${f} → ${spec}`);
    }
  }
  return {
    target: "1. The engine imports no module; all four run through one fight loop",
    passed: bad.length === 0,
    detail: bad.length ? bad.join(", ") : "no import leaves src/engine; Bet, Punish, Spend or hold and Telegraph all run through runBout",
  };
}

/** Interface target 3: Bet reproduces M3's held-out numbers exactly. */
function betReproducesM3(cells: readonly Cell[]): Check {
  const m3 = JSON.parse(readFileSync(new URL("../../reports/m3-temperament.json", import.meta.url), "utf8"));
  let compared = 0;
  const differ: string[] = [];
  for (const r of m3.results) {
    const cell = cells.find((c) => c.module === "bet" && c.step === r.id)!;
    r.byParty.forEach((party: { styles: { style: string; success: number; fixation: number; predictability: number; betsPerFight: number }[] }, pi: number) => {
      for (const want of party.styles) {
        const got = cell.byParty[pi]!.styles.find((s) => s.style === want.style)!.bets;
        compared += 1;
        if (got.success !== want.success || got.fixation !== want.fixation || got.predictability !== want.predictability || got.betsPerFight !== want.betsPerFight) {
          differ.push(`${r.id}/${want.style}`);
        }
      }
    });
  }
  return {
    target: "3. Bet reproduces M3's held-out numbers exactly",
    passed: differ.length === 0,
    detail: differ.length ? `differs on ${differ.join(", ")}` : `identical on all ${compared} (step, party, style) cells`,
  };
}

const checkTable = (checks: readonly Check[]) =>
  table(["Target", "Passed", "Detail"], checks.map((c) => [c.target, c.passed ? "yes" : "**no**", c.detail]), 3);

function moduleTable(cells: readonly Cell[], module: string): string {
  const rows = ids.map((id) => {
    const cell = cells.find((c) => c.module === module && c.step === id)!;
    const x = measures(cell);
    const per = (styles: readonly string[]) => num(mean(cell, styles, (s) => s.perFight.lethal), 2);
    const kinds = new Set(cell.byParty.flatMap((r) => r.styles.flatMap((s) => Object.keys(s.kinds))));
    const mix = [...kinds].sort().map((k) => `${k} ${num(mean(cell, ORDINARY, (s) => s.kinds[k] ?? 0), 1)}`).join(", ");
    return [
      names[id]!,
      `**${num(x.lethal, 2)}**`,
      per(["random"]),
      per(["contrarian", "second-guesser"]),
      per(["tell-reader"]),
      num(mean(cell, ORDINARY, (s) => s.perFight.tempo), 2),
      num(mean(cell, ORDINARY, (s) => s.perFight.show), 2),
      mean(cell, ORDINARY, (s) => s.bets.betsPerFight) > 0 ? pct(mean(cell, ORDINARY, (s) => s.bets.success)) : "–",
      mix,
    ];
  });
  return table(["Step", "`lethal` / fight", "vs Random", "vs Defiers", "vs Tell-reader", "`tempo` / fight", "`show` / fight", "Read success", "Moves / fight (ordinary)"], rows, 1);
}

function markdown(interfaceChecks: readonly Check[], tuneChecks: readonly Check[], tuneCells: readonly Cell[], evalChecks: readonly Check[] | null, evalCells: readonly Cell[] | null): string {
  const out: string[] = [];
  const partyName = (p: readonly SubclassId[]) => p.map((s) => SUBCLASSES[s].name).join(", ");
  out.push("# M4: the module interface and the reference modules", "");
  out.push(
    'The protocol is in DESIGN.md, section 8, "M4 protocol". ' +
      `Tuning data: seed ${TUNE.seed}, ${TUNE.trials} fights per style, ${partyName(TUNE.party)}, the ordinary styles. ` +
      `Held out: seed ${EVAL.seed}, ${EVAL.trials} fights per style, all ${STYLES.length} styles, on each of two parties. ` +
      `Every fight is ${ROUNDS} rounds. Belief: model C at its M2 settings; steps as M3 calibrated them, with the placeholder \`lethal\` and \`show\` weights. ` +
      "`lethal` per fight is the mean over the ordinary styles (Habitual, By the book, Adaptive) unless a column says otherwise." +
      (args.quick ? " **This was a --quick run: too few fights for the verdict to mean anything.**" : ""),
    "",
  );

  const done = evalChecks !== null && [...interfaceChecks, ...evalChecks].every((c) => c.passed);
  out.push("## Verdict", "");
  if (evalChecks === null) {
    out.push("**A value target failed on the tuning data, so the held-out data was not touched.** The protocol's next step is a change to the `lethal` or `show` weights, written down in DESIGN.md with its reason.", "");
  } else {
    out.push(done ? "**Every target holds: M4 is done.**" : "**Not every target holds.**", "");
  }
  out.push("### Interface targets", "");
  out.push(checkTable(interfaceChecks), "");
  out.push("Target 2 (the three boss sketches) is checked by hand in DESIGN.md 6.2.", "");
  if (evalChecks) {
    out.push("### Value targets, held out", "", checkTable(evalChecks), "");
  }
  out.push("### Value targets, tuning data", "", checkTable(tuneChecks), "");

  const cells = evalCells ?? tuneCells;
  out.push(`## By module${evalCells ? ", held out" : ", tuning data"}`, "");
  for (const module of evalCells ? REFERENCE_MODULES.map((m) => m.id) : LETHAL_MODULES) {
    out.push(`### ${moduleById(module).name}`, "", moduleTable(cells, module), "");
  }
  if (evalCells) EVAL.parties.forEach((p, i) => out.push(`Party ${i + 1}: ${partyName(p)}.`));
  out.push("");
  return out.join("\n");
}

function write(name: string, md: string, json: unknown, started: number): void {
  console.log(md);
  const dir = new URL("../../reports/", import.meta.url);
  mkdirSync(dir, { recursive: true });
  writeFileSync(new URL(`${name}.md`, dir), md);
  writeFileSync(new URL(`${name}.json`, dir), JSON.stringify(json, null, 2) + "\n");
  console.error(`Wrote reports/${name}.md and reports/${name}.json in ${((Date.now() - started) / 1000).toFixed(0)}s`);
}

function main(): void {
  const started = Date.now();
  const name = args.quick ? "m4-modules-quick" : "m4-modules";

  const tuneCells: Cell[] = [];
  for (const module of LETHAL_MODULES) {
    for (const step of STEPS) {
      process.stderr.write(`\rtuning data: ${module}, ${step.id}          `);
      tuneCells.push(run(module, step, TUNE.seed, TUNE.trials, [TUNE.party], TUNE.styles));
    }
  }
  process.stderr.write("\n");
  const tuneChecks = valueChecks(tuneCells);
  const interfaceChecks = [engineIsClean()];

  if (!tuneChecks.every((c) => c.passed)) {
    write(name, markdown(interfaceChecks, tuneChecks, tuneCells, null, null), { protocol: { tune: { ...TUNE, styles: TUNE.styles.map((s) => s.id) } }, tuneChecks, tuneCells }, started);
    return;
  }

  const evalCells: Cell[] = [];
  for (const { id } of REFERENCE_MODULES) {
    for (const step of STEPS) {
      process.stderr.write(`\rheld out: ${id}, ${step.id}          `);
      evalCells.push(run(id, step, EVAL.seed, EVAL.trials, EVAL.parties));
    }
  }
  process.stderr.write("\n");
  interfaceChecks.push(betReproducesM3(evalCells));
  const evalChecks = valueChecks(evalCells);
  write(
    name,
    markdown(interfaceChecks, tuneChecks, tuneCells, evalChecks, evalCells),
    { protocol: { tune: { ...TUNE, styles: TUNE.styles.map((s) => s.id) }, eval: EVAL, rounds: ROUNDS }, interfaceChecks, tuneChecks, evalChecks, evalCells },
    started,
  );
}

main();
