import { argmax, normalize, type Distribution } from "../actions.ts";

/**
 * What a player does when they dodge a prophecy: anything but the action they
 * would usually take, in the proportions they usually take the others. A
 * little `leak` stays on the usual action, since nobody dodges perfectly and a
 * zero would make one surprise infinitely costly.
 */
export function dodge(usual: Distribution, leak = 0.02): number[] {
  const top = argmax(usual);
  const rest = normalize(usual.map((p, i) => (i === top ? 0 : p)));
  return rest.map((p, i) => (i === top ? leak : p * (1 - leak)));
}
