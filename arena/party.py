# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""The Proving Grounds, party edition: every party of different subclasses
against four kinds of encounter, to see what each subclass is worth to a team.

Usage, from the repo root:

    uv run arena/party.py                 # all 330 four-hero parties, 100 fights per party and encounter
    uv run arena/party.py --size 6        # six-hero parties (462 of them) against six-creature encounters
    uv run arena/party.py --repeats       # allow the same subclass more than once in a party
    uv run arena/party.py --n 50          # quicker, noisier
    uv run arena/party.py --recalibrate   # re-tune the encounters first
    uv run arena/party.py --only gunman   # rerun just the parties with one subclass
    uv run arena/party.py --gear --only gunman   # Range with Tessarion's own weapons (heroes/ranged.py)

Writes arena/results/party_results.json and party_report.md (party6_* etc. for
other sizes, party4r_* etc. with repeats, each with its own encounter tuning;
*_gear with --gear, which keeps the plain run's tuning so the two compare
directly).
"""
import argparse
import itertools
import json
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
sys.path.insert(0, str(HERE))

from engine import Fight, seed  # noqa: E402
from foes import ENCOUNTERS, TIERS, encounter, lineup  # noqa: E402
from heroes import BY_KEY, ROSTER  # noqa: E402

LEVELS = (3, 7, 10, 15)
KEYS = [c.key for c in ROSTER]
# What battle() records per hero, summed over its fights: times down, damage
# dealt (with overkill), damage taken, Impact's parts (engine/impact.py), then
# descriptive stats: enemy attacks aimed at it, damage its own reactions and
# resistances kept off it, kills, and the share of the fight's rounds it was
# standing for.
FIELDS = ("dead", "dealt", "taken", "dealt_hp", "protect", "control", "enable", "tank",
          "aimed", "mitigated", "kills", "uptime")
PARTS = ("Damage", "Protection", "Control", "Enable", "Tanking")


@dataclass
class Setup:
    """One kind of party run: its parties and its files."""
    size: int = 4
    repeats: bool = False
    gear: bool = False
    parties: list = field(init=False)

    def __post_init__(self):
        combos = itertools.combinations_with_replacement if self.repeats else itertools.combinations
        self.parties = [list(p) for p in combos(KEYS, self.size)]

    @property
    def stem(self):
        """File prefix: party, party6, party4r..."""
        return f"party{self.size}r" if self.repeats else "party" if self.size == 4 else f"party{self.size}"

    @property
    def calibration(self):
        return OUT / f"{self.stem}_calibration.json"   # gear keeps the plain run's tuning

    @property
    def plain_results(self):
        """The same run without gear: where a first --gear --only starts from."""
        return OUT / f"{self.stem}_results.json"

    @property
    def results(self):
        return OUT / f"{self.stem}{'_gear' if self.gear else ''}_results.json"

    @property
    def report(self):
        return OUT / f"{self.stem}{'_gear' if self.gear else ''}_report.md"


PLAIN = Setup()   # four different subclasses, no gear: what evolve.py builds on


def battle(task):
    """n fights of one party against one encounter."""
    party, level, enc, scale, n, s, gear = task
    seed(s)
    wins = draws = 0
    rounds = []
    members = [[0] * len(FIELDS) for _ in party]   # per hero, in party order, see FIELDS
    for _ in range(n):
        heroes = [BY_KEY[k](level, gear=gear) for k in party]
        winner, r = Fight(heroes, encounter(enc, level, scale, len(party))).run()
        rounds.append(r)
        wins += winner == 0
        draws += winner is None
        for h in heroes:
            h.uptime = min(1, h.turns / r)
        for h, m in zip(heroes, members):
            for i, f in enumerate(FIELDS):
                m[i] += getattr(h, f)
    members = [[round(x, 1) for x in m] for m in members]
    return dict(party=party, wins=wins, draws=draws, n=n, rounds=round(statistics.mean(rounds), 2),
                members=members)


def win_rate(r):
    """Draws count as half a win."""
    return (r["wins"] + r["draws"] / 2) / r["n"]


# ----- running -----------------------------------------------------------------------

def calibrate(pool, setup, sample=48, n=40):
    """Scale each encounter's HP and damage so the average party wins half its fights."""
    rng = random.Random(5)
    picked = rng.sample(setup.parties, sample)
    out = {}
    for level in LEVELS:
        out[str(level)] = {}
        for enc in ENCOUNTERS:
            lo, hi = 0.2, 8.0
            for step in range(10):
                mid = (lo * hi) ** 0.5
                tasks = [(p, level, enc, mid, n, 100 * step + i, setup.gear) for i, p in enumerate(picked)]
                wr = statistics.mean(win_rate(r) for r in pool.map(battle, tasks))
                if wr > 0.5:
                    lo = mid
                else:
                    hi = mid
            out[str(level)][enc] = round((lo * hi) ** 0.5, 3)
        print(f"  calibrated L{level}: {out[str(level)]}", flush=True)
    setup.calibration.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def run_all(pool, setup, scales, n, only=None, previous=None):
    """Simulate every party, or with `only`, just the parties containing that
    subclass, merged into `previous` (for testing a change to one subclass)."""
    results = previous or {"n": n, "size": setup.size, "repeats": setup.repeats,
                           "levels": list(LEVELS), "encounters": list(ENCOUNTERS), "scales": scales,
                           "subclasses": [dict(key=c.key, label=c.label, chassis=c.chassis) for c in ROSTER],
                           "fights": {}}
    parties = setup.parties
    for level in LEVELS:
        for enc in ENCOUNTERS:
            t0 = time.time()
            idx = [i for i, p in enumerate(parties) if only is None or only in p]
            tasks = [(parties[i], level, enc, scales[str(level)][enc], n, 7 + i, setup.gear) for i in idx]
            fresh = pool.map(battle, tasks, chunksize=4)
            rows = results["fights"].get(f"{level}/{enc}") or [None] * len(parties)
            for i, r in zip(idx, fresh):
                rows[i] = r
            results["fights"][f"{level}/{enc}"] = rows
            print(f"  L{level} {enc}: {time.time() - t0:.1f}s", flush=True)
    return results


