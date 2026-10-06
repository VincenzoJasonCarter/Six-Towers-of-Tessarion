# M2b: reading players who read the boss

The protocol is in DESIGN.md, section 8, "M2b protocol". Tuning: seed 1, 300 fights per style, Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage. Held out: seed 2, 1000 fights per style, on each of two parties. Every fight is 10 rounds, every hero in a fight plays the same style, and all 9 styles are scored.

## Verdict

**Chosen: C: ensemble (M2).**

| Rule | Passed | Detail |
| --- | --- | --- |
| 1. Lower mean log loss over the nine styles | yes | 1.2503 against 1.2519 |
| 2. No style worse by more than 0.02 | yes | largest change +0.006 (Contrarian) |
| 3. Calibration error no worse | **no** | 0.024 against 0.021 |
| 4. Still passes M2's defier guards | yes | contrarian 1.39, second-guesser 1.47 (guard 1.61) |

## Held-out results

Log loss is the mean over the nine styles (lower is better; a blind guess scores 1.61). The defier columns are log loss on named turns only, worst of the two parties.

| Model | Log loss | Party 1 | Party 2 | Calibration error | Named: Contrarian | Named: Second-guesser |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C: ensemble (M2) | **1.252** | 1.253 | 1.251 | 0.021 | 1.37 | 1.47 |
| C2: ensemble with wary players | **1.250** | 1.253 | 1.248 | 0.024 | 1.39 | 1.47 |
| B: archetypes (M2) | **1.257** | 1.257 | 1.258 | 0.040 | 1.20 | 1.47 |
| B2: archetypes with wary players | **1.255** | 1.256 | 1.254 | 0.032 | 1.22 | 1.49 |

Party 1: Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage.
Party 2: Warbound Mage, Sanguine Aegis, Crystal Archer, Aether Mage.

## By style

Log loss, mean over the two parties, and the change from `c` to `c2` (rule 2).

| Player | c | c2 | b | b2 | c2 − c |
| --- | ---: | ---: | ---: | ---: | ---: |
| Habitual | 1.179 | 1.177 | 1.176 | 1.174 | -0.002 |
| By the book | 1.161 | 1.160 | 1.167 | 1.167 | -0.001 |
| Random | 1.819 | 1.817 | 1.773 | 1.771 | -0.002 |
| Alternator | 1.233 | 1.233 | 1.490 | 1.482 | +0.000 |
| Switcher | 1.007 | 1.002 | 0.959 | 0.961 | -0.005 |
| Contrarian | 1.179 | 1.185 | 1.140 | 1.147 | +0.006 |
| Second-guesser | 1.200 | 1.201 | 1.183 | 1.189 | +0.001 |
| Adaptive | 1.216 | 1.214 | 1.196 | 1.190 | -0.002 |
| Tell-reader | 1.273 | 1.263 | 1.231 | 1.214 | -0.011 |

## Party 1, by style

Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage. Log loss / accuracy / prophecy hit rate under the baseline policy.

| Player | c | c2 | b | b2 |
| --- | ---: | ---: | ---: | ---: |
| Habitual | 1.17 / 65% / 55% | 1.17 / 65% / 54% | 1.17 / 64% / 55% | 1.17 / 64% / 54% |
| By the book | 1.15 / 58% / 44% | 1.15 / 58% / 44% | 1.16 / 58% / 43% | 1.16 / 58% / 43% |
| Random | 1.82 / 20% / 19% | 1.82 / 20% / 19% | 1.77 / 20% / 20% | 1.77 / 20% / 20% |
| Alternator | 1.23 / 50% / 70% | 1.24 / 50% / 70% | 1.48 / 20% / 80% | 1.48 / 20% / 80% |
| Switcher | 1.05 / 65% / 63% | 1.05 / 68% / 71% | 0.99 / 68% / 67% | 0.99 / 70% / 75% |
| Contrarian | 1.17 / 60% / 57% | 1.18 / 60% / 55% | 1.13 / 62% / 70% | 1.14 / 62% / 70% |
| Second-guesser | 1.19 / 59% / 49% | 1.19 / 59% / 49% | 1.17 / 59% / 53% | 1.18 / 58% / 46% |
| Adaptive | 1.21 / 55% / 37% | 1.21 / 55% / 38% | 1.20 / 55% / 35% | 1.19 / 56% / 36% |
| Tell-reader | 1.27 / 54% / 36% | 1.26 / 54% / 38% | 1.24 / 54% / 32% | 1.22 / 56% / 36% |

## Party 2, by style

Warbound Mage, Sanguine Aegis, Crystal Archer, Aether Mage. Log loss / accuracy / prophecy hit rate under the baseline policy.

| Player | c | c2 | b | b2 |
| --- | ---: | ---: | ---: | ---: |
| Habitual | 1.19 / 63% / 50% | 1.19 / 63% / 50% | 1.18 / 63% / 44% | 1.18 / 63% / 44% |
| By the book | 1.17 / 56% / 47% | 1.17 / 56% / 46% | 1.18 / 55% / 38% | 1.18 / 55% / 38% |
| Random | 1.82 / 20% / 19% | 1.82 / 20% / 19% | 1.77 / 20% / 19% | 1.77 / 20% / 19% |
| Alternator | 1.23 / 50% / 40% | 1.23 / 50% / 40% | 1.50 / 25% / 0% | 1.48 / 28% / 0% |
| Switcher | 0.96 / 70% / 56% | 0.95 / 70% / 56% | 0.92 / 73% / 75% | 0.93 / 73% / 75% |
| Contrarian | 1.19 / 58% / 53% | 1.19 / 57% / 51% | 1.15 / 59% / 63% | 1.15 / 59% / 63% |
| Second-guesser | 1.21 / 56% / 45% | 1.21 / 56% / 46% | 1.20 / 55% / 41% | 1.20 / 55% / 39% |
| Adaptive | 1.22 / 54% / 37% | 1.22 / 54% / 38% | 1.20 / 54% / 32% | 1.19 / 55% / 33% |
| Tell-reader | 1.28 / 53% / 35% | 1.26 / 53% / 38% | 1.22 / 54% / 32% | 1.21 / 55% / 36% |

## Tuning

| Wary prior | Ensemble memory | Tuning log loss |
| ---: | ---: | ---: |
| 0.1 | 0.9 | 1.2509 |
| 0.2 | 0.9 | 1.2509 |
| 0.35 | 0.9 | 1.2528 |
| 0.5 | 0.9 | 1.2544 |
| 0.2 | 0.85 | 1.2504 |
| 0.2 | 0.9 | 1.2509 |
| 0.2 | 0.95 | 1.2515 |

Best: `{"ad":{"counts":{"priorStrength":4,"memory":0.8,"patternPrior":0.65},"defiance":{"prior":[1,1],"teachInner":"all","memory":0.9}},"b":{"subclassPrior":0.4,"defiantPrior":0.55,"memory":0.9,"waryPrior":0.2},"ensemble":{"memory":0.85}}`.

Model ids: `c` C: ensemble (M2), `c2` C2: ensemble with wary players, `b` B: archetypes (M2), `b2` B2: archetypes with wary players.
