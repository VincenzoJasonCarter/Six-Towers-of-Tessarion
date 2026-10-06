# M3: calibrating the temperament steps

The protocol is in DESIGN.md, section 8, "M3 protocol". Tuning: seed 1, 300 fights per style, Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage, styles Habitual, By the book, Adaptive, Tell-reader. Held out: seed 2, 1000 fights per style, all 9 styles, on each of two parties. Every fight is 10 rounds with one bet a round at most, and every hero in a fight plays the same style. Belief: model C at its M2 settings.

## Verdict

**Not every target holds.** The protocol's next step is a change to the failing steps' fixed levers, written down in DESIGN.md before a rerun.

| Target | Passed | Detail |
| --- | --- | --- |
| 1. Each step in its band | **no** | Curious 21% (15%–25%); Hunting 38% (30%–40%); Ruthless 65% (highest, ≥ 45%); Wrathful 39% (30%–40%); Bloodlusted 37% (20%–30%) ✗ |
| 2. Rises to Ruthless, then falls | yes | 21% → 38% → 65% → 39% → 37% |
| 3. Random at most 25% | yes | Curious 20%, Hunting 19%, Ruthless 20%, Wrathful 20%, Bloodlusted 20% |
| 4. Fixation highest at Bloodlusted; exploitability higher than Ruthless's | yes | fixation 1.00 (highest 1.00); exploitability 6 against -3 points |
| 5. Readability and predictability higher at Bloodlusted than at Ruthless | **no** | readability 6 against 19 points; predictability 0.45 against 0.39 |

## The tuned steps

Fixed levers as in DESIGN.md 5.2; the tuned ones are in bold.

| Step | Slack | Mixing | β | Rashness | `spread` | `tempo` | Explore | Disclosure | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | 30% | **0.5** | **0.3** | 0 | 1 | 0.5 | 0.5 | full |  |
| Hunting | 15% | **0.3** | **0.6** | 0 | 0.5 | 0.8 | 0.2 | name |  |
| Ruthless | 5% | **0.03** | 1 | 0 | 0.2 | 1 | 0.1 | hidden |  |
| Wrathful | 2% | 0.05 | 1 | **0.6** | -0.1 | 1 | 0 | name |  |
| Bloodlusted | **0%** | 0 | 1 | **0.8** | -0.6 | 0.8 | 0 | full | no point in the band |

## Held-out results

Bet success, mean over the two parties. Ordinary is the mean over Habitual, By the book and Adaptive; Defiers over Contrarian and Second-guesser. Exploitability is ordinary minus defiers and readability ordinary minus Tell-reader, in percentage points. Fixation and predictability are means over all styles.

| Step | Ordinary | Random | Defiers | Tell-reader | Exploitability | Readability | Fixation | Predictability | Bets / fight |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **21%** | 20% | 20% | 21% | 1 | -0 | 0.36 | 0.12 | 10.0 |
| Hunting | **38%** | 19% | 27% | 37% | 11 | 2 | 0.36 | 0.16 | 10.0 |
| Ruthless | **65%** | 20% | 68% | 45% | -3 | 19 | 0.46 | 0.39 | 10.0 |
| Wrathful | **39%** | 20% | 33% | 34% | 6 | 5 | 0.88 | 0.41 | 10.0 |
| Bloodlusted | **37%** | 20% | 31% | 31% | 6 | 6 | 1.00 | 0.45 | 10.0 |

Party 1: Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage.
Party 2: Warbound Mage, Sanguine Aegis, Crystal Archer, Aether Mage.

## Party 1, by style

Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage. Bet success / fixation.

