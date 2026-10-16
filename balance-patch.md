# Balance Patch Notes

Changes to the class and subclass rules in the lore-book, newest patch first. The full text of every feature is in the Library, on the *Rites of Ascension* shelf, in *Subclasses Skill*.

[buff] stronger · [nerf] weaker · [new] new feature or option · [change] reworked, about the same power

---

## Patch 4 — 2026-10-12

Two new traits shared by every Aegisbound order, a new Shackle Strike for the Warden, Blood Lure and a reworked Red Pact for the Sanguine Aegis, and for the Range longer-lasting special ammunition, Resonant Shot and a longer-ranged Black-Powder Rifle, tested in the Proving Grounds.

> *Why:* The Proving Grounds now play every class as Tessarion does: **one attack per turn at every level**, and no Action Surge, Second Wind or Indomitable for the Aegisbound or Range (earlier reports ran them on the 5e Fighter, with Extra Attack). On that footing all three Aegisbound orders fall below an even share from 7th level: the wall drew the blows (31–39% of every attack aimed at the party) and fell before it could keep the mages standing (30–37% still on their feet at the end). The Classes chapter has always promised them "high physical durability and HP"; these two traits are that promise in rules.

### Aegisbound

- **Hit points** [buff]: from 3rd level your hit die is a **d12** instead of a d10. Work out your hit points as if it had always been (about **+1 hit point per level**, +2 at 1st).
- **Reinforced Plating (5th level)** [new]: when a **weapon attack** hits you, the damage it deals is reduced by your **proficiency bonus** (+3 at 5th level, up to +6 at 17th). Spells, breath, and other area effects aren't weapon attacks. It applies before Anchored Stance's resistance halves what is left.

Magic resistance stays with the armor itself: it comes with Tier 3 Aegisbound armor and up, not with the order.

### Warden Aegis

> *Why:* Switched off one at a time in the Proving Grounds, Gravitic Anchor and Lockstep Field each carried about 6 points of the Warden's party value, and Shackle Strike carried almost none: a 10-foot slow means nothing to a foe already in reach, so the Warden had no answer to a single strong enemy (−20 against the Boss). It is now the tool for exactly that.

- **Shackle Strike (3rd level)** [change]: a hit slowed the target by 10 feet, proficiency bonus times per long rest → **every melee weapon hit shackles the target to you** until the start of your next turn, and a shackled creature has **disadvantage on attack rolls against anyone but you**.
- **Peacekeeper and Gravewell** (6th level) [change]: their Shackle Strike riders (Peacekeeper's disadvantage on the next attack, Gravewell's 1d4 force per Rank) keep the old **proficiency bonus uses per long rest**, so neither branch grows.

### Sanguine Aegis

> *Why:* The Sanguine Aegis drew more of the enemy's attacks than anyone (up to half of them against the Boss) and fell first, and everything it did with its charges healed only itself. Switched off one at a time, its self-healing was worth about 1 point of party value and Red Pact about 5. Healing the Aegis harder (temporary hit points at 1d6 instead of 1d4 changed nothing) doesn't win fights; keeping the enemy off the mages does. Blood Lure gives it that job, and ties it to the charges, so a Sanguine Aegis has to choose between burning its blood for damage or healing and keeping the enemy's eyes on itself.

- **Blood Lure (3rd level, part of Bloodwell Armor)** [new]: while you have at least **1 Blood Charge**, a hostile creature within **10 feet** of you has **disadvantage on attack rolls against anyone but you**. With no charges, the lure falls silent.
- **Red Pact (7th level)** [change]: spent as a **bonus action before the attack**, and lost if the attack missed → spent **when you hit** with a weapon attack, **no action required**. Same cap (half your fighter level), same 1d6 necrotic per charge and the same fear save. With one attack a turn, a miss no longer throws the charges away, and the bonus action stays free for healing.

### Range

> *Why:* With one attack a turn, a special arrow or shot is the Range's main way to shape a fight, and its effects lasted exactly one enemy turn. Tested at two rounds, the Gunman's party value rose by about 3 points (more from 7th level, where Powder Disruption rides on the special shots) and the Crystal Archer's didn't move: its usual arrows (Amber, Prismatic, Red) act at once and have nothing to extend.

