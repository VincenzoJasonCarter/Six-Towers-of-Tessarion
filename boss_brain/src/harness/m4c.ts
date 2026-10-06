/**
 * M4c: check temperament shifting (DESIGN.md 8, "M4c: temperament shift check").
 *
 * Usage, from boss_brain/:
 *
 *     npm run compare:m4c              # the check, a few minutes
 *     npm run compare:m4c -- --quick   # a smoke test with few fights; its verdict means nothing
 *
 * Runs the Placeholder Boss with the enrage triggers on a crude HP clock, and
 * with the insult trigger alone, checks that shifts behave as 5.3 says, and
 * writes reports/m4c-shift.md and reports/m4c-shift.json.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { ENRAGE, INSULT, type Trigger } from "../engine/decision/shift.ts";
import { stepById, STEPS } from "../engine/decision/temperament.ts";
import { SUBCLASSES, type SubclassId } from "../engine/subclasses.ts";
import { placeholder } from "../modules/placeholder.ts";
import { runModuleSuite, type ModuleSuiteResult, type PhaseSummary } from "./bout.ts";
import { makeC, TUNED_C } from "./candidates.ts";
import { STYLES } from "./players.ts";
import { num, pct, table } from "./report.ts";

const SPIKE_PARTY: SubclassId[] = ["gunman", "bulwark", "verdant", "hellbound"];
const SECOND_PARTY: SubclassId[] = ["warbound", "sanguine_aegis", "crystal_archer", "aether"];
const ORDINARY = ["habitual", "by-the-book", "adaptive"];
const SWITCHERS = ["alternator", "second-guesser"];
const DEFIERS = ["contrarian", "second-guesser"];
const BOSS_HP = 30;
const REACH = 0.9;
const MOVES = ["strike", "wind-up", "interrupt", "signature"];

const { values: args } = parseArgs({ options: { quick: { type: "boolean", default: false } } });
const DATA = { seed: 2, trials: args.quick ? 60 : 1000, parties: [SPIKE_PARTY, SECOND_PARTY] };
const ROUNDS = 10;
const BELIEF = makeC(TUNED_C);

type Row = ModuleSuiteResult["styles"][number];

function run(start: string, triggers: readonly Trigger[], bossHp?: number): ModuleSuiteResult[] {
  return DATA.parties.map((party) =>
    runModuleSuite({
      seed: DATA.seed,
      trials: DATA.trials,
      rounds: ROUNDS,
      party,
      styles: STYLES,
      belief: BELIEF,
      step: stepById(start),
      module: placeholder as never,
      triggers,
      ...(bossHp === undefined ? {} : { bossHp }),
    }),
  );
}

/** A per-style number, averaged over the styles that have it and then over the parties. */
function mean(byParty: readonly ModuleSuiteResult[], styles: readonly string[], f: (s: Row) => number | null | undefined): number | null {
  const perParty = byParty
    .map((r) => {
      const xs = r.styles.filter((s) => styles.includes(s.style)).map(f).filter((x): x is number => typeof x === "number" && !Number.isNaN(x));
      return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
    })
    .filter((x): x is number => x !== null);
  return perParty.length ? perParty.reduce((a, b) => a + b, 0) / perParty.length : null;
}

const phase = (id: string, f: (p: PhaseSummary) => number | null) => (s: Row) => {
  const p = s.phases[id];
  return p ? f(p) : null;
};
const show = (x: number | null, f: (x: number) => string) => (x === null ? "–" : f(x));

interface Check {
  readonly check: string;
  readonly passed: boolean;
  readonly detail: string;
}

function checks(enrage: readonly ModuleSuiteResult[], insult: readonly ModuleSuiteResult[]): Check[] {
  const reach = (to: string) => mean(enrage, ORDINARY, (s) => s.shifts[to]?.rate ?? 0) ?? 0;
  const when = (to: string) => mean(enrage, ORDINARY, (s) => s.shifts[to]?.round);
  const fix = (id: string) => mean(enrage, ORDINARY, phase(id, (p) => p.fixation));
  const switched = (id: string) => mean(enrage, SWITCHERS, phase(id, (p) => p.betSuccess));
  const wr = when("wrathful");
  const bl = when("bloodlusted");
  const [fr, fb] = [fix("ruthless"), fix("bloodlusted")];
  const [sr, sw, sb] = [switched("ruthless"), switched("wrathful"), switched("bloodlusted")];
  const insultsDefiers = mean(insult, DEFIERS, (s) => s.shiftsPerFight)!;
  const insultsOrdinary = mean(insult, ORDINARY, (s) => s.shiftsPerFight)!;
  return [
    {
      check: `1. The enrage happens (at least ${pct(REACH)} reach Wrathful, before Bloodlusted)`,
      passed: reach("wrathful") >= REACH && wr !== null && (bl === null || wr < bl),
      detail: `Wrathful in ${pct(reach("wrathful"))} of fights, round ${show(wr, (x) => num(x, 1))}; Bloodlusted in ${pct(reach("bloodlusted"))}, round ${show(bl, (x) => num(x, 1))}`,
    },
    {
      check: "2. Fixation is higher in the Bloodlusted phase than in the Ruthless phase",
      passed: fr !== null && fb !== null && fb > fr,
      detail: `Ruthless ${show(fr, (x) => num(x, 2))}, Wrathful ${show(fix("wrathful"), (x) => num(x, 2))}, Bloodlusted ${show(fb, (x) => num(x, 2))}`,
    },
    {
      check: "3. The enrage opens a window against players who switch",
      passed: sr !== null && sw !== null && sb !== null && sw < sr && sb < sr,
      detail: `read success against Alternator and Second-guesser: Ruthless ${show(sr, pct)}, Wrathful ${show(sw, pct)}, Bloodlusted ${show(sb, pct)}`,
    },
    {
      check: "4. Defiance angers the boss",
      passed: insultsDefiers > insultsOrdinary,
      detail: `insults per fight: defiers ${num(insultsDefiers, 2)}, ordinary play ${num(insultsOrdinary, 2)}`,
    },
  ];
}

