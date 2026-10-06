# M2: choosing the belief model

The protocol is in DESIGN.md, section 8, "M2 protocol". Tuning: seed 1, 300 fights per style, Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage. Held out: seed 2, 1000 fights per style, on each of two parties. Every fight is 10 rounds, and every hero in a fight plays the same style.

## Verdict

**Chosen: C: ensemble.**

- C: ensemble has the lowest held-out log loss among the candidates that pass the guards (1.249).
- A: counts fails a guard: named-turn log loss 2.46 against contrarian is worse than a blind guess (1.61); named-turn log loss 2.43 against second-guesser is worse than a blind guess (1.61).
- A + defiance fails a guard: named-turn log loss 1.73 against contrarian is worse than a blind guess (1.61).

## Held-out results

Log loss is the mean over the eight styles (lower is better; a blind guess scores 1.61). The defier columns are log loss on named turns only, worst of the two parties; the guard is 1.61.

| Model | Log loss | Party 1 | Party 2 | Calibration error | Named: Contrarian | Named: Second-guesser |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A: counts | **1.383** | 1.383 | 1.382 | 0.090 | 2.46 | 2.43 |
| A + defiance | **1.321** | 1.329 | 1.314 | 0.053 | 1.73 | 1.58 |
| B: archetypes | **1.261** | 1.259 | 1.262 | 0.045 | 1.20 | 1.47 |
| C: ensemble | **1.249** | 1.250 | 1.248 | 0.022 | 1.37 | 1.47 |

Party 1: Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage.
Party 2: Warbound Mage, Sanguine Aegis, Crystal Archer, Aether Mage.

## Party 1, by style

Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage. Log loss on every turn / accuracy on every turn / prophecy hit rate under the baseline policy.

| Player | a | ad | b | c |
| --- | ---: | ---: | ---: | ---: |
| Habitual | 1.18 / 69% / 69% | 1.20 / 64% / 46% | 1.17 / 64% / 55% | 1.17 / 65% / 55% |
| By the book | 1.16 / 60% / 68% | 1.18 / 57% / 41% | 1.16 / 58% / 43% | 1.15 / 58% / 44% |
| Random | 2.01 / 20% / 20% | 1.98 / 20% / 20% | 1.77 / 20% / 20% | 1.82 / 20% / 19% |
| Alternator | 1.18 / 60% / 70% | 1.22 / 45% / 20% | 1.48 / 20% / 80% | 1.23 / 50% / 70% |
| Switcher | 1.18 / 65% / 80% | 1.24 / 53% / 11% | 0.99 / 68% / 67% | 1.05 / 65% / 63% |
| Contrarian | 1.51 / 43% / 4% | 1.31 / 53% / 31% | 1.13 / 62% / 70% | 1.17 / 60% / 57% |
| Second-guesser | 1.50 / 43% / 3% | 1.25 / 58% / 44% | 1.17 / 59% / 53% | 1.19 / 59% / 49% |
| Adaptive | 1.35 / 52% / 49% | 1.24 / 55% / 36% | 1.20 / 55% / 35% | 1.21 / 55% / 37% |

## Party 2, by style

Warbound Mage, Sanguine Aegis, Crystal Archer, Aether Mage. Log loss on every turn / accuracy on every turn / prophecy hit rate under the baseline policy.

| Player | a | ad | b | c |
| --- | ---: | ---: | ---: | ---: |
| Habitual | 1.19 / 68% / 70% | 1.21 / 63% / 46% | 1.18 / 63% / 44% | 1.19 / 63% / 50% |
| By the book | 1.18 / 57% / 72% | 1.20 / 56% / 45% | 1.18 / 55% / 38% | 1.17 / 56% / 47% |
| Random | 2.00 / 20% / 21% | 1.97 / 20% / 20% | 1.77 / 20% / 19% | 1.82 / 20% / 19% |
| Alternator | 1.14 / 63% / 50% | 1.18 / 57% / 40% | 1.50 / 25% / 0% | 1.23 / 50% / 40% |
| Switcher | 1.07 / 68% / 80% | 1.11 / 63% / 50% | 0.92 / 73% / 75% | 0.96 / 70% / 56% |
| Contrarian | 1.55 / 41% / 4% | 1.31 / 51% / 28% | 1.15 / 59% / 63% | 1.19 / 58% / 53% |
| Second-guesser | 1.54 / 41% / 6% | 1.27 / 55% / 40% | 1.20 / 55% / 41% | 1.21 / 56% / 45% |
| Adaptive | 1.38 / 49% / 51% | 1.26 / 53% / 39% | 1.20 / 54% / 32% | 1.22 / 54% / 37% |

## Tuning

| Model | Settings tried | Tuning log loss | Best settings |
| --- | ---: | ---: | ---: |
| A: counts | 45 | 1.3825 | `{"priorStrength":4,"memory":0.8,"patternPrior":0.65}` |
| A + defiance | 20 | 1.3271 | `{"counts":{"priorStrength":4,"memory":0.8,"patternPrior":0.65},"defiance":{"prior":[1,1],"teachInner":"all","memory":0.9}}` |
| B: archetypes | 100 | 1.2567 | `{"subclassPrior":0.4,"defiantPrior":0.55,"memory":0.9}` |
| C: ensemble | 3 | 1.2480 | `{"ad":{"counts":{"priorStrength":4,"memory":0.8,"patternPrior":0.65},"defiance":{"prior":[1,1],"teachInner":"all","memory":0.9}},"b":{"subclassPrior":0.4,"defiantPrior":0.55,"memory":0.9},"ensemble":{"memory":0.9}}` |

Model ids: `a` A: counts, `ad` A + defiance, `b` B: archetypes, `c` C: ensemble.
