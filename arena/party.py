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

Writes arena/party_results.json and arena/party_report.md (party6_* etc. for
other sizes, party4r_* etc. with repeats, each with its own encounter tuning).
"""
import argparse
import itertools
import json
import os
import random
import statistics
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine import Fight, seed  # noqa: E402
from foes import ENCOUNTERS, TIERS, encounter, lineup  # noqa: E402
from heroes import BY_KEY, ROSTER  # noqa: E402

LEVELS = (3, 7, 10, 15)
SOLO = HERE / "results.json"
KEYS = [c.key for c in ROSTER]
PARTY_SIZE = 4
REPEATS = False
CALIBRATION = RESULTS = REPORT = None
PARTIES = []


def setup(size, repeats=False):
    """Point the module at one kind of party: its party list and its output files."""
    global PARTY_SIZE, REPEATS, CALIBRATION, RESULTS, REPORT, PARTIES
    PARTY_SIZE, REPEATS = size, repeats
    stem = f"party{size}r" if repeats else "party" if size == 4 else f"party{size}"
    CALIBRATION = HERE / f"{stem}_calibration.json"
    RESULTS = HERE / f"{stem}_results.json"
    REPORT = HERE / f"{stem}_report.md"
    combos = itertools.combinations_with_replacement if repeats else itertools.combinations
    PARTIES = [list(p) for p in combos(KEYS, size)]


setup(4)


def battle(task):
    """n fights of one party against one encounter."""
    party, level, enc, scale, n, s = task
    seed(s)
    size = len(party)
    wins = draws = 0
    rounds = []
    members = [[0, 0, 0] for _ in party]   # per hero, in party order: [times down, dealt, taken]
    for _ in range(n):
        heroes = [BY_KEY[k](level, True) for k in party]
        winner, r = Fight(heroes, encounter(enc, level, scale, size)).run()
        rounds.append(r)
        wins += winner == 0
        draws += winner is None
        for h, m in zip(heroes, members):
            m[0] += h.dead
            m[1] += h.dealt
            m[2] += h.taken
    return dict(party=party, wins=wins, draws=draws, n=n, rounds=round(statistics.mean(rounds), 2),
                members=members)


def slots(r):
    """(subclass, [down, dealt, taken]) for each hero in a result row. Older
    results stored one dict per subclass; both shapes are read."""
    m = r["members"]
    if isinstance(m, dict):
        return [(k, [m[k]["down"], m[k]["dealt"], m[k]["taken"]]) for k in r["party"]]
    return list(zip(r["party"], m))


def win_rate(r):
    return (r["wins"] + r["draws"] / 2) / r["n"]


# ----- calibration ---------------------------------------------------------

def calibrate(pool, sample=48, n=40):
    """Scale each encounter's HP and damage so the average party wins half its fights."""
    rng = random.Random(5)
    picked = rng.sample(PARTIES, sample)
    out = {}
    for level in LEVELS:
        out[str(level)] = {}
        for enc in ENCOUNTERS:
            lo, hi = 0.2, 8.0
            for step in range(10):
                mid = (lo * hi) ** 0.5
                tasks = [(p, level, enc, mid, n, 100 * step + i) for i, p in enumerate(picked)]
                wr = statistics.mean(win_rate(r) for r in pool.map(battle, tasks))
                if wr > 0.5:
                    lo = mid
                else:
                    hi = mid
            out[str(level)][enc] = round((lo * hi) ** 0.5, 3)
        print(f"  calibrated L{level}: {out[str(level)]}", flush=True)
    CALIBRATION.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def run_all(pool, scales, n, only=None, previous=None):
    """Simulate every party, or with `only`, just the parties containing that
    subclass, merged into `previous` (for testing a change to one subclass)."""
    results = previous or {"n": n, "size": PARTY_SIZE, "repeats": REPEATS, "levels": list(LEVELS), "encounters": list(ENCOUNTERS), "scales": scales,
                           "subclasses": [dict(key=c.key, label=c.label, chassis=c.chassis,
                                               patched=c.patch_sensitive) for c in ROSTER], "fights": {}}
    for level in LEVELS:
        for enc in ENCOUNTERS:
            t0 = time.time()
            idx = [i for i, p in enumerate(PARTIES) if only is None or only in p]
            tasks = [(PARTIES[i], level, enc, scales[str(level)][enc], n, 7 + i) for i in idx]
            fresh = pool.map(battle, tasks, chunksize=4)
            rows = results["fights"].get(f"{level}/{enc}") or [None] * len(PARTIES)
            for i, r in zip(idx, fresh):
                rows[i] = r
            results["fights"][f"{level}/{enc}"] = rows
            print(f"  L{level} {enc}: {time.time() - t0:.1f}s", flush=True)
    return results


# ----- analysis ------------------------------------------------------------

