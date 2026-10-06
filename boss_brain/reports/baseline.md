# Boss brain harness: baseline

Belief model `counts` against a party of Gunman, Bulwark Aegis, Verdant Mage, Hellbound Mage. 1000 fights of 10 rounds per player style, seed 1. Every hero in a fight plays the same style.

## Forecasts

Every hero turn, scored on the forecast the belief made just before it. Guessing blind gets 20% accuracy, a log loss of 1.61 and a Brier score of 0.80. Calibration error is how far the forecasts' confidence is from how often they come true (0 is perfect).

| Player | Accuracy | Rounds 1–3 | 4–6 | 7+ | Log loss | Brier | Calibration error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Habitual | 69% | 69% | 69% | 69% | 1.17 | 0.53 | 0.098 |
| By the book | 60% | 61% | 60% | 60% | 1.16 | 0.58 | 0.049 |
| Random | 20% | 20% | 20% | 20% | 2.00 | 0.93 | 0.254 |
| Alternator | 57% | 17% | 42% | 100% | 1.15 | 0.62 | 0.166 |
| Switcher | 53% | 42% | 33% | 75% | 1.24 | 0.62 | 0.090 |
| Contrarian | 44% | 44% | 44% | 45% | 1.49 | 0.75 | 0.152 |
| Second-guesser | 43% | 43% | 44% | 43% | 1.50 | 0.75 | 0.154 |
| Adaptive | 52% | 56% | 51% | 51% | 1.35 | 0.67 | 0.092 |
| **All** | 50% | 44% | 45% | 58% | 1.38 | 0.68 | 0.067 |

## Prophecies (baseline policy)

The spike's policy, the fixed yardstick for belief models: each round it names the hero it reads most clearly and foretells their most likely action, or stays silent if no forecast reaches 40%. A rewind becomes available at 3 Echo Charges; charges are counted, never spent.

| Player | Spoken / fight | Hit rate | Charges / fight | Fights reaching a rewind | Avg. round of first rewind |
| --- | ---: | ---: | ---: | ---: | ---: |
| Habitual | 10.0 | 69% | 6.9 | 100% | 4.3 |
| By the book | 10.0 | 69% | 6.9 | 100% | 4.3 |
| Random | 9.4 | 20% | 1.9 | 30% | 7.5 |
| Alternator | 10.0 | 60% | 6.0 | 100% | 7.0 |
| Switcher | 10.0 | 70% | 7.0 | 100% | 3.0 |
| Contrarian | 10.0 | 4% | 0.4 | 6% | 7.9 |
| Second-guesser | 10.0 | 2% | 0.2 | 1% | 9.0 |
| Adaptive | 10.0 | 49% | 4.9 | 98% | 5.3 |

## Calibration, all styles together

Turns grouped by how sure the top forecast was.

| Confidence | Turns | Said | Happened |
| --- | ---: | ---: | ---: |
| 20–30% | 2534 | 28% | 20% |
| 30–40% | 30079 | 36% | 30% |
| 40–50% | 69691 | 45% | 47% |
| 50–60% | 104958 | 55% | 54% |
| 60–70% | 54406 | 64% | 52% |
| 70–80% | 44072 | 73% | 52% |
| 80–90% | 13544 | 84% | 64% |
| 90–100% | 716 | 91% | 67% |

## Player styles

| Player | Plays |
| --- | --- |
| Habitual | the subclass's main action 9 times in 13, anything else otherwise |
| By the book | the subclass's usual mix, exactly as the prior assumes |
| Random | uniformly at random, ignoring everything (the floor) |
| Alternator | Strike, Guard, Strike, Guard, ... |
| Switcher | Shoot for four turns, then Strike for the rest of the fight |
| Contrarian | by the book, but never its subclass's main action when named |
| Second-guesser | by the book, but when named avoids whatever it has done most so far |
| Adaptive | by the book, but shies away from any action a prophecy caught it doing, and slowly forgets |
