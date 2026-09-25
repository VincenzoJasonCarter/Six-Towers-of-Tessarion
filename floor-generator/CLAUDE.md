# Thal'Vireth — Temporal Tower Context

## Core Identity

Thal'Vireth is the **Elf nation/tower associated with time manipulation**.

Its primary temporal authority is controlled through the **Verdant Tower** and its High Priestess.

The core concept is not simply "time stop". The domain controls the **rate at which time passes**, with extreme temporal states emerging when the High Priestess becomes corrupted.

---

## Temporal Authority

### Normal State

The High Priestess can manipulate the rate of time within specific areas.

There are two primary temporal zones:

* **Acceleration (ACC)** — time passes faster.
* **Deceleration (DEC)** — time passes slower.

These zones can exist naturally throughout Thal'Vireth.

### Normal Battle Effect

Temporal zones primarily affect **initiative**, rather than movement speed.

* **ACC:** initiative is doubled.
* **DEC:** initiative is halved.
* Effects apply to both players and enemies.
* Movement speed remains unchanged.

This keeps movement rules predictable and avoids complications when a creature crosses a temporal zone during movement.

A creature should ideally be affected based on the tile/zone where it **ends its movement or begins its turn**, rather than continuously changing movement speed while crossing zones.

---

# Temporal Progression

The mechanics should escalate as the party approaches the High Priestess.

## Open World

Certain districts of Thal'Vireth have persistent temporal zones.

These are relatively stable and understandable.

Example:

```text
District A
→ ACC zone

District B
→ DEC zone
```

The player learns that different areas of Thal'Vireth experience different rates of time.

---

## Tower — Lower Floors

The same **ACC / DEC** system is used inside the tower.

The party has not confronted the corrupted High Priestess yet, so temporal manipulation remains within its normal range.

Lower floors should primarily teach:

> Positioning around different rates of time.

The player should gradually become familiar with ACC and DEC before encountering their corrupted forms.

---

# Corrupted Temporal Authority

After confronting the High Priestess / progressing toward the corrupted Verdant Tower, temporal manipulation becomes unstable.

The normal temporal states are pushed toward their extreme cases:

| Normal State | Extreme / Corrupted State |
| ------------ | ------------------------- |
| Acceleration | **Time Skip**             |
| Deceleration | **Time Stop**             |

The important design principle is:

> Time Skip and Time Stop are not unrelated abilities. They are the corrupted extremes of the same temporal authority.

Conceptually:

```text
Deceleration ───────────── Normal ───────────── Acceleration
     ↓                                             ↓
  TIME STOP                                    TIME SKIP
```

---

# Corrupted Battlefield

The corrupted tower can use **temporal anomaly zones**.

The battlefield behaves somewhat like **Minesweeper**.

Each zone has a hidden state:

* Neutral
* Time Skip
* Time Stop

The player does not initially know the exact state of every zone.

However, zones should provide **visual cues** that allow players to infer their possible state.

The goal is not pure randomness.

Core gameplay loop:

> Observe → Infer → Move → Reveal → Adapt

---

# Time Stop vs Time Skip

These should have mechanically distinct identities.

## Time Stop

The creature's timeline is temporarily halted.

Possible implementation:

* Creature enters a Time Stop zone.
* Its movement ends immediately.
* It remains in its current position.
* It cannot move again until the relevant temporal effect expires / next turn.

Gameplay identity:

> **Stop punishes positioning.**

The creature becomes predictable because its position is forcibly preserved.

---

## Time Skip

Time does not stop. Instead, a portion of the creature's timeline is skipped.

Time Skip should therefore ideally have a different consequence from Time Stop.

Possible implementation:

* Creature enters a Time Skip zone.
* Its movement ends or its current action is interrupted.
* A portion of its timeline is skipped.
* The creature may be displaced to the position corresponding to the resumed timeline.

Gameplay identity:

> **Skip disrupts positioning and continuity.**

The exact displacement rules are still undecided.

---

# Floor Scale

A standard Thal'Vireth tower floor is approximately:

**20 × 20 meters**

This provides a sufficiently large tactical arena while keeping temporal zones meaningful.

Suggested temporal-zone scales:

* **2 × 2 m** — small anomaly
* **3 × 3 m** — standard temporal zone
* **4 × 4 m+** — major temporal field