# ----- analysis ------------------------------------------------------------------------

def team(r):
    """[(subclass, {field: value})] for each hero in a result row."""
    return [(k, dict(zip(FIELDS, m))) for k, m in zip(r["party"], r["members"])]


def impact(m):
    """A hero's Impact parts, in hit points, in the order of PARTS."""
    return [m[f] for f in ("dealt_hp", "protect", "control", "enable", "tank")]


def analyse(results):
    """Per level: each subclass's value to a party, plus party and pair scores."""
    out = {}
    for level in results["levels"]:
        per_enc = {enc: results["fights"][f"{level}/{enc}"] for enc in results["encounters"]}
        party_wr = {}   # tuple(party) -> mean win rate over encounters
        for rows in per_enc.values():
            for r in rows:
                party_wr.setdefault(tuple(r["party"]), []).append(win_rate(r))
        party_wr = {p: statistics.mean(v) for p, v in party_wr.items()}
        overall = statistics.mean(party_wr.values())
        subs = {k: subclass_value(k, per_enc, party_wr) for k in KEYS}
        out[level] = {"subs": subs, "parties": party_wr, "pairs": synergy(subs, party_wr, overall),
                      "overall": overall, "stack": stacking(party_wr)}
    return out


def subclass_value(k, per_enc, party_wr):
    """Win value (parties with k vs without), and k's average share of its party's
    Impact, damage, damage taken, aggro, kills..."""
    with_k = [v for p, v in party_wr.items() if k in p]
    without = [v for p, v in party_wr.items() if k not in p]
    row = {"with": statistics.mean(with_k), "delta": statistics.mean(with_k) - statistics.mean(without),
           "by_enc": {}, "impact_enc": {}}
    down = dealt_share = taken_share = 0.0
    parts = [0.0] * len(PARTS)   # summed shares of the party's Impact, by part
    hp = 0.0                     # summed Impact per fight, in hit points
    adv = dict(aggro=0.0, mitigated=0.0, kills=0.0, overkill=0.0, uptime=0.0)
    count = 0
    for enc, rows in per_enc.items():
        w = [win_rate(r) for r in rows if k in r["party"]]
        wo = [win_rate(r) for r in rows if k not in r["party"]]
        row["by_enc"][enc] = statistics.mean(w) - statistics.mean(wo)
        enc_share = []
        for r in rows:
            if k not in r["party"]:
                continue
            heroes = team(r)
            tot_dealt = sum(m["dealt"] for _, m in heroes) or 1
            tot_taken = sum(m["taken"] for _, m in heroes) or 1
            tot_impact = sum(sum(impact(m)) for _, m in heroes) or 1
            tot_aimed = sum(m["aimed"] for _, m in heroes) or 1
            tot_kills = sum(m["kills"] for _, m in heroes) or 1
            for key, m in heroes:
                if key != k:
                    continue
                down += m["dead"] / r["n"]
                dealt_share += m["dealt"] / tot_dealt
                taken_share += m["taken"] / tot_taken
                for i, x in enumerate(impact(m)):
                    parts[i] += x / tot_impact
                enc_share.append(sum(impact(m)) / tot_impact)
                hp += sum(impact(m)) / r["n"]
                adv["aggro"] += m["aimed"] / tot_aimed
                adv["mitigated"] += m["mitigated"] / ((m["mitigated"] + m["taken"]) or 1)
                adv["kills"] += m["kills"] / tot_kills
                adv["overkill"] += (m["dealt"] - m["dealt_hp"]) / (m["dealt"] or 1)
                adv["uptime"] += m["uptime"] / r["n"]
                count += 1
        row["impact_enc"][enc] = statistics.mean(enc_share)
    row.update(survive=1 - down / count, dealt=dealt_share / count, taken=taken_share / count,
               parts=[x / count for x in parts], impact=sum(parts) / count, impact_hp=hp / count,
               **{a: v / count for a, v in adv.items()})
    return row