- **Modular Ammunition and Crystal-Cased Rounds** [buff]: every effect of a special arrow or special shot that lasted until the start of your next turn (Verdant Dust and Verdant Snare, White Dust, Violet Dust and Violet Hex, Amber Slug, Prismatic Round's no-healing) now lasts **until the start of your turn after next**.
- **Gunman, Powder Disruption (7th level)** [buff]: the silence a special shot inflicts lasts likewise **until the start of your turn after next**.

> *Why Resonant Shot:* With one attack a turn, nothing in the Range's kit grew with its level: Marksman's Focus is a flat +2 and special ammunition is a few shots a rest. At 7th level a Gunman took about half as many hit points off the enemy as a mage did (97 a fight against 190). Resonant Shot is that growth. The Crystal Archer gets it at 7th level, not 3rd: at 3rd it already pulled its weight (+2), and with Resonant Shot from 3rd it overshot (+12).

- **Resonant Shot** [new]: once on each of your turns, when you hit a creature with a ranged weapon attack, it takes an extra **1d4 force damage per Resonance Rank**. The **Gunman** has it from **3rd level** (part of Ballistic Training), the **Crystal Archer** from **7th level** (with Crystal Sight, whether or not it is in hyper-focus).
- **Black-Powder Rifle** (Tier 2 Gunman weapon, Ch.7) [buff]: range **40/120 → 80/200**. A rifled barrel should reach further than the musket it replaces. Tested alone, it kept more Gunmen on their feet at 7th level (47% → 58% still standing at the end) and changed little from 10th, where the enemy reaches it anyway. With its Tier 2 guns the Gunman is +2 (`arena/results/party_gear_report.md`).

> *Proving Grounds fix:* the arena gave Soul Tether and the Warden's new Shackle Strike the same effect, so a creature the Sanguine Mage had tethered also attacked anyone but the mage at disadvantage, which the lore never gave it. Fixed, the Sanguine Mage's party value falls from +17 to +8. Its rules don't change.

**Party value** (win rate with the subclass minus without, averaged over 3rd, 7th, 10th and 15th level; every fight at full resources; `arena/results/party_report.md`):

| Subclass | Before | After | 3rd | 7th | 10th | 15th |
|---|---:|---:|---:|---:|---:|---:|
| Bulwark Aegis | −5 | **−3** | +12 | −1 | −5 | −16 |
| Warden Aegis | −10 | **−4** | −6 | −3 | +0 | −7 |
| Sanguine Aegis | −11 | **−4** | +6 | −5 | −9 | −7 |
| Crystal Archer | −9 | **−4** | +2 | +1 | −8 | −11 |
| Gunman | −9 | **+0** | −7 | +4 | −1 | +5 |
| Sanguine Mage (for comparison) | +12 | +8 | +2 | +5 | +10 | +14 |

The Range's *Before* is this patch's Aegisbound changes alone, without lasting ammunition or Resonant Shot.

All three orders now sit within 4 points of even, from 5 to 11 below it. The Sanguine Aegis gains the most (+7): with Blood Lure, the mages behind it live long enough to matter. The Bulwark is about even at 7th level, the Warden at 10th. At 15th level the Bulwark still trails, where Tier 3 armor is meant to carry it.

The Gunman is even, weakest at 3rd level and above even from 7th, where Powder Disruption silences the enemy's casters. The Crystal Archer is 4 below. It is a striker with no control, and from 10th level, where a landed Hold decides more fights than the same damage dealt, its party value trails (−8, −11) though its share of the party's damage is the largest of any subclass (24–25%).

The Sanguine Mage, which this patch doesn't touch, is still the strongest subclass (+8), most of it at 10th and 15th level.

---

## Patch 3 — 2026-10-07

Three changes, tested together in the Proving Grounds (`arena/results/party_report.md`, `arena/results/evolution_report.md`):

1. **Resonance Rank:** subclass dice now grow as the subclass grows.
2. **Subclass Evolution reworked:** Corrupted is now the subclass's own kit turned to raw damage for one fight at a time, and each subclass's two branches are matched in value.
3. **Base-kit rebalance** for the subclasses furthest from the middle of their pillar.

### Resonance Rank [new]

> *Why:* Many subclass features rolled the same dice from 2nd or 3rd level to 20th (Soul Tether's 1d6, Shadow Mark's flat damage, the special arrows and rounds), so they faded as enemies grew. Now every time a subclass gains a subclass feature, its dice step up.

| Resonance Rank | Crystal Mages | Aegisbound and Range |
|---|---|---|
| 1 | 2nd level | 3rd level |
| 2 | 6th | 7th |
| 3 | 10th | 10th |
| 4 | 14th | 15th |

- [new] A feature that says "per Resonance Rank" rolls that many dice: 1d6 per Rank is 1d6 at Rank 1 and 4d6 at Rank 4.
- Flat bonuses keep following the proficiency bonus. Effects that fire on every hit (War Drum's Beats, Spiteplate) don't scale, because they already grow with the number of attacks.

**Base-kit features that now scale**

- **Hellbound Mage, Shadow Mark** [buff]: Intelligence necrotic → **1d6 per Rank + Intelligence**
- **Sanguine Mage, Soul Tether** [buff]: 1d6 → **1d6 per Rank**
- **Crystal Archer, Crystal Sight** [buff]: +1d6 → **+1d6 per Rank**
- **Crystal Archer, Red Dust and Prismatic Dust** [buff]: +1d4 → **+1d4 per Rank** (Prismatic still heals what it deals)
- **Crystal Archer, Amber Dust** [buff]: 1d4 + proficiency bonus temporary HP → **1d4 per Rank** + proficiency bonus
- **Gunman, Red Impact and Prismatic Round** [change]: +1d6 → **+1d4 per Rank** (a little weaker at Rank 1, stronger from Rank 2)

### Base-kit rebalance

> *Why:* After Resonance Rank, the Crystal Mages spread from Stonewarden (+5.7) to Hellbound (−6.8) in party value, and the Aegisbound left the Sanguine Aegis behind. Values below are each subclass's party value as written, averaged over 7th, 10th and 15th level.

**Crystal Mages**

- **Hellbound Mage, Curseweaver (6th level)** [buff]: costs your reaction → **no reaction**, uses unchanged
- **Hellbound Mage, Pact Nexus (14th level)** [buff]: Intelligence necrotic → **Intelligence + 1d6 per Rank** necrotic
- **Warbound Mage, Crimson Attunement (2nd level)** [buff]: your martial melee weapon now uses **Intelligence** for its attack and damage rolls
- **Stonewarden Mage, Runic Bulwark (6th level)** [nerf]: uses equal to your Intelligence modifier → **half your Intelligence modifier, rounded up** (minimum 1)
- **Sanguine Mage, Flux Manipulation (6th level)** [nerf]: changing a save's ability score → **once per long rest**; changing the damage type keeps its Intelligence-modifier uses

**Aegisbound**

- **Sanguine Aegis, Bloodwell Armor (3rd level)** [buff]: 1d4 per Blood Charge spent on healing → **1d6**
- **Bulwark Aegis, Unmoving Bastion (7th level)** [buff]: +1 AC to allies within 10 feet → **+2 from 15th level**

**Range**

- **Crystal Archer, Marksman's Focus** unchanged at +2. Under Resonance Rank alone it was briefly tested at + proficiency bonus, which put the Range pillar about 10 points above the others.

| Subclass | Before | After |
|---|---:|---:|
| Stonewarden Mage | +5.7 | +4.9 |
| Sanguine Mage | +4.9 | +3.1 |
| Verdant Mage | −2.3 | −2.0 |
| Hellbound Mage | −6.8 | **−2.5** |
| Aether Mage | −3.7 | −3.5 |
| Warbound Mage | −6.6 | −6.0 |
| Bulwark Aegis | −2.0 | −1.4 |
| Warden Aegis | −1.2 | −1.9 |
| Sanguine Aegis | −5.8 | −5.2 |
| Gunman | +8.4 | +8.9 |
| Crystal Archer | +9.3 | +5.8 |

Spread within each pillar: Crystal Mages 12.5 → 10.9 points, Aegisbound 4.6 → 3.8, Range 0.9 → 3.1.

### Subclass Evolution: the seal and the Corrupted kits [change]

> *Why:* Patch 2's Corrupted powers were one bolt-on burst each, nearly identical across subclasses, and some still carried utility. Corrupted is now the subclass's **own kit turned to raw damage** for one fight at a time, so each one plays differently. For the Aegisbound, the damage carries the role: lifesteal, punishing hits on allies, crushing what the anchor holds. The goal is no longer that every evolution is worth the same. It is that **each subclass's Ascendant and Corrupted are worth the same over a day**, so a subclass is balanced once, as a whole (base kit + evolution).

**Opening the seal**

- [change] Each use of a Corrupted power adds 1 Assimilation → at the start of a fight, a Corrupted character may **open the seal**. For that fight their kit changes as listed below, and Assimilation goes up by **1**. With the seal closed, they fight with their base kit.
- A long rest still takes 1 Assimilation off, so opening the seal once a day holds steady. The kits are tuned for a day of two hard fights with the seal opened for one: in that fight, a Corrupted kit is worth about **twice** its Ascendant.
- [change] Patch 2's burst dice and its once-per-turn limit are gone. Marking, Fracture and Loss are unchanged.

**Crystal Mages**

| Subclass | Ascendant | Corrupted, seal open |
|---|---|---|
| Verdant Mage | **Grovekeeper** [buff]: also gives allies within 30 feet a bonus to saving throws equal to your **Resonance Rank**. | **Thornblood:** *rootbind* deals **1d8 piercing per Rank** on a failed save. A creature restrained by one of your spells takes **1d10 per Rank + 1d10 + your Intelligence modifier** in piercing at the start of each of its turns. |
| Warbound Mage | **Drumwarden** [nerf]: uses per long rest: proficiency bonus → **half your proficiency bonus, rounded up**. | **Ironblood:** each Beat you hold adds **1d8 fire** to your attack roll hits. Blood for Power adds **three times** the hit points you lose. |
| Stonewarden Mage | **Runekeeper:** unchanged. | **Splinterskin:** damage your Runic Bulwark prevents is stored as shards, and added as **force** to the next damaging spell you cast. |
| Hellbound Mage | **Ashwarden:** unchanged. | **Debtcaller:** your Shadow Mark lasts until collected; a failed save no longer ends it unless you collect. Each time the marked creature takes damage from you or an ally, its debt grows by **1d10**. Collect the whole debt as **necrotic** when it fails a save against your spell, or as a **bonus action**. |
| Sanguine Mage | **Penitent** [buff]: Soul Tether drains **d8s per Rank** instead of d6s and heals a creature of your choice within 30 feet for the damage + your Intelligence modifier. | **Prism-Burst:** Soul Tether drains an **extra 1d6 per Rank** in necrotic (the extra doesn't heal you) and has **no use limit** this fight. When the tethered creature drops to 0 hit points, the tether **leaps** to the nearest enemy within 30 feet of it, which takes **2d6 per Rank** at once. |
| Aether Mage | **Steadying Pulse:** unchanged. | **Hollow Mirror:** Stabilizing Pulse turns inside out. Bonus action: a creature within 30 feet makes a Constitution save, taking **1d8 + 1d8 per Rank + your Intelligence modifier** in force on a failure (half on a success), with twice the dice against a spellcaster. Same uses as Stabilizing Pulse. Also, reaction: when you or a creature within 30 feet takes damage from a hostile spell, the caster takes **half-level d6s** of force. |

**Aegisbound**

| Subclass | Ascendant | Corrupted, seal open |
|---|---|---|
| Sanguine Aegis | **Leashed:** unchanged. | **Bloodfused:** your first melee hit each turn deals extra necrotic equal to **twice your proficiency bonus**. Red Pact's dice are **d8s** instead of d6s. |
| Bulwark Aegis | **Shieldbearer** [buff]: temporary HP → **twice your proficiency bonus + your Constitution modifier**. | **Spiteplate:** while your Anchored Stance holds, a creature that hits you or an ally within 5 feet of you with a melee attack takes **2d6 + your Constitution modifier + your proficiency bonus** in thunder. |
| Warden Aegis | **Peacekeeper:** unchanged. | **Gravewell:** a creature that fails its save against your Gravitic Anchor takes **1d6 force per Rank**. A Shackle Strike hit deals an extra **1d4 force per Rank**. |

**Range**

| Subclass | Ascendant | Corrupted, seal open |
|---|---|---|
| Crystal Archer | **Spotter's Mark** [buff]: from **Rank 3**, the first ally hit on the marked creature also deals **1d6 per Rank**. | **Shardblood:** a special arrow deals an extra **1d6 force per Rank** and bursts: each other enemy within 5 feet of the target takes **1d4 force per Rank**. |
| Gunman | **Covering Fire** [buff]: the penalty die grows with Rank: **d4 / d6 / d8 / d10** at Rank 1 to 4. | **Powderveins:** a special shot deals an extra **1d6 force per Rank**. A creature that fails its save against Powder Disruption or Soulshot Barrage takes **1d6 thunder per Rank**. |

**Ascendant vs Corrupted per day** (party win-rate uplift, mean of 7th, 10th and 15th level; Corrupted counted at half, for one opened fight in two):

| Subclass | Ascendant | Corrupted per day | Gap |
|---|---:|---:|---:|
| Verdant Mage | +2.8 | +2.2 | −0.6 |
| Warbound Mage | +3.0 | +2.2 | −0.8 |
| Stonewarden Mage | +1.4 | +2.1 | +0.7 |
| Hellbound Mage | +3.1 | +2.8 | −0.3 |
| Sanguine Mage | +4.7 | +3.4 | −1.3 |
| Aether Mage | +3.1 | +2.8 | −0.3 |
| Sanguine Aegis | +3.0 | +2.4 | −0.7 |
| Bulwark Aegis | +2.7 | +2.0 | −0.8 |
| Warden Aegis | +2.0 | +3.2 | +1.2 |
| Crystal Archer | +3.7 | +3.3 | −0.4 |
| Gunman | +3.3 | +2.5 | −0.8 |

Differences under about 1.5 points are noise. Sanguine Mage and Warden Aegis drifted after the base-kit rebalance and are the next to retune.

### Known issues, not yet addressed

- **Crystal Archer falls off after 7th level** (+16 at 7th, −1 at 15th) even though its share of the party's damage keeps rising (37% to 42%). At high level the fights are decided by enemy spellcasters, and the Archer has no answer to them; the Gunman's Powder Disruption does. Candidate fixes: a way for the Archer to break concentration (Violet or White Dust), and a Silent Volley that protects allies, not just the Archer.
- **Warbound Mage is still the weakest Crystal Mage** (−6.0). The Intelligence weapon barely helped, because Warbound Mages rarely choose melee over a spell.
- **Bulwark Aegis** is strong at 3rd level (+17) and weak at 15th (−11).
- **The Range pillar sits well above the other two** (+6 to +9 against roughly −6 to +5). This is across pillars, so it doesn't break the within-pillar rule, but parties with a Range character win noticeably more often.
- Fracture text (Assimilation 4) is still to be written.
- The simulator tests 7th, 10th and 15th level; the Rank steps at 14th (Mages) and the evolutions above 15th are untested.

---

## Patch 2 — 2026-10-07

### Subclass Evolution [new]

> *Why:* After six Crystallizations a practitioner's body starts to form soulstone, and it has to settle one of two ways: contain the mana or pass it on (the lore is in *On Threshold Assimilation*, on the *Rites of Ascension* shelf). Every subclass now chooses a branch at 6th level. **Ascendant** gives support with no cost. **Corrupted** gives damage paid for with Assimilation. Both branches were tested in the Proving Grounds (`arena/results/evolution_report.md`): within each pillar, every subclass's Ascendant lands within 2 points of the others in party win rate, and so does every Corrupted.

**How it works**

- [new] At **6th level**, choose **Ascendant** or **Corrupted**. An Ascendant can later become Corrupted; a Corrupted character can never become Ascendant.
- [new] **Ascendant** (pre-assimilation): a support feature built on one you already have. No cost.
- [new] **Corrupted** (full assimilation): one Corrupted power. Each use adds **1 Assimilation**. No other limit, but at most once per turn.
- [new] Every Corrupted power deals the same **burst**: d8s equal to half your level (rounded down).

| Level | 6–7 | 8–9 | 10–11 | 12–13 | 14–15 | 16–17 | 18–19 | 20 |
|---|---|---|---|---|---|---|---|---|
| Burst | 3d8 | 4d8 | 5d8 | 6d8 | 7d8 | 8d8 | 9d8 | 10d8 |

**Assimilation (0–6)**

| Assimilation | Effect |
|---|---|
| Long rest | −1 |
| 2 | **Marking:** your crystal's physical signs show in full and don't fade. |
| 4 | **Fracture:** your crystal's long-term side effect becomes a rule, not a roleplay note (text to come). |
| 6 | **Loss:** at the start of each combat, DC 15 Constitution save or the DM controls you for that fight. Only a rite at an Aether Hall brings you back, and it sets Assimilation to 3. |

**Crystal Mages**

| Subclass | Ascendant | Corrupted |
|---|---|---|
| Verdant Mage | **Grovekeeper.** Memory of the Grove can reroll **any** failed saving throw (you or a creature within 30 feet), not only Perception, charm and fear. +1 use. | **Thornblood.** When a creature fails its Strength save against your *rootbind* or *entangle* on your turn: burst piercing, and it is **restrained** until the end of its next turn. |
| Warbound Mage | **Drumwarden.** Bonus action: each ally within 30 feet gains temporary HP equal to your Intelligence modifier (minimum 1) and **advantage** on its next attack roll before the end of its next turn. Proficiency bonus uses per long rest. | **Ironblood.** When you use Blood for Power, the empowered spell also deals the burst in fire to one damage roll. |
| Stonewarden Mage | **Runekeeper.** Runic Bulwark reaches **60 feet** (was 30). | **Splinterskin.** When you use Runic Bulwark, the creature that dealt the damage takes the burst in force, no save. |
| Hellbound Mage | **Ashwarden.** A creature under your Shadow Mark has **disadvantage** on its next attack roll before the end of your next turn. | **Debtcaller.** When a creature under your Shadow Mark fails a save against your spell: burst necrotic, its speed drops by 10 feet until the end of your next turn, and it has disadvantage on its next attack roll. No reaction, no Curseweaver use. |
| Sanguine Mage | **Penitent.** Soul Tether's drain heals you **or a creature of your choice within 30 feet**, for the damage + your Intelligence modifier. | **Prism-Burst.** Bonus action, with a tether active: detonate it for the burst in necrotic, and regain **half** the damage. The tether ends. Doesn't use a Soul Tether use. |
| Aether Mage | **Steadying Pulse.** Stabilizing Pulse is a **bonus action**, and the creature also gains temporary HP equal to your wizard level, even if no condition is ended. | **Hollow Mirror.** Reaction, when you or a creature within 30 feet takes damage from a hostile spell: that damage is **halved**, and the caster takes the burst in force. |

**Aegisbound**

| Subclass | Ascendant | Corrupted |
|---|---|---|
| Sanguine Aegis | **Leashed.** When Leeching Strikes heals you, one ally within 30 feet regains **twice your proficiency bonus** in hit points. | **Bloodfused.** When you hit with a melee weapon attack on your turn: burst necrotic, and you gain Blood Charges equal to your proficiency bonus (up to your maximum). |
| Bulwark Aegis | **Shieldbearer.** Living Wall's reaction protects allies within **10 feet** (was 5), and the protected ally gains temporary HP equal to your proficiency bonus + Constitution modifier. | **Spiteplate.** When a melee attack hits you (no reaction): you take **half** its damage, and the attacker takes the burst in thunder. |
| Warden Aegis | **Peacekeeper.** A creature hit by Shackle Strike also has **disadvantage** on its next attack roll before the start of your next turn. | **Gravewell.** Bonus action: your Gravitic Anchor collapses and ends. Each enemy within 10 feet of it is pulled up to 10 feet toward it and makes a Strength save against your Gravitic Anchor DC: the burst in force and speed 0 until the start of your next turn on a failure, half damage on a success. |

**Range**

| Subclass | Ascendant | Corrupted |
|---|---|---|
| Crystal Archer | **Spotter's Mark.** When you hit a creature with a special arrow, your allies have **advantage** on attack rolls against it until the start of your next turn. | **Shardblood.** When you hit with a bow on your turn: the burst in force. |
| Gunman | **Covering Fire.** Reaction, when a creature you can see within your firearm's normal range makes an attack roll against an ally: that roll takes a **−1d4** penalty. Uses per long rest: half your proficiency bonus + 1 (rounded down). | **Powderveins.** When you hit with a firearm on your turn: the burst in force, rolled as **d10s** instead of d8s. |

---

## Patch 1 — 2026-10-04

### Crystal Archer [buff]

> *Why:* The Archer trailed the Gunman at every tier and had the weakest capstone in the Range class. It is now flexible and quiet with an area finisher, while the Gunman breaks defenses and shuts down casters.

**Modular Ammunition (3rd level)**

- [buff] 2 arrow types (Verdant, Red) → 6 arrow types, one per soulstone. Crafting is still free.

| Arrow | Effect on a hit |
|---|---|
| Verdant Dust | *Unchanged.* Speed reduced by 10 feet until the start of your next turn. |
| Red Dust | *Unchanged.* +1d4 thunder damage; Strength save or pushed 5 feet. |
| Amber Dust [new] | One creature within 10 feet of the target, other than the target, gains 1d4 + proficiency bonus temporary hit points. |
| Violet Dust [new] | The target takes a −1d4 penalty to its next attack roll before the start of your next turn. |
| Prismatic Dust [new] | +1d4 necrotic damage, and you regain hit points equal to that damage. Crafting one costs a Hit Die. |
| White Dust [new] | Until the start of your next turn, the target sheds dim light, can't benefit from being invisible, and attacks against it ignore disadvantage from darkness, fog, or smoke. |

**Marksman's Focus (3rd level)**

- [buff] Proficiency with the longbow and hand crossbow (which Fighters already have) → proficiency in **Stealth** or **Perception**
- [buff] +2 damage with bows and crossbows if you moved 10 feet or less → +2 damage with bows and crossbows **always**

**Crystal Sight (7th level)**

- [buff] Double range and ignore cover → double range, ignore cover, and **+1d6 damage** on one ranged hit each turn

**Rain of Shards (15th level)**

- [buff] 4d8 piercing + 2d8 (about 27) → **6d8 piercing + 3d8** (about 40)
- [new] *Nothing* → expend a special arrow to apply its effect to **every creature that fails the save**

### Gunman [buff]

> *Why:* Only two of six crystals were usable. Gunman rounds lean toward breaking defenses (armor, healing, spells), in keeping with the class's anti-armor, anti-magic identity.

**Crystal-Cased Rounds (3rd level)**

- [buff] 2 round types (Red, Violet) → 6 round types, one per soulstone. Crafting is still free.

| Round | Effect on a hit |
|---|---|
| Verdant Snare [new] | Strength save or the target's speed becomes 0 until the start of your next turn. |
| Red Impact | *Unchanged.* +1d6 force damage. |
| Amber Slug [new] | The target's AC is reduced by 2 until the start of your next turn. |
| Violet Hex | *Unchanged.* −1d4 to the target's next saving throw before the start of your next turn. |
| Prismatic Round [new] | +1d6 necrotic damage, and the target can't regain hit points until the start of your next turn. Crafting one costs a Hit Die. |
| White Null [new] | Ends one spell of 2nd level or lower affecting the target. |

### Warbound Mage [buff]

> *Why:* The Warbound Mage was the weakest subclass by a wide margin. It is a close-range battle-mage with no armor, no weapon training, and features that cost more than they gave. These changes move it to the middle of the pack.

**Crimson Attunement (2nd level)**

- [buff] No armor or weapon training → proficiency with **light armor** and **one martial melee weapon** of your choice

**War Drum (2nd level)**

- [new] *Nothing* → **War Drum**

How War Drum works:

- Each hit with an attack roll (weapon or spell) gives you one **Beat**. At 3 Beats, your next attack that hits is a **critical hit**, and you lose all your Beats.
- **The crash:** after that attack, until the end of your next turn, you have disadvantage on attack rolls and on Constitution saves to maintain concentration.
- If that attack would already be a critical hit, such as a natural 20, you keep your Beats and don't suffer the crash.
- Beats last until a short or long rest. Missing doesn't remove them.
- A War Drum critical hit triggers **Battle Surge**.

**Blood for Power (6th level)**

- [buff] Add **half** the hit points lost → add **all** the hit points lost
- [nerf] To every damage roll of your wizard spells this turn → to **one damage roll** of the next wizard spell you damage with this turn

**Warstorm (14th level)**

- [buff] +Intelligence modifier to one damage roll of a spell → after casting a wizard spell with your action, **one melee weapon attack as a bonus action**

### Sanguine Aegis [buff]

> *Why:* A strong 3rd level was followed by a weak 7th and a 10th-level feature that was only a drawback. These changes keep the lifesteal identity and make each tier worth reaching.

**Bloodwell Armor (3rd level)**

- [change] Blood Charges equal to damage dealt ÷ 10 (minimum 1) → **1 Blood Charge** per hit, **2** on a critical hit

**Red Pact (7th level)**

- [buff] +1 damage per charge spent (about +3 at 7th level) → **+1d6 necrotic damage** per charge spent (about +10 at 7th level)

**Hunger of the Armor (10th level)**

- [buff] A drawback only → the same drawback, plus **Scent of Blood:** advantage on melee weapon attacks against creatures **below half their hit point maximum**
