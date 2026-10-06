import { ACTIONS, GUARD } from "../engine/actions.ts";
import type { Option } from "../engine/decision/decide.ts";
import type { ModuleFactory } from "../engine/module.ts";
import { announceRead, FIGHT_VALUE, heedModel, readOptions, spreadFor, type Read } from "./common.ts";

/** A plain attack: `lethal` 1 unless the target Guards. */
export const STRIKE_VALUE = 1;
/** A telegraphed big attack: `lethal` 1.5 unless the target Guards, and `show` 1. */
export const WIND_UP_VALUE = 1.5;
/** A readied reaction that cuts a hero's action: its fight value times this. */
export const INTERRUPT_FACTOR = 1.5;
/** The limited ability: an interrupt worth this much more. */
export const SIGNATURE_FACTOR = 3;
/** Signature uses per fight; they don't come back. */
export const SIGNATURE_BUDGET = 3;
/** How long the module expects a fight to last; at the table, the DM's guess. */
export const EXPECTED_ROUNDS = 10;

/**
 * The Placeholder Boss (DESIGN.md 6.2): a boss with no lore, to drape over
 * any monster's stat block until a real boss module exists. Each round it
 * makes one move:
 *
 *   strike     the monster's ordinary attack
 *   wind-up    its big attack, announced at the start of the round
 *   interrupt  a readied reaction against one hero's action ("if Kael heals, I cut it")
 *   signature  its limited ability: an interrupt worth twice as much, three a fight
 *
 * One module, so the shapes of decision M4 tested one at a time compete in
 * one choice. A signature spends a use, which costs the `tempo` of holding it:
 * the share of the fight still to come, as in Spend or hold.
 */
export type PlaceholderMove =
  | { readonly kind: "strike" | "wind-up"; readonly hero: string }
  | ({ readonly kind: "interrupt" | "signature" } & Read);

const holdValue = (round: number) => Math.max(0, EXPECTED_ROUNDS - round) / EXPECTED_ROUNDS;

/**
 * How the Placeholder fits the monster it is draped over (DESIGN.md 6.2,
 * "Fitting the Placeholder"). The defaults are the boss M4b checked.
 */
export interface PlaceholderConfig {
  /** Strike's `lethal`: 2 for a monster with a two-attack Multiattack. */
  readonly strike: number;
  /** Whether the monster has a reaction to ready; most have none. */
  readonly interrupt: boolean;
  /** Its limited ability: a number of uses, or a 5e recharge (the chance each round it comes back). */
  readonly signature: { readonly uses: number } | { readonly recharge: number };
}

export const PLACEHOLDER_DEFAULTS: PlaceholderConfig = {
  strike: STRIKE_VALUE,
  interrupt: true,
  signature: { uses: SIGNATURE_BUDGET },
};

/** Recharge 5–6 on a d6. */
export const RECHARGE_5_6 = 1 / 3;

