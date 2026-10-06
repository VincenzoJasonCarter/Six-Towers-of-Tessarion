# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""The Proving Grounds, evolution edition: what the Ascendant and Corrupted
branches (evolution.py) are worth to a party.

For every subclass and branch, every four-hero party containing that subclass
fights the four party encounters twice with the same seeds: once as written,
once with that one hero evolved. **Uplift** is the change in the party's win
rate. Within a pillar, the branches should land close together.

Usage, from the repo root:

    uv run arena/evolve.py               # 12 fights per party, encounter and level
    uv run arena/evolve.py --n 4         # quick and noisy
    uv run arena/evolve.py --uses 3      # Corrupted heroes may burn 3 powers a fight

Uses the encounter tuning in party_calibration.json. Writes
arena/evolution_results.json and arena/evolution_report.md
(evolution_u3_* with --uses 3).
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

import evolution  # noqa: E402
from engine import ALL_TACTICS, Fight, seed, set_tactics  # noqa: E402
from foes import ENCOUNTERS, encounter  # noqa: E402
from heroes import BY_KEY, ROSTER  # noqa: E402
from party import CALIBRATION, PARTIES, win_rate  # noqa: E402

LEVELS = (7, 10, 15)          # evolution opens at 6; 7 is the first calibrated level after it
BRANCHES = ("ascendant", "corrupted")
KEYS = [c.key for c in ROSTER]
PILLAR = {"verdant": "Crystal Mages", "warbound": "Crystal Mages", "stonewarden": "Crystal Mages",
          "hellbound": "Crystal Mages", "sanguine_mage": "Crystal Mages", "aether": "Crystal Mages",
          "sanguine_aegis": "Aegisbound", "bulwark": "Aegisbound", "warden": "Aegisbound",
          "archer": "Range", "gunman": "Range"}


def init_worker(uses):
    set_tactics(ALL_TACTICS)
    evolution.CORRUPT_USES = uses


def make(key, level, branch):
    cls = evolution.EVOLVED[(key, branch)] if branch else BY_KEY[key]
    return cls(level, True)


def battle(task):
    """n fights of one party against one encounter, optionally with hero `who` evolved."""
    party, level, enc, scale, n, s, who, branch = task
    seed(s)
    wins = draws = down = uses = 0
    for _ in range(n):
        heroes = [make(k, level, branch if i == who else None) for i, k in enumerate(party)]
        winner, _ = Fight(heroes, encounter(enc, level, scale, len(party))).run()
        wins += winner == 0
        draws += winner is None
        if who is not None:
            down += heroes[who].dead
            uses += getattr(heroes[who], "uses", 0)
    return dict(wins=wins, draws=draws, n=n, down=down, uses=uses)


def run(pool, scales, n, only=None, previous=None):
    """{level: {enc: {"base": [row per party], "<key>/<branch>": {party index: row}}}}

    With `only` (a list of "key/branch"), rerun just those branches and merge
    them into `previous`, reusing its unevolved baseline."""
    out = {}
    for level in LEVELS:
        out[level] = {}
        for enc in ENCOUNTERS:
            t0 = time.time()
            sc = scales[str(level)][enc]
            seed_of = lambda i: 1000 * i + 7
            if previous:
                cell = previous[level][enc]
            else:
                cell = {"base": pool.map(battle, [(p, level, enc, sc, n, seed_of(i), None, None)
                                                  for i, p in enumerate(PARTIES)], chunksize=4)}
            tasks, keys = [], []
            for k in KEYS:
                for b in BRANCHES:
                    if only and f"{k}/{b}" not in only:
                        continue
                    cell[f"{k}/{b}"] = {}
                    for i, p in enumerate(PARTIES):
                        if k in p:
                            tasks.append((p, level, enc, sc, n, seed_of(i), p.index(k), b))
                            keys.append((f"{k}/{b}", i))
            for (name, i), row in zip(keys, pool.map(battle, tasks, chunksize=4)):
                cell[name][i] = row
            out[level][enc] = cell
            print(f"  L{level} {enc}: {time.time() - t0:.0f}s", flush=True)
    return out


def analyse(fights):
    """Per (key, branch, level): uplift in win rate, the evolved hero's survival,
    and how often the branch feature fired per fight."""
    res = {}
    for k in KEYS:
        for b in BRANCHES:
            name = f"{k}/{b}"
            for level in LEVELS:
                ups, down, uses, n = [], 0, 0, 0
                for enc in ENCOUNTERS:
                    cell = fights[level][enc]
                    for i, row in cell[name].items():
                        ups.append(win_rate(row) - win_rate(cell["base"][int(i)]))
                        down += row["down"]
                        uses += row["uses"]
                        n += row["n"]
                res[(k, b, level)] = dict(up=statistics.mean(ups), survive=1 - down / n, uses=uses / n)
    return res