| Player | Curious | Hunting | Ruthless | Wrathful | Bloodlusted |
| --- | ---: | ---: | ---: | ---: | ---: |
| Habitual | 20% / 0.36 | 37% / 0.36 | 69% / 0.45 | 47% / 0.92 | 46% / 1.00 |
| By the book | 21% / 0.36 | 40% / 0.36 | 67% / 0.49 | 40% / 0.90 | 38% / 1.00 |
| Random | 20% / 0.36 | 20% / 0.36 | 20% / 0.43 | 20% / 0.97 | 20% / 1.00 |
| Alternator | 20% / 0.36 | 27% / 0.37 | 52% / 0.42 | 0% / 1.00 | 0% / 1.00 |
| Switcher | 20% / 0.36 | 39% / 0.36 | 75% / 0.37 | 80% / 1.00 | 80% / 1.00 |
| Contrarian | 20% / 0.36 | 28% / 0.36 | 66% / 0.49 | 52% / 0.80 | 54% / 1.00 |
| Second-guesser | 20% / 0.36 | 28% / 0.36 | 67% / 0.49 | 17% / 0.73 | 11% / 1.00 |
| Adaptive | 21% / 0.36 | 37% / 0.36 | 55% / 0.45 | 32% / 0.86 | 30% / 1.00 |
| Tell-reader | 21% / 0.36 | 36% / 0.36 | 46% / 0.43 | 34% / 0.82 | 32% / 1.00 |

## Party 2, by style

Warbound Mage, Sanguine Aegis, Crystal Archer, Aether Mage. Bet success / fixation.

| Player | Curious | Hunting | Ruthless | Wrathful | Bloodlusted |
| --- | ---: | ---: | ---: | ---: | ---: |
| Habitual | 20% / 0.36 | 38% / 0.36 | 69% / 0.48 | 47% / 0.91 | 46% / 1.00 |
| By the book | 21% / 0.36 | 41% / 0.36 | 70% / 0.53 | 37% / 0.86 | 34% / 1.00 |
| Random | 20% / 0.36 | 19% / 0.36 | 21% / 0.44 | 20% / 0.95 | 19% / 1.00 |
| Alternator | 20% / 0.36 | 29% / 0.37 | 62% / 0.47 | 0% / 1.00 | 0% / 1.00 |
| Switcher | 21% / 0.36 | 44% / 0.36 | 78% / 0.39 | 80% / 1.00 | 80% / 1.00 |
| Contrarian | 20% / 0.37 | 26% / 0.37 | 69% / 0.53 | 46% / 0.79 | 47% / 1.00 |
| Second-guesser | 20% / 0.36 | 26% / 0.37 | 70% / 0.53 | 17% / 0.71 | 12% / 1.00 |
| Adaptive | 21% / 0.36 | 37% / 0.36 | 57% / 0.50 | 31% / 0.84 | 28% / 1.00 |
| Tell-reader | 20% / 0.36 | 37% / 0.37 | 45% / 0.48 | 34% / 0.79 | 30% / 1.00 |

## Robustness: defiance priors at 25%

The same steps, held out the same way, with model C's two defiance priors lowered to 25%. A failure here doesn't block M3; it is the first thing for playtests (M6) to check.

| Step | Ordinary | Random | Defiers | Tell-reader | Exploitability | Readability | Fixation | Predictability | Bets / fight |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **21%** | 20% | 20% | 21% | 1 | -0 | 0.36 | 0.12 | 10.0 |
| Hunting | **48%** | 20% | 23% | 42% | 26 | 6 | 0.37 | 0.18 | 10.0 |
| Ruthless | **65%** | 20% | 68% | 45% | -3 | 19 | 0.46 | 0.39 | 10.0 |
| Wrathful | **56%** | 20% | 21% | 43% | 35 | 13 | 0.73 | 0.40 | 10.0 |
| Bloodlusted | **48%** | 20% | 16% | 33% | 32 | 15 | 1.00 | 0.47 | 10.0 |

| Target | Passed | Detail |
| --- | --- | --- |
| 1. Each step in its band | **no** | Curious 21% (15%–25%); Hunting 48% (30%–40%) ✗; Ruthless 65% (highest, ≥ 45%); Wrathful 56% (30%–40%) ✗; Bloodlusted 48% (20%–30%) ✗ |
| 2. Rises to Ruthless, then falls | yes | 21% → 48% → 65% → 56% → 48% |
| 3. Random at most 25% | yes | Curious 20%, Hunting 20%, Ruthless 20%, Wrathful 20%, Bloodlusted 20% |
| 4. Fixation highest at Bloodlusted; exploitability higher than Ruthless's | yes | fixation 1.00 (highest 1.00); exploitability 32 against -3 points |
| 5. Readability and predictability higher at Bloodlusted than at Ruthless | **no** | readability 15 against 19 points; predictability 0.47 against 0.39 |

## Tuning

### Curious