export const placeholderWith = (over: Partial<PlaceholderConfig> = {}): ModuleFactory<PlaceholderMove> => (heroes, rng) => {
  const config = { ...PLACEHOLDER_DEFAULTS, ...over };
  const recharge = "recharge" in config.signature ? config.signature.recharge : null;
  let last: string | null = null;
  // With a recharge, one use is ready at a time and comes back on a roll at the start of a round.
  let signatures = recharge === null ? (config.signature as { uses: number }).uses : 1;
  const heed = heedModel(heroes);
  /** What spending a use costs: holding it is worth the share of the fight to come, less the chance it comes back anyway. */
  const signatureCost = (round: number) => holdValue(round) * (recharge === null ? 1 : 1 - recharge);
  return {
    id: "placeholder",
    options(moment, ctx) {
      if (moment.kind !== "round") return [];
      const { round } = moment;
      if (recharge !== null && signatures === 0 && round > 1 && rng.next() < recharge) signatures = 1;
      const options: Option<PlaceholderMove>[] = [];
      for (const hero of ctx.heroes) {
        const spread = spreadFor(last, hero.id);
        const guards = heed.look(hero.id, round, ctx);
        options.push({
          move: { kind: "strike", hero: hero.id },
          outcomes: [
            { p: 1 - guards.unwarned, utility: { lethal: config.strike, spread } },
            { p: guards.unwarned, utility: { spread } },
          ],
        });
        options.push({
          move: { kind: "wind-up", hero: hero.id },
          outcomes: [
            { p: 1 - guards.warned, utility: { lethal: WIND_UP_VALUE, show: 1, spread } },
            { p: guards.warned, utility: { show: 1, spread } },
          ],
          waiting: true,
        });
      }
      if (config.interrupt) {
        const interrupts = readOptions(
          round,
          ctx,
          last,
          (action) => ({ lethal: INTERRUPT_FACTOR * FIGHT_VALUE[action]! }),
          (read): PlaceholderMove => ({ kind: "interrupt", ...read }),
        );
        // A readied reaction waits for its trigger; a signature is let loose on the boss's own turn.
        options.push(...interrupts.map((o) => ({ ...o, waiting: true })));
      }
      if (signatures > 0) {
        const cost = signatureCost(round);
        const uses = readOptions(
          round,
          ctx,
          last,
          (action) => ({ lethal: SIGNATURE_FACTOR * FIGHT_VALUE[action]! }),
          (read): PlaceholderMove => ({ kind: "signature", ...read }),
          { probe: false },
        );
        // Spending a use forfeits what holding it was worth, hit or miss.
        options.push(...uses.map((o) => ({ ...o, outcomes: o.outcomes.map((x) => ({ ...x, utility: { ...x.utility, tempo: -cost } })) })));
      }
      return options;
    },
    describe(move) {
      switch (move.kind) {
        case "strike":
          return `Strike ${move.hero}`;
        case "wind-up":
          return `Wind up the big attack at ${move.hero}`;
        case "interrupt":
          return `Ready a reaction: cut ${move.hero}'s ${ACTIONS[move.action]!.label}`;
        case "signature":
          return `Signature on ${move.hero}'s ${ACTIONS[move.action]!.label}`;
      }
    },
    announce(move, step) {
      switch (move.kind) {
        case "strike":
          return { named: [], warned: [], text: "" };
        case "wind-up":
          return { named: [], warned: [move.hero], text: `The boss winds up its big attack at ${move.hero}.` };
        case "interrupt":
          return announceRead(move, step.disclosure, "is ready to cut it");
        case "signature":
          return announceRead(move, step.disclosure, "is ready to answer it with everything it has");
      }
    },
    resolve(move, moment, { actions }) {
      const spread = spreadFor(last, move.hero);
      last = move.hero;
      const action = actions.get(move.hero);
      const guard = action === GUARD;
      switch (move.kind) {
        case "strike":
          return { kind: "strike", utility: { lethal: guard ? 0 : config.strike, spread }, bets: [] };
        case "wind-up":
          heed.learn(move.hero, guard);
          return { kind: "wind-up", utility: { lethal: guard ? 0 : WIND_UP_VALUE, show: 1, spread }, bets: [] };
        case "interrupt":
        case "signature": {
          const fulfilled = action === move.action;
          const factor = move.kind === "interrupt" ? INTERRUPT_FACTOR : SIGNATURE_FACTOR;
          const tempo = move.kind === "signature" ? -signatureCost(moment.round) : 0;
          if (move.kind === "signature") signatures -= 1;
          return {
            kind: move.kind,
            utility: { lethal: fulfilled ? factor * FIGHT_VALUE[move.action]! : 0, spread, tempo },
            bets: [{ hero: move.hero, action: move.action, fulfilled }],
            ...(move.kind === "signature" ? { detail: { signatureRound: moment.round } } : {}),
          };
        }
      }
    },
  };
};

/** The Placeholder Boss as M4b checked it. */
export const placeholder: ModuleFactory<PlaceholderMove> = placeholderWith();
