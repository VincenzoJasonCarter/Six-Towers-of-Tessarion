# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""The Proving Grounds, Common Workings edition: how much stronger a Crystal
Mage is with the Aether Hall's general spells (lore-book chapter 27, modelled
in heroes/workings.py).

For each Crystal Mage subclass and each environment ("bare": floor and walls
only; "furnished": loose objects, liquid, a rug and something hanging), every
four-hero party containing that mage fights the four party encounters twice
with the same seeds: once as written, once with that one mage also knowing
every working. **Uplift** is the change in the party's win rate.

Usage, from the repo root:

    uv run arena/workings.py               # 12 fights per party, encounter and level
    uv run arena/workings.py --n 4         # quick and noisy
    uv run arena/workings.py --report-only
    uv run arena/workings.py --without overtime,"red tape"   # after a full run: what each one is worth

`--without` reruns the bare environment with one working left out at a time,
against the saved full run (same seeds), and adds a table of what each
working adds to the report.

Uses the encounter tuning in results/party_calibration.json. Writes
arena/results/workings_results.json, workings_without_results.json and
workings_report.md.
"""
import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
sys.path.insert(0, str(HERE))

from engine import Fight, seed  # noqa: E402
from foes import ENCOUNTERS, encounter  # noqa: E402
from heroes import BY_KEY, ROSTER  # noqa: E402
from heroes.workings import ENVIRONMENTS, WORKINGS, with_workings  # noqa: E402
import party  # noqa: E402
from party import LEVELS, PLAIN, win_rate  # noqa: E402

PARTIES = PLAIN.parties
MAGES = [c.key for c in ROSTER if c.chassis == "Wizard"]
IMPACT = ("dealt_hp", "protect", "control", "enable", "tank")


def make(key, level, env):
    """env: None (as written), an environment, or (environment, workings left out)."""
    cls = BY_KEY[key]
    if not env:
        return cls(level)
    env, without = env if isinstance(env, tuple) else (env, ())
    return with_workings(cls, env, frozenset(without))(level)


def battle(task):
    """n fights of one party against one encounter, optionally with hero `who` knowing the workings."""
    members, level, enc, scale, n, s, who, env = task
    seed(s)
    wins = draws = 0
    down = [0] * len(members)
    impact = [0.0] * len(members)
    casts = Counter()
    for _ in range(n):
        heroes = [make(k, level, env if i == who else None) for i, k in enumerate(members)]
        winner, _ = Fight(heroes, encounter(enc, level, scale, len(members))).run()
        wins += winner == 0
        draws += winner is None
        for i, h in enumerate(heroes):
            down[i] += h.dead
            impact[i] += sum(getattr(h, f) for f in IMPACT)
        if who is not None:
            casts.update(heroes[who].cast_log)
    return dict(wins=wins, draws=draws, n=n, down=down, impact=[round(x, 1) for x in impact], casts=dict(casts))


def run(pool, scales, n):
    """{level: {enc: {"base": [row per party], "<mage>/<env>": {party index: row}}}}"""
    out = {}
    for level in LEVELS:
        out[level] = {}
        for enc in ENCOUNTERS:
            t0 = time.time()
            sc = scales[str(level)][enc]
            seed_of = lambda i: 1000 * i + 7
            cell = {"base": pool.map(battle, [(p, level, enc, sc, n, seed_of(i), None, None)
                                              for i, p in enumerate(PARTIES)], chunksize=4)}
            tasks, keys = [], []
            for k in MAGES:
                for env in ENVIRONMENTS:
                    cell[f"{k}/{env}"] = {}
                    for i, p in enumerate(PARTIES):
                        if k in p:
                            tasks.append((p, level, enc, sc, n, seed_of(i), p.index(k), env))
                            keys.append((f"{k}/{env}", i))
            for (name, i), row in zip(keys, pool.map(battle, tasks, chunksize=4)):
                cell[name][i] = row
            out[level][enc] = cell
            print(f"  L{level} {enc}: {time.time() - t0:.0f}s", flush=True)
    return out


def run_without(pool, scales, n, spells):
    """{spell: {level: {enc: {mage: {party index: row}}}}}: the bare run with that working left out."""
    out = {}
    for spell in spells:
        t0 = time.time()
        out[spell] = {}
        for level in LEVELS:
            out[spell][level] = {}
            for enc in ENCOUNTERS:
                sc = scales[str(level)][enc]
                tasks, keys = [], []
                for k in MAGES:
                    for i, p in enumerate(PARTIES):
                        if k in p:
                            tasks.append((p, level, enc, sc, n, 1000 * i + 7, p.index(k), ("bare", (spell,))))
                            keys.append((k, i))
                cell = {k: {} for k in MAGES}
                for (k, i), row in zip(keys, pool.map(battle, tasks, chunksize=4)):
                    cell[k][i] = row
                out[spell][level][enc] = cell
        print(f"  without {spell}: {time.time() - t0:.0f}s", flush=True)
    return out


def worth(fights, without):
    """{spell: {level: points}}: the bare uplift with every working minus the uplift without that one,
    averaged over the mages."""
    res = {}
    for spell, by_level in without.items():
        res[spell] = {}
        for level in LEVELS:
            gaps = []
            for enc in ENCOUNTERS:
                cell = fights[level][enc]
                for k in MAGES:
                    for i, row in by_level[level][enc][k].items():
                        gaps.append(win_rate(cell[f"{k}/bare"][i]) - win_rate(row))
            res[spell][level] = statistics.mean(gaps)
    return res


def analyse(fights):
    """Per (mage, env, level): uplift in party win rate, the mage's own Impact
    before and after, its survival, and what it cast per fight."""
    res = {}
    for k in MAGES:
        for env in ENVIRONMENTS:
            for level in LEVELS:
                ups, imp0, imp1, down0, down1, n = [], 0.0, 0.0, 0, 0, 0
                casts = Counter()
                per_enc = {}
                for enc in ENCOUNTERS:
                    cell = fights[level][enc]
                    enc_ups = []
                    for i, row in cell[f"{k}/{env}"].items():
                        base = cell["base"][int(i)]
                        who = PARTIES[int(i)].index(k)
                        up = win_rate(row) - win_rate(base)
                        ups.append(up)
                        enc_ups.append(up)
                        imp0 += base["impact"][who]
                        imp1 += row["impact"][who]
                        down0 += base["down"][who]
                        down1 += row["down"][who]
                        n += row["n"]
                        casts.update(row["casts"])
                    per_enc[enc] = statistics.mean(enc_ups)
                res[(k, env, level)] = dict(up=statistics.mean(ups), per_enc=per_enc, imp0=imp0 / n, imp1=imp1 / n,
                                            surv0=1 - down0 / n, surv1=1 - down1 / n,
                                            casts={s: c / n for s, c in casts.items()})
    return res


def base_values():
    """Each subclass's win value as written (party_results.json), by level."""
    if not PLAIN.results.exists():
        return None
    a = party.analyse(json.loads(PLAIN.results.read_text(encoding="utf-8")))
    return {lv: {k: a[lv]["subs"][k]["delta"] for k in a[lv]["subs"]} for lv in LEVELS}


