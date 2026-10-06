# The boss brain

A Bayesian decision engine for bosses: it watches how the players play,
builds a belief about each of them, and picks whatever move it judges most
profitable for the boss, played as well as its temperament lets it: best
when cold (Ruthless), worse when Curious or Bloodlusted. The
Threadkeeper Failed Prophet is the first boss to use it. The why and the how
are in [DESIGN.md](DESIGN.md); this file covers running the code.

Where the project is (DESIGN.md section 10): **M0 design**, **M1 harness**
and **M2 belief** are done; the chosen belief model is C, the ensemble
([reports/m2-belief.md](reports/m2-belief.md)). **M2b** tested reading
players who read the boss and kept C as it was
([reports/m2b-wary.md](reports/m2b-wary.md)). **M3**, decision and
temperament, is done: the five steps are calibrated
([reports/m3-temperament.md](reports/m3-temperament.md)). M4, the Prophet
module, is next.

## Layout

```
src/engine/            what the real engine will be built from
  actions.ts           the five action categories the DM records
  subclasses.ts        each subclass's prior shape of a turn
  rng.ts               seeded random numbers
  belief/types.ts      the BeliefModel interface every candidate model implements
  belief/counts.ts     model A, "counts" (ported from the spike)
  belief/defiance.ts   the defiance layer, wrapped around any model (`ad` = A + this)
  belief/dodge.ts      what "dodging a prophecy" means, shared by the defiance models
  belief/archetypes.ts model B, "archetypes": a Bayesian posterior over player types
  belief/ensemble.ts   model C: Bayesian model averaging over other models
  decision/temperament.ts  the temperament steps and their levers (DESIGN.md 5)
  decision/decide.ts   expected utility, care, mixing, sharpness, rashness, exploration
src/harness/           the research harness (DESIGN.md 8)
  players.ts           synthetic players, nine styles (M2 used the first eight)
  fight.ts             one simulated fight, for any Prophet; the spike's prophecy policy
  metrics.ts           forecast and prophecy scores
  suite.ts             every style × N fights
  report.ts, cli.ts    the report and the command line
  candidates.ts        the M2 candidates and their tuning grids
  compare.ts           the M2 protocol: tune, evaluate on held-out data, choose
  m2b.ts               the M2b protocol: should the belief read players who read the boss?
  bettor.ts            M3's baseline module: one bet a round, chosen under a temperament
  m3.ts                the M3 protocol: calibrate the temperament steps
test/                  unit tests, including one that pins the spike's numbers
reports/               harness output: <name>.md to read, <name>.json raw
prophet/model.js       the original throwaway spike, kept for reference
```

## Running it

Needs Node 22.18 or newer, which runs the TypeScript directly with no build
step. From this folder:

```
npm install                                      # once: TypeScript, for type-checking only
npm test                                         # unit tests (a few seconds)
npm run check                                    # type-check
npm run harness                                  # every style, 1000 fights each → reports/baseline.md
npm run harness -- --trials 200 --no-write       # quick look, writes nothing
npm run harness -- --styles contrarian,random
npm run harness -- --party gunman,bulwark --rounds 6
npm run harness -- --name low-memory --memory 0.7    # an experiment → reports/low-memory.md
npm run harness -- --belief b --name archetypes      # another belief model: a, ad, b or c
npm run compare                                  # the M2 protocol → reports/m2-belief.md (several minutes)
npm run compare -- --quick                       # smoke test of the protocol; not results, not committed
npm run compare:m2b                              # the M2b protocol → reports/m2b-wary.md (several minutes)
npm run compare:m3                               # the M3 protocol → reports/m3-temperament.md (about 15 minutes)
```

Or from the repo root: `make boss-brain-test` and `make boss-brain-harness
ARGS="--trials 200"`.

The run is deterministic: the same options and seed give the same numbers.
Each style's fights are seeded by the style's id, so a style's numbers don't
move when other styles are added or left out.

Options: `--trials`, `--rounds`, `--seed`, `--party` (subclass ids from
`src/engine/subclasses.ts`), `--styles` (ids from `src/harness/players.ts`),
`--name`, `--no-write`, `--belief`; for belief model A only, `--prior-strength`, `--memory`,
`--pattern-prior`; for the baseline prophecy policy, `--threshold`,
`--per-round`, `--rewind-cost`.

## Reading a report

**Forecasts** scores the belief model on every hero turn, against the
forecast it made just before the turn. Guessing blind scores 20% accuracy, a
log loss of 1.61 and a Brier score of 0.80; lower log loss and Brier are
better. *Calibration error* is how far the model's confidence is from how
often it turns out right. The three round columns show how fast a style is
read.

**Prophecies** runs the spike's policy on top of the belief: each round,
foretell the most likely action of the most predictable hero. It is a fixed
yardstick for comparing belief models, not the Prophet's design; that is M4.

**Named turns** (in the JSON, and in the M2 report) score only the turns
where the boss had named the hero. That is where defiance shows.

## Adding a belief model

Implement `BeliefModel` from `src/engine/belief/types.ts` and export a
factory like `countsBelief`. Besides `forecast` and `observe`, a model is
told every bet the boss has revealed (`reveal`); a model that doesn't use
them says so with an empty method, as model A does. To put it through the M2 protocol, add it with a
tuning grid to `src/harness/candidates.ts` and `src/harness/compare.ts`. The
harness only ever talks to the interface, so the same styles, metrics and
seeds apply to every candidate.

## Adding a player style

Add a `Style` to `src/harness/players.ts` and list it in `STYLES`. A style
sees what a player at the table would: the round, whether the boss named it,
its own past actions, and the prophecies about it revealed so far.
