"""Opponents: benchmark archetypes built from the DMG's monster-by-CR math for
each tested level, the encounter groups the party simulator throws them in,
and a handful of real stat blocks from data/enemies.yaml for level 3 (the
campaign's current tier).
"""
import re
from pathlib import Path

import yaml

from engine import (R, TACTICS, Creature, attack, avg, cage_over, causes, credit, d, d20, deal, deny, move,
                    p_hit, roll_damage, saving_throw)

ENEMIES = Path(__file__).resolve().parent.parent / "data" / "enemies.yaml"

# One foe that is a hard fight for one character of this level:
# AC, attack bonus and save DC from the CR table, HP and damage per round
# before the calibrated scale is applied.
TIERS = {
    3: dict(cr="1", ac=13, atk=4, dc=12, pb=2, mod=3, hp=45, dmg=10),
    7: dict(cr="3", ac=14, atk=5, dc=13, pb=2, mod=4, hp=90, dmg=20),
    10: dict(cr="5", ac=15, atk=6, dc=14, pb=3, mod=4, hp=130, dmg=30),
    15: dict(cr="8", ac=16, atk=7, dc=15, pb=3, mod=5, hp=180, dmg=45),
}
ARCHETYPES = ("brute", "soldier", "sniper", "caster")

# Party encounters: one creature per hero (the boss stands alone). Each one
# stresses something different: a melee rush, pressure on the back rank, a bit
# of everything, and a single big target.
ENCOUNTERS = {
    "warband": ("brute", "soldier", "soldier", "skirmisher"),
    "ambush": ("skirmisher", "skirmisher", "sniper", "caster"),
    "mixed": ("brute", "soldier", "sniper", "caster"),
    "boss": ("boss",),
}


def dice_for(avg_dmg, dtype):
    """Damage parts (d8s plus a flat bonus) averaging about avg_dmg."""
    avg_dmg = max(1.0, avg_dmg)
    n = max(1, round(avg_dmg * 0.6 / 4.5))
    return [(n, 8, round(avg_dmg - 4.5 * n), dtype)]


