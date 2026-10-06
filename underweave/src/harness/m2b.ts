/**
 * M2b: should the belief read players who read the boss? (DESIGN.md 8,
 * "M2b protocol").
 *
 * Usage, from underweave/:
 *
 *     npm run compare:m2b              # the full protocol, a few minutes
 *     npm run compare:m2b -- --quick   # a smoke test with few fights; its verdict means nothing
 *
 * Tunes the wary prior and then the ensemble's memory on top of model C's M2
 * settings, evaluates `c` and `c2` (and `b`, `b2` for information) on held-out
 * data with all nine styles, applies the protocol's rules and writes
 * reports/m2b-wary.md and reports/m2b-wary.json.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import type { BeliefFactory } from "../engine/belief/types.ts";
import { SUBCLASSES, type SubclassId } from "../engine/subclasses.ts";
import { makeB, makeC, product, TUNED_C, type ParamsC } from "./candidates.ts";
import { SPIKE_PROPHET } from "./fight.ts";
import { STYLES } from "./players.ts";
import { num, pct, table } from "./report.ts";
import { runSuite, type SuiteResult } from "./suite.ts";

const SPIKE_PARTY: SubclassId[] = ["gunman", "bulwark", "verdant", "hellbound"];
const SECOND_PARTY: SubclassId[] = ["warbound", "sanguine_aegis", "crystal_archer", "aether"];
const BLIND = Math.log(5);
const DEFIERS = ["contrarian", "second-guesser"];
/** Rule 2: no style may get worse than this, in log loss. */
const STYLE_SLACK = 0.02;

const { values: args } = parseArgs({ options: { quick: { type: "boolean", default: false } } });
const TUNE = { seed: 1, trials: args.quick ? 30 : 300, party: SPIKE_PARTY };
const EVAL = { seed: 2, trials: args.quick ? 60 : 1000, parties: [SPIKE_PARTY, SECOND_PARTY] };
const ROUNDS = 10;
const WARY_PRIORS = [0.1, 0.2, 0.35, 0.5];
const ENSEMBLE_MEMORIES = [0.85, 0.9, 0.95];

const run = (belief: BeliefFactory, seed: number, trials: number, party: readonly SubclassId[]) =>
  runSuite({ seed, trials, rounds: ROUNDS, party, styles: STYLES, belief, policy: SPIKE_PROPHET });

/** Mean log loss over the styles, each weighted equally. */
const meanLogLoss = (r: SuiteResult) => r.styles.reduce((s, x) => s + x.forecast.logLoss, 0) / r.styles.length;

interface Tried {
  readonly params: ParamsC;
  readonly logLoss: number;
}

function tune(label: string, grid: readonly ParamsC[]): { best: ParamsC; tried: Tried[] } {
  const tried: Tried[] = [];
  grid.forEach((params, i) => {
    tried.push({ params, logLoss: meanLogLoss(run(makeC(params), TUNE.seed, TUNE.trials, TUNE.party)) });
    process.stderr.write(`\rtuning ${label}: ${i + 1}/${grid.length}   `);
  });
  process.stderr.write("\n");
  const best = tried.reduce((x, y) => (y.logLoss < x.logLoss ? y : x));
  return { best: best.params, tried };
}

interface Evaluated {
  readonly id: string;
  readonly name: string;
  readonly byParty: readonly SuiteResult[];
  readonly logLoss: number;
  readonly calibrationError: number;
  /** Log loss per style, mean over the parties. */
  readonly byStyle: Record<string, number>;
  /** Named-turn log loss against each defier style, worst party. */
  readonly defierLogLoss: Record<string, number>;
}

