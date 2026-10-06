/**
 * M3: calibrate the temperament steps (DESIGN.md 8, "M3 protocol").
 *
 * Usage, from boss_brain/:
 *
 *     npm run compare:m3              # the full protocol, about a quarter of an hour
 *     npm run compare:m3 -- --quick   # a smoke test with few fights; its verdict means nothing
 *
 * Tunes each step's free levers on seed 1 against the ordinary styles and the
 * Tell-reader, evaluates the tuned steps once on held-out data (seed 2, both
 * parties, all nine styles), checks the protocol's targets, repeats the
 * evaluation with model C's defiance priors lowered, and writes
 * reports/m3-temperament.md and reports/m3-temperament.json.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import type { BeliefFactory } from "../engine/belief/types.ts";
import { PLACEHOLDER_STEPS, type Temperament } from "../engine/decision/temperament.ts";
import { SUBCLASSES, type SubclassId } from "../engine/subclasses.ts";
import { runBetSuite, type BetSuiteResult } from "./bettor.ts";
import { makeC, product, TUNED_C } from "./candidates.ts";
import { ADAPTIVE, BY_THE_BOOK, HABITUAL, STYLES, TELL_READER } from "./players.ts";
import { num, pct, table } from "./report.ts";

const SPIKE_PARTY: SubclassId[] = ["gunman", "bulwark", "verdant", "hellbound"];
const SECOND_PARTY: SubclassId[] = ["warbound", "sanguine_aegis", "crystal_archer", "aether"];
const ORDINARY = ["habitual", "by-the-book", "adaptive"];
const DEFIERS = ["contrarian", "second-guesser"];

const { values: args } = parseArgs({ options: { quick: { type: "boolean", default: false } } });
const TUNE = { seed: 1, trials: args.quick ? 30 : 300, party: SPIKE_PARTY, styles: [HABITUAL, BY_THE_BOOK, ADAPTIVE, TELL_READER] };
const EVAL = { seed: 2, trials: args.quick ? 60 : 1000, parties: [SPIKE_PARTY, SECOND_PARTY] };
const ROUNDS = 10;

const BELIEF = makeC(TUNED_C);
/** Robustness: both defiance priors in model C lowered to 25% (M2 results, point 1). */
const LOW_DEFIANCE = makeC({
  ...TUNED_C,
  ad: { ...TUNED_C.ad, defiance: { ...TUNED_C.ad.defiance, prior: [1, 3] } },
  b: { ...TUNED_C.b, defiantPrior: 0.25 },
});

/** Bet success against ordinary play: the step's band, or null for Ruthless (the peak). As amended after the first run. */
const BANDS: Record<string, readonly [number, number] | null> = {
  curious: [0.25, 0.3],
  hunting: [0.3, 0.4],
  ruthless: null,
  wrathful: [0.3, 0.4],
  bloodlusted: [0.3, 0.4],
};
const PEAK_FLOOR = 0.45;
const RANDOM_CEILING = 0.25;
const SLACKS = [0, 0.05, 0.15, 0.3, 0.4];

type Levers = Partial<Pick<Temperament, "sharpness" | "mixing" | "rashness" | "slack">>;

const placeholder = (id: string) => PLACEHOLDER_STEPS.find((s) => s.id === id)!;
const withLevers = (step: Temperament, levers: Levers): Temperament => ({ ...step, ...levers });

/** Each step's grid of free levers (the protocol's tuning table), given the steps tuned before it. */
function gridFor(id: string, tuned: Record<string, Temperament>): Levers[] {
  switch (id) {
    case "curious":
      return product({ sharpness: [0.3, 0.45, 0.6, 0.75, 0.9], mixing: [0.07, 0.15, 0.3, 0.5] });
    case "hunting":
      return product({ sharpness: [0.6, 0.75, 0.85, 0.95, 1], mixing: [0.03, 0.07, 0.15, 0.3] }).filter(
        (l) => l.sharpness >= tuned["curious"]!.sharpness,
      );
    case "ruthless":
      return product({ mixing: [0, 0.03, 0.07, 0.15, 0.3] });
    case "wrathful":
      return product({ rashness: [0.2, 0.3, 0.4, 0.5, 0.6] });
    case "bloodlusted":
      return product({ rashness: [0.5, 0.65, 0.8, 0.9, 0.95] }).filter((l) => l.rashness > tuned["wrathful"]!.rashness);
    default:
      throw new Error(`no grid for ${id}`);
  }
}

const successOf = (r: BetSuiteResult, ids: readonly string[]) =>
  ids.reduce((s, id) => s + r.styles.find((x) => x.style === id)!.success, 0) / ids.length;

