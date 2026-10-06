/**
 * M4b: check the Placeholder Boss (DESIGN.md 8, "M4b: Placeholder Boss check").
 *
 * Usage, from boss_brain/:
 *
 *     npm run compare:m4b                          # the check, a few minutes
 *     npm run compare:m4b -- --variant recharge    # the same checks on another fitting (VARIANTS)
 *     npm run compare:m4b -- --quick               # a smoke test with few fights; its verdict means nothing
 *
 * Runs the calibrated steps through the Placeholder Boss on both parties and
 * every style, checks whether M4's findings survive when the shapes of
 * decision compete in one module, and writes reports/m4b-placeholder.md and
 * reports/m4b-placeholder.json.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { STEPS } from "../engine/decision/temperament.ts";
import { SUBCLASSES, type SubclassId } from "../engine/subclasses.ts";
import { placeholderWith, RECHARGE_5_6, type PlaceholderConfig } from "../modules/placeholder.ts";
import { runModuleSuite, type ModuleSuiteResult } from "./bout.ts";
import { makeC, TUNED_C } from "./candidates.ts";
import { STYLES } from "./players.ts";
import { num, pct, table } from "./report.ts";

const SPIKE_PARTY: SubclassId[] = ["gunman", "bulwark", "verdant", "hellbound"];
const SECOND_PARTY: SubclassId[] = ["warbound", "sanguine_aegis", "crystal_archer", "aether"];
const ORDINARY = ["habitual", "by-the-book", "adaptive"];
const MOVES = ["strike", "wind-up", "interrupt", "signature"];
const MOVESET = (c: Partial<PlaceholderConfig>) => MOVES.filter((m) => m !== "interrupt" || c.interrupt !== false);
const WIND_UP_CEILING = 0.1;
const DEAD_MOVE = 0.05;

/**
 * Fittings of the Placeholder to the monsters in the bestiary (DESIGN.md 6.2,
 * "Fitting the Placeholder"): the default, and the shapes most stat blocks
 * actually have.
 */
const VARIANTS: Record<string, { readonly name: string; readonly config: Partial<PlaceholderConfig> }> = {
  default: { name: "as checked: reaction, three signature uses", config: {} },
  "no-interrupt": { name: "no reaction", config: { interrupt: false } },
  recharge: { name: "signature on Recharge 5–6", config: { signature: { recharge: RECHARGE_5_6 } } },
  typical: { name: "no reaction, signature on Recharge 5–6 (Construct, Iron-Hound, Drone)", config: { interrupt: false, signature: { recharge: RECHARGE_5_6 } } },
  multiattack: { name: "two-attack Multiattack, no reaction, recharge (Scavenger Leader, Hydraform)", config: { strike: 2, interrupt: false, signature: { recharge: RECHARGE_5_6 } } },
};

const { values: args } = parseArgs({
  options: { quick: { type: "boolean", default: false }, variant: { type: "string", default: "default" } },
});
const found = VARIANTS[args.variant];
if (!found) throw new Error(`No variant "${args.variant}". Known: ${Object.keys(VARIANTS).join(", ")}`);
const variant = found;
const module = placeholderWith(variant.config);
const available = MOVESET(variant.config);
const DATA = { seed: 2, trials: args.quick ? 60 : 1000, parties: [SPIKE_PARTY, SECOND_PARTY] };
const ROUNDS = 10;
const BELIEF = makeC(TUNED_C);

type Row = ModuleSuiteResult["styles"][number];

function mean(byParty: readonly ModuleSuiteResult[], styles: readonly string[], f: (s: Row) => number): number {
  const perParty = byParty.map((r) => {
    const picked = r.styles.filter((s) => styles.includes(s.style));
    return picked.reduce((sum, s) => sum + f(s), 0) / picked.length;
  });
  return perParty.reduce((a, b) => a + b, 0) / perParty.length;
}

interface StepResult {
  readonly id: string;
  readonly name: string;
  readonly byParty: readonly ModuleSuiteResult[];
  readonly lethal: number;
  /** Each move's share of the step's moves. */
  readonly share: Record<string, number>;
  readonly signatureRound: number;
}

function evaluate(): StepResult[] {
  return STEPS.map((step) => {
    process.stderr.write(`\r${step.id}          `);
    const byParty = DATA.parties.map((party) =>
      runModuleSuite({ seed: DATA.seed, trials: DATA.trials, rounds: ROUNDS, party, styles: STYLES, belief: BELIEF, step, module: module as never }),
    );
    const signatures = mean(byParty, ORDINARY, (s) => s.kinds["signature"] ?? 0);
    return {
      id: step.id,
      name: step.name,
      byParty,
      lethal: mean(byParty, ORDINARY, (s) => s.perFight.lethal),
      share: Object.fromEntries(MOVES.map((m) => [m, mean(byParty, ORDINARY, (s) => (s.kinds[m] ?? 0) / ROUNDS)])),
      signatureRound: signatures ? mean(byParty, ORDINARY, (s) => s.detail["signatureRound"] ?? 0) / signatures : NaN,
    };
  });
}

interface Check {
  readonly check: string;
  readonly passed: boolean;
  readonly detail: string;
}

