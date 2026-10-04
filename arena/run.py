# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""The Proving Grounds: Monte Carlo power rankings for the eleven subclasses.

Usage, from the repo root:

    uv run arena/run.py                  # everything, 1000 fights per matchup
    uv run arena/run.py --n 200          # quicker, noisier
    uv run arena/run.py --recalibrate    # re-tune the benchmark foes first

Writes arena/results.json and arena/report.md. See README.md for what is
simulated and what isn't.
"""
import argparse
import json
import os
import statistics
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine import Fight, seed  # noqa: E402
from foes import ARCHETYPES, TIERS, archetype, bestiary_foe, load_bestiary  # noqa: E402
from heroes import BY_KEY, ROSTER, VARIANTS  # noqa: E402

LEVELS = (3, 7, 10, 15)
CALIBRATION = HERE / "calibration.json"
RESULTS = HERE / "results.json"
REPORT = HERE / "report.md"
SPAR_ROUNDS = 3


# ----- building combatants in a worker -------------------------------------

def build(spec):
    kind = spec[0]
    if kind == "hero":
        _, key, level, patched = spec
        return BY_KEY[key](level, patched)
    if kind == "arch":
        _, name, level, scale = spec
        return archetype(name, level, scale)
    if kind == "beast":
        return bestiary_foe(load_bestiary_cached()[spec[1]])
    if kind == "dummy":
        _, level, scale = spec
        m = archetype("soldier", level, scale)
        m.name = "Sparring dummy"
        m.max_hp = m.hp = 10 ** 7
        return m
    raise ValueError(spec)


_BEASTS = None


def load_bestiary_cached():
    global _BEASTS
    if _BEASTS is None:
        _BEASTS = load_bestiary()
    return _BEASTS


def bout(task):
    """Run n fights of spec a vs spec b. Returns a's wins, b's wins, draws and extras."""
    a_spec, b_spec, n, s = task
    seed(s)
    wins = losses = draws = 0
    rounds, hp_left = [], []
    for _ in range(n):
        a, b = build(a_spec), build(b_spec)
        winner, r = Fight(a, b).run()
        rounds.append(r)
        if winner == 0:
            wins += 1
            hp_left.append(a.hp / a.max_hp)
        elif winner == 1:
            losses += 1
        else:
            draws += 1
    return dict(wins=wins, losses=losses, draws=draws, n=n,
                rounds=statistics.mean(rounds), hp_left=statistics.mean(hp_left) if hp_left else 0.0)


def spar(task):
    """Hero vs an unkillable soldier: damage in the first rounds, and rounds survived."""
    hero_spec, dummy_spec, n, s = task
    seed(s)
    dealt, survived = [], []
    for _ in range(n):
        h, dmy = build(hero_spec), build(dummy_spec)
        f = Fight(h, dmy)
        snapshot = {}

        def turn(c, _orig=f.turn):
            _orig(c)
            if c is h and h.turns == SPAR_ROUNDS:
                snapshot["dealt"] = h.dealt
        f.turn = turn
        _, r = f.run()
        dealt.append(snapshot.get("dealt", h.dealt))
        survived.append(r if h.dead else r + 1)
    return dict(dealt=statistics.mean(dealt), survived=statistics.mean(survived), n=n)


# ----- calibration ---------------------------------------------------------

CHASSIS = ("Wizard", "Fighter")


def mean_winrate(pool, level, chassis, arch, scale, n, seed0):
    tasks = [(("hero", c.key, level, True), ("arch", arch, level, scale), n, seed0 + i)
             for i, c in enumerate(ROSTER) if c.chassis == chassis]
    res = pool.map(bout, tasks)
    return statistics.mean((r["wins"] + r["draws"] / 2) / r["n"] for r in res)


def calibrate(pool, n=250):
    """Scale each archetype's HP and damage, separately for each chassis, so the
    average (post-patch) subclass of that chassis wins half its fights."""
    out = {}
    for level in LEVELS:
        out[str(level)] = {}
        for chassis in CHASSIS:
            out[str(level)][chassis] = {}
            for arch in ARCHETYPES:
                lo, hi = 0.15, 8.0
                for step in range(11):
                    mid = (lo * hi) ** 0.5
                    if mean_winrate(pool, level, chassis, arch, mid, n, 1000 * step) > 0.5:
                        lo = mid
                    else:
                        hi = mid
                out[str(level)][chassis][arch] = round((lo * hi) ** 0.5, 3)
            print(f"  calibrated L{level} {chassis}: {out[str(level)][chassis]}", flush=True)
    CALIBRATION.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def dummy_scale(scales, level):
    """The sparring dummy sits between the two chassis' Soldiers."""
    s = scales[str(level)]
    return round((s["Wizard"]["soldier"] * s["Fighter"]["soldier"]) ** 0.5, 3)


