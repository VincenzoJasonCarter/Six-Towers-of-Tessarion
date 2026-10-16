# The Proving Grounds

A Monte Carlo combat simulator for the eleven subclasses in
`../lore-book/05-subclasses-skill.md`, at levels 3, 7, 10 and 15. It has
two modes:

- **One-on-one** (`run.py` → [report.md](results/report.md)). Every subclass
  against benchmark foes and against each other.
- **Party** (`party.py` → [party_report.md](results/party_report.md)). Every party of
  four different subclasses (330 of them) against four kinds of encounter.
  It measures what each subclass is worth to a team, which is where support
  and control features earn their keep.

A third mode, **evolution** (`evolve.py` → [evolution_report.md](results/evolution_report.md)),
tests the draft Ascendant and Corrupted branches in `heroes/evolution.py`, which
open at 6th level. For each subclass and branch, every party containing it
fights the party encounters twice with the same seeds, once with that hero
evolved, and the report gives the change in win rate (`make arena-evolution`;
`--only gunman/ascendant` reruns one branch against the saved baseline).

Everything the runs write (reports, raw results, encounter tuning) goes to
[`results/`](results/).

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
uv run arena/party.py --gear --only gunman   # Range with Tessarion's own weapons (party_gear_* files)
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

The tuned foe sizes are kept in `results/calibration.json` and
`results/party_calibration.json`, so results stay comparable between runs
until you recalibrate.