def synergy(subs, party_wr, overall):
    """How much better a pair does together than its two halves predict."""
    pairs = {}
    for a, b in itertools.combinations(KEYS, 2):
        both = [v for p, v in party_wr.items() if a in p and b in p]
        pairs[(a, b)] = statistics.mean(both) - (subs[a]["with"] + subs[b]["with"] - overall)
    return pairs


def stacking(party_wr):
    """Average win rate by how many copies of a subclass the party has (1, 2, 3+)."""
    stack = {}
    for k in KEYS:
        by = {}
        for p, v in party_wr.items():
            c = p.count(k)
            if c:
                by.setdefault(min(c, 3), []).append(v)
        stack[k] = {c: statistics.mean(v) for c, v in by.items()}
    return stack


# ----- the report ------------------------------------------------------------------------

def pct(x):
    return f"{100 * x:.0f}%"


def pts(x):
    return f"{100 * x:+.0f}"


def solo_ranks():
    """Gauntlet means from the one-on-one run, if it exists, for comparison."""
    import run as solo   # noqa: E402 - the one-on-one runner's analysis
    if not solo.RESULTS.exists():
        return None
    res = json.loads(solo.RESULTS.read_text(encoding="utf-8"))
    t = solo.tables(res)
    return {k: statistics.mean(t[str(lv)][k]["gauntlet"] for lv in res["levels"]) for k in KEYS}