interface Point {
  readonly levers: Levers;
  readonly ordinary: number;
  readonly tellReader: number;
}

interface TunedStep {
  readonly id: string;
  readonly step: Temperament;
  readonly tried: readonly Point[];
  /** Whether a point landed in the band (always true for Ruthless). */
  readonly inBand: boolean;
  /** Whether the slack had to join the grid. */
  readonly slackJoined: boolean;
}

function tryPoints(id: string, levers: readonly Levers[], label = id): Point[] {
  return levers.map((l, i) => {
    const r = runBetSuite({ ...TUNE, rounds: ROUNDS, belief: BELIEF, step: withLevers(placeholder(id), l) });
    process.stderr.write(`\rtuning ${label}: ${i + 1}/${levers.length}   `);
    return { levers: l, ordinary: successOf(r, ORDINARY), tellReader: successOf(r, [TELL_READER.id]) };
  });
}

/** How far a point is from the placeholder, for breaking ties. */
function fromPlaceholder(id: string, l: Levers): number {
  const p = placeholder(id);
  return (Object.keys(l) as (keyof Levers)[]).reduce((s, k) => s + Math.abs((l[k] ?? p[k]) - p[k]), 0);
}

function pick(id: string, points: readonly Point[], by: (p: Point) => number): Point {
  return [...points].sort((x, y) => by(x) - by(y) || fromPlaceholder(id, x.levers) - fromPlaceholder(id, y.levers))[0]!;
}

function tuneStep(id: string, tuned: Record<string, Temperament>): TunedStep {
  const band = BANDS[id]!;
  const grid = gridFor(id, tuned);
  let tried = tryPoints(id, grid);
  process.stderr.write("\n");
  if (band === null) {
    const best = pick(id, tried, (p) => -(p.ordinary + p.tellReader) / 2);
    return { id, step: withLevers(placeholder(id), best.levers), tried, inBand: true, slackJoined: false };
  }
  const mid = (band[0] + band[1]) / 2;
  const inBand = (p: Point) => p.ordinary >= band[0] && p.ordinary <= band[1];
  const nearest = (ps: readonly Point[]) => pick(id, ps, (p) => Math.abs(p.ordinary - mid));
  if (tried.some(inBand)) {
    const best = nearest(tried.filter(inBand));
    return { id, step: withLevers(placeholder(id), best.levers), tried, inBand: true, slackJoined: false };
  }
  const wider = grid.flatMap((l) => SLACKS.map((slack) => ({ ...l, slack })));
  tried = [...tried, ...tryPoints(id, wider, `${id} with slack`)];
  process.stderr.write("\n");
  const landed = tried.filter(inBand);
  const best = nearest(landed.length ? landed : tried);
  return { id, step: withLevers(placeholder(id), best.levers), tried, inBand: landed.length > 0, slackJoined: true };
}

interface StepResult {
  readonly id: string;
  readonly name: string;
  readonly byParty: readonly BetSuiteResult[];
  readonly ordinary: number;
  readonly random: number;
  readonly defiers: number;
  readonly tellReader: number;
  /** Mean over all styles. */
  readonly fixation: number;
  readonly predictability: number;
  readonly exploitability: number;
  readonly readability: number;
  readonly betsPerFight: number;
}

function evaluate(step: Temperament, belief: BeliefFactory, label: string): StepResult {
  process.stderr.write(`evaluating ${step.id}${label}\n`);
  const byParty = EVAL.parties.map((party) =>
    runBetSuite({ seed: EVAL.seed, trials: EVAL.trials, rounds: ROUNDS, party, styles: STYLES, belief, step }),
  );
  const mean = (f: (r: BetSuiteResult) => number) => byParty.reduce((s, r) => s + f(r), 0) / byParty.length;
  const overStyles = (f: (s: BetSuiteResult["styles"][number]) => number) =>
    mean((r) => r.styles.reduce((s, x) => s + f(x), 0) / r.styles.length);
  const ordinary = mean((r) => successOf(r, ORDINARY));
  const defiers = mean((r) => successOf(r, DEFIERS));
  const tellReader = mean((r) => successOf(r, [TELL_READER.id]));
  return {
    id: step.id,
    name: step.name,
    byParty,
    ordinary,
    random: mean((r) => successOf(r, ["random"])),
    defiers,
    tellReader,
    fixation: overStyles((s) => s.fixation),
    predictability: overStyles((s) => s.predictability),
    exploitability: ordinary - defiers,
    readability: ordinary - tellReader,
    betsPerFight: overStyles((s) => s.betsPerFight),
  };
}

interface Check {
  readonly target: string;
  readonly passed: boolean;
  readonly detail: string;
}

