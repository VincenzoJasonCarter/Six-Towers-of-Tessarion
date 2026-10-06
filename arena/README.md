# The Proving Grounds

A Monte Carlo combat simulator for the eleven subclasses in
`../lore-book/05-subclasses-skill.md`, at levels 3, 7, 10 and 15. It has
two modes:

- **One-on-one** (`run.py` → [report.md](report.md)). Every subclass against
  benchmark foes and against each other, both as written now and as they
  were before Patch 1 (`../balance-patch.md`).
- **Party** (`party.py` → [party_report.md](party_report.md)). Every party of
  four different subclasses (330 of them) against four kinds of encounter.
  It measures what each subclass is worth to a team, which is where support
  and control features earn their keep.

Raw numbers go to `results.json` and `party_results.json`.

## Running it

From the repo root:

```
make arena                            # or: uv run arena/run.py
make arena-party                      # or: uv run arena/party.py
uv run arena/run.py --n 200           # quicker and noisier (default 1000 fights per matchup)
uv run arena/party.py --n 50          # quicker and noisier (default 100 per party and encounter)
uv run arena/run.py --recalibrate     # re-tune the foes (do this after changing rules)
uv run arena/party.py --recalibrate
uv run arena/party.py --only gunman   # rerun just the parties with one subclass, after changing it
uv run arena/party.py --size 6        # six-hero parties against six-creature encounters (party6_* files)
uv run arena/party.py --size 6 --repeats --n 10   # the same subclass may appear more than once (party6r_* files)
uv run arena/party.py --legacy        # the bots and arena from before the tactics fixes (party_legacy_* files)
uv run arena/run.py --report-only     # rebuild a report from its saved results
```

On 8 cores the one-on-one run takes about 6 minutes plus 7 to recalibrate.
The party run takes about 25 minutes (528,000 fights) plus about 17 to
recalibrate. `--only` reruns the 120 parties containing one subclass (about
10 minutes) against the saved encounter tuning. That's the quick way to test a
change to one subclass, as long as the change doesn't shift the average
party much.

`--size N` runs every party of N different subclasses. Encounters grow to one
creature per hero, using the line-ups in `ENCOUNTERS_BY_SIZE` in `foes.py`
(sizes without an entry repeat the four-creature line-up), and the Boss stays
alone. Each size gets its own encounter tuning and its own
`party{N}_calibration.json`, `party{N}_results.json` and `party{N}_report.md`.
Six-hero parties are the slowest: 462 parties and fights about half as fast,
so roughly an hour at `--n 50` including calibration.

`--repeats` lets a party bring the same subclass more than once (two
Bulwarks, three Verdants). That's 1,001 parties at size 4 and 8,008 at size
6, so use a small `--n`; each subclass still appears in thousands of parties.
The report adds a **Stacking** table: the party win rate with one, two, and
three or more copies of each subclass, and how much the second copy adds.
With this many parties and few fights each, a single party's win rate is
noisy, so the best and worst lists flatter lucky parties. The per-subclass
numbers are solid.

`--legacy` turns off four fixes to the bots and the arena that undersold
the Wizards in parties: area spells could only be centred on an enemy (so
any ally fighting nearby blocked them), the whole back rank started on one
spot, Skirmishers and Snipers always knew which hero had the fewest hit
points, and Holds that Legendary Resistance ate used up the bot's two tries.
They are switches in `TACTICS` in `engine.py`. Legacy runs write
`*_legacy_*` files with their own encounter tuning; the report says which
version produced it.
The tuned foe sizes are kept in `calibration.json` and
`party_calibration.json`, so results stay comparable between runs until you
recalibrate.

## What it measures

**One-on-one**

- **Gauntlet**. Each subclass fights four solo foes built from the DMG's
  monster-by-CR numbers: a **Brute** (beast, one huge hit, fast), a
  **Soldier** (humanoid, armoured, two attacks), a **Sniper** (humanoid
  archer who keeps its distance) and a **Caster** (humanoid, a 10-foot
  Dexterity-save blast every turn). Each foe's HP and damage are scaled,
  separately for Wizards and Fighters, until the average subclass of that
  chassis wins half its fights. 50% is par within a chassis.
- **Chassis gap**. The ratio of those scales: how much tougher a foe the
  Wizards can handle than the Fighters. It measures 5e itself, not your
  subclasses.
- **Duel**. Every subclass against every other at the same level. The
  chassis decides most 1v1s, so read the *vs own chassis* column.
- **Sparring**. Against an unkillable Soldier: damage dealt in the first three
  rounds and rounds survived (capped at 20). It separates offence from
  defence and control.
- **Campaign monsters** (level 3 only). Real stat blocks from
  `../data/enemies.yaml`.

**Party**

- Encounters, one creature per hero:
  - **Warband**: Brute, two Soldiers and a Skirmisher.
  - **Ambush**: two Skirmishers, a Sniper and a Caster.
  - **Mixed**: Brute, Soldier, Sniper and Caster.
  - **Boss**: alone. Three attacks, 10-foot reach, and two Legendary
    Resistances.

  Each encounter is scaled until the average party wins half its fights.