def pts(x):
    return f"{100 * x:+.1f}"


def write_report(fights, meta, path, without=None):
    a = analyse(fights)
    label = {c.key: c.label for c in ROSTER}
    mean = lambda k, env, f="up": statistics.mean(a[(k, env, lv)][f] for lv in LEVELS)
    L = ["# Proving Grounds: the Common Workings\n",
         f"What the Aether Hall's general spells (`lore-book/27-common-workings.md`, modelled in "
         f"`heroes/workings.py`) add to a Crystal Mage. Every four-hero party containing the mage "
         f"({len(PARTIES) * 4 // len(ROSTER)} parties) against the four party encounters at levels "
         f"{', '.join(map(str, LEVELS))}, {meta['n']} fights each, once as written and once with that one mage also "
         f"knowing every working (same seeds). Generated by `uv run arena/workings.py`.\n",
         "**How to read it**\n",
         "- **Uplift** is the change in the party's win rate, in percentage points, from that one mage knowing the "
         "workings. Encounters are tuned so the average party wins 50%.",
         "- **Bare**: floor, walls and ceiling only. **Furnished**: also loose objects, liquid, a rug and something "
         "hanging overhead, so Throw the Book, Flash Boil, Rug Pull and Assessed Weight work too.",
         "- **Impact** is the mage's own contribution in HP per fight (damage + protection + control + enable + "
         "tanking, as in `party_report.md`).",
         "- Noise: treat differences under about 1.5 points as noise.\n"]

    L.append("## Uplift per mage\n")
    L.append("| Mage | Bare | Furnished | Impact as written | Impact with workings (bare) |")
    L.append("|---|---:|---:|---:|---:|")
    for k in MAGES:
        i0, i1 = mean(k, "bare", "imp0"), mean(k, "bare", "imp1")
        L.append(f"| {label[k]} | **{pts(mean(k, 'bare'))}** | **{pts(mean(k, 'furnished'))}** | {i0:.0f} | "
                 f"{i1:.0f} ({100 * (i1 / i0 - 1):+.0f}%) |")
    allb = statistics.mean(mean(k, "bare") for k in MAGES)
    allf = statistics.mean(mean(k, "furnished") for k in MAGES)
    L.append(f"| **Average mage** | **{pts(allb)}** | **{pts(allf)}** | | |")
    L.append("")

    L.append("## By level\n")
    L.append("| Mage | Env | " + " | ".join(f"L{lv}" for lv in LEVELS) + " |")
    L.append("|---|---|" + "---:|" * len(LEVELS))
    for k in MAGES:
        for env in ENVIRONMENTS:
            L.append(f"| {label[k]} | {env} | " + " | ".join(pts(a[(k, env, lv)]["up"]) for lv in LEVELS) + " |")
    for env in ENVIRONMENTS:
        L.append(f"| **Average** | {env} | " + " | ".join(
            pts(statistics.mean(a[(k, env, lv)]["up"] for k in MAGES)) for lv in LEVELS) + " |")
    L.append("")

    L.append("## By encounter (average mage, bare)\n")
    L.append("| Level | " + " | ".join(ENCOUNTERS) + " |")
    L.append("|---|" + "---:|" * len(ENCOUNTERS))
    for lv in LEVELS:
        L.append(f"| L{lv} | " + " | ".join(
            pts(statistics.mean(a[(k, 'bare', lv)]["per_enc"][e] for k in MAGES)) for e in ENCOUNTERS) + " |")
    L.append("")

    L.append("## What the mages cast\n")
    L.append("Workings cast per fight by the average mage that knows them.\n")
    for env in ENVIRONMENTS:
        spells = sorted({s for k in MAGES for lv in LEVELS for s in a[(k, env, lv)]["casts"]})
        per = {s: [statistics.mean(a[(k, env, lv)]["casts"].get(s, 0) for k in MAGES) for lv in LEVELS]
               for s in spells}
        spells.sort(key=lambda s: -sum(per[s]))
        L.append(f"**{env.capitalize()}**\n")
        L.append("| Working | " + " | ".join(f"L{lv}" for lv in LEVELS) + " |")
        L.append("|---|" + "---:|" * len(LEVELS))
        for s in spells:
            L.append(f"| {s} | " + " | ".join(f"{x:.2f}" for x in per[s]) + " |")
        L.append("")

    if without:
        w = worth(fights, without)
        L.append("## What each working is worth\n")
        L.append("The bare uplift with every working, minus the uplift with that one left out (same seeds), averaged "
                 "over the six mages: the points of party win rate that working adds on top of all the others. "
                 "Workings that do the same job share credit, so the column needn't add up to the total.\n")
        L.append("| Working | " + " | ".join(f"L{lv}" for lv in LEVELS) + " | Mean |")
        L.append("|---|" + "---:|" * (len(LEVELS) + 1))
        for spell in sorted(w, key=lambda s: -statistics.mean(w[s].values())):
            L.append(f"| {spell} | " + " | ".join(pts(w[spell][lv]) for lv in LEVELS)
                     + f" | **{pts(statistics.mean(w[spell].values()))}** |")
        L.append("")

    base = base_values()
    if base:
        L.append("## Against the gap between subclasses\n")
        L.append("Each mage's win value as written (from `party_report.md`: the win rate of parties with it minus "
                 "parties without), next to the same plus its uplift (bare). The uplift is for one mage knowing the "
                 "workings; a party with two such mages gets roughly twice it.\n")
        L.append("| Mage | " + " | ".join(f"L{lv} as written / with" for lv in LEVELS) + " |")
        L.append("|---|" + "---:|" * len(LEVELS))
        for k in MAGES:
            L.append(f"| {label[k]} | " + " | ".join(
                f"{pts(base[lv][k])} / {pts(base[lv][k] + a[(k, 'bare', lv)]['up'])}" for lv in LEVELS) + " |")
        L.append("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=12, help="fights per party, encounter and level (default 12)")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--without", help="comma-separated workings to leave out one at a time (or 'all'), "
                                      "against the saved full run")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    results, report = OUT / "workings_results.json", OUT / "workings_report.md"
    wpath = OUT / "workings_without_results.json"
    load_without = lambda: ({s: {int(lv): v for lv, v in d.items()} for s, d in
                             json.loads(wpath.read_text(encoding="utf-8")).items()} if wpath.exists() else None)
    if args.report_only or args.without:
        saved = json.loads(results.read_text(encoding="utf-8"))
        fights = {int(lv): v for lv, v in saved["fights"].items()}
        for lv in fights:   # JSON turned the party indices into strings
            for enc in fights[lv]:
                for name, rows in fights[lv][enc].items():
                    if isinstance(rows, dict):
                        fights[lv][enc][name] = {int(i): r for i, r in rows.items()}
        without = load_without()
        if args.without:
            spells = list(WORKINGS) if args.without == "all" else [x.strip() for x in args.without.split(",")]
            bad = [x for x in spells if x not in WORKINGS]
            if bad:
                sys.exit(f"unknown workings: {bad}; choose from {list(WORKINGS)}")
            scales = json.loads(PLAIN.calibration.read_text(encoding="utf-8"))
            with Pool(args.workers) as pool:
                fresh = run_without(pool, scales, saved["meta"]["n"], spells)
            without = dict(without or {}, **fresh)
            wpath.write_text(json.dumps(without) + "\n", encoding="utf-8")
            without = load_without()
        if without:
            for s in without:
                for lv in without[s]:
                    for enc in without[s][lv]:
                        for k in without[s][lv][enc]:
                            without[s][lv][enc][k] = {int(i): r for i, r in without[s][lv][enc][k].items()}
        write_report(fights, saved["meta"], report, without)
        print(f"wrote {report.relative_to(HERE.parent)}")
        return
    scales = json.loads(PLAIN.calibration.read_text(encoding="utf-8"))
    meta = {"n": args.n, "levels": list(LEVELS), "environments": list(ENVIRONMENTS)}
    print(f"workings run: {meta['n']} fights per cell", flush=True)
    with Pool(args.workers) as pool:
        fights = run(pool, scales, args.n)
    results.write_text(json.dumps({"meta": meta, "fights": fights}) + "\n", encoding="utf-8")
    write_report(fights, meta, report)
    print(f"wrote {results.relative_to(HERE.parent)} and {report.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
