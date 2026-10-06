# Balance Patch Notes

Changes to the class and subclass rules in the lore-book, newest patch first. The full text of every feature is in the Library, on the *Rites of Ascension* shelf, in *Subclasses Skill*.

[buff] stronger · [nerf] weaker · [new] new feature or option · [change] reworked, about the same power

---

## Patch 2 — 2026-10-07

### Subclass Evolution [new]

> *Why:* After six Crystallizations a practitioner's body starts to form soulstone, and it has to settle one of two ways: contain the mana or pass it on (the lore is in *On Threshold Assimilation*, on the *Rites of Ascension* shelf). Every subclass now chooses a branch at 6th level. **Ascendant** gives support with no cost. **Corrupted** gives damage paid for with Assimilation. Both branches were tested in the Proving Grounds (`arena/evolution_report.md`): within each pillar, every subclass's Ascendant lands within 2 points of the others in party win rate, and so does every Corrupted.

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
