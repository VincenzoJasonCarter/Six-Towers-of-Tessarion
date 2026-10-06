/**
 * M2: choose the belief model (DESIGN.md 8, "M2 protocol").
 *
 * Usage, from underweave/:
 *
 *     npm run compare              # the full protocol, a few minutes
 *     npm run compare -- --quick   # a smoke test with few fights; its verdict means nothing
 *
 * Tunes every candidate on seed 1, evaluates the winners once on seed 2 with
 * two parties, applies the protocol's rules and writes reports/m2-belief.md
 * and reports/m2-belief.json.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import type { BeliefFactory } from "../engine/belief/types.ts";
import { SUBCLASSES, type SubclassId } from "../engine/subclasses.ts";
import {
  gridA,
  gridAD,
  gridB,
  gridC,
  makeA,
  makeAD,
  makeB,
  makeC,
  type ParamsA,
  type ParamsAD,
  type ParamsB,
  type ParamsC,
} from "./candidates.ts";
import { SPIKE_PROPHET } from "./fight.ts";
import { STYLES } from "./players.ts";
import { num, pct, table } from "./report.ts";
import { runSuite, type SuiteResult } from "./suite.ts";

const SPIKE_PARTY: SubclassId[] = ["gunman", "bulwark", "verdant", "hellbound"];
const SECOND_PARTY: SubclassId[] = ["warbound", "sanguine_aegis", "crystal_archer", "aether"];
const BLIND = Math.log(5);
const DEFIERS = ["contrarian", "second-guesser"];
const TIE = 0.02;
const EXPLAINABLE = new Set(["b", "c"]);

const { values: args } = parseArgs({ options: { quick: { type: "boolean", default: false } } });
const TUNE = { seed: 1, trials: args.quick ? 30 : 300, party: SPIKE_PARTY };
const EVAL = { seed: 2, trials: args.quick ? 60 : 1000, parties: [SPIKE_PARTY, SECOND_PARTY] };
const ROUNDS = 10;

const run = (belief: BeliefFactory, seed: number, trials: number, party: readonly SubclassId[]) =>
  runSuite({ seed, trials, rounds: ROUNDS, party, styles: STYLES, belief, policy: SPIKE_PROPHET });

/** The protocol's primary measure: mean log loss over the styles, each weighted equally. */
const meanLogLoss = (r: SuiteResult) => r.styles.reduce((s, x) => s + x.forecast.logLoss, 0) / r.styles.length;

interface Tuned<P> {
  readonly id: string;
  readonly name: string;
  readonly tried: number;
  readonly best: P;
  readonly tuneLogLoss: number;
}

function tune<P>(id: string, name: string, grid: readonly P[], make: (p: P) => BeliefFactory): Tuned<P> {
  let best: P = grid[0]!;
  let bestLoss = Infinity;
  grid.forEach((params, i) => {
    const loss = meanLogLoss(run(make(params), TUNE.seed, TUNE.trials, TUNE.party));
    if (loss < bestLoss) [best, bestLoss] = [params, loss];
    process.stderr.write(`\rtuning ${id}: ${i + 1}/${grid.length}, best ${bestLoss.toFixed(4)}   `);
  });
  process.stderr.write("\n");
  return { id, name, tried: grid.length, best, tuneLogLoss: bestLoss };
}

interface Evaluated {
  readonly id: string;
  readonly name: string;
  readonly byParty: readonly SuiteResult[];
  readonly logLoss: number;
  readonly calibrationError: number;
  /** Named-turn log loss against each defier style, worst party. */
  readonly defierLogLoss: Record<string, number>;
}

function evaluate(id: string, name: string, belief: BeliefFactory): Evaluated {
  process.stderr.write(`evaluating ${id}\n`);
  const byParty = EVAL.parties.map((party) => run(belief, EVAL.seed, EVAL.trials, party));
  const mean = (f: (r: SuiteResult) => number) => byParty.reduce((s, r) => s + f(r), 0) / byParty.length;
  const defierLogLoss = Object.fromEntries(
    DEFIERS.map((style) => [style, Math.max(...byParty.map((r) => r.styles.find((s) => s.style === style)!.named.logLoss))]),
  );
  return { id, name, byParty, logLoss: mean(meanLogLoss), calibrationError: mean((r) => r.pooled.calibrationError), defierLogLoss };
}

interface Verdict {
  readonly chosen: string;
  readonly reasons: readonly string[];
  readonly failed: Record<string, string[]>;
}

