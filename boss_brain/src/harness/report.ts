import { SUBCLASSES } from "../engine/subclasses.ts";
import { PHASES } from "./metrics.ts";
import type { SuiteResult } from "./suite.ts";

const missing = (x: number | null): x is null => x === null || Number.isNaN(x);
export const pct = (x: number | null) => (missing(x) ? "–" : `${Math.round(x * 100)}%`);
export const num = (x: number | null, digits = 1) => (missing(x) ? "–" : x.toFixed(digits));

/** A Markdown table; the first `textColumns` columns are left-aligned, the rest are numbers. */
export function table(head: readonly string[], rows: readonly (readonly string[])[], textColumns = 1): string {
  const align = head.map((_, i) => (i < textColumns ? "---" : "---:"));
  return [head, align, ...rows].map((r) => `| ${r.join(" | ")} |`).join("\n");
}

export function toMarkdown(result: SuiteResult, title: string): string {
  const party = result.party.map((s) => SUBCLASSES[s].name).join(", ");
  const { threshold, perRound, rewindCost } = result.policy;
  const out: string[] = [];

  out.push(`# Boss brain harness: ${title}`, "");
  out.push(
    `Belief model \`${result.belief}\` against a party of ${party}. ` +
      `${result.trials} fights of ${result.rounds} rounds per player style, seed ${result.seed}. ` +
      `Every hero in a fight plays the same style.`,
    "",
  );

  out.push("## Forecasts", "");
  out.push(
    "Every hero turn, scored on the forecast the belief made just before it. " +
      "Guessing blind gets 20% accuracy, a log loss of 1.61 and a Brier score of 0.80. " +
      "Calibration error is how far the forecasts' confidence is from how often they come true (0 is perfect).",
    "",
  );
  out.push(
    table(
      ["Player", "Accuracy", ...PHASES.map((p) => p.label), "Log loss", "Brier", "Calibration error"],
      [
        ...result.styles.map((s) => [
          s.name,
          pct(s.forecast.accuracy),
          ...s.forecast.accuracyByPhase.map(pct),
          num(s.forecast.logLoss, 2),
          num(s.forecast.brier, 2),
          num(s.forecast.calibrationError, 3),
        ]),
        [
          "**All**",
          pct(result.pooled.accuracy),
          ...result.pooled.accuracyByPhase.map(pct),
          num(result.pooled.logLoss, 2),
          num(result.pooled.brier, 2),
          num(result.pooled.calibrationError, 3),
        ],
      ],
    ),
    "",
  );

  out.push("## Prophecies (baseline policy)", "");
  out.push(
    `The spike's policy, standing in for the Prophet module until M4: each round it names ` +
      `${perRound === 1 ? "the hero" : `the ${perRound} heroes`} it reads most clearly and foretells ` +
      `their most likely action, or stays silent if no forecast reaches ${pct(threshold)}. ` +
      `A rewind becomes available at ${rewindCost} Echo Charges; charges are counted, never spent.`,
    "",
  );
  out.push(
    table(
      ["Player", "Spoken / fight", "Hit rate", "Charges / fight", "Fights reaching a rewind", "Avg. round of first rewind"],
      result.styles.map((s) => [
        s.name,
        num(s.prophecy.spokenPerFight),
        pct(s.prophecy.hitRate),
        num(s.prophecy.chargesPerFight),
        pct(s.prophecy.rewindReached),
        num(s.prophecy.firstRewindRound),
      ]),
    ),
    "",
  );

  out.push("## Calibration, all styles together", "");
  out.push("Turns grouped by how sure the top forecast was.", "");
  out.push(
    table(
      ["Confidence", "Turns", "Said", "Happened"],
      result.pooled.calibration.map((b) => [
        `${Math.round(b.from * 100)}–${Math.round(b.to * 100)}%`,
        String(b.turns),
        pct(b.said),
        pct(b.happened),
      ]),
    ),
    "",
  );

  out.push("## Player styles", "");
  out.push(table(["Player", "Plays"], result.styles.map((s) => [s.name, s.plays]), 2), "");
  return out.join("\n");
}
