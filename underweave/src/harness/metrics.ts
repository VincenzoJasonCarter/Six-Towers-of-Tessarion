import { argmax, type Action, type Distribution } from "../engine/actions.ts";
import type { FightRecord, TurnRecord } from "./fight.ts";

const BINS = 10;
/** Round brackets for "how quickly is a player read": early, middle, late. */
export const PHASES = [
  { label: "Rounds 1–3", from: 1, to: 3 },
  { label: "4–6", from: 4, to: 6 },
  { label: "7+", from: 7, to: Infinity },
] as const;

export interface CalibrationBin {
  readonly from: number;
  readonly to: number;
  readonly turns: number;
  /** Average confidence of the top forecast in this bin. */
  readonly said: number;
  /** How often the top forecast happened. */
  readonly happened: number;
}

export interface ForecastSummary {
  readonly turns: number;
  /** How often the most likely action was the one taken. */
  readonly accuracy: number;
  readonly accuracyByPhase: readonly (number | null)[];
  /** Mean -ln p(action taken). ln 5 ≈ 1.609 for a uniform forecast. */
  readonly logLoss: number;
  /** Mean squared error over all five actions. 0.8 for a uniform forecast. */
  readonly brier: number;
  /** Expected calibration error of the top forecast: 0 means "60% sure" is right 60% of the time. */
  readonly calibrationError: number;
  readonly calibration: readonly CalibrationBin[];
}

/** Scores forecasts against what happened. */
export class ForecastScore {
  #turns = 0;
  #hits = 0;
  #logLoss = 0;
  #brier = 0;
  readonly #bins = Array.from({ length: BINS }, () => ({ turns: 0, said: 0, hits: 0 }));
  readonly #phases = PHASES.map(() => ({ turns: 0, hits: 0 }));

  add(forecast: Distribution, action: Action, round: number): void {
    const top = argmax(forecast);
    const hit = top === action ? 1 : 0;
    this.#turns += 1;
    this.#hits += hit;
    this.#logLoss -= Math.log(Math.max(forecast[action]!, 1e-12));
    this.#brier += forecast.reduce((s, p, i) => s + (p - (i === action ? 1 : 0)) ** 2, 0);
    const bin = this.#bins[Math.min(BINS - 1, Math.floor(forecast[top]! * BINS))]!;
    bin.turns += 1;
    bin.said += forecast[top]!;
    bin.hits += hit;
    const phase = this.#phases[PHASES.findIndex((ph) => round >= ph.from && round <= ph.to)];
    if (phase) {
      phase.turns += 1;
      phase.hits += hit;
    }
  }

  /** Score a fight's turns, or only those that pass `only`. */
  addFight(fight: FightRecord, only: (t: TurnRecord) => boolean = () => true): void {
    for (const t of fight.turns) if (only(t)) this.add(t.forecast, t.action, t.round);
  }

  /** With no turns scored, every average is NaN. */
  summary(): ForecastSummary {
    const n = this.#turns;
    const calibration = this.#bins
      .map((b, i) => ({
        from: i / BINS,
        to: (i + 1) / BINS,
        turns: b.turns,
        said: b.turns ? b.said / b.turns : 0,
        happened: b.turns ? b.hits / b.turns : 0,
      }))
      .filter((b) => b.turns > 0);
    return {
      turns: n,
      accuracy: this.#hits / n,
      accuracyByPhase: this.#phases.map((ph) => (ph.turns ? ph.hits / ph.turns : null)),
      logLoss: this.#logLoss / n,
      brier: this.#brier / n,
      calibrationError: calibration.reduce((s, b) => s + (b.turns / n) * Math.abs(b.happened - b.said), 0),
      calibration,
    };
  }
}

export interface ProphecySummary {
  readonly fights: number;
  readonly spokenPerFight: number;
  readonly hitRate: number;
  readonly chargesPerFight: number;
  /** Share of fights in which charges reached the rewind cost. */
  readonly rewindReached: number;
  /** Average round in which that happened, over the fights where it did. */
  readonly firstRewindRound: number | null;
}

/** Scores the baseline Prophet's prophecies, fight by fight. */
export class ProphecyScore {
  #fights = 0;
  #spoken = 0;
  #fulfilled = 0;
  #reached = 0;
  #firstRewindRounds = 0;

  addFight(fight: FightRecord): void {
    this.#fights += 1;
    this.#spoken += fight.prophecies.length;
    this.#fulfilled += fight.prophecies.filter((p) => p.fulfilled).length;
    if (fight.firstRewindRound !== null) {
      this.#reached += 1;
      this.#firstRewindRounds += fight.firstRewindRound;
    }
  }

  summary(): ProphecySummary {
    const f = this.#fights;
    return {
      fights: f,
      spokenPerFight: this.#spoken / f,
      hitRate: this.#spoken ? this.#fulfilled / this.#spoken : 0,
      chargesPerFight: this.#fulfilled / f,
      rewindReached: this.#reached / f,
      firstRewindRound: this.#reached ? this.#firstRewindRounds / this.#reached : null,
    };
  }
}