def write_report(results, setup):
    a = analyse(results)
    levels, encs = results["levels"], results["encounters"]
    label = {s["key"]: s["label"] for s in results["subclasses"]}
    chassis = {s["key"]: s["chassis"] for s in results["subclasses"]}
    even = pct(1 / setup.size)
    mean_over_levels = lambda f: statistics.mean(f(lv) for lv in levels)
    impact_order = sorted(KEYS, key=lambda k: -mean_over_levels(lambda lv: a[lv]["subs"][k]["impact"]))
    L = []
    _intro(L, results, setup, even)
    _value_table(L, a, levels, encs, label, even, impact_order)
    _advanced_stats(L, a, levels, label, even, impact_order)
    for lv in levels:
        _level_table(L, a[lv]["subs"], lv, label)
    _parties(L, a, levels, label, chassis, setup.size)
    _synergy(L, a, levels, label)
    if setup.repeats:
        _stacking(L, a, levels, label)
    _encounters(L, results, levels, encs, setup.size)
    setup.report.write_text("\n".join(L) + "\n", encoding="utf-8")


def _intro(L, results, setup, even):
    levels, encs = results["levels"], results["encounters"]
    n_parties = len(setup.parties)
    L.append(f"# Proving Grounds: party simulation ({setup.size} heroes)\n")
    kind = "subclasses, repeats allowed" if setup.repeats else "different subclasses"
    L.append(f"Every party of {setup.size} {kind} ({n_parties:,} parties) against four encounters "
             f"at levels {', '.join(map(str, levels))}, {results['n']} fights each: "
             f"{n_parties * len(levels) * len(encs) * results['n']:,} fights. "
             "Generated by `uv run arena/party.py`; [README.md](../README.md) has the rules and assumptions.\n")
    L.append("**How to read it**\n")
    L.append("- Each encounter is tuned so the average party wins 50%.")
    L.append("- **Impact** is the main number: the subclass's share of everything its party did in a fight, "
             f"averaged over every party it is in ({even} is an even share). Everything is counted in hit "
             "points, so the parts add up without weights:")
    L.append("  - **Damage**: damage it took off enemies' hit points (overkill doesn't count).")
    L.append("  - **Protection**: damage it kept off its allies: AC auras, Living Wall, Verdant Veil, Runic "
             "Bulwark on others, Intercepting Guard, Mana Cage, save bonuses and rerolls, temporary HP and "
             "healing it gave.")
    L.append("  - **Control**: enemy damage it denied: a held or stunned enemy's lost turn, a restrained one "
             "spending its action to escape, a slowed, rooted or frightened one that can't reach its target, "
             "a silenced caster, and attacks at disadvantage from its debuffs.")
    L.append("  - **Enable**: extra damage its allies dealt because of it: advantage against enemies it "
             "held or restrained, auto-crits on held enemies, lowered AC, worse saves.")
    L.append("  - **Tanking**: damage it kept off the party by drawing attacks: for each attack aimed at it, "
             "what the attacker expected to deal to the hero it would have picked otherwise (by its own "
             "targeting rule) minus what it expected to deal to this one, after armour and resistances. "
             "Drawing a hit you take no better than the ally behind you earns nothing.")
    L.append("  - Rolls are credited by expectation (the change in the chance to hit or save times the damage "
             "at stake), and a lost turn at the enemy's expected damage per round. Apart from Tanking, helping "
             "yourself (your own *shield*, your own advantage) is not credited; it shows under Advanced "
             "stats instead.")
    L.append("- **Win value** is the older measure: the win rate of parties that include the subclass minus "
             "the win rate of parties that don't, in percentage points. It captures everything, but doesn't "
             "say why, and it flattens out where parties win or lose regardless.")
    L.append("- **Survives** is how often that character is still standing at the end. **Taken** is its share of "
             f"the damage the party took ({even} is an even share).")
    L.append("- Every fight starts fresh with full resources, as in the one-on-one run.\n")
    if setup.gear:
        L.append("- Gear: the Crystal Archer and the Gunman carry Tessarion's own weapons from `data/items.yaml` "
                 "(Tier 1 at 3rd level, Tier 2 from 5th) with their misfires and Heavy Draw; see "
                 "heroes/ranged.py. Parties without either are the plain run's.\n")