def analyse(results):
    """Per level: each subclass's value to a party, plus party and pair scores."""
    out = {}
    for level in results["levels"]:
        per_enc = {}
        for enc in results["encounters"]:
            per_enc[enc] = results["fights"][f"{level}/{enc}"]
        party_wr = {}   # tuple(party) -> mean win rate over encounters
        for enc, rows in per_enc.items():
            for r in rows:
                party_wr.setdefault(tuple(r["party"]), []).append(win_rate(r))
        party_wr = {p: statistics.mean(v) for p, v in party_wr.items()}
        overall = statistics.mean(party_wr.values())
        subs = {}
        for k in KEYS:
            with_k = [v for p, v in party_wr.items() if k in p]
            without = [v for p, v in party_wr.items() if k not in p]
            row = {"with": statistics.mean(with_k), "delta": statistics.mean(with_k) - statistics.mean(without),
                   "by_enc": {}}
            down = dealt_share = taken_share = 0.0
            count = 0
            for enc, rows in per_enc.items():
                w = [win_rate(r) for r in rows if k in r["party"]]
                wo = [win_rate(r) for r in rows if k not in r["party"]]
                row["by_enc"][enc] = statistics.mean(w) - statistics.mean(wo)
                for r in rows:
                    if k not in r["party"]:
                        continue
                    sl = slots(r)
                    tot_dealt = sum(m[1] for _, m in sl) or 1
                    tot_taken = sum(m[2] for _, m in sl) or 1
                    for key, m in sl:
                        if key != k:
                            continue
                        down += m[0] / r["n"]
                        dealt_share += m[1] / tot_dealt
                        taken_share += m[2] / tot_taken
                        count += 1
            row.update(survive=1 - down / count, dealt=dealt_share / count, taken=taken_share / count)
            subs[k] = row
        # Pair synergy: how much better a pair does together than its two halves predict.
        pairs = {}
        for a, b in itertools.combinations(KEYS, 2):
            both = [v for p, v in party_wr.items() if a in p and b in p]
            pairs[(a, b)] = statistics.mean(both) - (subs[a]["with"] + subs[b]["with"] - overall)
        # Stacking: average win rate by how many copies of a subclass the party has.
        stack = {}
        for k in KEYS:
            by = {}
            for p, v in party_wr.items():
                c = p.count(k)
                if c:
                    by.setdefault(min(c, 3), []).append(v)
            stack[k] = {c: statistics.mean(v) for c, v in by.items()}
        out[level] = {"subs": subs, "parties": party_wr, "pairs": pairs, "overall": overall, "stack": stack}
    return out


def pct(x):
    return f"{100 * x:.0f}%"


def pts(x):
    return f"{100 * x:+.0f}"


def solo_ranks():
    """Gauntlet means from the one-on-one run, if it exists, for comparison."""
    if not SOLO.exists():
        return None
    import run as solo   # noqa: E402 - the one-on-one runner's analysis
    res = json.loads(SOLO.read_text(encoding="utf-8"))
    t = solo.tables(res)
    return {k: statistics.mean(t[f"{lv}/post"][k]["gauntlet"] for lv in res["levels"]) for k in KEYS}


