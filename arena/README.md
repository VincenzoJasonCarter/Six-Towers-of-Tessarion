# The Proving Grounds

A Monte Carlo combat simulator for the eleven subclasses in
`../lore-book/05-subclasses-skill.md`. It runs hundreds of thousands of
one-on-one fights and ranks the subclasses at levels 3, 7, 10 and 15, both
as written now and as they were before Patch 1 (`../balance-patch.md`).

The output is [report.md](report.md) (the rankings) and `results.json` (every
raw number).

## Running it

From the repo root:

```
make arena                          # or: uv run arena/run.py
uv run arena/run.py --n 200         # quicker and noisier (default is 1000 fights per matchup)
uv run arena/run.py --recalibrate   # re-tune the benchmark foes (do this after changing rules)
uv run arena/run.py --report-only   # rebuild report.md from results.json
```

A full run takes about 5 minutes on 8 cores; `--recalibrate` adds about 5
more. The tuned foe sizes are kept in `calibration.json` so the rankings stay
comparable between runs until you recalibrate.

## What it measures

- **Gauntlet** (the ranking). Each subclass fights four solo foes built from
  the DMG's monster-by-CR numbers: a **Brute** (beast, one huge hit, fast), a
  **Soldier** (humanoid, armoured, two attacks), a **Sniper** (humanoid
  archer who keeps its distance) and a **Caster** (humanoid, a Dexterity-save
  blast every turn). Each foe's HP and damage are scaled, separately for
  Wizards and Fighters, until the average subclass of that chassis wins half
  its fights. 50% is par within a chassis.
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

## Files

| File | What it holds |
|---|---|
| `engine.py` | Dice, conditions, attacks, saves, damage, concentration, movement and the turn loop |
| `heroes.py` | The Wizard and Fighter chassis and the eleven subclasses, feature by feature, with the pre-patch rules behind `patched=False` |
| `foes.py` | The benchmark archetypes and the loader for the campaign's stat blocks |
| `run.py` | Calibration, the experiments, `results.json` and `report.md` |

To test a rules change, edit the subclass in `heroes.py`, run with
`--recalibrate`, and compare the report. To compare against the current rules
instead, add the change behind a flag the way `patched` works.

## The arena

Two combatants start 60 feet apart on a 120-foot line with a wall at each
end, so a shooter can back away 30 feet before it is cornered. Movement is in
5-foot steps. Entering difficult terrain costs double, and leaving a foe's
reach provokes an opportunity attack. A fight ends when one side drops to 0
HP. There are no death saves, and after 20 rounds the fight is a draw, which
counts as half a win.

The combatants are bots. Melee fighters close in, dashing when they can't
reach, and use Action Surge on the first turn they can attack. Shooters and
casters back away from anything that wants to melee them. Once engaged, they
step out (and take the opportunity attack) only when the foe can't follow,
for example after Verdant Snare or Entangle. Wizards cast Hold Person (Hold
Monster from 10th level) when it's likely to land and nothing is held yet.
Otherwise they cast whatever has the highest expected damage this turn, so
they spend their biggest slots first. Ammunition and other choices are also
picked by expected value.

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
Overlord, Soulshot Barrage) and Wizards in general.

## How each feature was read

Where the text left a choice or room for interpretation, the simulator does this:

- **Verdant Mage** takes *entangle*, which competes with Hold Person for
  concentration. Rootbind is used only when the slow keeps a charging foe out
  of reach this round. Memory of the Grove rerolls fear saves. Verdant Veil is
  used against ranged foes. Master of Living Paths gives disadvantage on the
  save and the 15-foot teleport.
- **Warbound Mage** takes *shield* and *booming blade*. After Patch 1 it
  wields a rapier, before it a dagger. Both use Dexterity, so its melee
  attacks are weak, and the bot only melees when that beats casting.
  Light-armour proficiency adds nothing: *mage armor* is better at Dex 14.
  War Drum, Battle Surge, Blood for Power (only while above half HP, both
  versions), Crimson Presence and Warstorm (both versions) are all modelled.
- **Stonewarden Mage** takes the free *mage armor* (AC 16, no slot). Runic
  Bulwark halves any hit of 8+ damage. Living Rampart does nothing here (no
  wall spells), and Stoneheart Aegis protects allies, so it is never used solo.
- **Hellbound Mage** takes *hex*. Shadow Mark goes on before save spells,
  and Curseweaver gives disadvantage on the foe's next attack. From 10th
  level it opens with *darkness* centred on itself (it sees through it)
  against shooters and casters, or after one Hold attempt against melee.
  Pact Nexus is used when its expected damage beats a spell.
- **Sanguine Mage** takes *inflict wounds* and uses Soul Tether every turn it
  can. **Flux Manipulation's save swap is assumed always DM-approved**: Hold
  Person against a fighter becomes an Intelligence save, and Hold Monster
  against a beast too. That is the single strongest thing in the book; see the
  report. Overlord opens the fight from 14th level, flips saves within 30 feet
  while above 25 HP, and pushes melee foes 10 feet away. Prismatic Echoes
  never triggers, because the kill ends the fight.
- **Aether Mage**: guidance, Stabilizing Pulse and Adaptive Resonance do
  nothing in a fight like this. Null Field goes up against spellcasters.
  Anchor of Tessarion's resistance applies (including against
  *disintegrate*); its death-save clause doesn't come up.
- **Sanguine Aegis**: Blood Charges, Leeching Strikes, Red Pact (spends the
  most charges it may), Hunger of the Armor with Scent of Blood, and
  Overdrive on turn one at 15th level. It heals with charges below 40% HP.
- **Bulwark Aegis**: Living Wall's +1 AC, Anchored Stance whenever it moved
  10 feet or less, immunity to being pushed from 7th level, and Fortress
  against melee foes once engaged. Its features that protect allies don't
  apply in a duel.
- **Warden Aegis**: the anchor is placed on the foe once it's within 30 feet.
  Shackle Strike is used on shooters and casters, Lockstep Field roots on an
  opportunity-attack hit, and Mana Cage goes up on turn one against a caster.
  Field Commander does nothing solo.
- **Crystal Archer**: Crystal Sight opens the fight from 7th level. **Silent
  Volley is read as giving the foe disadvantage on attacks against the archer
  until the archer's next turn** (the arena is assumed to have scattered
  cover). Rain of Shards is used when it beats a volley and the archer isn't
  inside the blast. Before Patch 1 it never is.
- **Gunman** carries a backup pistol (1d10, 30/90 ft) for after Soulshot
  Barrage disables the musket. Powder Disruption silences casters, and
  Recoil Step backs off 10 feet after a shot when a melee foe is adjacent.
  Amber Slug's −2 AC only helps the Gunman's own later shots that turn, so
  solo it rarely beats Red Impact. In a party, every ally's attacks would
  benefit.

## Not modelled

- Party play: allies, healing others, intercepting, auras for allies. This is
  where Bulwark, Warden, Stonewarden and Aether earn their keep, so their
  solo numbers understate them.
- The Aegisbound's shared "magic-resistant armor" trait (the lore gives no
  numbers).
- *Counterspell*, *misty step*, prone, cover, flying, feats, consumables, and
  magic items beyond the +N weapon or focus.
- Rests between fights: every fight starts fresh.
- For the campaign monsters: saving throws aren't in the YAML (they are
  guessed in `foes.py`), and of their recharge abilities only Iron-Hound's
  Wire-Net and the Mana-Mite Swarm's Surge are simulated.