function checks(rs: readonly StepResult[]): Check[] {
  const lethal = rs.map((r) => r.lethal);
  const windUps = rs.map((r) => r.share["wind-up"]!);
  const rounds = rs.map((r) => (Number.isNaN(r.signatureRound) ? Infinity : r.signatureRound));
  const used = available.map((m) => ({ m, top: Math.max(...rs.map((r) => r.share[m]!)) }));
  const arrow = (xs: readonly number[], f: (x: number) => string) => xs.map(f).join(" → ");
  return [
    {
      check: "1. The bell",
      passed: lethal[0]! < lethal[1]! && lethal[1]! < lethal[2]! && lethal[2]! > lethal[3]! && lethal[2]! > lethal[4]!,
      detail: arrow(lethal, (x) => num(x, 2)),
    },
    { check: "2. Rage is frightening", passed: lethal[4]! > lethal[0]!, detail: `Bloodlusted ${num(lethal[4]!, 2)} against Curious ${num(lethal[0]!, 2)}` },
    {
      check: "3. Impatience: Bloodlusted signs earliest",
      passed: rounds.indexOf(Math.min(...rounds)) === 4,
      detail: `mean round of a signature ${arrow(rounds, (x) => (Number.isFinite(x) ? num(x, 1) : "never"))}`,
    },
    {
      check: `4. Wind-ups: highest at Curious, under ${pct(WIND_UP_CEILING)} from Ruthless on`,
      passed: windUps.indexOf(Math.max(...windUps)) === 0 && windUps.slice(2).every((x) => x < WIND_UP_CEILING),
      detail: arrow(windUps, pct),
    },
    {
      check: `5. No dead move (each at least ${pct(DEAD_MOVE)} of some step's moves)`,
      passed: used.every((u) => u.top >= DEAD_MOVE),
      detail: used.map((u) => `${u.m} up to ${pct(u.top)}`).join(", "),
    },
  ];
}

function markdown(rs: readonly StepResult[], cs: readonly Check[]): string {
  const out: string[] = [];
  const partyName = (p: readonly SubclassId[]) => p.map((s) => SUBCLASSES[s].name).join(", ");
  out.push("# M4b: the Placeholder Boss", "");
  out.push(
    'The check is in DESIGN.md, section 8, "M4b: Placeholder Boss check". ' +
      `Seed ${DATA.seed}, ${DATA.trials} fights per style, all ${STYLES.length} styles, on each of two parties, ${ROUNDS} rounds. ` +
      `Fitting: **${args.variant}**, ${variant.name}. ` +
      "Belief: model C at its M2 settings; steps as calibrated. Numbers are against ordinary play (Habitual, By the book, Adaptive), mean over the two parties, unless a column says otherwise." +
      (args.quick ? " **This was a --quick run: too few fights for the verdict to mean anything.**" : ""),
    "",
  );
  out.push("## Verdict", "");
  out.push(cs.every((c) => c.passed) ? "**Every check holds.**" : "**Not every check holds.** A failed check is a question for the design, answered before the boss goes to the table.", "");
  out.push(table(["Check", "Passed", "Detail"], cs.map((c) => [c.check, c.passed ? "yes" : "**no**", c.detail]), 3), "");

  out.push("## By step", "");
  out.push(
    table(
      ["Step", "`lethal` / fight", "vs Random", "vs Defiers", "vs Tell-reader", ...MOVES.map((m) => `${m}`), "Read success", "Signature round"],
      rs.map((r) => [
        r.name,
        `**${num(r.lethal, 2)}**`,
        num(mean(r.byParty, ["random"], (s) => s.perFight.lethal), 2),
        num(mean(r.byParty, ["contrarian", "second-guesser"], (s) => s.perFight.lethal), 2),
        num(mean(r.byParty, ["tell-reader"], (s) => s.perFight.lethal), 2),
        ...MOVES.map((m) => pct(r.share[m]!)),
        mean(r.byParty, ORDINARY, (s) => s.bets.betsPerFight) > 0 ? pct(mean(r.byParty, ORDINARY, (s) => s.bets.success)) : "–",
        Number.isNaN(r.signatureRound) ? "never" : num(r.signatureRound, 1),
      ]),
    ),
    "",
  );
  out.push("Move columns are each move's share of the step's moves against ordinary play.", "");

  DATA.parties.forEach((party, pi) => {
    out.push(`## Party ${pi + 1}, by style`, "");
    out.push(`${partyName(party)}. \`lethal\` per fight.`, "");
    out.push(
      table(
        ["Player", ...rs.map((r) => r.name)],
        STYLES.map((style, si) => [style.name, ...rs.map((r) => num(r.byParty[pi]!.styles[si]!.perFight.lethal, 2))]),
      ),
      "",
    );
  });
  return out.join("\n");
}

function main(): void {
  const started = Date.now();
  const rs = evaluate();
  process.stderr.write("\n");
  const cs = checks(rs);
  const md = markdown(rs, cs);
  console.log(md);
  const base = args.variant === "default" ? "m4b-placeholder" : `m4b-placeholder-${args.variant}`;
  const name = args.quick ? `${base}-quick` : base;
  const dir = new URL("../../reports/", import.meta.url);
  mkdirSync(dir, { recursive: true });
  writeFileSync(new URL(`${name}.md`, dir), md);
  writeFileSync(new URL(`${name}.json`, dir), JSON.stringify({ data: DATA, rounds: ROUNDS, variant: { id: args.variant, ...variant }, checks: cs, results: rs }, null, 2) + "\n");
  console.error(`Wrote reports/${name}.md and reports/${name}.json in ${((Date.now() - started) / 1000).toFixed(0)}s`);
}

main();