The code only knows the current rules. To see what a rules change does,
commit, make the change, rerun, and compare the reports with `git diff`.
Older versions of the rules (before Patch 1 to 4, the 5e Fighter chassis, the
bots before the tactics fixes) live in git history before the arena refactor
of 15 October 2026.

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
- **Impact** of a subclass, the report's main number: its share of
  everything its party did, averaged over every party it is in (25% is even
  in a party of four). It is counted in hit points, so its five parts add up
  without weights:
  - **Damage**: what it took off enemies' hit points, without overkill.
  - **Protection**: damage it kept off allies. AC auras, Living Wall, Verdant
    Veil, the Mana Cage's disadvantage and blocked spells, save advantage and
    bonuses (Stoneheart, Null Field, Fortress, Field Commander), save
    rerolls, Runic Bulwark on an ally, Intercepting Guard (the whole hit),
    temporary HP and healing given to others.
  - **Control**: enemy damage it denied. A held or stunned enemy's turn, a
    restrained one spending its action to escape, a melee enemy that would
    have closed and attacked but for its slow, root, fear or difficult
    terrain, a silenced caster, and attacks at disadvantage from its debuffs.
  - **Enable**: extra damage allies dealt because of it. Advantage against
    enemies it held, stunned or restrained, auto-crits on held enemies,
    lowered AC (Amber Slug), worse saves (Violet, restrained Dexterity saves).
  - **Tanking**: damage kept off the party by drawing attacks. For each
    attack aimed at it, the attacker's expected damage against the hero it
    would have picked otherwise (its own targeting rule, run without it and
    without dice) minus its expected damage against this one, after armour
    and resistances. A Brute that swings at the Bulwark instead of the Wizard
    behind it credits the Bulwark with the difference; drawing a hit you take
    no better than that ally earns nothing, and it is never negative.

  Rolls are credited by expectation: the change in the chance to hit or to
  save, times the damage at stake. A lost turn is worth the enemy's expected
  damage per round. Two sources of the same advantage or disadvantage share
  it, and one the creature had anyway (its own, or the situation's) leaves
  nothing to credit. Apart from Tanking, helping yourself (*shield*, your own
  advantage, Runic Bulwark on yourself) isn't credited; it shows up under the
  report's Advanced stats. The crediting never rolls a die, so fights come out
  exactly as without it. Known gaps: Anchor of Tessarion's save is credited
  only for the damage past 1 HP, not for keeping the ally in the fight;
  pushes and Booming Blade's threat aren't credited as control; and a hit
  point counts the same on anyone, so a tank soaking damage that would have
  dropped the party's best damage dealer gets no more than its armour earns.
- **Advanced stats**, descriptive and not part of Impact: Aggro (share of the
  enemy attack rolls aimed at it), Mitigated (share of the damage coming at
  it that its own reactions and resistances took off), Taken, Uptime (share
  of the fight's rounds it was standing), Survives, Kills and Overkill.
- **Win value** of a subclass: the win rate of parties that include it minus
  the win rate of parties that don't. It catches everything, credited or not,
  but doesn't say why, and it flattens out where parties win or lose
  regardless. The report gives both, with the ranks side by side. It also
  lists each subclass's survival rate and share of damage taken, the best and
  worst parties, results by number of mages, and pair synergies.

## The code

```
arena/
  engine/          the rules, independent of any subclass
    dice.py          Dice(2, 6, "fire", 3) is 2d6+3 fire; d20 rolls; hit and save chances
    context.py       Ctx: what an attack, save or damage packet is (spell? melee? a control effect?)
    creature.py      Creature: effects, position, and every hook a feature can override
    combat.py        attack(), saving_throw(), deal(): the three rules everything goes through
    impact.py        crediting protection, control, enable and tanking (never rolls a die)
    movement.py      walking the line, opportunity attacks, pushes
    fight.py         Fight: formation, initiative, the turn loop
  heroes/          the eleven subclasses, feature by feature
    wizard.py        the Wizard chassis: slots, spell list, the spell-picking bot
    crystal_mages.py Verdant, Warbound, Stonewarden, Hellbound, Sanguine, Aether
    fighter.py       the martial chassis: one attack a turn, weapons, the melee bot
    aegisbound.py    Sanguine, Bulwark, Warden
    ranged.py        Crystal Archer, Gunman, their ammunition loadouts and Tessarion gear
    evolution.py     the Ascendant and Corrupted branches (draft)
  foes.py          benchmark archetypes, party encounters, the campaign's stat blocks
  run.py           one-on-one: calibration, experiments, report
  party.py         parties: calibration, every party, report
  evolve.py        evolution branches: uplift per subclass and branch
  results/         everything the runs write
```

**How a feature plugs in.** A subclass is a class that overrides hooks on
`Creature` (listed, grouped and commented at the bottom of
`engine/creature.py`). The rules call them at fixed moments: `attack()` asks
the attacker for `my_attack_adv` and `bonus_damage`, asks the target's allies
for `ally_attacked` (Living Wall) and `ally_hit_reaction` (Null Field), then
calls `on_hit`; `deal()` asks for `intercept`, `reduce_damage`, `resists`,
`damage_reaction` and `ally_damage_reaction`; `saving_throw()` asks for the
save's advantage, bonuses and rerolls. Effects on creatures are named strings
(`"paralyzed"`, `"tethered"`, `"slow"`...); the table at the top of
`engine/creature.py` says what each one does and who adds it. Zones on the
line (Gravitic Anchor, Pact Nexus, Lockstep Field) are `Zone` subclasses with
`on_enemy_turn_start` and `on_enemy_turn_end`.

To test a rules change, edit the subclass, run with `--recalibrate`, and
compare the reports.

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
  most hurt enemy in reach.
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
- Ammunition and other choices are also picked by expected value, from what
  the hero actually carries.
- **Competent play**: every subclass is meant to be played at the same
  level, by someone who knows their kit but not what the next fight holds.
  Range characters craft their special ammunition at a rest, so they carry a
  fixed loadout (`LOADOUT` in `heroes/ranged.py`: the mix the bot chose when
  it could pick any kind at the moment it fired, over all four encounters)
  instead of the best kind for this enemy. The Warbound plays as described
  below.

## Builds and gear

**One attack per turn**: Tessarion's class progression (the sheet linked
from lore-book Ch.2) gives every class a single attack per turn at every
level, and the Aegisbound and Range have none of the 5e Fighter's Action
Surge, Second Wind or Indomitable. Their damage grows only through their
weapon, Resonance Rank and subclass features. Reports from before 12 October
2026 were run on the full 5e Fighter chassis, which overrated the Aegisbound
and Range from 5th level.

**Patch 4**: every Aegisbound has a d12 hit die (about +1 HP a level), and
from 5th level Reinforced Plating takes its proficiency bonus off the damage
of each weapon attack that hits it, before resistance (`Aegis.reduce_damage`).
Spells and area effects aren't weapon attacks. The Warden's Shackle Strike
shackles every creature it hits until the start of its next turn, and a
shackled creature attacks anyone but the Warden at disadvantage (credited to
the Warden as Control); the Peacekeeper and Gravewell riders keep the old
proficiency-bonus uses. The Sanguine Aegis's Blood Lure (`lures`) gives an
enemy within 10 feet of it disadvantage against anyone else while it has a
Blood Charge (also credited as Control), and its Red Pact is spent as a hit
lands instead of as a bonus action before the attack. Special arrows' and
shots' effects, and Powder Disruption's silence, last until the start of the
shooter's turn after next. Resonant Shot adds 1d4 force per Resonance Rank to
the first weapon hit on each of the shooter's turns: the Gunman's from 3rd
level, the Crystal Archer's from 7th. The Sanguine Mage's Soul Tether is its
own effect (`soul_tether`); until Patch 4 it shared the Warden's, so a
creature the mage had tethered also attacked anyone but the mage at
disadvantage, which the lore never gave it (worth about 8 points of its
party value).

All characters are human with no feats, average HP, and ability score
increases into the main stat and then Constitution.

| | Wizard | Aegisbound | Range |
|---|---|---|---|
| Scores (1st level) | Int 16, Dex 14, Con 14 | Str 16, Con 14 | Dex 16, Con 14 |
| Armour | *Mage armor*, cast before the day (costs a 1st-level slot) | Chain mail and shield (plate from 5th), Defense style | Studded leather, Archery style |
| Weapon | Spells | Longsword | Longbow (Archer), musket 1d12, 40/120 ft (Gunman) |

With `--gear` (`uv run arena/party.py --gear --only gunman`, then `--only
archer`; `heroes/ranged.py`), the two Range subclasses carry Tessarion's own weapons from
`data/items.yaml` instead: Tier 1 at 3rd level, Tier 2 from 5th. The Gunman
has the Matchlock Musket and Crude Handgun, then the Black-Powder Rifle
(80/200 ft from Patch 4) and Heavy Handgun, and keeps its distance by its long
gun's normal range; a natural 1 fouls the gun (Misfire), and clearing it costs an
action at Tier 1 or a bonus action at Tier 2. With the long gun fouled the
bot fires its handgun, and spends an action clearing only once both are
fouled. The Crystal Archer has the Crude Crossbow (a natural 1 slips the
latch: an action to re-span), then the Composite Bow (1d8 + 1, no
disadvantage at long range, Heavy Draw: half speed on a turn it fires).
Marksman's Focus counts for any bow or crossbow. A Tier 2 item's own +1 is
damage only, on top of the magic weapon below. The run keeps the plain run's
encounter tuning and dice seeds and writes `party_gear_*` files, so it
compares straight against `party_report.md`.

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
  wields a greatsword (its one martial weapon, attacking with Intelligence
  since Patch 3; a rapier without competent play), before it a dagger. The
  bot stays in the back rank and only melees when that beats casting: a
  front-line Warbound was tried and stood for about half the fight instead of
  two thirds, for less Impact. Light-armour proficiency adds nothing: *mage
  armor* is better at Dex 14. It starts each fight with 0 to 3 Beats (they
  last until a rest), and with 3 it counts the War Drum crit toward attacks
  that can carry it. War Drum, Battle Surge, Blood for Power (only while
  above half HP, both versions), Crimson Presence and Warstorm (both
  versions) are all modelled.
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