def _value_table(L, a, levels, encs, label, even, impact_order):
    solo = solo_ranks()
    mean_of = lambda f: {k: statistics.mean(f(a[lv]["subs"][k]) for lv in levels) for k in KEYS}
    mean_impact = mean_of(lambda r: r["impact"])
    mean_parts = {k: [statistics.mean(a[lv]["subs"][k]["parts"][i] for lv in levels) for i in range(len(PARTS))]
                  for k in KEYS}
    mean_delta = mean_of(lambda r: r["delta"])
    L.append("## Value to a party\n")
    L.append(f"Impact share by level ({even} is even), its parts averaged over levels, and the win value "
             "for comparison.\n")
    head = ("| Subclass | " + " | ".join(f"L{lv}" for lv in levels) + " | Impact | "
            + " | ".join(PARTS) + " | Win value | Impact rank | Win rank |")
    if solo:
        head += " Solo rank |"
    L.append(head)
    L.append("|---|" + "---:|" * (len(levels) + 1 + len(PARTS) + 3) + ("---:|" if solo else ""))
    win_order = sorted(KEYS, key=lambda k: -mean_delta[k])
    solo_order = sorted(KEYS, key=lambda k: -solo[k]) if solo else None
    for i, k in enumerate(impact_order, 1):
        row = (f"| {label[k]} | " + " | ".join(pct(a[lv]["subs"][k]["impact"]) for lv in levels)
               + f" | **{pct(mean_impact[k])}** | " + " | ".join(pct(x) for x in mean_parts[k])
               + f" | {pts(mean_delta[k])} | {i} | {win_order.index(k) + 1} |")
        if solo:
            row += f" {solo_order.index(k) + 1} |"
        L.append(row)
    L.append("\nThe parts add up to Impact. Win rank orders the subclasses by win value"
             + (", and solo rank by the one-on-one gauntlet (report.md) across both chassis" if solo else "")
             + ". A subclass ranked far higher by Impact than by win value does a lot that its party "
             "didn't need to win, or that came too late to change the result; the reverse means its "
             "contribution is worth more than its hit points suggest (or isn't credited here: see README.md).\n")
    L.append("Impact share by encounter, averaged over levels:\n")
    L.append("| Subclass | " + " | ".join(e.title() for e in encs) + " |")
    L.append("|---|" + "---:|" * len(encs))
    for k in impact_order:
        L.append(f"| {label[k]} | " + " | ".join(
            pct(statistics.mean(a[lv]["subs"][k]["impact_enc"][e] for lv in levels)) for e in encs) + " |")
    L.append("")


def _advanced_stats(L, a, levels, label, even, impact_order):
    L.append("## Advanced stats\n")
    L.append("Not part of Impact; averaged over levels.\n")
    L.append(f"- **Aggro**: its share of the enemy attack rolls aimed at the party ({even} is even).")
    L.append("- **Mitigated**: the share of the damage coming at it that its own *shield* and other "
             "reactions, resistances and Runic Bulwark took off.")
    L.append("- **Taken**: its share of the damage the party took. **Uptime**: the share of the fight's "
             "rounds it was standing for. **Survives**: how often it is standing at the end.")
    L.append("- **Kills**: its share of the party's kills. **Overkill**: the share of its damage that went "
             "past 0 HP and was wasted.\n")
    L.append("| Subclass | Aggro | Mitigated | Taken | Uptime | Survives | Kills | Overkill |")
    L.append("|---|" + "---:|" * 7)
    for k in impact_order:
        m = lambda f: pct(statistics.mean(a[lv]["subs"][k][f] for lv in levels))
        L.append(f"| {label[k]} | {m('aggro')} | {m('mitigated')} | {m('taken')} | {m('uptime')} | "
                 f"{m('survive')} | {m('kills')} | {m('overkill')} |")
    L.append("")