function evaluate(id: string, name: string, belief: BeliefFactory): Evaluated {
  process.stderr.write(`evaluating ${id}\n`);
  const byParty = EVAL.parties.map((party) => run(belief, EVAL.seed, EVAL.trials, party));
  const mean = (f: (r: SuiteResult) => number) => byParty.reduce((s, r) => s + f(r), 0) / byParty.length;
  const styleOf = (r: SuiteResult, style: string) => r.styles.find((s) => s.style === style)!;
  const byStyle = Object.fromEntries(STYLES.map((s) => [s.id, mean((r) => styleOf(r, s.id).forecast.logLoss)]));
  const defierLogLoss = Object.fromEntries(
    DEFIERS.map((style) => [style, Math.max(...byParty.map((r) => styleOf(r, style).named.logLoss))]),
  );
  return {
    id,
    name,
    byParty,
    logLoss: mean(meanLogLoss),
    calibrationError: mean((r) => r.pooled.calibrationError),
    byStyle,
    defierLogLoss,
  };
}

interface Verdict {
  readonly chosen: "c" | "c2";
  readonly rules: readonly { readonly rule: string; readonly passed: boolean; readonly detail: string }[];
}

function decide(c: Evaluated, c2: Evaluated): Verdict {
  const worst = STYLES.map((s) => ({ style: s.name, diff: c2.byStyle[s.id]! - c.byStyle[s.id]! })).reduce((x, y) =>
    y.diff > x.diff ? y : x,
  );
  const defiers = Object.entries(c2.defierLogLoss);
  const rules = [
    {
      rule: "1. Lower mean log loss over the nine styles",
      passed: c2.logLoss < c.logLoss,
      detail: `${num(c2.logLoss, 4)} against ${num(c.logLoss, 4)}`,
    },
    {
      rule: `2. No style worse by more than ${STYLE_SLACK}`,
      passed: worst.diff <= STYLE_SLACK,
      detail: `largest change ${worst.diff >= 0 ? "+" : ""}${num(worst.diff, 3)} (${worst.style})`,
    },
    {
      rule: "3. Calibration error no worse",
      passed: c2.calibrationError <= c.calibrationError,
      detail: `${num(c2.calibrationError, 3)} against ${num(c.calibrationError, 3)}`,
    },
    {
      rule: "4. Still passes M2's defier guards",
      passed: defiers.every(([, loss]) => loss <= BLIND),
      detail: defiers.map(([style, loss]) => `${style} ${num(loss, 2)}`).join(", ") + ` (guard ${num(BLIND, 2)})`,
    },
  ];
  return { chosen: rules.every((r) => r.passed) ? "c2" : "c", rules };
}

