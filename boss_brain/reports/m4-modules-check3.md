# M4: the module interface and the reference modules

The protocol is in DESIGN.md, section 8, "M4 protocol". Tuning data: seed 1, 300 fights per style, Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage, the ordinary styles. Held out: seed 2, 1000 fights per style, all 9 styles, on each of two parties. Every fight is 10 rounds. Belief: model C at its M2 settings; steps as M3 calibrated them, with the placeholder `lethal` and `show` weights. `lethal` per fight is the mean over the ordinary styles (Habitual, By the book, Adaptive) unless a column says otherwise.

## Verdict

**A value target failed on the tuning data, so the held-out data was not touched.** The protocol's next step is a change to the `lethal` or `show` weights, written down in DESIGN.md with its reason.

### Interface targets

| Target | Passed | Detail |
| --- | --- | --- |
| 1. The engine imports no module; all four run through one fight loop | yes | no import leaves src/engine; Bet, Punish, Spend or hold and Telegraph all run through runBout |

Target 2 (the three boss sketches) is checked by hand in DESIGN.md 6.2.

### Value targets, tuning data

| Target | Passed | Detail |
| --- | --- | --- |
| 1. Bell carries over: Punish | yes | 2.22 → 3.25 → 6.32 → 4.17 → 4.39 |
| 1. Bell carries over: Spend or hold | yes | 0.71 → 0.94 → 1.92 → 1.22 → 1.47 |
| 2. Rage is frightening: Punish | yes | Bloodlusted 4.39 against Curious 2.22 |
| 2. Rage is frightening: Spend or hold | yes | Bloodlusted 1.47 against Curious 0.71 |
| 2. Rage is frightening: Telegraph | yes | Bloodlusted 8.64 against Curious 6.29 |
| 3. Patience: Bloodlusted spends earliest | yes | mean round of a spend 8.9 → 7.3 → 5.3 → 4.3 → 3.1 (reported, not targets: aimed value 1.13 → 1.14 → 1.01 → 1.24 → 1.11; `lethal` per spend 0.27 → 0.32 → 0.64 → 0.41 → 0.49) |
| 4. Wind-ups: highest at Curious, under 10% from Ruthless on | **no** | 100% → 93% → 1% → 10% → 19% |

## By module, tuning data

### Punish

| Step | `lethal` / fight | vs Random | vs Defiers | vs Tell-reader | `tempo` / fight | `show` / fight | Read success | Moves / fight (ordinary) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **2.22** | – | – | – | 0.00 | 0.00 | 23% | cut 9.8, press 0.2 |
| Hunting | **3.25** | – | – | – | 0.00 | 0.00 | 29% | cut 8.7, press 1.3 |
| Ruthless | **6.32** | – | – | – | 0.00 | 0.00 | 63% | cut 10.0, press 0.0 |
| Wrathful | **4.17** | – | – | – | 0.00 | 0.00 | 39% | cut 10.0, press 0.0 |
| Bloodlusted | **4.39** | – | – | – | 0.00 | 0.00 | 40% | cut 9.2, press 0.8 |

### Spend or hold

| Step | `lethal` / fight | vs Random | vs Defiers | vs Tell-reader | `tempo` / fight | `show` / fight | Read success | Moves / fight (ordinary) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **0.71** | – | – | – | 4.20 | 0.00 | 24% | hold 7.1, spend 2.7 |
| Hunting | **0.94** | – | – | – | 3.56 | 0.00 | 29% | hold 5.3, spend 3.0 |
| Ruthless | **1.92** | – | – | – | 2.60 | 0.00 | 64% | hold 3.3, spend 3.0 |
| Wrathful | **1.22** | – | – | – | 1.93 | 0.00 | 37% | hold 2.4, spend 3.0 |
| Bloodlusted | **1.47** | – | – | – | 1.02 | 0.00 | 47% | hold 1.2, spend 3.0 |

### Telegraph

| Step | `lethal` / fight | vs Random | vs Defiers | vs Tell-reader | `tempo` / fight | `show` / fight | Read success | Moves / fight (ordinary) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **6.29** | – | – | – | 0.00 | 10.00 | – | wind-up 10.0 |
| Hunting | **6.47** | – | – | – | 0.00 | 9.25 | – | quick 0.7, wind-up 9.3 |
| Ruthless | **8.99** | – | – | – | 0.00 | 0.07 | – | quick 9.9, wind-up 0.1 |
| Wrathful | **8.84** | – | – | – | 0.00 | 0.97 | – | quick 9.0, wind-up 1.0 |
| Bloodlusted | **8.64** | – | – | – | 0.00 | 1.86 | – | quick 8.1, wind-up 1.9 |

