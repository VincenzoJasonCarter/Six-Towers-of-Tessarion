import { GUARD, K, SHOOT, STRIKE, type Action } from "../engine/actions.ts";
import type { Rng } from "../engine/rng.ts";
import { mainAction, shapeOf, type SubclassId } from "../engine/subclasses.ts";

/** A prophecy about this hero, as the table heard it once its round was over. */
export interface Told {
  readonly round: number;
  readonly action: Action;
  readonly fulfilled: boolean;
}

/** What a synthetic player knows when choosing its action. */
export interface PlayerView {
  readonly round: number;
  /** The boss named this hero this round. */
  readonly named: boolean;
  /** This hero's own actions so far this fight. */
  readonly history: readonly Action[];
  /** Past prophecies about this hero, revealed after their rounds. */
  readonly told: readonly Told[];
}

export interface Player {
  act(view: PlayerView): Action;
}

/** A way of playing (DESIGN.md 8), which makes one Player per hero. */
export interface Style {
  readonly id: string;
  readonly name: string;
  readonly plays: string;
  make(subclass: SubclassId, rng: Rng): Player;
}

const draw = (rng: Rng, weights: readonly number[]): Action => rng.weighted(weights) as Action;

/** The subclass shape with one action ruled out. */
function without(subclass: SubclassId, banned: Action): number[] {
  return shapeOf(subclass).map((p, i) => (i === banned ? 0 : p));
}

/** The action this hero has taken most so far; on a tie, the one its subclass favours. */
function mostUsed(history: readonly Action[], subclass: SubclassId): Action {
  if (history.length === 0) return mainAction(subclass);
  const counts = new Array<number>(K).fill(0);
  for (const a of history) counts[a]! += 1;
  const shape = shapeOf(subclass);
  let best = 0;
  for (let i = 1; i < K; i++) {
    if (counts[i]! > counts[best]! || (counts[i] === counts[best] && shape[i]! > shape[best]!)) best = i;
  }
  return best as Action;
}

export const HABITUAL: Style = {
  id: "habitual",
  name: "Habitual",
  plays: "the subclass's main action 9 times in 13, anything else otherwise",
  make(subclass, rng) {
    const main = mainAction(subclass);
    const weights = Array.from({ length: K }, (_, i) => (i === main ? 9 : 1));
    return { act: () => draw(rng, weights) };
  },
};

export const BY_THE_BOOK: Style = {
  id: "by-the-book",
  name: "By the book",
  plays: "the subclass's usual mix, exactly as the prior assumes",
  make(subclass, rng) {
    return { act: () => draw(rng, shapeOf(subclass)) };
  },
};

export const RANDOM: Style = {
  id: "random",
  name: "Random",
  plays: "uniformly at random, ignoring everything (the floor)",
  make(_subclass, rng) {
    return { act: () => rng.int(K) as Action };
  },
};

export const ALTERNATOR: Style = {
  id: "alternator",
  name: "Alternator",
  plays: "Strike, Guard, Strike, Guard, ...",
  make() {
    return { act: ({ history }) => (history.length % 2 === 0 ? STRIKE : GUARD) };
  },
};

export const SWITCHER: Style = {
  id: "switcher",
  name: "Switcher",
  plays: "Shoot for four turns, then Strike for the rest of the fight",
  make() {
    return { act: ({ history }) => (history.length < 4 ? SHOOT : STRIKE) };
  },
};

export const CONTRARIAN: Style = {
  id: "contrarian",
  name: "Contrarian",
  plays: "by the book, but never its subclass's main action when named",
  make(subclass, rng) {
    const dodge = without(subclass, mainAction(subclass));
    return { act: ({ named }) => draw(rng, named ? dodge : shapeOf(subclass)) };
  },
};

export const SECOND_GUESSER: Style = {
  id: "second-guesser",
  name: "Second-guesser",
  plays: "by the book, but when named avoids whatever it has done most so far",
  make(subclass, rng) {
    return {
      act: ({ named, history }) =>
        draw(rng, named ? without(subclass, mostUsed(history, subclass)) : shapeOf(subclass)),
    };
  },
};

/** How hard a fulfilled prophecy puts the Adaptive player off that action, and how fast it gets over it. */
const BURN = 0.3;
const HEAL = 0.2;

export const ADAPTIVE: Style = {
  id: "adaptive",
  name: "Adaptive",
  plays: "by the book, but shies away from any action a prophecy caught it doing, and slowly forgets",
  make(subclass, rng) {
    const shape = shapeOf(subclass);
    const wary = new Array<number>(K).fill(1);
    let heard = 0;
    return {
      act({ told }) {
        for (; heard < told.length; heard++) {
          const t = told[heard]!;
          if (t.fulfilled) wary[t.action]! *= BURN;
        }
        const action = draw(rng, shape.map((p, i) => p * wary[i]!));
        for (let i = 0; i < K; i++) wary[i]! += (1 - wary[i]!) * HEAL;
        return action;
      },
    };
  },
};

/**
 * How much each bet the boss has made on an action puts the Tell-reader off
 * it. Unlike model B's wary players, it never forgets: the belief shouldn't
 * be graded against a copy of itself.
 */
const TELL = 0.5;

export const TELL_READER: Style = {
  id: "tell-reader",
  name: "Tell-reader",
  plays: "by the book, but steers away from the actions the boss has bet on about it, named or not",
  make(subclass, rng) {
    const shape = shapeOf(subclass);
    return {
      act({ told }) {
        const bets = new Array<number>(K).fill(0);
        for (const t of told) bets[t.action]! += 1;
        return draw(rng, shape.map((p, i) => p * TELL ** bets[i]!));
      },
    };
  },
};

/** The eight styles M2 chose its belief model against; its report keeps to them. */
export const M2_STYLES: readonly Style[] = [
  HABITUAL,
  BY_THE_BOOK,
  RANDOM,
  ALTERNATOR,
  SWITCHER,
  CONTRARIAN,
  SECOND_GUESSER,
  ADAPTIVE,
];

export const STYLES: readonly Style[] = [...M2_STYLES, TELL_READER];

export function styleById(id: string): Style {
  const style = STYLES.find((s) => s.id === id);
  if (!style) throw new Error(`No player style "${id}". Known: ${STYLES.map((s) => s.id).join(", ")}`);
  return style;
}
