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
| 1. Bell carries over: Punish | **no** | 2.22 → 3.25 → 6.32 → 4.17 → 4.39 |
| 1. Bell carries over: Spend or hold | **no** | 2.17 → 2.46 → 5.03 → 3.54 → 3.99 |
| 1. Bell carries over: Telegraph | **no** | 8.39 → 8.50 → 8.56 → 8.50 → 8.97 |
| 2. Rage is frightening: Punish | yes | Bloodlusted 4.39 against Curious 2.22 |
| 2. Rage is frightening: Spend or hold | yes | Bloodlusted 3.99 against Curious 2.17 |
| 2. Rage is frightening: Telegraph | yes | Bloodlusted 8.97 against Curious 8.39 |
| 3. Patience: Bloodlusted spends most, Ruthless aims highest | **no** | spends 9.9 → 8.0 → 8.0 → 8.0 → 8.3; aimed value 0.98 → 1.05 → 1.02 → 1.17 → 1.09 |
| 4. Show's U: wind-ups highest at Curious, lowest at Ruthless | yes | 100% → 97% → 86% → 100% → 100% |

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
| Curious | **2.17** | – | – | – | 0.05 | 0.00 | 23% | hold 0.1, spend 9.9 |
| Hunting | **2.46** | – | – | – | 1.99 | 0.00 | 30% | hold 2.0, spend 8.0 |
| Ruthless | **5.03** | – | – | – | 2.00 | 0.00 | 63% | hold 2.0, spend 8.0 |
| Wrathful | **3.54** | – | – | – | 2.00 | 0.00 | 42% | hold 2.0, spend 8.0 |
| Bloodlusted | **3.99** | – | – | – | 1.66 | 0.00 | 46% | hold 1.7, spend 8.3 |

### Telegraph

| Step | `lethal` / fight | vs Random | vs Defiers | vs Tell-reader | `tempo` / fight | `show` / fight | Read success | Moves / fight (ordinary) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Curious | **8.39** | – | – | – | 0.00 | 10.00 | 0% | wind-up 10.0 |
| Hunting | **8.50** | – | – | – | 0.00 | 9.68 | 0% | quick 0.3, wind-up 9.7 |
| Ruthless | **8.56** | – | – | – | 0.00 | 8.63 | 0% | quick 1.4, wind-up 8.6 |
| Wrathful | **8.50** | – | – | – | 0.00 | 9.99 | 0% | quick 0.0, wind-up 10.0 |
| Bloodlusted | **8.97** | – | – | – | 0.00 | 10.00 | 0% | wind-up 10.0 |

