/**
 * The boss brain's research harness: plays a belief model against synthetic
 * players and scores it (DESIGN.md 8).
 *
 * Usage, from boss_brain/:
 *
 *     npm run harness                                  # every style, 1000 fights each
 *     npm run harness -- --trials 200                  # quicker, noisier
 *     npm run harness -- --styles random,contrarian    # just these styles
 *     npm run harness -- --party gunman,bulwark --rounds 6
 *     npm run harness -- --name tuned --memory 0.8     # write reports/tuned.{md,json}
 *     npm run harness -- --belief b --name archetypes  # another belief model (a, ad, b, c)
 *
 * Prints the report and writes it to reports/<name>.md, with the raw numbers
 * in reports/<name>.json. Same options and seed, same numbers.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { countsBelief, COUNTS_DEFAULTS } from "../engine/belief/counts.ts";
import { DEFAULT_CANDIDATES } from "./candidates.ts";
import { isSubclass, SUBCLASSES, type SubclassId } from "../engine/subclasses.ts";
import { SPIKE_PROPHET } from "./fight.ts";
import { STYLES, styleById } from "./players.ts";
import { toMarkdown } from "./report.ts";
import { runSuite } from "./suite.ts";

const { values: args } = parseArgs({
  options: {
    trials: { type: "string", default: "1000" },
    rounds: { type: "string", default: "10" },
    seed: { type: "string", default: "1" },
    party: { type: "string", default: "gunman,bulwark,verdant,hellbound" },
    styles: { type: "string", default: STYLES.map((s) => s.id).join(",") },
    name: { type: "string", default: "baseline" },
    "no-write": { type: "boolean", default: false },
    belief: { type: "string", default: "a" },
    // belief model A only
    "prior-strength": { type: "string", default: String(COUNTS_DEFAULTS.priorStrength) },
    memory: { type: "string", default: String(COUNTS_DEFAULTS.memory) },
    "pattern-prior": { type: "string", default: String(COUNTS_DEFAULTS.patternPrior) },
    // baseline prophecy policy
    threshold: { type: "string", default: String(SPIKE_PROPHET.threshold) },
    "per-round": { type: "string", default: String(SPIKE_PROPHET.perRound) },
    "rewind-cost": { type: "string", default: String(SPIKE_PROPHET.rewindCost) },
  },
});

function number(name: string, raw: string, { min = -Infinity, max = Infinity, integer = false } = {}): number {
  const n = Number(raw);
  if (!Number.isFinite(n) || n < min || n > max || (integer && !Number.isInteger(n))) {
    throw new Error(`--${name} must be ${integer ? "an integer" : "a number"} between ${min} and ${max}, not "${raw}"`);
  }
  return n;
}

function main(): void {
  const party = args.party.split(",").map((s) => s.trim());
  const unknown = party.filter((s) => !isSubclass(s));
  if (unknown.length) {
    throw new Error(`Unknown subclass ${unknown.join(", ")}. Known: ${Object.keys(SUBCLASSES).join(", ")}`);
  }
  if (!/^[\w-]+$/.test(args.name)) throw new Error(`--name may only use letters, digits, - and _`);
  const candidate = DEFAULT_CANDIDATES[args.belief];
  if (!candidate) throw new Error(`Unknown --belief "${args.belief}". Known: ${Object.keys(DEFAULT_CANDIDATES).join(", ")}`);
  const countsFlags = ["prior-strength", "memory", "pattern-prior"] as const;
  if (args.belief !== "a" && countsFlags.some((f) => process.argv.includes(`--${f}`))) {
    throw new Error(`--${countsFlags.join(", --")} only apply to --belief a`);
  }

  const result = runSuite({
    seed: number("seed", args.seed, { min: 0, integer: true }),
    trials: number("trials", args.trials, { min: 1, integer: true }),
    rounds: number("rounds", args.rounds, { min: 1, integer: true }),
    party: party as SubclassId[],
    styles: args.styles.split(",").map((s) => styleById(s.trim())),
    belief:
      args.belief === "a"
        ? countsBelief({
            priorStrength: number("prior-strength", args["prior-strength"], { min: 0.01 }),
            memory: number("memory", args.memory, { min: 0, max: 1 }),
            patternPrior: number("pattern-prior", args["pattern-prior"], { min: 0, max: 1 }),
          })
        : candidate.make(),
    policy: {
      threshold: number("threshold", args.threshold, { min: 0, max: 1 }),
      perRound: number("per-round", args["per-round"], { min: 1, integer: true }),
      rewindCost: number("rewind-cost", args["rewind-cost"], { min: 1, integer: true }),
    },
  });

  const markdown = toMarkdown(result, args.name);
  console.log(markdown);
  if (!args["no-write"]) {
    const dir = new URL("../../reports/", import.meta.url);
    mkdirSync(dir, { recursive: true });
    writeFileSync(new URL(`${args.name}.md`, dir), markdown);
    writeFileSync(new URL(`${args.name}.json`, dir), JSON.stringify(result, null, 2) + "\n");
    console.error(`Wrote reports/${args.name}.md and reports/${args.name}.json`);
  }
}

try {
  main();
} catch (e) {
  console.error((e as Error).message);
  process.exit(1);
}
