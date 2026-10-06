# The Boss Brain: design

**Status:** 1.1, 2026-10-06. The open questions are closed (section 11).
M1 and M2 are done: the harness is in `src/harness/`, and the belief model
is chosen, model C (see [M2 results](#m2-results)). 1.1 redesigns the
temperament dial as a bell curve (section 5) and adds the
[M2b](#m2b-protocol) and [M3](#m3-protocol) protocols. The code in `prophet/` is the throwaway spike
(see [Spike results](#spike-results)), kept for reference only.

## 1. What this is

A decision engine for bosses, run by the DM at the table. During a fight it
watches what the players do, builds a belief about how each of them plays, and
uses that belief to choose whatever move it judges most profitable for the
boss. A **temperament** dial, from *Curious* through *Ruthless* to
*Bloodlusted*, decides how it pursues that profit. It plays best in the
middle, cold and focused, and worse at either end, for reasons the players
can read: a Curious boss is still learning, a Bloodlusted one is too angry
to think.

The model is Akinator's, aimed at the party: Akinator keeps a belief over who
you are thinking of, updates it with each answer, and guesses once it is sure
enough. The boss keeps a belief over how each player plays and updates it with
each turn. Instead of guessing, it acts on what it believes.

One engine, many bosses. The engine owns belief, decision and temperament.
Each boss is a **module** that supplies only what is unique to it: the moves it
has and what it counts as winning. The Threadkeeper Failed Prophet is the first
module. The Coin-Mad Hoardwyrm and the Sangrith Debt-Collector are the test of
whether the module interface is general enough (section 6.2).

## 2. Goals and non-goals

**Goals**

- **Adaptive.** The boss plays differently against a party that repeats itself
  than against one that mixes it up, and players can feel it learning.
- **Readable by players.** A party that pays attention can work out what the
  boss has learned and play around it. Beating the brain is part of the fight.
- **Explainable to the DM.** Every decision comes with its reasons ("named
  Kael: 64% he shoots, from his habit").
- **Tunable.** One temperament dial, calibrated so each step means something
  measurable.
- **Cheap at the table.** At most one tap per hero turn in normal play.
- **Reusable.** A new boss is a new module, not a new engine.

**Non-goals**

- Replacing the DM. The brain proposes, and the DM can always overrule.
- Simulating 5e combat. The arena (`../arena/`) does that and stays separate.
- Rolling dice, tracking HP or running initiative. The DM's existing tools do
  that.
- Playing optimally. Even at Ruthless, the goal is a boss that feels
  dangerous, not one that is provably best.

## 3. Terms

| Term | Meaning |
|---|---|
| **Observation** | What the DM records: mostly "hero X took action category Y". |
| **Belief** | The brain's probability model of each player, updated by observations. |
| **Profile** | One player's belief, which can carry over between fights and sessions. |
| **Option** | One move the boss could make right now (a prophecy, a bribe offer, a clause). |
| **Outcome** | What might happen after an option, with a probability taken from the belief. |
| **Utility** | How much the boss gains from an outcome, as scores along shared axes (5.2). |
| **Temperament** | The dial that turns expected utility into a choice (section 5). |
| **Module** | One boss: its options, outcomes, utility and what players are told. |

## 4. Architecture

```
          ┌───────────────────────────────────────────────────────┐
          │                                                       │
 DM taps  ▼                                                       │
 ──► Observe ──► Update belief ──► Enumerate options ──► Score ──► Choose ──► Explain
                     (engine)          (module)         (module   (engine,     (engine)
                                                       + engine)  temperament)    │
                                                                                  ▼
                                                           DM resolves it at the table
```

### 4.1 Observations

The DM records each hero's **main action** on their turn as one of five
categories. The categories come from the spike and should be revisited once
the harness exists:

| Category | Covers |
|---|---|
| Strike | melee weapon attack |
| Shoot | ranged weapon attack |
| Cast | attack or control spell |
| Mend | heal, buff, shield an ally |
| Guard | dodge, dash, hold, anything else |

Optional **context tags** could sharpen predictions, for example "an ally is
below half HP", "engaged in melee" or "was named by the boss this round". Each
one costs the DM a tap, so the engine starts with none (Q3). A tag is added
only when the harness shows it improves prediction enough to be worth its tap.

All observations go into one append-only **event log**. Belief, charges and
everything else are rebuilt by replaying it. That gives undo for free, makes
fights reproducible, and turns playtest logs into training data (section 9).

### 4.2 Belief

Each player has a profile that answers "what will they do next, given what I
have seen?". Three candidate models, to be compared in the harness:

- **A. Counts (the spike).** A Dirichlet over the five categories, seeded with
  the subclass's usual shape and updated each turn. A second, sequence model
  conditions on the previous action (it catches players who alternate), and
  the two are mixed by Bayesian model averaging. It is cheap and works, but it
  can't explain itself beyond "they shoot a lot".
- **B. Archetypes (Akinator-style).** A fixed set of player types (Brute,
  Medic, Opportunist, Alternator, Contrarian, ...), each with its own
  likelihood for actions in context. The belief is a posterior over types, so
  it can explain itself ("72% Contrarian"). It is only as good as the type list.
- **C. Ensemble (chosen in M2).** Bayesian model averaging of A (with a
  defiance layer) and B, weighted per player by how well each has predicted
  them. It gets "types plus individual quirks" without counting the same
  evidence twice, which a hierarchical model with archetypes as the prior
  would have done. See [M2 results](#m2-results).

**Being named is evidence.** When a boss announces something about a player
(the Prophet naming Kael), the player's reaction is itself behaviour: do they
comply, defy, or second-guess? The belief keeps a per-player **defiance** rate
(a Beta prior, updated each time they are named), and the forecast for a named
player shifts accordingly. A boss that knows Kael always dodges its prophecies
can foretell the dodge. This is what makes the Prophet more than a counter.

**Being read is evidence too.** Players learn the boss as the boss learns
them. Once the table has seen what the boss bet on a player (a prophecy,
opened or sealed, once its round is over), a wary player steers away from
those actions, named or not. The belief is told every bet the table has
seen, so it can recognise a player who has started playing the boss rather
than the fight ([M2b protocol](#m2b-protocol)).

**Memory.** Within a fight, older evidence fades by a forgetting factor, so a
player who changes style is followed. Between fights and sessions, profiles
persist, one per player rather than per character (Q5). The people at the table don't change, and a boss
that remembers them from last session is the payoff.

### 4.3 Modules

A module is a boss. It provides:

```
options(fight, belief)          -> list of Option        what the boss could do now
outcomes(option, fight, belief) -> list of (p, Outcome)  what might follow, using the belief
utility(outcome, fight)         -> {lethal, spread, show, tempo}   scores on shared axes
announce(option, reveal)        -> text for the players at the given reveal level
resolve(option, observations)   -> what actually happened, for the log
```

Utility is scored on **shared axes** rather than as one number, so the
temperament dial means the same thing for every boss:

| Axis | Rewards | Example |
|---|---|---|
| `lethal` | damage, downs, kills, denying healing | Prophet rewinds a heal |
| `spread` | involving every player, not tunnelling one | Prophet names someone new |
| `show` | drama: telegraphed attacks, theatrics, a puzzle for the table (not disclosure, which is temperament's, 5.1) | a boss winds up a big attack in plain sight |
| `tempo` | the boss's own resources: charges, actions, position | Prophet gains an Echo Charge |

### 4.4 Decision

For each option, expected utility is the probability-weighted sum over its
outcomes, with axes weighted by temperament:

```
EU(option) = Σ  p(outcome | option, belief) · Σ  w_axis(temperament) · utility_axis(outcome)
           outcomes                          axes
```

The choice itself is also governed by temperament (section 5). The engine
mixes two decision modes (Q6), with how much it explores set by temperament:

- **Exploit:** pick by EU on the current belief. Simple and predictable.
- **Explore/exploit:** occasionally pick an option because it would teach the
  brain the most, as Akinator picks the question that best splits its
  candidates. A Curious boss probes; a Ruthless one cashes in; a Bloodlusted
  one doesn't stop to ask. The engine's measure is the uncertainty of the
  forecast an option bets on (section 5.1, Exploration).

### 4.5 Explanation

Every decision is logged with the numbers behind it: the top options and their
EU, the forecast it relied on and which model produced it, and the temperament
in force. The DM sees this; the players see only what `announce` gives them.

## 5. Temperament

### 5.1 A bell curve, not a ramp

The dial sets how hot the boss runs, from cool interest to rage. How well it
plays follows a bell curve over the dial, as performance does over arousal
(the Yerkes–Dodson law): best in the middle, worse at both ends. The two
ends fall short for different reasons, and neither is random. A boss that
plays worse by rolling dice looks stupid; one that plays worse because it is
curious, or because it is furious, looks like a character, and the players
can learn to play around it.

- **Curious** is still learning. It spends bets probing players it can't
  read yet, hedges on what it has read, and shows its hand to see how the
  table reacts.
- **Ruthless** is the peak: cold, focused, using everything it has read, and
  keeping its bets to itself.
- **Bloodlusted** is enraged. It jumps to conclusions from one turn, fixes on
  one player and won't let go, and roars its intentions so the table hears
  them. It wants blood more than anything else on the dial, so what it does
  land is the most lethal; it just lands less. A party can bait it.

What the dial moves:

| Lever | What it does | Curious → Ruthless → Bloodlusted |
|---|---|---|
| **Care** (slack) | Only options within this share of the best EU are considered: how bad a move it will settle for | careless → careful → careless |
| **Mixing** (softmax temperature) | How evenly it picks among the options it considers: how hard it is to read | mixes → mixes among good moves only → never mixes |
| **Values** | Axis weights in the utility | `show`, `spread` high → `tempo` high → `lethal` high, `spread` negative |
| **Sharpness** | Tempers the belief before use: p^β, renormalised | β < 1, hedges → β = 1, uses all of it → β > 1, jumps to conclusions |
| **Exploration** | Bonus for betting where the forecast is unsure (its entropy), to learn | high → none → none |
| **Disclosure** | Which level `announce` uses | full → hidden → full |

**Care and mixing are different things.** A boss can be careful and still
hard to read: against players who learn the boss, always making the same
best move is a weakness, and the answer is to mix among moves that are
nearly as good (a mixed strategy, in game-theory terms). So Ruthless never
settles for a poor move but mixes among good ones, while Bloodlusted
settles for poor moves and never mixes. Its rage is readable, and a party
can bait it.

**Values** rise in one direction: `lethal` grows from one end of the dial to
the other. A negative `spread` weight is **fixation**: the boss is rewarded
for going after the same player again, which is how a grudge looks in the
utility.

**Disclosure** has three levels. *Full* says what and who ("Kael will loose
from afar"). *Name only* says who ("I have seen what Kael will do").
*Hidden* commits to the bet in secret and reveals it afterwards (for the
Prophet, a sealed prophecy), so the player can't react to it. Each step
has one level, and it is a rule of character, not a choice made for profit:
a boss that picked its disclosure by EU would always hide, and an enraged
one doesn't hold its tongue. For the same reason `show` doesn't reward
disclosure; that would count it twice. Disclosure runs in a U: the curious
boss shows its hand to watch, the cold one hides it, the enraged one shouts
it.

### 5.2 The steps

Placeholder values, to be calibrated in the harness ([M3 protocol](#m3-protocol)):

| Step | Slack | Mixing temp. | `lethal` | `spread` | `show` | `tempo` | β | Explore | Disclosure |
|---|---|---|---|---|---|---|---|---|---|
| Curious | 30% | 0.30 | 0.2 | 1.0 | 1.0 | 0.5 | 0.6 | 0.5 | full |
| Hunting | 15% | 0.15 | 0.5 | 0.5 | 0.4 | 0.8 | 0.85 | 0.2 | name only |
| **Ruthless** | 5% | 0.15 | 0.8 | 0.2 | 0 | 1.0 | 1.0 | 0.1 | hidden |
| Wrathful | 2% | 0.05 | 0.9 | −0.3 | 0.3 | 1.0 | 1.5 | 0 | name only |
| Bloodlusted | 0% | 0 | 1.0 | −0.6 | 0.5 | 0.8 | 2.5 | 0 | full |

Ruthless explores a little: against players who change, a belief goes
stale, and a cold boss knows information has a price worth paying. Curious
still explores most (Q6). Wrathful sits between Ruthless and Bloodlusted on
every lever.

The DM picks a step; each lever can still be overridden by hand. The two
ends are both easier to beat than the middle, but they feel different: a
Curious boss is a gentle fight, a Bloodlusted one a frightening fight with a
weakness the party can find.

### 5.3 Shifting temperament mid-fight

Temperament can move by itself in response to the fight, for example:

- boss HP thresholds (Ruthless above half, Wrathful below half,
  Bloodlusted below a quarter: the classic enrage, more dangerous and easier
  to bait),
- an insult to the boss (a minion slain, a prophecy defied three times),
- a round count (the boss tires of playing).

Each module declares its triggers. A separate and more contentious idea
is a **director** mode, as in Left 4 Dead's AI Director: shift temperament to
keep the fight tense, easing off when the party is near a wipe and tightening
when they are coasting. That makes the brain a fun-maximiser rather than a
boss-maximiser, so it is an opt-in DM setting, off by default (Q4).

## 6. Modules

### 6.1 The Threadkeeper Failed Prophet (first module)

From `data/enemies.yaml`: at round start the Prophet declares a prediction, and
each one that comes true gives an Echo Charge. At 3 charges it rewinds the
last player action.

As a module:

- **Options:** per round, a prophecy (hero × action category) or silence,
  disclosed at the temperament's level. A
  second decision runs whenever charges allow it: rewind now, or hold the
  charges for a better moment (a crit, a killing blow, a heal on a downed
  ally).
- **Outcomes:** the prophecy is fulfilled with the forecast probability for
  that hero, adjusted for their defiance when named.
- **Utility:** a fulfilled prophecy is `tempo` (a charge). Naming someone not
  named recently is `spread`. A rewind is scored by what it unmakes: a heal
  or a killing blow is `lethal`, a plain hit is `tempo`. Holding a rewind
  for a dramatic moment is `show`; how much the prophecy reveals is not
  (5.1).
- **Disclosure:** full ("Kael will loose from afar"), name only ("I have seen
  what Kael will do"), or hidden (a sealed prophecy, written down and opened
  when the round ends), as the temperament allows.

Note that the existing yaml examples ("the archer will miss", "someone will
fall") predict dice, not choices. Dice outcomes need no learning, so they
stay as a separate, fixed-odds kind of prophecy that the Prophet can choose
alongside prophecies about choices (Q7).

### 6.2 Interface checks (not to be built yet)

These exist to keep the interface honest. If either one can't be written as a
module, the interface is wrong.

- **Coin-Mad Hoardwyrm.** Options: offer a bribe, at what price, or none.
  Belief: how greedy the party is, and how desperate they are right now.
  Utility: attacks skipped (negative `tempo`) against coin gained and the
  chance the party is too poor to fight on (`lethal`).
- **Sangrith Debt-Collector.** Options: which Oath Clause goes to whom. Belief:
  who is most likely to break which clause. Utility: expected breaches times
  their cost (`lethal`), against how fair it looks (`show`).

## 7. The table tool

- One screen, usable on a laptop or tablet beside the DM screen.
- One tap per hero turn in normal play, always with undo.
- A **DM view** with the forecasts and reasons, and a **proclaim view** to turn
  toward the players with only what `announce` allows.
- DM-only. It must stay out of the public site build (`web/build.py`); the hub
  is fine.
- Works offline; state saved locally; the event log can be exported.

## 8. Validation: the research harness

Before any model is chosen, a harness plays the brain against **synthetic
players** and measures it.

**Synthetic players**

| Player | Plays |
|---|---|
| Habitual | the subclass's main action 9 times in 13 (~70%) |
| By the book | the subclass's usual mix, exactly as the prior assumes |
| Random | uniformly at random (the floor) |
| Alternator | Strike, Guard, Strike, Guard, ... |
| Switcher | Shoot for four turns, then Strike |
| Contrarian | by the book, but never its subclass's main action when named |
| Second-guesser | by the book, but when named avoids whatever it has done most so far |
| Adaptive | by the book, but shies away from any action a revealed prophecy caught it doing, and slowly forgets |
| Tell-reader | by the book, but steers away from the actions the boss has bet on about it, named or not, whether or not the bets came true (added in M2b) |

The Adaptive player reacts to being caught; the Tell-reader reads the boss's
habits and moves first, so a boss that keeps making the same bet pays for
it. Both see only what the boss reveals, which is every bet once its round
is over. Reading a module's own tells (a wind-up, a stance) is left for
when there is a real module with tells to study (M4).

**Metrics:** forecast accuracy (and calibration: is 60% right 60% of the
time?), prophecy hit rate, charges per round, rounds to first rewind, how
quickly each player style is detected, and how the temperament steps differ
from each other.

**Calibration targets (provisional).** Temperament is the engine's, so it is
calibrated on a measure every module has: **bet success**, how often a bet
the boss makes about a player comes true (for the Prophet, the prophecy hit
rate). Against ordinary play (Habitual, By the book, Adaptive) it should
follow the bell of section 5.1:

| Step | Bet success against ordinary play |
|---|---|
| Curious | 15–25% |
| Hunting | 30–40% |
| Ruthless | the highest of the five, at least 45% |
| Wrathful | 30–40% |
| Bloodlusted | 20–30% |

Against Random, every step should fall to chance, so that playing
unpredictably works but costs the party efficiency.

A module's own economy is the module's to tune, not the engine's. For the
Prophet (M4): a rewind about once every 4–5 rounds. With one prophecy a
round and a rewind costing 3 charges, that needs a hit rate of 60–75%, above
any band here, so M4 will have to change the cost, the prophecies per round
or the target.

Party win rate per temperament step is the number the DM would care about
most, but it needs a combat model, which the harness doesn't have. It is
measured in playtests (Q8); borrowing the arena's engine would be a project of
its own.

### Spike results

`prophet/model.js` (model A, no temperament, always picks the most likely
prophecy) against a Gunman, Bulwark, Verdant and Hellbound party, one prophecy
per round over 10 rounds, 400 fights per row:

| Synthetic player | Hit rate | Charges / fight | Fights reaching a rewind | Avg. round of first rewind |
|---|---|---|---|---|
| Habitual | 69% | 6.9 | 100% | 4.3 |
| By the book | 70% | 7.0 | 100% | 4.3 |
| Random | 21% | 2.0 | 32% | 7.1 |
| Alternator (Strike/Guard) | 60% | 6.0 | 100% | 7.0 |
| Switcher (after round 4) | 70% | 7.0 | 100% | 3.0 |

What this shows: the counting model works, falls to chance against random play
(20% is chance with five categories), and its sequence model catches an
alternating player by about round 7. It also shows the spike is far too strong
against ordinary play. Hit rates around 70% mean a rewind every four rounds,
which is the case for temperament and for modelling defiance.

### M1 baseline

The harness (`src/harness/`, run with `npm run harness`) reproduces the spike
with model A ported to TypeScript. Full numbers are in
[reports/baseline.md](reports/baseline.md): the spike's party, 1000 fights of
10 rounds per style, seed 1. The one figure that looked different, Random's
average round of first rewind (7.5 against the spike's 7.1), was sampling
noise: at 5000 fights the spike gives 7.3 and the harness 7.4. A unit test now
pins these numbers.

| Synthetic player | Forecast accuracy | Prophecy hit rate | Charges / fight | Avg. round of first rewind |
|---|---|---|---|---|
| Habitual | 69% | 69% | 6.9 | 4.3 |
| By the book | 60% | 69% | 6.9 | 4.3 |
| Random | 20% | 20% | 1.9 | 7.5 |
| Alternator | 57% (17% in rounds 1–3, 100% from 7) | 60% | 6.0 | 7.0 |
| Switcher | 53% (33% in rounds 4–6) | 70% | 7.0 | 3.0 |
| Contrarian | 44% | **4%** | 0.4 | 7.9 |
| Second-guesser | 43% | **2%** | 0.2 | 9.0 |
| Adaptive | 52% | 49% | 4.9 | 5.3 |

What M2 has to deal with:

1. **Defiance breaks the baseline.** Against players who dodge when named,
   the prophecy hit rate falls to 2–4%, far *below* the 20% of a blind guess,
   while forecasts on their other turns stay around 44%. Model A ignores being
   named, so it foretells exactly the action these players have just ruled out.
   This confirms that being named has to be part of the belief (4.2), and it
   means a boss that knew could foretell the dodge instead.
2. **The forecasts are overconfident.** Pooled over all styles, turns where the
   top forecast said 70–80% came true 52% of the time, and 80–90% came true
   64% of the time. Defiance accounts for part of it.
3. **The prior hurts against random play.** Random's log loss is 2.00, worse
   than the 1.61 of a blind guess, because the subclass shapes are confident
   and a random player never earns them. A belief that can tell "this player
   ignores their subclass" would fix it.
4. **Players who learn cost the boss a third of its take.** Adaptive, which
   only shies away from actions it was caught doing, cuts the hit rate from
   69% to 49%.
5. **Changes of style take a few turns to follow.** Switcher's accuracy drops
   to 33% in rounds 4–6 before recovering to 75%. Alternator is read by
   round 7. Memory and pattern settings trade this speed against stability.

Forecast accuracy and prophecy hit rate differ for By the book (60% against
69%) because the policy names the most predictable hero each round, here the
Hellbound Mage.

### M2 protocol

Written before any M2 numbers existed, so the choice can't be fitted to
them afterwards.

**Candidates.**

| Id | Model |
|---|---|
| `a` | Model A, counts, as in M1. The control. |
| `ad` | Model A with a **defiance layer**: a per-player Beta belief over how often they dodge when named. When named, the forecast mixes "plays as usual" with "avoids the action they'd usually take", and each named turn updates the Beta by how well each explained it. Tried in two variants: named turns also teach the counts, or they don't. |
| `b` | Model B, **archetypes**: an exact Bayesian posterior over a fixed set of player types (follows the subclass, favours one action, chaotic, repeats itself, avoids repeating itself), each crossed with a reaction to being named (complies or defies). It can explain itself. |
| `c` | Model C, **ensemble**: Bayesian model averaging of the best `ad` and the best `b`, weighted by how well each has predicted this player so far. This replaces the "hierarchical" model in 4.2, which would count the same evidence twice; averaging gets the same "types plus quirks" effect honestly. |

**Tuning and evaluation.** Each candidate's settings are tuned on a small
grid with seed 1 (300 fights per style, the spike's party). The best settings
are then evaluated once on held-out data: seed 2, 1000 fights per style, on
the spike's party and on a second party none of the tuning saw (Warbound
Mage, Sanguine Aegis, Crystal Archer, Aether Mage).

**Choosing.** On the held-out data:

1. **Primary:** mean log loss over the eight styles, each style weighted
   equally. Log loss rewards honest probabilities, not just a right top guess.
2. **Guards:** on named turns, the winner must not do worse than a blind
   guess against Contrarian and Second-guesser, and its calibration error
   must not be worse than model A's.
3. **Tie-break:** if two candidates are within 0.02 of each other in log
   loss, the one that can explain itself wins (`b` or `c` over `ad`).

The prophecy policy changes in one way for M2: it forecasts each candidate
as if named, since naming them is what a prophecy does. Model A ignores
this, so its M1 numbers stand.

### M2 results

Run with `npm run compare`; full numbers in
[reports/m2-belief.md](reports/m2-belief.md). Held-out log loss, mean over
the eight styles and the two parties:

| Model | Log loss | Calibration error | Named turns: Contrarian | Named turns: Second-guesser | Guards |
|---|---|---|---|---|---|
| A: counts | 1.383 | 0.090 | 2.46 | 2.43 | fails both defier guards |
| A + defiance | 1.321 | 0.053 | 1.73 | 1.58 | fails the Contrarian guard |
| B: archetypes | 1.261 | 0.045 | 1.20 | 1.47 | passes |
| **C: ensemble** | **1.249** | **0.022** | 1.37 | 1.47 | passes |

A blind guess scores 1.61. **Model C is chosen** under the protocol: lowest
log loss among the candidates that pass the guards, and it can explain
itself through its archetype member. The ranking is the same on both
parties, including the one tuning never saw.

These are the numbers after the grids were widened (2026-10-06, point 4).
The first run chose C too, at 1.253.

What it fixed, against model A:

- **Defiance.** The baseline prophecy hit rate against Contrarian rises from
  4% to 57% (party 1), and against Second-guesser from 3% to 49%: the brain
  now foretells the dodge.
- **Overconfidence.** Calibration error falls from 0.090 to 0.022.
- **Random play.** Log loss against Random improves from 2.01 to 1.82,
  because "chaotic" is one of the types it can conclude a player is.

What M3 and later have to know:

1. **The defiance prior was learned from our synthetic table, not a real
   one.** Tuning picked a high prior on defiance (B: 55%; A + defiance: 50%),
   because two of the eight styles defy and a third shies away. Against
   players who comply, that caution costs prophecies: with the same greedy
   policy, the hit rate against Habitual falls from 69% to 55%, and against
   By the book from 68% to 44% (party 1). Widening the grid moved B's prior
   up from 40%, and made this cost worse. The real share of defiant players
   has to come from playtests (M6). Until then this prior is the most
   important setting to revisit, and M3 should check that its calibration
   holds at a lower one too.
2. **Alternating players are C's weak spot.** B has no type for "alternates
   between two actions", so it reads Alternator at chance (20% accuracy). C
   does get there through its A member, 100% accurate from round 7, but
   slowly: 0% in rounds 1–3 and 33% in rounds 4–6, against A's 17% and 50%.
   Overall that is 50% against A's 60%. Adding a learned two-action cycle to
   B is the obvious fix.
3. **A + defiance learns *that* a player dodges, not *where* to.** Its dodge
   is spread evenly over the other actions, so a player who always Guards
   when named is never forecast to Guard. B's types and C's averaging cover
   this better; it's why A + defiance fails the Contrarian guard.
4. **The grids were widened once.** In the first run several winners sat at
   the edge of their grids (A's pattern prior 0.5, B's subclass prior 0.6
   and defiance prior 0.4, A + defiance's prior 50%). The rerun added values
   past each one. Every one of these winners is now inside its grid: B's
   subclass prior came back to 0.4, B's defiance prior rose to 0.55 (0.7 was
   tried), A's pattern prior to 0.65 (0.8 was tried), and A + defiance kept
   50% (67% and 75% were tried). Three memories now sit at
   the low edge (A 0.8, A + defiance's dodge memory 0.9, C 0.9). The rerun
   gained 0.004 in C's held-out log loss, so a further widening is unlikely
   to matter. A + defiance tuned slightly worse than before, because the
   protocol tunes it on top of the best A, and the new best A is a worse
   base for it.
5. **A better belief makes the greedy baseline policy *less* profitable
   against ordinary players** (point 1). Choosing prophecies well is M3's job,
   not the belief's: the belief should be honest, and the policy and
   temperament decide what to do with it.

### M2b protocol

Written before any M2b numbers existed. M2 chose model C against players who
react to being named; it never met a player who reads the boss. A general
boss brain needs to, and M3 should not calibrate temperament on top of a
belief with that hole in it.

**What changes.**

- *Reveals.* The belief is told every bet the table has seen: which player,
  which action, whether it came true. Model A ignores them.
- *Wary players.* Model B gains a third dimension, crossed with its habits
  and its reactions to being named: a player either ignores the boss's bets
  or is **wary** of them. A wary player's usual turn is scaled down on every
  action the boss has bet on, by a factor that grows with each bet (fulfilled
  or not) and fades over the following turns. Its prior is a new setting,
  `waryPrior`; at 0, model B is exactly M2's.
- *Players.* The Tell-reader joins the styles (section 8).

**Candidates.** `c` as chosen in M2, and `c2`: the same, with a wary model
B. `b` and `b2` are reported alongside for information.

**Tuning.** Seed 1, 300 fights per style, the spike's party, all nine
styles. Every M2 setting stays; only the new ones are tuned: `waryPrior` in
0.1, 0.2, 0.35, 0.5, then the ensemble's memory in 0.85, 0.9, 0.95 on top of
the best.

**Evaluation and choosing.** Held out as in M2: seed 2, 1000 fights per
style, both parties, nine styles. `c2` replaces `c` if all of these hold:

1. its mean log loss over the nine styles is lower;
2. on no style is its log loss worse than `c`'s by more than 0.02, so that
   reading learners doesn't cost the players who aren't;
3. its calibration error is no worse than `c`'s;
4. it still passes M2's defier guards.

Otherwise `c` stays, and the report says which rule failed. The M2 report
keeps its eight styles, so its numbers stay reproducible.

### M2b results

Run with `npm run compare:m2b`; full numbers in
[reports/m2b-wary.md](reports/m2b-wary.md). **Model C stays as chosen in
M2.** The wary model `c2` passed three of the four rules and failed the
calibration rule:

| Rule | `c` | `c2` | Passed |
|---|---|---|---|
| 1. Mean log loss, nine styles | 1.2519 | 1.2503 | yes |
| 2. Worst change on any style | | +0.006 (Contrarian) | yes |
| 3. Calibration error | 0.021 | 0.024 | **no** |
| 4. Defier guards (named turns) | | 1.39, 1.47 against 1.61 | yes |

What M3 and later have to know:

1. **The gain was small even where it was aimed.** Against the Tell-reader,
   log loss improved by 0.011, and the baseline prophecy hit rate rose from
   36% to 38%. With one bet a round spread over four heroes, a player sees
   only two or three bets about themselves in a fight, so there is little
   wariness to read.
2. **The calibration loss may not be the wary types' fault.** Tuning also
   moved the ensemble's memory from 0.9 to 0.85, and model B on its own
   became *better* calibrated with wary types (0.040 to 0.032). Which change
   cost C its calibration was not tested; testing it now would be fitting
   the protocol to the numbers. It is a question for when playtests (M6)
   show how much real players read the boss.
3. **The code stays, switched off.** Reveals reach every belief model, and
   model B's wary types are there at `waryPrior` 0, where the model is M2's
   exactly. A module whose players see more bets per fight may want them.
4. **The Tell-reader already costs the boss.** Even unread, it holds the
   baseline hit rate to 36%, against 44–55% for By the book and Habitual.
   That gap is what M3's readability measure works with.

### M3 protocol

Written before any M3 numbers existed, so the calibration can't be fitted to
them afterwards.

**What is built.** The decision layer of 4.4 and the levers of 5.1, in the
engine, with the five steps of 5.2 as data. The engine knows nothing about
prophecies: it sees options, outcome probabilities and axis scores.

**The baseline module.** A minimal Prophet, used only as a yardstick (the
real one is M4):

- *Options:* each round, one bet per (hero, action), plus silence, disclosed
  at the step's level. One bet a round.
- *Outcome:* the bet comes true with the tempered forecast probability. The
  forecast is made as if named, unless the disclosure is hidden.
- *Utility:* a bet that comes true is `tempo` 1. Betting on a hero who was
  not bet on last round is `spread` 1. Nothing is `lethal` or `show`, so
  those weights are not calibrated in M3; they wait for modules with lethal
  outcomes and drama (M4). Silence scores 0.
- *Exploration:* the bonus is the explore weight times the entropy of the
  hero's untempered forecast, divided by ln 5 so it runs from 0 to 1.
- *Choice:* the options whose EU is within the slack of the best (a share of
  the best EU), then a softmax at the step's temperature; at temperature 0,
  the best.

**Measures**, per step:

1. *Bet success* against ordinary play (the mean over Habitual, By the book
   and Adaptive), against Random, against the defiers (Contrarian and
   Second-guesser) and against the Tell-reader.
2. *Fixation:* in each fight, the share of bets on the hero bet on most;
   averaged over fights.
3. *Exploitability:* bet success against ordinary play minus against the
   defiers.
4. *Readability:* bet success against ordinary play minus against the
   Tell-reader.
5. *Predictability:* the share of bets that repeat the boss's most common
   bet so far in the fight (same hero, same action).

**Targets.** M3 is done when all of these hold on the held-out data, using
the mean over the two parties:

1. Bet success against ordinary play is in the step's band (section 8).
2. It rises from Curious to Ruthless and falls from Ruthless to Bloodlusted.
3. Against Random, every step is at most 25%.
4. Fixation is highest at Bloodlusted, and exploitability is higher at
   Bloodlusted than at Ruthless.
5. Readability and predictability are both higher at Bloodlusted than at
   Ruthless: the cold boss is harder to read than the enraged one.

If a target fails, the report says which, and the fix is a change to the
step's fixed levers, written down here before the rerun.

**Robustness.** The held-out evaluation is repeated with both defiance
priors in model C lowered to 25% (M2 results, point 1). A failure there
doesn't block M3; it is recorded as the first thing for playtests (M6) to
check.

**Tuning.** Seed 1, 300 fights per style, the spike's party, the three
ordinary styles and the Tell-reader (the only ones tuning looks at).
Belief: model C at its M2 settings (M2b kept them). Axis weights, exploration, disclosure and
slack stay as in 5.2: they are the design's intent, not numbers to fit. Per
step, β and, where the step mixes, the mixing temperature are tuned on a
grid:

| Step | β tried | Mixing temp. tried | Picked by |
|---|---|---|---|
| Curious | 0.3, 0.45, 0.6, 0.75, 0.9 | 0.07, 0.15, 0.3, 0.5 | closest to the middle of its band |
| Hunting | 0.6, 0.75, 0.85, 0.95, 1 | 0.03, 0.07, 0.15, 0.3 | closest to the middle of its band |
| Ruthless | 1 | 0, 0.03, 0.07, 0.15, 0.3 | highest mean of bet success against ordinary play and against the Tell-reader |
| Wrathful | 1.1, 1.3, 1.5, 2, 2.5 | 0.05 | closest to the middle of its band |
| Bloodlusted | 1.5, 2, 2.5, 3.5, 5 | 0 | closest to the middle of its band |

Ruthless is picked partly on the Tell-reader so that tuning can't buy bet
success by making it readable. Each step's β must stay on its side of the
curve: Hunting's at least Curious's, Bloodlusted's above Wrathful's. Ties go
to the point closest to the placeholder in 5.2. If no point lands in the
band, the slack joins the grid (0%, 5%, 15%, 30%, 40%); if still none does,
the step fails and the report says which lever ran out.

**Evaluation.** Seed 2, 1000 fights per style, all nine styles, on both
parties of M2. Every fight is 10 rounds. Written to
`reports/m3-temperament.md` and `.json`.

## 9. Data and persistence

- **Event log** per fight, as JSON: the source of truth.
- **Profiles** per player, kept between fights and sessions. Keyed to the
  player, not the character, if a player swaps characters (Q5).
- **Playtest logs** feed back into the priors: the subclass shapes and the
  archetype likelihoods should come from real play, not from this document.
  This is the Akinator loop, where every game makes the next one better.

## 10. Milestones

| | Milestone | Done when |
|---|---|---|
| M0 | This design | Done: open questions closed, doc at 1.0 |
| M1 | Harness | Done: synthetic players and metrics, the spike reproduced ([M1 baseline](#m1-baseline)) |
| M2 | Belief | Done: model C chosen ([M2 results](#m2-results)) |
| M2b | Belief reads learners | Done: model C stays; wary types kept, switched off ([M2b results](#m2b-results)) |
| M3 | Decision + temperament | Five steps calibrated against the targets in section 8 ([M3 protocol](#m3-protocol)) |
| M4 | Prophet module | The Prophet runs end to end in the harness |
| M5 | Table tool | Usable at a real session |
| M6 | Playtest loop | Logs from real sessions retune the priors |
| M7 | Second module | Hoardwyrm or Debt-Collector, with no engine changes needed |

## 11. Decisions

Closed 2026-10-05. Reopen one by editing its row and saying why.

| # | Question | Decision |
|---|---|---|
| Q1 | Where does this live: `underweave/` in this repo, or its own repo? | This repo, while it is campaign-specific. Renamed to `boss_brain/` on 2026-10-06: it is a general engine, not the Underweave's. |
| Q2 | Language: Python harness plus JS table tool, or one TypeScript core for both? | One TypeScript core, so the harness and the table run the same code. The repo already has Node for `charasheet/`. |
| Q3 | Which context tags, if any, beyond the action category? | None at first. Add a tag only if the harness shows it's worth its tap. |
| Q4 | Can temperament shift mid-fight, and is director mode allowed? | Triggers yes, declared per module. Director mode as an opt-in DM setting, off by default. |
| Q5 | Do profiles persist between sessions, and per player or per character? | Yes, per player. |
| Q6 | Exploit only, or explore/exploit? | Explore/exploit, with exploration tied to temperament (Curious explores most). |
| Q7 | Keep dice-outcome prophecies ("the archer will miss")? | Yes, as a fixed-odds option the module can choose alongside choice prophecies. |
| Q8 | How is party win rate per temperament step measured? | Playtests first. Borrowing the arena engine would be a project of its own. |
| Q9 | Are five action categories right? | Revisit in M1, with the categories judged by how well they predict. |

## 12. References

- Akinator: belief over candidates, information-gain questioning, learning
  from games played.
- Dirichlet–multinomial updating; Bayesian model averaging.
- Softmax (quantal response, Boltzmann-rational) choice for imperfect but
  sensible play.
- Thompson sampling and expected information gain for explore/exploit.
- Level-k reasoning, for players who second-guess the boss.
- Left 4 Dead's AI Director, for pacing driven by fight state.