| sharpness | mixing | Ordinary | Tell-reader |
| ---: | ---: | ---: | ---: |
| 0.3 | 0.07 | 26% | 25% |
| 0.3 | 0.15 | 23% | 23% |
| 0.3 | 0.3 | 22% | 20% |
| 0.3 | 0.5 | 21% | 21% |
| 0.45 | 0.07 | 28% | 28% |
| 0.45 | 0.15 | 24% | 23% |
| 0.45 | 0.3 | 22% | 23% |
| 0.45 | 0.5 | 21% | 21% |
| 0.6 | 0.07 | 30% | 32% |
| 0.6 | 0.15 | 25% | 24% |
| 0.6 | 0.3 | 23% | 22% |
| 0.6 | 0.5 | 21% | 22% |
| 0.75 | 0.07 | 33% | 33% |
| 0.75 | 0.15 | 27% | 26% |
| 0.75 | 0.3 | 24% | 23% |
| 0.75 | 0.5 | 22% | 23% |
| 0.9 | 0.07 | 36% | 33% |
| 0.9 | 0.15 | 28% | 28% |
| 0.9 | 0.3 | 25% | 23% |
| 0.9 | 0.5 | 23% | 22% |

### Hunting

| sharpness | mixing | Ordinary | Tell-reader |
| ---: | ---: | ---: | ---: |
| 0.6 | 0.03 | 46% | 41% |
| 0.6 | 0.07 | 42% | 38% |
| 0.6 | 0.15 | 39% | 38% |
| 0.6 | 0.3 | 38% | 36% |
| 0.75 | 0.03 | 46% | 42% |
| 0.75 | 0.07 | 45% | 41% |
| 0.75 | 0.15 | 43% | 41% |
| 0.75 | 0.3 | 42% | 40% |
| 0.85 | 0.03 | 46% | 41% |
| 0.85 | 0.07 | 45% | 42% |
| 0.85 | 0.15 | 44% | 41% |
| 0.85 | 0.3 | 43% | 40% |
| 0.95 | 0.03 | 47% | 41% |
| 0.95 | 0.07 | 45% | 40% |
| 0.95 | 0.15 | 43% | 42% |
| 0.95 | 0.3 | 43% | 41% |
| 1 | 0.03 | 47% | 41% |
| 1 | 0.07 | 45% | 41% |
| 1 | 0.15 | 44% | 42% |
| 1 | 0.3 | 43% | 41% |

### Ruthless

| mixing | Ordinary | Tell-reader |
| ---: | ---: | ---: |
| 0 | 63% | 45% |
| 0.03 | 64% | 45% |
| 0.07 | 64% | 45% |
| 0.15 | 63% | 45% |
| 0.3 | 63% | 45% |

### Wrathful

| rashness | Ordinary | Tell-reader |
| ---: | ---: | ---: |
| 0.2 | 45% | 39% |
| 0.3 | 45% | 39% |
| 0.4 | 44% | 38% |
| 0.5 | 42% | 37% |
| 0.6 | 40% | 35% |

### Bloodlusted

| rashness | slack | Ordinary | Tell-reader |
| ---: | ---: | ---: | ---: |
| 0.65 | – | 38% | 32% |
| 0.8 | – | 38% | 32% |
| 0.9 | – | 38% | 32% |
| 0.95 | – | 38% | 32% |
| 0.65 | 0 | 38% | 32% |
| 0.65 | 0.05 | 38% | 32% |
| 0.65 | 0.15 | 38% | 32% |
| 0.65 | 0.3 | 38% | 32% |
| 0.65 | 0.4 | 38% | 32% |
| 0.8 | 0 | 38% | 32% |
| 0.8 | 0.05 | 38% | 32% |
| 0.8 | 0.15 | 38% | 32% |
| 0.8 | 0.3 | 38% | 32% |
| 0.8 | 0.4 | 38% | 32% |
| 0.9 | 0 | 38% | 32% |
| 0.9 | 0.05 | 38% | 32% |
| 0.9 | 0.15 | 38% | 32% |
| 0.9 | 0.3 | 38% | 32% |
| 0.9 | 0.4 | 38% | 32% |
| 0.95 | 0 | 38% | 32% |
| 0.95 | 0.05 | 38% | 32% |
| 0.95 | 0.15 | 38% | 32% |
| 0.95 | 0.3 | 38% | 32% |
| 0.95 | 0.4 | 38% | 32% |