# ----- the three experiments -----------------------------------------------

def run_all(pool, scales, n):
    results = {"n": n, "levels": list(LEVELS), "subclasses": [
        dict(key=c.key, label=c.label, chassis=c.chassis, patched=c.patch_sensitive) for c in ROSTER],
        "scales": scales, "duels": {}, "gauntlet": {}, "bestiary": {}, "sparring": {}}
    keys = [c.key for c in ROSTER]
    seed_base = 7
    for level in LEVELS:
        for patched in (True, False):
            tag = f"{level}/{'post' if patched else 'pre'}"
            t0 = time.time()
            # Duels: every pair, both sides counted.
            pairs = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]]
            if not patched:   # only pairs touching a changed subclass differ
                pairs = [(a, b) for a, b in pairs if BY_KEY[a].patch_sensitive or BY_KEY[b].patch_sensitive]
            tasks = [(("hero", a, level, patched), ("hero", b, level, patched), n, seed_base + k)
                     for k, (a, b) in enumerate(pairs)]
            duel = {}
            for (a, b), r in zip(pairs, pool.map(bout, tasks)):
                duel[f"{a}|{b}"] = r
            results["duels"][tag] = duel
            # Gauntlet: each subclass vs each calibrated archetype.
            heroes = keys if patched else [k for k in keys if BY_KEY[k].patch_sensitive]
            tasks, labels = [], []
            for k in heroes:
                for arch in ARCHETYPES:
                    scale = scales[str(level)][BY_KEY[k].chassis][arch]
                    tasks.append((("hero", k, level, patched), ("arch", arch, level, scale),
                                  n, seed_base + len(tasks)))
                    labels.append(f"{k}|{arch}")
            results["gauntlet"][tag] = dict(zip(labels, pool.map(bout, tasks)))
            # Sparring: damage and staying power against an unkillable soldier.
            tasks = [(("hero", k, level, patched), ("dummy", level, dummy_scale(scales, level)),
                      n, seed_base + i) for i, k in enumerate(heroes)]
            results["sparring"][tag] = dict(zip(heroes, pool.map(spar, tasks)))
            # The campaign's own monsters, at level 3 only.
            if level == 3:
                beasts = list(load_bestiary_cached())
                tasks, labels = [], []
                for k in heroes:
                    for bid in beasts:
                        tasks.append((("hero", k, level, patched), ("beast", bid), n, seed_base + len(tasks)))
                        labels.append(f"{k}|{bid}")
                results["bestiary"][tag] = dict(zip(labels, pool.map(bout, tasks)))
            if patched and VARIANTS:
                tasks, labels = [], []
                for v in VARIANTS:
                    for arch in ARCHETYPES:
                        scale = scales[str(level)][v.chassis][arch]
                        tasks.append((("hero", v.key, level, True), ("arch", arch, level, scale),
                                      n, seed_base + len(tasks)))
                        labels.append(f"{v.key}|{arch}")
                results.setdefault("variants", {})[tag] = dict(zip(labels, pool.map(bout, tasks)))
            print(f"  L{tag}: {time.time() - t0:.1f}s", flush=True)
    return results


