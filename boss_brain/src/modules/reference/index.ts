import type { ModuleFactory } from "../../engine/module.ts";
import { bet } from "./bet.ts";
import { punish } from "./punish.ts";
import { spendOrHold } from "./spend.ts";
import { telegraph } from "./telegraph.ts";

/** The four reference modules of DESIGN.md 6.1, the engine's test bench. */
export const REFERENCE_MODULES: readonly { readonly id: string; readonly name: string; readonly make: ModuleFactory<unknown> }[] = [
  { id: "bet", name: "Bet", make: bet as ModuleFactory<unknown> },
  { id: "punish", name: "Punish", make: punish as ModuleFactory<unknown> },
  { id: "spend-or-hold", name: "Spend or hold", make: spendOrHold as ModuleFactory<unknown> },
  { id: "telegraph", name: "Telegraph", make: telegraph as ModuleFactory<unknown> },
];

export { bet, punish, spendOrHold, telegraph };