For the current prototype, use:

```text
Floor: 20 × 20 m
Temporal zone: 3 × 3 m
```

Temporal zones should generally be treated as **areas**, not single trap tiles.

---

# Design Principles

1. **Temporal manipulation should remain the core identity.**
2. ACC/DEC should feel like normal, controlled time manipulation.
3. Skip/Stop should feel like corrupted extremes of ACC/DEC.
4. Player and enemies are both affected by temporal zones unless explicitly stated otherwise.
5. Avoid dynamic movement-speed modification because crossing a zone creates too many edge cases.
6. Prefer effects that depend on where a creature ends its movement / starts its turn.
7. Temporal zones should reward tactical positioning rather than simply provide buffs.
8. Corrupted temporal zones should provide visual information so the mechanic is not purely RNG.
9. The mechanic should progressively escalate as the party approaches the High Priestess.
10. Different temporal states should have distinct gameplay identities.

---

# Procedural Floor Generator

A Python generator is being developed to prototype Thal'Vireth battlefields.

Current prototype parameters:

```python
generate_temporal_floor(
    size=20,
    zone_size_range=(2, 4),
    n_zones=5,
    min_zone_gap=1,
    zone_types=None,       # defaults to ACC / DEC / NEUTRAL
    zone_weights=None,
    seed=42,
    show=True,
    pixels_per_meter=32,
    export_vtt=None,       # path to write a Foundry VTT scene JSON
    export_texture=None,   # path to save the floor texture as PNG
    grid_pixels=100,
)
```

Current generator capabilities:

* 20 × 20 m floor generation
* Variable zone width/height (rolled independently per zone, not a single fixed size)
* Configurable number of zones
* ACC / DEC / NEUTRAL zone generation, with configurable per-type weights
* ACC / DEC apply a fixed initiative multiplier (×2 / ×0.5), matching the design doc; NEUTRAL has no effect
* Custom zone type registries (color, multiplier, texture noise scale) can be passed in, so new types don't require touching generator logic
* Minimum spacing between zones
* Reproducible layouts using seeds
* Procedural per-pixel floor texture (stone-noise base, each zone blended with its own noise pattern and type color) rendered via matplotlib and optionally exported as PNG
* Foundry VTT scene export (zone drawings + optional texture background), importable via Scenes > Import Data
* Matplotlib visualization

Current prototype does **not yet** include:

* Player / enemy spawn generation (removed — out of scope for this generator)
* Walls
* Obstacles
* Entrance / exit
* Guaranteed pathfinding
* Tactical encounter validation
* Corrupted Skip / Stop zones (the current NEUTRAL type is a plain always-neutral zone, not yet the hidden-state Minesweeper mechanic described above)
* Visual anomaly cues
* Difficulty scaling
* Floor-specific generation rules

---

# Planned Generator Progression

The generator should eventually support:

```python
generate_floor(
    size=20,
    floor_type="lower_tower",
    difficulty=3,
    seed=1337
)
```

Potential floor types:

```text
open_world
lower_tower
upper_tower
corrupted
```

Potential validation rules:

* Player spawn cannot overlap hazards.
* Enemy spawn cannot overlap hazards.
* Entrance and exit must be reachable.
* Temporal zones cannot create an inaccessible area.
* There must be sufficient safe space.
* Temporal zones should serve tactical purposes rather than being completely random.
* Corrupted floors should have readable visual cues.
* Different seeds should produce different layouts while preserving playability.

---

# Current Open Design Questions

The following are intentionally unresolved:

1. Exact mechanical distinction between **Time Skip** and **Time Stop**.
2. Whether Time Skip causes forced displacement, lost actions, or another temporal effect.
3. Exact timing for applying ACC/DEC initiative modification.
4. Whether temporal effects persist until the next turn, round, or while occupying a zone.
5. Exact visual language for ACC, DEC, Skip, Stop, and Neutral zones.
6. How many temporal zones should appear on a 20 × 20 m floor.
7. How temporal zones interact with terrain, obstacles, and line of sight.
8. How corrupted floors transition from readable ACC/DEC mechanics into Minesweeper-like anomaly mechanics.

The design should preserve the underlying principle:

> **Thal'Vireth is about controlling the rate and continuity of time, with corruption progressively breaking that control.**