function check(results: readonly StepResult[]): Check[] {
  const by = (id: string) => results.find((r) => r.id === id)!;
  const [cur, hun, rut, wra, blo] = [by("curious"), by("hunting"), by("ruthless"), by("wrathful"), by("bloodlusted")];
  const bandDetail = results.map((r) => {
    const band = BANDS[r.id];
    const ok = band
      ? r.ordinary >= band[0] && r.ordinary <= band[1]
      : r.ordinary >= PEAK_FLOOR && results.every((x) => x.ordinary <= r.ordinary);
    const want = band ? `${pct(band[0])}–${pct(band[1])}` : `highest, ≥ ${pct(PEAK_FLOOR)}`;
    return { ok, text: `${r.name} ${pct(r.ordinary)} (${want})${ok ? "" : " ✗"}` };
  });
  const maxFixation = Math.max(...results.map((r) => r.fixation));
  return [
    { target: "1. Each step in its band", passed: bandDetail.every((d) => d.ok), detail: bandDetail.map((d) => d.text).join("; ") },
    {
      target: "2. Rises to Ruthless, then falls",
      passed: cur.ordinary < hun.ordinary && hun.ordinary < rut.ordinary && rut.ordinary > wra.ordinary && wra.ordinary > blo.ordinary,
      detail: results.map((r) => pct(r.ordinary)).join(" → "),
    },
    {
      target: `3. Random at most ${pct(RANDOM_CEILING)}`,
      passed: results.every((r) => r.random <= RANDOM_CEILING),
      detail: results.map((r) => `${r.name} ${pct(r.random)}`).join(", "),
    },
    {
      target: "4. Fixation highest at Bloodlusted; exploitability higher than Ruthless's",
      passed: blo.fixation === maxFixation && blo.exploitability > rut.exploitability,
      detail: `fixation ${num(blo.fixation, 2)} (highest ${num(maxFixation, 2)}); exploitability ${num(blo.exploitability * 100, 0)} against ${num(rut.exploitability * 100, 0)} points`,
    },
    {
      target: "5. Predictability higher at Bloodlusted than at Ruthless",
      passed: blo.predictability > rut.predictability,
      detail: `${num(blo.predictability, 2)} against ${num(rut.predictability, 2)} (readability, reported but no longer a target: ${num(blo.readability * 100, 0)} against ${num(rut.readability * 100, 0)} points)`,
    },
  ];
}