function markdown(enrage: readonly ModuleSuiteResult[], insult: readonly ModuleSuiteResult[], cs: readonly Check[]): string {
  const out: string[] = [];
  const partyName = (p: readonly SubclassId[]) => p.map((s) => SUBCLASSES[s].name).join(", ");
  out.push("# M4c: temperament shifting", "");
  out.push(
    'The check is in DESIGN.md, section 8, "M4c: temperament shift check". ' +
      `The Placeholder Boss (default fitting), seed ${DATA.seed}, ${DATA.trials} fights per style, all ${STYLES.length} styles, on each of two parties, ${ROUNDS} rounds. ` +
      `Enrage: from Ruthless, with the enrage triggers, ${BOSS_HP} HP on the crude clock. Insult: from Hunting, the insult trigger alone. ` +
      "Belief: model C at its M2 settings. Numbers are means over the two parties, against ordinary play unless a column says otherwise." +
      (args.quick ? " **This was a --quick run: too few fights for the verdict to mean anything.**" : ""),
    "",
  );
  out.push("## Verdict", "");
  out.push(cs.every((c) => c.passed) ? "**Every check holds.**" : "**Not every check holds.**", "");
  out.push(table(["Check", "Passed", "Detail"], cs.map((c) => [c.check, c.passed ? "yes" : "**no**", c.detail]), 3), "");

  out.push("## The enrage, by phase", "");
  out.push(
    table(
      ["Phase", "Share of moves", "`lethal` / move", ...MOVES, "Read success", "vs switchers", "Fixation"],
      ["ruthless", "wrathful", "bloodlusted"].map((id) => {
        const total = (s: Row) => Object.values(s.phases).reduce((a, p) => a + p.moves, 0);
        return [
          stepById(id).name,
          show(mean(enrage, ORDINARY, (s) => (s.phases[id] ? s.phases[id]!.moves / total(s) : 0)), pct),
          show(mean(enrage, ORDINARY, phase(id, (p) => p.lethalPerMove)), (x) => num(x, 2)),
          ...MOVES.map((m) => show(mean(enrage, ORDINARY, phase(id, (p) => p.kinds[m] ?? 0)), pct)),
          show(mean(enrage, ORDINARY, phase(id, (p) => p.betSuccess)), pct),
          show(mean(enrage, SWITCHERS, phase(id, (p) => p.betSuccess)), pct),
          show(mean(enrage, ORDINARY, phase(id, (p) => p.fixation)), (x) => num(x, 2)),
        ];
      }),
    ),
    "",
  );
  out.push(`\`lethal\` per fight over the whole enrage fight: ${show(mean(enrage, ORDINARY, (s) => s.perFight.lethal), (x) => num(x, 2))}.`, "");

  out.push("## By style", "");
  out.push(
    table(
      ["Player", "Reaches Wrathful", "round", "Reaches Bloodlusted", "round", "`lethal` / fight (enrage)", "Insults / fight"],
      STYLES.map((style) => {
        const e = (f: (s: Row) => number | null | undefined) => mean(enrage, [style.id], f);
        return [
          style.name,
          show(e((s) => s.shifts["wrathful"]?.rate ?? 0), pct),
          show(e((s) => s.shifts["wrathful"]?.round), (x) => num(x, 1)),
          show(e((s) => s.shifts["bloodlusted"]?.rate ?? 0), pct),
          show(e((s) => s.shifts["bloodlusted"]?.round), (x) => num(x, 1)),
          show(e((s) => s.perFight.lethal), (x) => num(x, 2)),
          show(mean(insult, [style.id], (s) => s.shiftsPerFight), (x) => num(x, 2)),
        ];
      }),
    ),
    "",
  );
  out.push(`Parties: ${DATA.parties.map(partyName).join("; ")}. Steps: ${STEPS.map((s) => s.name).join(", ")}.`, "");
  return out.join("\n");
}

function main(): void {
  const started = Date.now();
  process.stderr.write("enrage\n");
  const enrage = run("ruthless", ENRAGE, BOSS_HP);
  process.stderr.write("insult\n");
  const insult = run("hunting", [INSULT]);
  const cs = checks(enrage, insult);
  const md = markdown(enrage, insult, cs);
  console.log(md);
  const name = args.quick ? "m4c-shift-quick" : "m4c-shift";
  const dir = new URL("../../reports/", import.meta.url);
  mkdirSync(dir, { recursive: true });
  writeFileSync(new URL(`${name}.md`, dir), md);
  writeFileSync(new URL(`${name}.json`, dir), JSON.stringify({ data: DATA, rounds: ROUNDS, bossHp: BOSS_HP, checks: cs, enrage, insult }, null, 2) + "\n");
  console.error(`Wrote reports/${name}.md and reports/${name}.json in ${((Date.now() - started) / 1000).toFixed(0)}s`);
}

main();