function markdown(
  wary: { best: ParamsC; tried: Tried[] },
  memory: { best: ParamsC; tried: Tried[] },
  results: readonly Evaluated[],
  verdict: Verdict,
): string {
  const out: string[] = [];
  const partyName = (p: readonly SubclassId[]) => p.map((s) => SUBCLASSES[s].name).join(", ");
  const [c, c2] = [results.find((r) => r.id === "c")!, results.find((r) => r.id === "c2")!];

  out.push("# M2b: reading players who read the boss", "");
  out.push(
    'The protocol is in DESIGN.md, section 8, "M2b protocol". ' +
      `Tuning: seed ${TUNE.seed}, ${TUNE.trials} fights per style, ${partyName(TUNE.party)}. ` +
      `Held out: seed ${EVAL.seed}, ${EVAL.trials} fights per style, on each of two parties. ` +
      `Every fight is ${ROUNDS} rounds, every hero in a fight plays the same style, and all ${STYLES.length} styles are scored.` +
      (args.quick ? " **This was a --quick run: too few fights for the verdict to mean anything.**" : ""),
    "",
  );

  out.push("## Verdict", "");
  out.push(`**Chosen: ${verdict.chosen === "c2" ? c2.name : c.name}.**`, "");
  out.push(table(["Rule", "Passed", "Detail"], verdict.rules.map((r) => [r.rule, r.passed ? "yes" : "**no**", r.detail]), 3), "");

  out.push("## Held-out results", "");
  out.push(
    "Log loss is the mean over the nine styles (lower is better; a blind guess scores 1.61). " +
      "The defier columns are log loss on named turns only, worst of the two parties.",
    "",
  );
  out.push(
    table(
      ["Model", "Log loss", ...EVAL.parties.map((_, i) => `Party ${i + 1}`), "Calibration error", "Named: Contrarian", "Named: Second-guesser"],
      results.map((r) => [
        r.name,
        `**${num(r.logLoss, 3)}**`,
        ...r.byParty.map((p) => num(meanLogLoss(p), 3)),
        num(r.calibrationError, 3),
        num(r.defierLogLoss["contrarian"]!, 2),
        num(r.defierLogLoss["second-guesser"]!, 2),
      ]),
    ),
    "",
  );
  EVAL.parties.forEach((p, i) => out.push(`Party ${i + 1}: ${partyName(p)}.`));
  out.push("");

  out.push("## By style", "");
  out.push("Log loss, mean over the two parties, and the change from `c` to `c2` (rule 2).", "");
  out.push(
    table(
      ["Player", ...results.map((r) => r.id), "c2 − c"],
      STYLES.map((s) => {
        const diff = c2.byStyle[s.id]! - c.byStyle[s.id]!;
        return [s.name, ...results.map((r) => num(r.byStyle[s.id]!, 3)), `${diff >= 0 ? "+" : ""}${num(diff, 3)}`];
      }),
    ),
    "",
  );

  EVAL.parties.forEach((party, pi) => {
    out.push(`## Party ${pi + 1}, by style`, "");
    out.push(`${partyName(party)}. Log loss / accuracy / prophecy hit rate under the baseline policy.`, "");
    out.push(
      table(
        ["Player", ...results.map((r) => r.id)],
        STYLES.map((style, si) => [
          style.name,
          ...results.map((r) => {
            const s = r.byParty[pi]!.styles[si]!;
            return `${num(s.forecast.logLoss, 2)} / ${pct(s.forecast.accuracy)} / ${pct(s.prophecy.hitRate)}`;
          }),
        ]),
      ),
      "",
    );
  });

  out.push("## Tuning", "");
  out.push(
    table(
      ["Wary prior", "Ensemble memory", "Tuning log loss"],
      [...wary.tried, ...memory.tried].map((t) => [
        String(t.params.b.waryPrior),
        String(t.params.ensemble.memory),
        num(t.logLoss, 4),
      ]),
      0,
    ),
    "",
  );
  out.push(`Best: \`${JSON.stringify(memory.best)}\`.`, "");
  out.push("Model ids: " + results.map((r) => `\`${r.id}\` ${r.name}`).join(", ") + ".", "");
  return out.join("\n");
}

function main(): void {
  const started = Date.now();
  const wary = tune(
    "wary prior",
    WARY_PRIORS.map((w) => ({ ...TUNED_C, b: { ...TUNED_C.b, waryPrior: w } })),
  );
  const memory = tune(
    "ensemble memory",
    product({ memory: ENSEMBLE_MEMORIES }).map((ensemble) => ({ ...wary.best, ensemble })),
  );
  const best = memory.best;

  const results = [
    evaluate("c", "C: ensemble (M2)", makeC(TUNED_C)),
    evaluate("c2", "C2: ensemble with wary players", makeC(best)),
    evaluate("b", "B: archetypes (M2)", makeB(TUNED_C.b)),
    evaluate("b2", "B2: archetypes with wary players", makeB(best.b)),
  ];
  const verdict = decide(results[0]!, results[1]!);
  const md = markdown(wary, memory, results, verdict);
  console.log(md);

  const name = args.quick ? "m2b-wary-quick" : "m2b-wary";
  const dir = new URL("../../reports/", import.meta.url);
  mkdirSync(dir, { recursive: true });
  writeFileSync(new URL(`${name}.md`, dir), md);
  const json = {
    protocol: { tune: TUNE, eval: EVAL, rounds: ROUNDS, waryPriors: WARY_PRIORS, ensembleMemories: ENSEMBLE_MEMORIES },
    tuning: { wary: wary.tried, memory: memory.tried, best },
    results,
    verdict,
  };
  writeFileSync(new URL(`${name}.json`, dir), JSON.stringify(json, null, 2) + "\n");
  console.error(`Wrote reports/${name}.md and reports/${name}.json in ${((Date.now() - started) / 1000).toFixed(0)}s`);
}

main();