def pts(x):
    return f"{100 * x:+.1f}"


def write_report(fights, meta, path):
    a = analyse(fights)
    label = {c.key: c.label for c in ROSTER}
    mean_up = lambda k, b: statistics.mean(a[(k, b, lv)]["up"] for lv in LEVELS)
    L = ["# Proving Grounds: subclass evolution\n",
         f"Ascendant and Corrupted branches from `evolution.py`, unlocked at 6th level. Every four-hero party "
         f"containing the subclass ({len(PARTIES) * 4 // len(KEYS)} parties) against the four party encounters at "
         f"levels {', '.join(map(str, LEVELS))}, {meta['n']} fights each, once as written and once with that one "
         f"hero evolved (same seeds). Corrupted powers per fight: **{meta['uses']}**. "
         "Generated by `uv run arena/evolve.py`.\n",
         "**How to read it**\n",
         "- **Uplift** is the change in the party's win rate, in percentage points, from evolving that one hero. "
         "Branches in the same pillar should land close together.",
         "- **Fires** is how often the branch feature triggered per fight. Near 0 means the feature rarely "
         "comes up in these encounters, so its uplift says little.",
         "- Noise: each uplift averages about "
         f"{len(ENCOUNTERS) * (len(PARTIES) * 4 // len(KEYS)) * meta['n']:,} fights per level; treat differences "
         "under about 1.5 points as noise.\n"]
    for pillar in ("Crystal Mages", "Aegisbound", "Range"):
        ks = [k for k in KEYS if PILLAR[k] == pillar]
        L.append(f"## {pillar}\n")
        for b in BRANCHES:
            L.append(f"**{b.title()}**\n")
            L.append("| Subclass | " + " | ".join(f"L{lv}" for lv in LEVELS) + " | Mean | Fires (L10) | Survives (L10) |")
            L.append("|---|" + "---:|" * (len(LEVELS) + 3))
            for k in sorted(ks, key=lambda k: -mean_up(k, b)):
                r10 = a[(k, b, 10)]
                L.append(f"| {label[k]} | " + " | ".join(pts(a[(k, b, lv)]["up"]) for lv in LEVELS)
                         + f" | **{pts(mean_up(k, b))}** | {r10['uses']:.1f} | {100 * r10['survive']:.0f}% |")
            spread = max(mean_up(k, b) for k in ks) - min(mean_up(k, b) for k in ks)
            L.append(f"\nSpread within the pillar: **{100 * spread:.1f} points**.\n")
    L.append("## Ascendant vs Corrupted, per subclass\n")
    L.append("Mean uplift over levels. A big gap means one branch is the obvious pick.\n")
    L.append("| Subclass | Ascendant | Corrupted | Gap |")
    L.append("|---|---:|---:|---:|")
    for k in KEYS:
        asc, cor = mean_up(k, "ascendant"), mean_up(k, "corrupted")
        L.append(f"| {label[k]} | {pts(asc)} | {pts(cor)} | {pts(cor - asc)} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=12, help="fights per party, encounter and level (default 12)")
    ap.add_argument("--uses", type=int, default=1, help="Corrupted powers per fight (default 1)")
    ap.add_argument("--only", help="comma-separated key/branch list to rerun (e.g. gunman/ascendant), "
                                   "merged into the saved results")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    stem = "evolution" if args.uses == 1 else f"evolution_u{args.uses}"
    results, report = HERE / f"{stem}_results.json", HERE / f"{stem}_report.md"
    saved = previous = None
    if args.report_only or args.only:
        saved = json.loads(results.read_text(encoding="utf-8"))
        previous = {int(lv): v for lv, v in saved["fights"].items()}
    if args.report_only:
        write_report(previous, saved["meta"], report)
        print(f"wrote {report.relative_to(HERE.parent)}")
        return
    scales = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    meta = saved["meta"] if saved else {"n": args.n, "uses": args.uses, "levels": list(LEVELS)}
    only = args.only.split(",") if args.only else None
    print(f"evolution run: {meta['n']} fights per cell, {meta['uses']} Corrupted use(s) per fight"
          + (f", only {', '.join(only)}" if only else ""), flush=True)
    with Pool(args.workers, initializer=init_worker, initargs=(meta["uses"],)) as pool:
        fights = run(pool, scales, meta["n"], only, previous)
    results.write_text(json.dumps({"meta": meta, "fights": fights}) + "\n", encoding="utf-8")
    write_report(fights, meta, report)
    print(f"wrote {results.relative_to(HERE.parent)} and {report.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