- Monsters pick targets by type. Brutes and Soldiers take the nearest hero.
  Skirmishers run past the front rank to the lowest-AC hero. Snipers shoot
  the lowest-AC hero in range. Both can see armour but not hit points, so
  among heroes tied for the lowest AC they keep last turn's pick or choose at
  random. Casters blast wherever the most heroes stand together.
- **Value** of a subclass: the win rate of parties that include it minus the
  win rate of parties that don't. The report also lists each subclass's
  survival rate and its share of damage dealt and taken, the best and worst
  parties, results by number of mages, and pair synergies.

## Files

| File | What it holds |
|---|---|
| `engine.py` | Dice, conditions, attacks, saves, damage, concentration, movement, targeting and the turn loop |
| `heroes.py` | The Wizard and Fighter chassis and the eleven subclasses, feature by feature, with the pre-patch rules behind `patched=False` |
| `foes.py` | The benchmark archetypes, the party encounters, and the loader for the campaign's stat blocks |
| `run.py` | One-on-one: calibration, experiments, `results.json` and `report.md` |
| `party.py` | Party: calibration, all 330 parties, `party_results.json` and `party_report.md` |

To test a rules change, edit the subclass in `heroes.py`, run with
`--recalibrate`, and compare the reports. To compare against the current
rules instead, add the change behind a flag the way `patched` works.

## The arena

Combatants stand on a 120-foot line with a wall at each end. One-on-one, they
start 60 feet apart. In a party fight, melee heroes form a front rank around
30 feet and everyone else a back rank around 10, staggered 5 feet apart (10,
15, 5, 20, ...), and the enemy mirrors that around 90 and 110 feet. Creatures
can pass each other, as they could step around each other on a real map.

Movement is in 5-foot steps. Entering difficult terrain costs double, and
leaving an enemy's reach provokes an opportunity attack. A creature at 0 HP
is out of the fight; there are no death saves and no healing of allies. A
fight ends when one side is down. After 20 rounds it is a draw, which counts
as half a win.

The combatants are bots:

- **Melee heroes** close in, dashing when they can't reach, and attack the
  most hurt enemy in reach. They use Action Surge on the first turn they can
  attack.
- **Guards** (Bulwark and Warden, when the party has a back rank) don't
  charge. They stand just in front of the most vulnerable ally and engage
  whatever comes for it.
- **Shooters and casters** focus the most hurt enemy in range and back away
  from anything that wants to melee them. Once engaged, they step out (taking
  the opportunity attack) only when the enemy can't follow, for example after
  Verdant Snare or Entangle.
- **Wizards** cast Hold Person (Hold Monster from 10th level) on the most
  dangerous enemy when it's likely to land and nothing is held yet. Otherwise
  they cast whatever has the highest expected damage this turn, so they spend
  their biggest slots first. Area spells go where they catch the most enemies
  and no allies, centred on any point in range (so a fireball can sit behind
  an enemy to miss the ally fighting it), and aren't cast if every spot would
  hit a friend. The bot gives up on Holds after two tries, but a try that
  Legendary Resistance shrugs off doesn't count, since the table hears about it.
- Ammunition and other choices are also picked by expected value.

## Builds and gear

All characters are human with no feats, average HP, and ability score
increases into the main stat and then Constitution.

| | Wizard | Aegisbound | Range |
|---|---|---|---|
| Scores (1st level) | Int 16, Dex 14, Con 14 | Str 16, Con 14 | Dex 16, Con 14 |
| Armour | *Mage armor*, cast before the day (costs a 1st-level slot) | Chain mail and shield (plate from 5th), Defense style | Studded leather, Archery style |
| Weapon | Spells | Longsword | Longbow (Archer), musket 1d12, 40/120 ft (Gunman) |

Everyone carries a +1 weapon or spellcasting focus from 5th level and +2 from
15th. Magic weapons get through Bulwark's Anchored Stance; the monsters'
natural weapons don't.

Every Wizard knows *fire bolt*, *toll the dead*, *shield* (one 1st-level slot
is kept back for it), *magic missile*, *scorching ray*, *hold person*,
*fireball*, *vitriolic sphere*, *hold monster*, *disintegrate* and *finger of
death*, using whichever its slots allow. Each fight starts with every spell
slot and every once-per-rest feature unspent. Compared with a full
adventuring day, that favours once-per-rest features (Overdrive, Fortress,
Overlord, Stoneheart, Soulshot Barrage) and Wizards in general.

## How each feature was read

Where the text left a choice or room for interpretation, the simulator does this:

- **Verdant Mage** takes *entangle*, cast on the spot that restrains the most
  enemies without catching allies. It competes with Hold Person for
  concentration. Rootbind is used only when the slow keeps a charging enemy
  out of reach this round, and hits extra creatures from 5th level. Memory of
  the Grove rerolls fear saves for itself and allies within 30 feet (the
  benchmark foes cause no fear, so this only comes up against the Sanguine
  Aegis). Verdant Veil goes on the lowest-AC member of the party while enemy
  archers are alive. Master of Living Paths gives disadvantage on the save
  and the 15-foot teleport.
- **Warbound Mage** takes *shield* and *booming blade*. After Patch 1 it
  wields a rapier, before it a dagger. Both use Dexterity, so its melee
  attacks are weak, and the bot only melees when that beats casting.
  Light-armour proficiency adds nothing: *mage armor* is better at Dex 14.
  War Drum, Battle Surge, Blood for Power (only while above half HP, both
  versions), Crimson Presence and Warstorm (both versions) are all modelled.
- **Stonewarden Mage** takes the free *mage armor* (AC 16, no slot). Runic
  Bulwark halves any hit of 8+ damage on itself or an ally within 30 feet.
  Stoneheart Aegis goes up on turn one when at least two allies are within 30
  feet (+2 AC and advantage on Con saves for them; the redirect is not
  modelled). Living Rampart does nothing here (no wall spells).
- **Hellbound Mage** takes *hex*. Shadow Mark goes on before save spells,
  and Curseweaver gives disadvantage on the target's next attack. From 10th
  level, fighting alone, it opens with *darkness* centred on itself (it sees
  through it) when no Hold is worth casting. With allies it never does,
  because the darkness would blind them too. Pact Nexus is used when its
  expected damage beats a spell.
- **Sanguine Mage** takes *inflict wounds* and uses Soul Tether every turn it
  can. **Flux Manipulation's save swap is assumed always DM-approved**: Hold
  Person against a fighter becomes an Intelligence save, and Hold Monster
  against a beast too. That is the single strongest thing in the book; see the
  report. Overlord opens the fight from 14th level, flips saves within 30 feet
  while above 25 HP, and pushes melee enemies 10 feet away. Prismatic Echoes
  isn't modelled.
- **Aether Mage**: guidance, Stabilizing Pulse and Adaptive Resonance do
  nothing in a fight like this. Null Field goes up when there are enemy
  spellcasters, and covers allies within 10 feet. Anchor of Tessarion's
  resistance applies (including against *disintegrate*), and its once-a-day
  save keeps someone within 30 feet at 1 HP.
- **Sanguine Aegis**: Blood Charges, Leeching Strikes, Red Pact (spends the
  most charges it may), Hunger of the Armor with Scent of Blood, and
  Overdrive on turn one at 15th level. It heals with charges below 40% HP.
- **Bulwark Aegis** guards the back rank. It has Living Wall (+1 AC, and its
  reaction gives disadvantage on attacks against an adjacent ally), Anchored
  Stance whenever it moved 10 feet or less, and immunity to being pushed from
  7th level. Unmoving Bastion gives +1 AC to allies within 10 feet. Intercepting
  Guard takes hits of 10+ (or a killing blow) meant for an ally within 10 feet,
  while above 30% HP. Fortress goes up against melee enemies once engaged and
  gives allies within 10 feet half cover.
- **Warden Aegis** guards the back rank. The anchor goes on the nearest enemy
  once it is within 30 feet. Shackle Strike is used on any hit when it has
  allies to protect (alone, only on shooters and casters). Lockstep Field
  roots on an opportunity-attack hit. Mana Cage goes up on turn one when
  there are enemy casters and protects everyone in the dome. Field Commander
  lends allies within 10 feet its Strength or Constitution for those saves.
- **Crystal Archer**: Crystal Sight opens the fight from 7th level. **Silent
  Volley is read as giving the target disadvantage on attacks against the
  archer until the archer's next turn** (the arena is assumed to have
  scattered cover). Amber Dust's temporary HP go to the most hurt friend
  within 10 feet of the target. Rain of Shards is used when it beats a volley
  and the area catches no allies.
- **Gunman** carries a backup pistol (1d10, 30/90 ft) for after Soulshot
  Barrage disables the musket. From 7th level it shoots enemy casters first,
  and Powder Disruption silences them. Recoil Step backs off 10 feet after a
  shot when a melee enemy is adjacent. Amber Slug's −2 AC counts for its own
  remaining shots and every ally's attacks until its next turn.

## Not modelled

- The Aegisbound's shared "magic-resistant armor" trait (the lore gives no
  numbers).
- *Counterspell*, *misty step*, healing allies, death saves, prone, cover,
  flying, feats, consumables, and magic items beyond the +N weapon or focus.
- Real map geometry: the line lets area spells and guards work roughly as
  they would, but flanking, chokepoints and shaping a blast around allies
  don't exist.
- Rests between fights: every fight starts fresh.
- For the campaign monsters: saving throws aren't in the YAML (they are
  guessed in `foes.py`), and of their recharge abilities only Iron-Hound's
  Wire-Net and the Mana-Mite Swarm's Surge are simulated.