class Monster(Creature):
    def __init__(self, name, *, ac, hp, attacks, saves, multi=1, speed=30, style="melee",
                 ctype="humanoid", pb=2, spell=None, net=None, silence=None, reach=5,
                 cast_mod=0, frenzy=False, targeting="nearest", legendary=0):
        scores = dict(str=10, dex=10 + 2 * saves.get("dex", 0), con=10, int=10, wis=10, cha=10)
        super().__init__(name, 0, scores, (), pb, hp, ac, speed=speed, reach=reach)
        self.attacks, self.saves, self.multi = attacks, saves, multi
        self.style, self.creature_type = style, ctype
        self.caster = spell is not None
        self.spell, self.net, self.silence = spell, net, silence
        self.cast_mod, self.frenzy, self.targeting = cast_mod, frenzy, targeting
        self.legendary = legendary
        self.recharged = {"net": True, "silence": True}
        ranged = [a for a in attacks if a["kind"] == "ranged"]
        self.max_range = 60 if self.caster else (min(a["normal"] for a in ranged) if ranged else 5)
        self.can_oa = any(a["kind"] == "melee" for a in attacks)

    def save_bonus(self, abil):
        return self.saves.get(abil, 0)

    def save_reroll(self, abil, dc, src, ctx):
        # Legendary Resistance: shrug off a save that would end the fight.
        if self.legendary and (ctx.get("control") or ctx.get("big")):
            self.legendary -= 1
            return True
        return False

    def est_dpr(self, target):
        if self.spell:
            return 0.6 * sum(n * (die + 1) / 2 + f for n, die, f, _ in self.spell["parts"])
        return sum(self.multi * p_hit(a["bonus"], target.ac()) *
                   sum(n * (die + 1) / 2 + f for n, die, f, _ in a["parts"]) for a in self.attacks[:1])

    def pick_target(self):
        foes = self.enemies()
        if not foes:
            return None
        if self.targeting == "weakest":            # dives for the softest target
            return self.softest(foes)
        if self.targeting == "sniper":             # shoots the softest target it can reach
            rng = max(a["long"] for a in self.attacks)
            near = [e for e in foes if self.dist_to(e) <= rng] or foes
            return self.softest(near)
        if self.targeting == "cluster":            # blasts where the most heroes stand
            return max(foes, key=lambda e: (sum(1 for o in foes if o.dist_to(e) <= 10), -e.hp))
        return self.nearest(foes)

    def softest(self, foes):
        """The lowest-AC hero. With sight_targeting it can see armour but not hit
        points: it keeps last turn's pick if that is still among the softest,
        otherwise picks one of them at random."""
        if "sight_targeting" not in TACTICS:
            return min(foes, key=lambda e: (e.ac(), e.hp))
        low = min(e.ac() for e in foes)
        soft = [e for e in foes if e.ac() == low]
        return self.foe if self.foe in soft else R.choice(soft)

    def attack_mods(self, tgt, ctx):
        return bool(self.frenzy and tgt.caster), False   # Slag Ghoul's Mana-Frenzy

    def strike(self, a, ctx=None):
        dis = a["kind"] == "ranged" and self.dist() > a["normal"]
        attack(self, self.foe, bonus=a["bonus"], parts=a["parts"], kind=a["kind"],
               weapon=a["name"], dis=dis, ctx=ctx)

    def opportunity_attack(self, tgt):
        melee = [a for a in self.attacks if a["kind"] == "melee"]
        if melee:
            foe, self.foe = self.foe, tgt
            self.strike(melee[0], {"oa": True})
            self.foe = foe

    def usable(self):
        dist = self.dist()
        return [a for a in self.attacks
                if (a["kind"] == "melee" and dist <= a.get("reach", 5))
                or (a["kind"] == "ranged" and dist <= a["long"])]

    def take_turn(self):
        for k in self.recharged:
            if not self.recharged[k] and d(1, 6) >= 5:
                self.recharged[k] = True
        action = True
        e = self.get("restrained")
        if e and e.value and e.value[0] == "escape" and self.style == "melee":
            action = False
            deny(self, causes(self, ("restrained",)))
            if d20() + self.saves.get("str", 0) >= e.value[1]:
                self.remove(effect=e)
                src = e.source
                if src.conc and any(x is e for _, x in src.conc.held):
                    src.conc.held = [(h, x) for h, x in src.conc.held if x is not e]
                    if not src.conc.held:
                        src.conc = None
        if self.style == "melee":
            sp = self.speed_now()
            gap, hindered, free = self.dist() - self.reach, self.hindrance(), action
            if self.dist() > self.reach and sp:
                move(self, True, sp)
                if self.dist() > self.reach and action and self.speed_now():
                    action = False
                    move(self, True, sp)
            if free and not self.dead and self.dist() > self.reach and 0 < gap <= self.base_speed:
                deny(self, hindered)   # unhindered, it would have closed and attacked
        else:
            self.keep_distance()
        if not action or self.foe.dead:
            return
        if self.net and self.recharged["net"] and self.dist() <= self.net["range"] and not self.foe.has("restrained"):
            self.recharged["net"] = False
            if not saving_throw(self.foe, "dex", self.net["dc"], self, {"control": True}):
                self.foe.add("restrained", self, value=("escape", self.net["dc"]))
            return
        if self.silence and self.recharged["silence"] and self.dist() <= 5 and self.foe.caster:
            self.recharged["silence"] = False
            if not saving_throw(self.foe, "con", self.silence, self, {"control": True}):
                self.foe.add("silenced", self, until=("end", self.foe))
            return
        if self.spell and self.has("silenced") and self.dist() <= self.spell["range"]:
            deny(self, causes(self, ("silenced",)))   # Powder Disruption: the staff instead
        if self.spell and not self.has("silenced") and self.dist() <= self.spell["range"]:
            self.cast()
        else:
            for _ in range(self.multi):
                if self.foe.dead:
                    self.foe = self.pick_target()
                    if self.foe is None:
                        break
                options = self.usable()
                if not options:
                    break
                self.strike(options[0])
        if self.style != "melee" and self.enemies() and not self.dead:
            if self.foe.dead:
                self.foe = self.pick_target()
            self.keep_distance()

    def hindrance(self):
        """The heroes slowing me down on the way to my target: speed effects, fear,
        and difficult-terrain zones between us."""
        out = causes(self, ("speed0", "slow", "frightened"))
        lo, hi = sorted((self.x, self.foe.x))
        for z in self.fight.zones:
            if (z.owner.side != self.side and z.name in ("anchor", "lockstep", "nexus") and not z.owner.dead
                    and z.center() - z.radius <= hi and z.center() + z.radius >= lo and z.owner not in out):
                out.append(z.owner)
        return out

    def cast(self):
        """A blast centred on the target that catches its neighbours (10-foot radius)."""
        s, foe = self.spell, self.foe
        self.acted = True
        hit = [e for e in self.enemies() if e.dist_to(foe) <= s.get("radius", 0)] or [foe]
        w, cage = cage_over(foe)
        if cage and abs(self.x - w.x) > 15 and d20() + self.cast_mod < cage.value:
            credit(w, "protect", 0.75 * avg(s["parts"]) * len([t for t in hit if t is not w]))
            return
        dmg = roll_damage(s["parts"])
        stake = sum(dmg.values()) - sum(v // 2 for v in dmg.values())
        for t in hit:
            ctx = {"spell": True, "level": s["level"], "name": s["name"], "damage": True,
                   "single": len(hit) == 1, "stake": stake}
            ok = saving_throw(t, s["abil"], s["dc"], self, ctx)
            deal(t, {k: v // 2 for k, v in dmg.items()} if ok else dict(dmg), self, ctx)


def archetype(name, level, scale):
    t = TIERS[level]
    m, pb = t["mod"], t["pb"]
    hp = lambda k: max(1, round(t["hp"] * k * scale))
    dmg = t["dmg"] * scale
    if name == "brute":
        return Monster(f"Brute (CR {t['cr']})", ac=t["ac"] - 1, hp=hp(1.3), speed=40, ctype="beast", pb=pb,
                       attacks=[dict(name="maul", bonus=t["atk"] + 1, parts=dice_for(dmg, "bludgeoning"),
                                     kind="melee", normal=5, long=5)],
                       saves=dict(str=m + pb, dex=0, con=m + pb, int=-3, wis=0, cha=-2))
    if name == "soldier":
        return Monster(f"Soldier (CR {t['cr']})", ac=t["ac"] + 2, hp=hp(1.0), multi=2, pb=pb,
                       attacks=[dict(name="blade", bonus=t["atk"], parts=dice_for(dmg / 2, "slashing"),
                                     kind="melee", normal=5, long=5)],
                       saves=dict(str=m + pb, dex=1, con=2 + pb, int=0, wis=1, cha=0))
    if name == "skirmisher":
        return Monster(f"Skirmisher (CR {t['cr']})", ac=t["ac"] + 1, hp=hp(0.8), multi=2, speed=40, pb=pb,
                       targeting="weakest",
                       attacks=[dict(name="knives", bonus=t["atk"] + 1, parts=dice_for(dmg / 2, "piercing"),
                                     kind="melee", normal=5, long=5)],
                       saves=dict(str=1, dex=m + pb, con=1, int=0, wis=1 + pb, cha=0))
    if name == "sniper":
        return Monster(f"Sniper (CR {t['cr']})", ac=t["ac"], hp=hp(0.8), multi=2, style="ranged", pb=pb,
                       targeting="sniper",
                       attacks=[dict(name="bow", bonus=t["atk"], parts=dice_for(dmg * 0.45, "piercing"),
                                     kind="ranged", normal=150, long=600)],
                       saves=dict(str=0, dex=m + pb, con=1, int=0, wis=1 + pb, cha=0))
    if name == "caster":
        return Monster(f"Caster (CR {t['cr']})", ac=t["ac"] - 2, hp=hp(0.7), style="caster", pb=pb,
                       cast_mod=m, targeting="cluster",
                       attacks=[dict(name="staff", bonus=t["atk"] - 2, parts=[(1, 6, 0, "bludgeoning")],
                                     kind="melee", normal=5, long=5)],
                       spell=dict(name="searing burst", abil="dex", dc=t["dc"], level=3, range=120, radius=10,
                                  parts=dice_for(dmg * 1.1, "fire")),
                       saves=dict(str=-1, dex=1, con=1, int=m + pb, wis=1 + pb, cha=0))
    if name == "boss":
        return Monster(f"Boss (CR {t['cr']}+)", ac=t["ac"] + 1, hp=hp(4.5), multi=3, speed=40, pb=pb + 1,
                       ctype="monstrosity", reach=10, legendary=2,
                       attacks=[dict(name="claws", bonus=t["atk"] + 2, parts=dice_for(dmg * 0.9, "slashing"),
                                     kind="melee", normal=10, long=10, reach=10)],
                       saves=dict(str=m + pb + 1, dex=1, con=m + pb + 1, int=0, wis=2 + pb, cha=1))
    raise ValueError(name)


# Line-ups for bigger parties; edit freely. A party size without an entry here
# repeats the four-creature line-up above until there is one creature per hero.
ENCOUNTERS_BY_SIZE = {
    6: {
        "warband": ("brute", "brute", "soldier", "soldier", "soldier", "skirmisher"),
        "ambush": ("skirmisher", "skirmisher", "skirmisher", "sniper", "sniper", "caster"),
        "mixed": ("brute", "soldier", "soldier", "skirmisher", "sniper", "caster"),
        "boss": ("boss",),
    },
}


def lineup(name, size=4):
    """The creatures in an encounter for a party of `size` (the boss always stands alone)."""
    if size in ENCOUNTERS_BY_SIZE:
        return ENCOUNTERS_BY_SIZE[size][name]
    base = ENCOUNTERS[name]
    if name == "boss":
        return base
    return tuple(base[i % len(base)] for i in range(size))


def encounter(name, level, scale, size=4):
    return [archetype(a, level, scale) for a in lineup(name, size)]


# ----- the campaign's own stat blocks (level 3) -----------------------------

# What the YAML doesn't say: creature type, multiattack and the specials the
# simulator models. Saves are guesses from the descriptions (+1 by default).
BESTIARY = {
    "scavenger_leader": dict(ctype="humanoid", multi=2, saves=dict(str=3, con=3, dex=1, wis=0)),
    "guard_leader": dict(ctype="humanoid", saves=dict(str=2, con=2, dex=1, wis=1)),
    "iron_hound": dict(ctype="construct", saves=dict(str=2, dex=2, con=2),
                       net=dict(dc=12, range=30)),
    "smuggler_king_hydraform": dict(ctype="monstrosity", multi=2, saves=dict(str=3, con=3, dex=1)),
    "alpha_mite": dict(ctype="aberration", style="ranged", saves=dict(dex=2, con=2)),
    "resonance_construct": dict(ctype="construct", saves=dict(str=3, con=2, dex=-1)),
    "slag_ghoul": dict(ctype="undead", frenzy=True, saves=dict(str=2, con=2, dex=1)),
    "mana_mite_swarm": dict(ctype="swarm", silence=11, saves=dict(dex=1, con=1)),
}
DICE = re.compile(r"^(\d+)d(\d+)\s*([+-]\s*\d+)?$")


def load_bestiary():
    data = yaml.safe_load(ENEMIES.read_text(encoding="utf-8"))
    out = {}
    for e in data["enemies"]:
        extra = BESTIARY.get(e["id"])
        if not extra:
            continue
        v = e["versions"][0]
        acts = []
        for a in v.get("actions") or []:
            m = DICE.match(str(a.get("damage", "")).strip())
            if not m or "to_hit" not in a:
                continue
            n, die, flat = int(m[1]), int(m[2]), int((m[3] or "0").replace(" ", ""))
            kind = "ranged" if "ranged" in a.get("kind", "") else "melee"
            rng = a.get("range_ft", 5)
            normal, long = (map(int, str(rng).split("/")) if "/" in str(rng) else (int(rng), int(rng)))
            acts.append(dict(name=a["name"], bonus=a["to_hit"], parts=[(n, die, flat, a.get("damage_type", "bludgeoning"))],
                             kind=kind, normal=normal, long=long, reach=a.get("reach_ft", 5) or 5))
        if acts:
            out[e["id"]] = dict(name=e["name"], ac=v["ac"], hp=v["hp"], attacks=acts, **extra)
    return out


def bestiary_foe(spec):
    s = dict(spec)
    name = s.pop("name")
    reach = max(a.get("reach", 5) for a in s["attacks"])
    return Monster(name, reach=reach, **s)