# ----- the report ----------------------------------------------------------

def wr(r, side="a"):
    w = r["wins"] if side == "a" else r["losses"]
    return (w + r["draws"] / 2) / r["n"]


def tables(results):
    """Derive per-level rankings from raw results (post-patch, with pre-patch for changed ones)."""
    keys = [s["key"] for s in results["subclasses"]]
    out = {}
    for level in results["levels"]:
        for when in ("post", "pre"):
            tag = f"{level}/{when}"
            post = f"{level}/post"
            duel_src = dict(results["duels"][post])
            duel_src.update(results["duels"][tag])
            matrix = {a: {} for a in keys}
            for pair, r in duel_src.items():
                a, b = pair.split("|")
                matrix[a][b] = wr(r, "a")
                matrix[b][a] = wr(r, "b")
            g_src = dict(results["gauntlet"][post])
            g_src.update(results["gauntlet"][tag])
            s_src = dict(results["sparring"][post])
            s_src.update(results["sparring"][tag])
            rows = {}
            for k in keys:
                g = {arch: wr(g_src[f"{k}|{arch}"]) for arch in ARCHETYPES}
                rows[k] = dict(
                    gauntlet=statistics.mean(g.values()), by_arch=g,
                    duel=statistics.mean(matrix[k].values()), duel_vs=matrix[k],
                    duel_wiz=statistics.mean(v for o, v in matrix[k].items() if BY_KEY[o].chassis == "Wizard"),
                    duel_ftr=statistics.mean(v for o, v in matrix[k].items() if BY_KEY[o].chassis == "Fighter"),
                    dealt=s_src[k]["dealt"], survived=s_src[k]["survived"])
                if level == 3:
                    b_src = dict(results["bestiary"][post])
                    b_src.update(results["bestiary"][tag])
                    rows[k]["bestiary"] = {p.split("|")[1]: wr(r) for p, r in b_src.items() if p.startswith(k + "|")}
            out[tag] = rows
    return out


def pct(x):
    return f"{100 * x:.0f}%"


def gmean(xs):
    xs = list(xs)
    return statistics.geometric_mean(xs)


SHORT = {"verdant": "Verd", "warbound": "Warb", "stonewarden": "Ston", "hellbound": "Hell",
         "sanguine_mage": "SgMg", "aether": "Aeth", "sanguine_aegis": "SgAe", "bulwark": "Bulw",
         "warden": "Ward", "archer": "Arch", "gunman": "Gunm"}