function markdown(tuned: readonly TunedStep[], results: readonly StepResult[], checks: readonly Check[], robust: readonly StepResult[], robustChecks: readonly Check[]): string {
  const out: string[] = [];
  const partyName = (p: readonly SubclassId[]) => p.map((s) => SUBCLASSES[s].name).join(", ");
  const passed = checks.every((c) => c.passed);

  out.push("# M3: calibrating the temperament steps", "");
  out.push(
    'The protocol is in DESIGN.md, section 8, "M3 protocol". ' +
      `Tuning: seed ${TUNE.seed}, ${TUNE.trials} fights per style, ${partyName(TUNE.party)}, styles ${TUNE.styles.map((s) => s.name).join(", ")}. ` +
      `Held out: seed ${EVAL.seed}, ${EVAL.trials} fights per style, all ${STYLES.length} styles, on each of two parties. ` +
      `Every fight is ${ROUNDS} rounds with one bet a round at most, and every hero in a fight plays the same style. ` +
      "Belief: model C at its M2 settings." +
      (args.quick ? " **This was a --quick run: too few fights for the verdict to mean anything.**" : ""),
    "",
  );

  out.push("## Verdict", "");
  out.push(passed ? "**Every target holds: M3 is done.**" : "**Not every target holds.** The protocol's next step is a change to the failing steps' fixed levers, written down in DESIGN.md before a rerun.", "");
  out.push(table(["Target", "Passed", "Detail"], checks.map((c) => [c.target, c.passed ? "yes" : "**no**", c.detail]), 3), "");

  out.push("## The tuned steps", "");
  out.push("Fixed levers as in DESIGN.md 5.2; the tuned ones are in bold.", "");
  out.push(
    table(
      ["Step", "Slack", "Mixing", "β", "Rashness", "`spread`", "`tempo`", "Explore", "Disclosure", "Note"],
      tuned.map((t) => {
        const s = t.step;
        const free = new Set(Object.keys(t.tried[0]?.levers ?? {}).concat(t.slackJoined ? ["slack"] : []));
        const show = (k: string, v: string) => (free.has(k) ? `**${v}**` : v);
        const note = !t.inBand ? "no point in the band" : t.slackJoined ? "slack joined the grid" : "";
        return [
          s.name,
          show("slack", pct(s.slack)),
          show("mixing", String(s.mixing)),
          show("sharpness", String(s.sharpness)),
          show("rashness", String(s.rashness)),
          String(s.weights.spread),
          String(s.weights.tempo),
          String(s.explore),
          s.disclosure,
          note,
        ];
      }),
      1,
    ),
    "",
  );

  const stepTable = (rs: readonly StepResult[]) =>
    table(
      ["Step", "Ordinary", "Random", "Defiers", "Tell-reader", "Exploitability", "Readability", "Fixation", "Predictability", "Bets / fight"],
      rs.map((r) => [
        r.name,
        `**${pct(r.ordinary)}**`,
        pct(r.random),
        pct(r.defiers),
        pct(r.tellReader),
        num(r.exploitability * 100, 0),
        num(r.readability * 100, 0),
        num(r.fixation, 2),
        num(r.predictability, 2),
        num(r.betsPerFight, 1),
      ]),
    );

  out.push("## Held-out results", "");
  out.push(
    "Bet success, mean over the two parties. Ordinary is the mean over Habitual, By the book and Adaptive; Defiers over Contrarian and Second-guesser. " +
      "Exploitability is ordinary minus defiers and readability ordinary minus Tell-reader, in percentage points. " +
      "Fixation and predictability are means over all styles.",
    "",
  );
  out.push(stepTable(results), "");
  EVAL.parties.forEach((p, i) => out.push(`Party ${i + 1}: ${partyName(p)}.`));
  out.push("");

  EVAL.parties.forEach((party, pi) => {
    out.push(`## Party ${pi + 1}, by style`, "");
    out.push(`${partyName(party)}. Bet success / fixation.`, "");
    out.push(
      table(
        ["Player", ...results.map((r) => r.name)],
        STYLES.map((style, si) => [
          style.name,
          ...results.map((r) => {
            const s = r.byParty[pi]!.styles[si]!;
            return `${pct(s.success)} / ${num(s.fixation, 2)}`;
          }),
        ]),
      ),
      "",
    );
  });

  out.push("## Robustness: defiance priors at 25%", "");
  out.push(
    "The same steps, held out the same way, with model C's two defiance priors lowered to 25%. " +
      "A failure here doesn't block M3; it is the first thing for playtests (M6) to check.",
    "",
  );
  out.push(stepTable(robust), "");
  out.push(table(["Target", "Passed", "Detail"], robustChecks.map((c) => [c.target, c.passed ? "yes" : "**no**", c.detail]), 3), "");

  out.push("## Tuning", "");
  for (const t of tuned) {
    out.push(`### ${t.step.name}`, "");
    const keys = [...new Set(t.tried.flatMap((p) => Object.keys(p.levers)))] as (keyof Levers)[];
    out.push(
      table(
        [...keys, "Ordinary", "Tell-reader"],
        t.tried.map((p) => [...keys.map((k) => String(p.levers[k] ?? "–")), pct(p.ordinary), pct(p.tellReader)]),
        0,
      ),
      "",
    );
  }
  return out.join("\n");
}

function main(): void {
  const started = Date.now();
  const tuned: Record<string, Temperament> = {};
  const tunedSteps: TunedStep[] = [];
  for (const { id } of PLACEHOLDER_STEPS) {
    const t = tuneStep(id, tuned);
    tuned[id] = t.step;
    tunedSteps.push(t);
  }

  const results = tunedSteps.map((t) => evaluate(t.step, BELIEF, ""));
  const checks = check(results);
  const robust = tunedSteps.map((t) => evaluate(t.step, LOW_DEFIANCE, " (defiance priors at 25%)"));
  const robustChecks = check(robust);

  const md = markdown(tunedSteps, results, checks, robust, robustChecks);
  console.log(md);

  const name = args.quick ? "m3-temperament-quick" : "m3-temperament";
  const dir = new URL("../../reports/", import.meta.url);
  mkdirSync(dir, { recursive: true });
  writeFileSync(new URL(`${name}.md`, dir), md);
  const json = {
    protocol: { tune: { ...TUNE, styles: TUNE.styles.map((s) => s.id) }, eval: EVAL, rounds: ROUNDS, bands: BANDS, peakFloor: PEAK_FLOOR },
    tuned: tunedSteps,
    results,
    checks,
    robustness: { results: robust, checks: robustChecks },
  };
  writeFileSync(new URL(`${name}.json`, dir), JSON.stringify(json, null, 2) + "\n");
  console.error(`Wrote reports/${name}.md and reports/${name}.json in ${((Date.now() - started) / 1000).toFixed(0)}s`);
}

main();