def write_report(results):
    setup(results.get("size", 4), results.get("repeats", False))
    a = analyse(results)
    levels, encs = results["levels"], results["encounters"]
    label = {s["key"]: s["label"] for s in results["subclasses"]}
    chassis = {s["key"]: s["chassis"] for s in results["subclasses"]}
    L = []
    L.append(f"# Proving Grounds: party simulation ({PARTY_SIZE} heroes)\n")
    kind = "subclasses, repeats allowed" if REPEATS else "different subclasses"
    L.append(f"Every party of {PARTY_SIZE} {kind} ({len(PARTIES):,} parties) against four encounters "
             f"at levels {', '.join(map(str, levels))}, {results['n']} fights each: "
             f"{len(PARTIES) * len(levels) * len(encs) * results['n']:,} fights. "
             "Generated by `uv run arena/party.py`; [README.md](README.md) has the rules and assumptions.\n")
    L.append("**How to read it**\n")
    L.append("- Each encounter is tuned so the average party wins 50%.")
    L.append("- **Value** is the main number: the win rate of parties that include the subclass minus the "
             "win rate of parties that don't, in percentage points. +5 means bringing it makes a party "
             "about 5 points more likely to win. Around 0 is average. Because a party has "
             f"{PARTY_SIZE} of the 11 subclasses, values are relative to the field.")
    L.append("- **Survives** is how often that character is still standing at the end. **Damage** and **Taken** "
             f"are its share of the party's damage dealt and taken ({100 / PARTY_SIZE:.0f}% is an even share).")
    L.append("- Every fight starts fresh with full resources, as in the one-on-one run.\n")

    solo = solo_ranks()
    mean_delta = {k: statistics.mean(a[lv]["subs"][k]["delta"] for lv in levels) for k in KEYS}
    L.append("## Value to a party\n")
    head = "| Subclass | " + " | ".join(f"L{lv}" for lv in levels) + " | Mean |"
    if solo:
        head += " Party rank | Solo rank |"
    L.append(head)
    L.append("|---|" + "---:|" * (len(levels) + 1) + ("---:|---:|" if solo else ""))
    party_order = sorted(KEYS, key=lambda k: -mean_delta[k])
    solo_order = sorted(KEYS, key=lambda k: -solo[k]) if solo else None
    for i, k in enumerate(party_order, 1):
        row = f"| {label[k]} | " + " | ".join(pts(a[lv]["subs"][k]["delta"]) for lv in levels) + f" | **{pts(mean_delta[k])}** |"
        if solo:
            row += f" {i} | {solo_order.index(k) + 1} |"
        L.append(row)
    if solo:
        L.append("\nSolo rank is the one-on-one gauntlet (report.md) across both chassis, for comparison: "
                 "a big jump means the subclass's strength is in what it does for others.")
    L.append("")

    for lv in levels:
        s = a[lv]["subs"]
        L.append(f"## Level {lv}\n")
        L.append("| # | Subclass | Win with | Value | " + " | ".join(e.title() for e in encs)
                 + " | Survives | Damage | Taken |")
        L.append("|---:|---|---:|---:|" + "---:|" * len(encs) + "---:|---:|---:|")
        for i, k in enumerate(sorted(KEYS, key=lambda k: -s[k]["delta"]), 1):
            r = s[k]
            L.append(f"| {i} | {label[k]} | {pct(r['with'])} | **{pts(r['delta'])}** | "
                     + " | ".join(pts(r["by_enc"][e]) for e in encs)
                     + f" | {pct(r['survive'])} | {pct(r['dealt'])} | {pct(r['taken'])} |")
        L.append("\nThe encounter columns are the value against that encounter alone.\n")

    # Parties
    mean_party = {}
    for p in a[levels[0]]["parties"]:
        mean_party[p] = statistics.mean(a[lv]["parties"][p] for lv in levels)
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
    for m in range(PARTY_SIZE + 1):
        group = [p for p in mean_party if wiz(p) == m]
        if group:
            L.append(f"| {m} | {len(group)} | "
                     + " | ".join(pct(statistics.mean(a[lv]['parties'][p] for p in group)) for lv in levels) + " |")
    L.append("")

    # Pairs
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

    if REPEATS:
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

    L.append("## Encounters\n")
    L.append("One creature per hero (the boss alone), built like the gauntlet's benchmark foes, with HP and "
             "damage multiplied by the calibrated scale.\n")
    L.append("| Encounter | Creatures | " + " | ".join(f"L{lv} scale" for lv in levels) + " |")
    L.append("|---|---|" + "---:|" * len(levels))
    for e in encs:
        L.append(f"| {e.title()} | {', '.join(lineup(e, PARTY_SIZE))} | "
                 + " | ".join(f"×{results['scales'][str(lv)][e]}" for lv in levels) + " |")
    L.append("\n- **Skirmishers** ignore the front rank and go for the lowest-AC hero. **Snipers** shoot the "
             "lowest-AC hero in range. **Casters** blast a 10-foot radius wherever the most heroes stand. The "
             "**Boss** has three attacks, 10-foot reach and two Legendary Resistances (it shrugs off a save "
             "against Hold or a big spell).")
    L.append(f"- Base numbers per level: " + "; ".join(
        f"L{lv} CR {TIERS[lv]['cr']} (AC {TIERS[lv]['ac']}, +{TIERS[lv]['atk']}, DC {TIERS[lv]['dc']})" for lv in levels) + ".")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=100, help="fights per party and encounter (default 100)")
    ap.add_argument("--recalibrate", action="store_true", help="re-tune the encounters first")
    ap.add_argument("--only", choices=KEYS, metavar="SUBCLASS",
                    help="rerun only the parties containing this subclass (e.g. sanguine_mage) and "
                         "merge them into the saved results; uses the saved encounter tuning")
    ap.add_argument("--report-only", action="store_true", help="rebuild party_report.md from party_results.json")
    ap.add_argument("--size", type=int, default=4, help="heroes per party (default 4); enemies scale to match")
    ap.add_argument("--repeats", action="store_true", help="allow the same subclass more than once in a party")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    setup(args.size, args.repeats)
    if args.report_only:
        write_report(json.loads(RESULTS.read_text(encoding="utf-8")))
        print(f"wrote {REPORT.relative_to(HERE.parent)}")
        return
    with Pool(args.workers) as pool:
        if args.only:
            previous = json.loads(RESULTS.read_text(encoding="utf-8"))
            scales, n = previous["scales"], previous["n"]
            print(f"rerunning the parties with {args.only}, {n} fights each...", flush=True)
            results = run_all(pool, scales, n, only=args.only, previous=previous)
        else:
            if args.recalibrate or not CALIBRATION.exists():
                print("calibrating encounters...", flush=True)
                scales = calibrate(pool)
            else:
                scales = json.loads(CALIBRATION.read_text(encoding="utf-8"))
            print(f"running {len(PARTIES)} parties x {len(LEVELS)} levels x {len(ENCOUNTERS)} encounters, "
                  f"{args.n} fights each...", flush=True)
            results = run_all(pool, scales, args.n)
    RESULTS.write_text(json.dumps(results) + "\n", encoding="utf-8")
    write_report(results)
    print(f"wrote {RESULTS.relative_to(HERE.parent)} and {REPORT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
