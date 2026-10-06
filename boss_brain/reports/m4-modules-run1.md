# M4: the module interface and the reference modules

The protocol is in DESIGN.md, section 8, "M4 protocol". Tuning data: seed 1, 300 fights per style, Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage, the ordinary styles. Held out: seed 2, 1000 fights per style, all 9 styles, on each of two parties. Every fight is 10 rounds. Belief: model C at its M2 settings; steps as M3 calibrated them, with the placeholder `lethal` and `show` weights. `lethal` per fight is the mean over the ordinary styles (Habitual, By the book, Adaptive) unless a column says otherwise.

## Verdict

**Every target holds: M4 is done.**

### Interface targets

| Target | Passed | Detail |
| --- | --- | --- |
| 1. The engine imports no module; all four run through one fight loop | yes | no import leaves src/engine; Bet, Punish, Spend or hold and Telegraph all run through runBout |
| 3. Bet reproduces M3's held-out numbers exactly | yes | identical on all 90 (step, party, style) cells |

Target 2 (the three boss sketches) is checked by hand in DESIGN.md 6.2.

### Value targets, held out

| Target | Passed | Detail |
| --- | --- | --- |
| 1. Bell carries over: Punish | yes | 2.42 → 3.42 → 6.77 → 4.98 → 4.43 |
| 1. Bell carries over: Spend or hold | yes | 0.84 → 1.00 → 2.08 → 1.49 → 1.62 |
| 2. Rage is frightening: Punish | yes | Bloodlusted 4.43 against Curious 2.42 |
| 2. Rage is frightening: Spend or hold | yes | Bloodlusted 1.62 against Curious 0.84 |
| 2. Rage is frightening: Telegraph | yes | Bloodlusted 6.86 against Curious 6.64 |
| 3. Patience: Bloodlusted spends earliest | yes | mean round of a spend 9.0 → 7.2 → 5.1 → 3.9 → 3.1 (reported, not targets: aimed value 1.09 → 1.12 → 1.10 → 1.31 → 1.17; `lethal` per spend 0.31 → 0.34 → 0.69 → 0.50 → 0.54) |
| 4. Show's U: wind-ups highest at Curious, lowest at Ruthless | yes | 100% → 92% → 0% → 93% → 98% |

### Value targets, tuning data

| Target | Passed | Detail |
| --- | --- | --- |
| 1. Bell carries over: Punish | yes | 2.22 → 3.25 → 6.32 → 4.17 → 4.39 |
| 1. Bell carries over: Spend or hold | yes | 0.71 → 0.94 → 1.92 → 1.22 → 1.47 |
| 2. Rage is frightening: Punish | yes | Bloodlusted 4.39 against Curious 2.22 |
| 2. Rage is frightening: Spend or hold | yes | Bloodlusted 1.47 against Curious 0.71 |
| 2. Rage is frightening: Telegraph | yes | Bloodlusted 6.86 against Curious 6.29 |
| 3. Patience: Bloodlusted spends earliest | yes | mean round of a spend 8.9 → 7.3 → 5.3 → 4.3 → 3.1 (reported, not targets: aimed value 1.13 → 1.14 → 1.01 → 1.24 → 1.11; `lethal` per spend 0.27 → 0.32 → 0.64 → 0.41 → 0.49) |
| 4. Show's U: wind-ups highest at Curious, lowest at Ruthless | yes | 100% → 93% → 1% → 92% → 97% |

## By module, held out

### Bet

| Step | `lethal` / fight | vs Random | vs Defiers | vs Tell-reader | `tempo` / fight | `show` / fight | Read success | Moves / fight (ordinary) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **0.00** | 0.00 | 0.00 | 0.00 | 2.82 | 0.00 | 28% | bet 10.0 |
| Hunting | **0.00** | 0.00 | 0.00 | 0.00 | 3.52 | 0.00 | 35% | bet 10.0 |
| Ruthless | **0.00** | 0.00 | 0.00 | 0.00 | 6.46 | 0.00 | 65% | bet 10.0 |
| Wrathful | **0.00** | 0.00 | 0.00 | 0.00 | 3.89 | 0.00 | 39% | bet 10.0 |
| Bloodlusted | **0.00** | 0.00 | 0.00 | 0.00 | 3.67 | 0.00 | 37% | bet 10.0 |

### Punish

| Step | `lethal` / fight | vs Random | vs Defiers | vs Tell-reader | `tempo` / fight | `show` / fight | Read success | Moves / fight (ordinary) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **2.42** | 1.98 | 1.93 | 2.43 | 0.00 | 0.00 | 23% | cut 9.8, press 0.2 |
| Hunting | **3.42** | 2.48 | 2.68 | 3.28 | 0.00 | 0.00 | 30% | cut 8.7, press 1.3 |
| Ruthless | **6.77** | 2.81 | 6.77 | 4.77 | 0.00 | 0.00 | 63% | cut 10.0, press 0.0 |
| Wrathful | **4.98** | 2.80 | 3.01 | 4.06 | 0.00 | 0.00 | 42% | cut 9.5, press 0.5 |
| Bloodlusted | **4.43** | 2.78 | 3.49 | 3.72 | 0.00 | 0.00 | 40% | cut 8.9, press 1.1 |

### Spend or hold

| Step | `lethal` / fight | vs Random | vs Defiers | vs Tell-reader | `tempo` / fight | `show` / fight | Read success | Moves / fight (ordinary) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **0.84** | 0.55 | 0.78 | 0.85 | 4.22 | 0.00 | 28% | hold 7.2, spend 2.7 |
| Hunting | **1.00** | 0.68 | 0.89 | 1.03 | 3.56 | 0.00 | 30% | hold 5.3, spend 3.0 |
| Ruthless | **2.08** | 0.73 | 2.03 | 1.93 | 2.44 | 0.00 | 64% | hold 3.1, spend 3.0 |
| Wrathful | **1.49** | 0.83 | 0.87 | 1.31 | 1.64 | 0.00 | 40% | hold 2.0, spend 3.0 |
| Bloodlusted | **1.62** | 0.76 | 0.64 | 1.46 | 0.99 | 0.00 | 48% | hold 1.1, spend 3.0 |

### Telegraph

| Step | `lethal` / fight | vs Random | vs Defiers | vs Tell-reader | `tempo` / fight | `show` / fight | Read success | Moves / fight (ordinary) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **6.64** | 11.98 | 6.51 | 6.53 | 0.00 | 10.00 | – | wind-up 10.0 |
| Hunting | **6.82** | 11.81 | 6.70 | 6.71 | 0.00 | 9.18 | – | quick 0.8, wind-up 9.2 |
| Ruthless | **9.05** | 8.16 | 8.94 | 8.90 | 0.00 | 0.04 | – | quick 10.0, wind-up 0.0 |
| Wrathful | **6.86** | 11.96 | 6.79 | 6.72 | 0.00 | 9.29 | – | quick 0.7, wind-up 9.3 |
| Bloodlusted | **6.86** | 12.01 | 6.72 | 6.79 | 0.00 | 9.80 | – | quick 0.2, wind-up 9.8 |

Party 1: Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage.
Party 2: Warbound Mage, Sanguine Aegis, Crystal Archer, Aether Mage.