def _level_table(L, s, lv, label):
    L.append(f"## Level {lv}\n")
    L.append("| # | Subclass | Impact | HP/fight | " + " | ".join(PARTS)
             + " | Win with | Win value | Survives | Taken |")
    L.append("|---:|---|---:|---:|" + "---:|" * len(PARTS) + "---:|---:|---:|---:|")
    for i, k in enumerate(sorted(KEYS, key=lambda k: -s[k]["impact"]), 1):
        r = s[k]
        L.append(f"| {i} | {label[k]} | **{pct(r['impact'])}** | {r['impact_hp']:.0f} | "
                 + " | ".join(pct(x) for x in r["parts"])
                 + f" | {pct(r['with'])} | {pts(r['delta'])} | {pct(r['survive'])} | {pct(r['taken'])} |")
    L.append("\nHP/fight is its Impact in hit points per fight.\n")


def _parties(L, a, levels, label, chassis, size):
    mean_party = {p: statistics.mean(a[lv]["parties"][p] for lv in levels) for p in a[levels[0]]["parties"]}
    name = lambda p: ", ".join(label[k] for k in p)
    wiz = lambda p: sum(chassis[k] == "Wizard" for k in p)
    L.append("## Best and worst parties\n")
    L.append("Average win rate across all levels and encounters (50% is par).\n")
    L.append("| | Party | Mages | " + " | ".join(f"L{lv}" for lv in levels) + " | Mean |")
    L.append("|---|---|---:|" + "---:|" * (len(levels) + 1))
    ranked = sorted(mean_party, key=lambda p: -mean_party[p])
    for tag, group in (("Best", ranked[:10]), ("Worst", ranked[-10:])):
        for p in group:
            L.append(f"| {tag} | {name(p)} | {wiz(p)} | " + " | ".join(pct(a[lv]['parties'][p]) for lv in levels)
                     + f" | **{pct(mean_party[p])}** |")
    L.append("")
    L.append("By number of mages in the party:\n")
    L.append("| Mages | Parties | " + " | ".join(f"L{lv}" for lv in levels) + " |")
    L.append("|---:|---:|" + "---:|" * len(levels))
    for m in range(size + 1):
        group = [p for p in mean_party if wiz(p) == m]
        if group:
            L.append(f"| {m} | {len(group)} | "
                     + " | ".join(pct(statistics.mean(a[lv]['parties'][p] for p in group)) for lv in levels) + " |")
    L.append("")


def _synergy(L, a, levels, label):
    mean_pair = {pair: statistics.mean(a[lv]["pairs"][pair] for lv in levels) for pair in a[levels[0]]["pairs"]}
    ranked = sorted(mean_pair, key=lambda pr: -mean_pair[pr])
    L.append("## Synergy\n")
    L.append("How much better (or worse) parties containing both do than the two subclasses' separate "
             "values predict, averaged over levels. Only the largest are shown; anything within about "
             "±2 points is noise.\n")
    L.append("| Pair | Synergy |")
    L.append("|---|---:|")
    for pr in ranked[:8]:
        L.append(f"| {label[pr[0]]} + {label[pr[1]]} | {pts(mean_pair[pr])} |")
    L.append("| … | |")
    for pr in ranked[-8:]:
        L.append(f"| {label[pr[0]]} + {label[pr[1]]} | {pts(mean_pair[pr])} |")
    L.append("")


def _stacking(L, a, levels, label):
    L.append("## Stacking\n")
    L.append("Average party win rate by how many copies of the subclass it brings, averaged over levels. "
             "**2nd copy** is the change from one copy to two: positive means doubling up pays, negative "
             "means a second one adds less than a different subclass would.\n")
    L.append("| Subclass | 1 copy | 2 copies | 3+ copies | 2nd copy |")
    L.append("|---|---:|---:|---:|---:|")

    def mean_c(k, c):
        vals = [a[lv]["stack"][k][c] for lv in levels if c in a[lv]["stack"][k]]
        return statistics.mean(vals) if vals else None
    cell = lambda v: "—" if v is None else pct(v)
    gain = lambda k: (mean_c(k, 2) - mean_c(k, 1)) if mean_c(k, 2) is not None else 0
    for k in sorted(KEYS, key=lambda k: -gain(k)):
        L.append(f"| {label[k]} | {cell(mean_c(k, 1))} | {cell(mean_c(k, 2))} | {cell(mean_c(k, 3))} | "
                 f"**{pts(gain(k))}** |")
    L.append("")