function decide(results: readonly Evaluated[]): Verdict {
  const control = results.find((r) => r.id === "a")!;
  const failed: Record<string, string[]> = {};
  for (const r of results) {
    const why: string[] = [];
    for (const [style, loss] of Object.entries(r.defierLogLoss)) {
      if (loss > BLIND) why.push(`named-turn log loss ${loss.toFixed(2)} against ${style} is worse than a blind guess (${BLIND.toFixed(2)})`);
    }
    if (r.id !== "a" && r.calibrationError > control.calibrationError) {
      why.push(`calibration error ${r.calibrationError.toFixed(3)} is worse than model A's ${control.calibrationError.toFixed(3)}`);
    }
    if (why.length) failed[r.id] = why;
  }
  const eligible = results.filter((r) => !failed[r.id]).sort((x, y) => x.logLoss - y.logLoss);
  if (eligible.length === 0) return { chosen: "none", reasons: ["No candidate passed the guards."], failed };
  const best = eligible[0]!;
  const reasons = [`${best.name} has the lowest held-out log loss among the candidates that pass the guards (${best.logLoss.toFixed(3)}).`];
  if (!EXPLAINABLE.has(best.id)) {
    const near = eligible.find((r) => EXPLAINABLE.has(r.id) && r.logLoss - best.logLoss <= TIE);
    if (near) {
      return {
        chosen: near.id,
        reasons: [
          ...reasons,
          `${near.name} is within ${TIE} (${near.logLoss.toFixed(3)}) and can explain itself, so the tie-break picks it.`,
        ],
        failed,
      };
    }
  }
  return { chosen: best.id, reasons, failed };
}

function markdown(tuned: readonly Tuned<unknown>[], results: readonly Evaluated[], verdict: Verdict): string {
  const out: string[] = [];
  const partyName = (p: readonly SubclassId[]) => p.map((s) => SUBCLASSES[s].name).join(", ");
  const nameOf = (id: string) => results.find((r) => r.id === id)!.name;

  out.push("# M2: choosing the belief model", "");
  out.push(
    "The protocol is in DESIGN.md, section 8, \"M2 protocol\". " +
      `Tuning: seed ${TUNE.seed}, ${TUNE.trials} fights per style, ${partyName(TUNE.party)}. ` +
      `Held out: seed ${EVAL.seed}, ${EVAL.trials} fights per style, on each of two parties. ` +
      `Every fight is ${ROUNDS} rounds, and every hero in a fight plays the same style.` +
      (args.quick ? " **This was a --quick run: too few fights for the verdict to mean anything.**" : ""),
    "",
  );

  out.push("## Verdict", "");
  out.push(`**Chosen: ${verdict.chosen === "none" ? "none" : nameOf(verdict.chosen)}.**`, "");
  for (const r of verdict.reasons) out.push(`- ${r}`);
  for (const [id, why] of Object.entries(verdict.failed)) out.push(`- ${nameOf(id)} fails a guard: ${why.join("; ")}.`);
  out.push("");

  out.push("## Held-out results", "");
  out.push(
    "Log loss is the mean over the eight styles (lower is better; a blind guess scores 1.61). " +
      "The defier columns are log loss on named turns only, worst of the two parties; the guard is 1.61.",
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

  EVAL.parties.forEach((party, pi) => {
    out.push(`## Party ${pi + 1}, by style`, "");
    out.push(`${partyName(party)}. Log loss on every turn / accuracy on every turn / prophecy hit rate under the baseline policy.`, "");
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
      ["Model", "Settings tried", "Tuning log loss", "Best settings"],
      tuned.map((t) => [t.name, String(t.tried), num(t.tuneLogLoss, 4), `\`${JSON.stringify(t.best)}\``]),
    ),
    "",
  );
  out.push("Model ids: " + results.map((r) => `\`${r.id}\` ${r.name}`).join(", ") + ".", "");
  return out.join("\n");
}

function main(): void {
  const started = Date.now();
  const a = tune<ParamsA>("a", "A: counts", gridA(), makeA);
  const ad = tune<ParamsAD>("ad", "A + defiance", gridAD(a.best), makeAD);
  const b = tune<ParamsB>("b", "B: archetypes", gridB(), makeB);
  const c = tune<ParamsC>("c", "C: ensemble", gridC(ad.best, b.best), makeC);
  const tuned = [a, ad, b, c];

  const results = [
    evaluate("a", a.name, makeA(a.best)),
    evaluate("ad", ad.name, makeAD(ad.best)),
    evaluate("b", b.name, makeB(b.best)),
    evaluate("c", c.name, makeC(c.best)),
  ];
  const verdict = decide(results);
  const md = markdown(tuned, results, verdict);
  console.log(md);

  const name = args.quick ? "m2-belief-quick" : "m2-belief";
  const dir = new URL("../../reports/", import.meta.url);
  mkdirSync(dir, { recursive: true });
  writeFileSync(new URL(`${name}.md`, dir), md);
  const json = {
    protocol: { tune: TUNE, eval: EVAL, rounds: ROUNDS },
    tuned,
    results,
    verdict,
  };
  writeFileSync(new URL(`${name}.json`, dir), JSON.stringify(json, null, 2) + "\n");
  console.error(`Wrote reports/${name}.md and reports/${name}.json in ${((Date.now() - started) / 1000).toFixed(0)}s`);
}

main();