def write_report(results):
    t = tables(results)
    subs = {s["key"]: s for s in results["subclasses"]}
    keys = list(subs)
    levels = results["levels"]
    scales = results["scales"]
    name = lambda k: subs[k]["label"] + (" †" if subs[k]["patched"] else "")
    L = []
    L.append("# Proving Grounds: subclass power rankings\n")
    L.append(f"Monte Carlo, {results['n']:,} fights per matchup. Generated by `uv run arena/run.py`; "
             "[README.md](README.md) explains what is simulated and every assumption.\n")
    L.append("**How to read it**\n")
    L.append("- **Gauntlet** is the ranking. One character fights four solo benchmark foes (Brute, Soldier, "
             "Sniper, Caster) one at a time. The foes are tuned *per chassis*, so the average Wizard "
             "subclass and the average Fighter subclass each win 50% of the time. Read a subclass against "
             "its own chassis: 60% is strong, 40% is weak.")
    L.append("- **Chassis gap** shows how much tougher a foe the Wizards handle than the Fighters at par. "
             "That gap is 5e's Wizard-vs-Fighter balance, not your subclasses.")
    L.append("- **Duel** is every subclass against every other at the same level. In a 1v1 the chassis "
             "decides most of it, so the column that says something about the subclass is **vs own chassis**.")
    L.append(f"- **Sparring** is against an unkillable Soldier: damage in the first {SPAR_ROUNDS} rounds "
             "(offence) and rounds survived, capped at 20 (defence and control).")
    L.append("- **†** marks the four subclasses changed in Patch 1. **Δ** is percentage points gained from it.")
    L.append("- Each fight starts with full resources (all slots, once-per-rest features). That favours "
             "burst features; see the README.\n")

    for chassis, title in (("Wizard", "Wizard traditions (Crystal Mages)"),
                           ("Fighter", "Martial archetypes (Aegisbound and Range)")):
        mine = [k for k in keys if subs[k]["chassis"] == chassis]
        L.append(f"## {title}: gauntlet win rate\n")
        L.append("| Subclass | " + " | ".join(f"L{lv}" for lv in levels) + " | Mean |")
        L.append("|---|" + "---:|" * (len(levels) + 1))
        mean = lambda k: statistics.mean(t[f"{lv}/post"][k]["gauntlet"] for lv in levels)
        for k in sorted(mine, key=lambda k: -mean(k)):
            cells = []
            for lv in levels:
                v = t[f"{lv}/post"][k]["gauntlet"]
                cell = pct(v)
                if subs[k]["patched"]:
                    cell += f" ({(v - t[f'{lv}/pre'][k]['gauntlet']) * 100:+.0f})"
                cells.append(cell)
            L.append(f"| {name(k)} | " + " | ".join(cells) + f" | **{pct(mean(k))}** |")
        if any(subs[k]["patched"] for k in mine):
            L.append("\nBracketed: percentage points gained from Patch 1.")
        L.append("")

    L.append("## Chassis gap\n")
    L.append("How much bigger (HP and damage) the benchmark foes had to be for the Wizards to sit at par, "
             "compared with the Fighters.\n")
    L.append("| Level | " + " | ".join(a.title() for a in ARCHETYPES) + " | Overall |")
    L.append("|---:|" + "---:|" * (len(ARCHETYPES) + 1))
    for lv in levels:
        s = scales[str(lv)]
        ratios = [s["Wizard"][a] / s["Fighter"][a] for a in ARCHETYPES]
        L.append(f"| {lv} | " + " | ".join(f"×{r:.2f}" for r in ratios) + f" | **×{gmean(ratios):.2f}** |")
    L.append("\nAbove ×1 the Wizards are stronger solo; below ×1 the Fighters are.\n")

    for lv in levels:
        post, pre = t[f"{lv}/post"], t[f"{lv}/pre"]
        L.append(f"## Level {lv}\n")
        L.append("| # | Subclass | Gauntlet | Δ | Brute | Soldier | Sniper | Caster | Duel vs own chassis | Duel vs all | Dmg 3 rds | Survives |")
        L.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for chassis in ("Wizard", "Fighter"):
            mine = sorted((k for k in keys if subs[k]["chassis"] == chassis), key=lambda k: -post[k]["gauntlet"])
            for i, k in enumerate(mine, 1):
                r = post[k]
                dlt = f"{(r['gauntlet'] - pre[k]['gauntlet']) * 100:+.0f}" if subs[k]["patched"] else ""
                own = r["duel_wiz"] if chassis == "Wizard" else r["duel_ftr"]
                L.append(f"| {chassis[0]}{i} | {name(k)} | **{pct(r['gauntlet'])}** | {dlt} | "
                         + " | ".join(pct(r["by_arch"][a]) for a in ARCHETYPES)
                         + f" | {pct(own)} | {pct(r['duel'])} | {r['dealt']:.0f} | {r['survived']:.1f} |")
        L.append("")
        L.append(f"<details><summary>Level {lv} duel matrix (row's win rate against column)</summary>\n")
        L.append("| | " + " | ".join(SHORT[k] for k in keys) + " |")
        L.append("|---|" + "---:|" * len(keys))
        for a in keys:
            L.append(f"| {subs[a]['label']} | " + " | ".join("—" if a == b else pct(post[a]["duel_vs"][b]) for b in keys) + " |")
        L.append("\n</details>\n")
        if lv == 3:
            names = load_bestiary_cached()
            beasts = list(next(iter(post.values()))["bestiary"])
            L.append("### Level 3 against the campaign's own monsters\n")
            L.append("Real stat blocks from `data/enemies.yaml`, fought 1v1 (they were written for a party, "
                     "so high numbers are expected). The hard ones are the ones that tell subclasses apart.\n")
            L.append("| Subclass | " + " | ".join(names[b]["name"].split(" / ")[0] for b in beasts) + " | Mean |")
            L.append("|---|" + "---:|" * (len(beasts) + 1))
            for k in sorted(keys, key=lambda k: -statistics.mean(post[k]["bestiary"].values())):
                r = post[k]["bestiary"]
                L.append(f"| {name(k)} | " + " | ".join(pct(r[b]) for b in beasts)
                         + f" | **{pct(statistics.mean(r.values()))}** |")
            L.append("")

    if results.get("variants"):
        L.append("## What-ifs\n")
        L.append("The same gauntlet for a rules variant, next to the subclass as written.\n")
        L.append("| Variant | " + " | ".join(f"L{lv}" for lv in levels) + " |")
        L.append("|---|" + "---:|" * len(levels))
        for v in VARIANTS:
            base = next(c for c in ROSTER if isinstance(c, type) and issubclass(v, c) and c is not v)
            cells_b, cells_v = [], []
            for lv in levels:
                vr = results["variants"][f"{lv}/post"]
                cells_v.append(pct(statistics.mean(wr(vr[f"{v.key}|{a}"]) for a in ARCHETYPES)))
                cells_b.append(pct(t[f"{lv}/post"][base.key]["gauntlet"]))
            L.append(f"| {base.label} (as written) | " + " | ".join(cells_b) + " |")
            L.append(f"| {v.label} | " + " | ".join(cells_v) + " |")
        L.append("")

    L.append("## Benchmark foes\n")
    L.append("Base numbers come from the DMG monster-by-CR table for a hard solo fight at each level. HP "
             "and damage are then multiplied by the calibrated scale (Wizard / Fighter).\n")
    L.append("| Level | CR row | AC | Attack | DC | " + " | ".join(a.title() for a in ARCHETYPES) + " |")
    L.append("|---:|---:|---:|---:|---:|" + "---:|" * len(ARCHETYPES))
    for lv in levels:
        tr, s = TIERS[lv], scales[str(lv)]
        L.append(f"| {lv} | {tr['cr']} | {tr['ac']} | +{tr['atk']} | {tr['dc']} | "
                 + " | ".join(f"×{s['Wizard'][a]} / ×{s['Fighter'][a]}" for a in ARCHETYPES) + " |")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=1000, help="fights per matchup (default 1000)")
    ap.add_argument("--recalibrate", action="store_true", help="re-tune the benchmark foes first")
    ap.add_argument("--report-only", action="store_true", help="rebuild report.md from results.json")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    if args.report_only:
        write_report(json.loads(RESULTS.read_text(encoding="utf-8")))
        print(f"wrote {REPORT.relative_to(HERE.parent)}")
        return
    with Pool(args.workers) as pool:
        if args.recalibrate or not CALIBRATION.exists():
            print("calibrating benchmark foes...", flush=True)
            scales = calibrate(pool)
        else:
            scales = json.loads(CALIBRATION.read_text(encoding="utf-8"))
        print(f"running {args.n} fights per matchup...", flush=True)
        results = run_all(pool, scales, args.n)
    RESULTS.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    write_report(results)
    print(f"wrote {RESULTS.relative_to(HERE.parent)} and {REPORT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