def _encounters(L, results, levels, encs, size):
    L.append("## Encounters\n")
    L.append("One creature per hero (the boss alone), built like the gauntlet's benchmark foes, with HP and "
             "damage multiplied by the calibrated scale.\n")
    L.append("| Encounter | Creatures | " + " | ".join(f"L{lv} scale" for lv in levels) + " |")
    L.append("|---|---|" + "---:|" * len(levels))
    for e in encs:
        L.append(f"| {e.title()} | {', '.join(lineup(e, size))} | "
                 + " | ".join(f"×{results['scales'][str(lv)][e]}" for lv in levels) + " |")
    L.append("\n- **Skirmishers** ignore the front rank and go for the lowest-AC hero. **Snipers** shoot the "
             "lowest-AC hero in range. **Casters** blast a 10-foot radius wherever the most heroes stand. The "
             "**Boss** has three attacks, 10-foot reach and two Legendary Resistances (it shrugs off a save "
             "against Hold or a big spell).")
    L.append("- Base numbers per level: " + "; ".join(
        f"L{lv} CR {TIERS[lv]['cr']} (AC {TIERS[lv]['ac']}, +{TIERS[lv]['atk']}, DC {TIERS[lv]['dc']})"
        for lv in levels) + ".")


# ----- main --------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=100, help="fights per party and encounter (default 100)")
    ap.add_argument("--recalibrate", action="store_true", help="re-tune the encounters first")
    ap.add_argument("--only", choices=KEYS, metavar="SUBCLASS",
                    help="rerun only the parties containing this subclass (e.g. sanguine_mage) and "
                         "merge them into the saved results; uses the saved encounter tuning")
    ap.add_argument("--report-only", action="store_true", help="rebuild the report from the saved results")
    ap.add_argument("--size", type=int, default=4, help="heroes per party (default 4); enemies scale to match")
    ap.add_argument("--repeats", action="store_true", help="allow the same subclass more than once in a party")
    ap.add_argument("--gear", action="store_true",
                    help="Range carries Tessarion's own weapons (heroes/ranged.py); writes *_gear files, "
                         "starting --only from the plain run's results and tuning")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    setup = Setup(args.size, args.repeats, args.gear)
    if args.report_only:
        write_report(json.loads(setup.results.read_text(encoding="utf-8")), setup)
        print(f"wrote {setup.report.relative_to(HERE.parent)}")
        return
    with Pool(args.workers) as pool:
        if args.only:
            saved = setup.results if setup.results.exists() else setup.plain_results
            previous = json.loads(saved.read_text(encoding="utf-8"))
            scales, n = previous["scales"], previous["n"]
            print(f"rerunning the parties with {args.only}, {n} fights each...", flush=True)
            results = run_all(pool, setup, scales, n, only=args.only, previous=previous)
        else:
            if args.recalibrate or not setup.calibration.exists():
                print("calibrating encounters...", flush=True)
                scales = calibrate(pool, setup)
            else:
                scales = json.loads(setup.calibration.read_text(encoding="utf-8"))
            print(f"running {len(setup.parties)} parties x {len(LEVELS)} levels x {len(ENCOUNTERS)} encounters, "
                  f"{args.n} fights each...", flush=True)
            results = run_all(pool, setup, scales, args.n)
    setup.results.write_text(json.dumps(results) + "\n", encoding="utf-8")
    write_report(results, setup)
    print(f"wrote {setup.results.relative_to(HERE.parent)} and {setup.report.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
