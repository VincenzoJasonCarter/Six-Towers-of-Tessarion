"""The three rules everything goes through: an attack roll, a saving throw, and
taking damage. Each calls the creatures' hooks (creature.py) at the moments a
feature can step in, and impact.py to credit whoever changed the outcome."""
from __future__ import annotations

from . import impact
from .context import Ctx, replace
from .dice import avg, d, d20, roll_damage
from .impact import credit


def cage_over(c):
    """The Mana Cage effect whose dome covers c (raised by c or an ally): (Warden, effect)."""
    for w in [c] + c.allies():
        e = w.get("cage")
        if e and abs(w.x - c.x) <= 15:
            return w, e
    return None, None


# ----- attack rolls ------------------------------------------------------------

def attack_adv(att, tgt, ctx, why=None):
    """Advantage/disadvantage on an attack, without using anything up.

    With `why`, also lists each source as ("adv" | "dis", creature to credit or
    None, "protect" | "control" | "enable"). A debuff on the attacker (control)
    counts whoever it attacks; a buff (protect, enable) only counts when it
    helps someone other than its source."""
    def note(kind, src, cat):
        if why is not None:
            if src is None:
                ok = False
            elif cat == "control":
                ok = src.side != att.side
            else:
                helped = att if cat == "enable" else tgt
                ok = src is not helped and src.side == helped.side
            why.append((kind, src if ok else None, cat))

    adv, dis = att.my_attack_adv(tgt, ctx)
    if adv:
        note("adv", None, None)
    if dis:
        note("dis", None, None)
    # conditions on the target
    for n in ("paralyzed", "stunned", "restrained", "blinded"):
        e = tgt.get(n)
        if e:
            adv = True
            note("adv", e.source, "enable")
    # conditions on the attacker
    for n in ("restrained", "blinded", "crash", "next_atk_disadv", "hunger"):
        e = att.get(n)
        if e:
            dis = True
            note("dis", e.source, "control")
    e = att.get("tethered")   # Shackle Strike: anyone but the Warden is attacked at disadvantage
    if e and e.source is not tgt and not e.source.dead:
        dis = True
        note("dis", e.source, "control")
    if att.fight:
        for h in att.enemies():   # Blood Lure: likewise, anyone but the Sanguine Aegis
            if h is not tgt and h.lures(att):
                dis = True
                note("dis", h, "control")
                break
    fear = att.get("frightened")
    if fear and fear.source and not fear.source.dead and att.can_see(fear.source):
        dis = True
        note("dis", fear.source, "control")
    lost = att.get("unlocated")
    if lost and lost.source is tgt:
        dis = True   # Silent Volley: it can't pin down the archer
        note("dis", None, None)
    # the situation
    if ctx.kind == "ranged" and att.threatened():
        dis = True
        note("dis", None, None)
    if not att.can_see(tgt):
        dis = True
        note("dis", None, None)
    if att.has("darkness") and not att.has("white_dust") and not tgt.devils_sight:
        adv = True   # the attacker is unseen
        note("adv", None, None)
    # the target's protectors
    veil = tgt.get("veiled")
    if veil and ctx.kind == "ranged" and not ctx.spell and att.dist_to(tgt) > 10:
        dis = True   # Verdant Veil
        note("dis", veil.source, "protect")
    if ctx.spell and ctx.kind == "ranged":
        w = cage_over(tgt)[0]
        if w:
            dis = True   # Mana Cage
            note("dis", w, "protect")
    # the attacker's helpers (evolutions)
    insp = att.get("inspired")
    if insp:
        adv = True   # Drumwarden
        note("adv", insp.source, "enable")
    spot = tgt.get("spotted")
    if spot and spot.source is not att and spot.source.side == att.side:
        adv = True   # Spotter's Mark
        note("adv", spot.source, "enable")
    return adv, dis


def attack(att, tgt, *, bonus, parts, kind, spell=False, level=0, magical=False,
           weapon=None, dis=False, ctx=None):
    """One attack roll. kind: "melee" | "ranged". `dis`: the attacker's own
    disadvantage (long range). Returns (hit, crit)."""
    if att.dead or tgt.dead:
        return False, False
    att.acted = True
    ctx = replace(ctx or Ctx(), kind=kind, spell=spell, level=level, magical=magical or spell, weapon=weapon)

    # 1. Advantage and disadvantage, noting who caused them.
    why = [("dis", None, None)] if dis else []
    adv, d2 = attack_adv(att, tgt, ctx, why)
    dis = dis or d2
    if not dis:
        for g in tgt.allies():
            if g.ally_attacked(att, tgt, ctx):   # Living Wall (Covering Fire adds a penalty die instead)
                dis = True
                why.append(("dis", g, "protect"))
                break
    for once in ("next_atk_disadv", "hunger", "inspired"):
        att.take(once)
    pen = att.take("next_atk_pen")
    pen_avg = ((pen.value or 4) + 1) / 2 if pen else 0

    # 2. Impact: who moved the odds, and who drew the attack.
    stake = impact.attack_roll(att, tgt, bonus, parts, adv, dis, why, pen_avg)
    tgt.aimed += 1
    other = att.stand_in(tgt)
    if other is not None:
        impact.tanking(att, tgt, other, attack_adv(att, other, ctx), bonus, parts, ctx, adv, dis, pen_avg)
    impact.penalty_die(att, tgt, pen, bonus, adv, dis, stake)

    # 3. The roll, and reactions that raise AC after seeing it (shield, Null Field).
    roll = d20(adv, dis)
    att.last_natural = roll
    total = roll + bonus - (d(1, pen.value or 4) if pen else 0)
    crit = roll == 20
    ac = tgt.ac()
    hit = crit or (roll != 1 and total >= ac)
    if hit and not crit:
        hit = not _reacted(att, tgt, ctx, bonus, total, ac, stake)
    if not hit:
        return False, False

    # 4. Damage.
    held = tgt.get("paralyzed")
    if held and att.dist_to(tgt) <= 5:
        if not crit:
            impact.auto_crit(att, held, parts)
        crit = True
    ctx.crit = crit
    att.on_hit_roll(tgt, ctx)
    crit = ctx.crit
    att.hit_this_turn = True
    extra = att.bonus_damage(tgt, ctx)
    mark = tgt.get("spotted_dmg")
    if mark and mark.source is not att and mark.source.side == att.side:
        tgt.remove(effect=mark)
        extra = list(extra) + [mark.value]   # Spotter's Mark: the first ally hit
        credit(mark.source, "enable", avg([mark.value]))
    deal(tgt, roll_damage(list(parts) + extra, crit), att, replace(ctx, attack=True))
    att.on_hit(tgt, ctx, crit)
    return True, crit


def _reacted(att, tgt, ctx, bonus, total, ac, stake):
    """The target's own reaction, then an ally's, may raise its AC against a hit
    it has seen. True if that turned the hit into a miss."""
    ctx.bonus = bonus
    raised = 0
    if tgt.reaction and not tgt.incapacitated():
        raised = tgt.hit_reaction(att, ctx, total, ac)
        if raised and total < ac + raised:
            tgt.mitigated += stake   # its own shield turned the hit into a miss
    if not raised or total >= ac + raised:
        for g in tgt.allies():
            raised = g.ally_hit_reaction(att, tgt, ctx, total, ac)
            if raised:
                if total < ac + raised:
                    credit(g, "protect", stake)
                break
    return bool(raised) and total < ac + raised


# ----- saving throws -------------------------------------------------------------

def saving_throw(tgt, abil, dc, src, ctx):
    """True if the save succeeds. ctx.stake, when given, is the damage a failure
    costs over a success; it is what the save's helpers and hinderers get credit for."""
    if abil in ("str", "dex") and tgt.incapacitated():
        ok = False
        impact.save_auto_fail(tgt, abil, dc, src, ctx.stake)
    else:
        ok = _roll_save(tgt, abil, dc, src, ctx)
    if ok and src and not src.dead and src.force_fail(tgt, ctx):
        ok = False
    if not ok and src:
        src.on_failed_save(tgt, ctx)
    return ok


def _roll_save(tgt, abil, dc, src, ctx):
    # 1. Advantage, disadvantage and bonuses: its own, the attacker's, its allies' auras.
    a1, d1 = tgt.my_save_adv(abil, src, ctx)
    a2, d2 = src.target_save_adv(tgt, abil, ctx) if src else (False, False)
    adv, dis = a1 or a2, d1 or d2
    bonus = tgt.save_bonus(abil)
    lift, lifter, boosters, own_dis = 0, None, [], dis
    for g in tgt.allies():
        a3, d3 = g.aura_save_adv(tgt, abil, src, ctx)
        adv, dis = adv or a3, dis or d3
        own_dis = own_dis or d3
        if a3:
            boosters.append(g)
        b = g.aura_save_bonus(tgt, abil)
        if b > lift:
            lift, lifter = b, g
    hold = tgt.get("restrained") if abil == "dex" else None
    if hold:
        dis = True
    pen = tgt.take("next_save_pen")
    impact.save_roll(tgt, src, dc, bonus, ctx.stake, adv=adv, dis=dis, own_adv=a1 or a2, own_dis=own_dis,
                     boosters=boosters, lift=lift, lifter=lifter, hold=hold, pen=pen)

    # 2. The roll, then rerolls: its own, then one ally's.
    if d20(adv, dis) + bonus + lift - (d(1, 4) if pen else 0) >= dc:
        return True
    if tgt.save_reroll(abil, dc, src, ctx):
        return True
    for g in tgt.allies():
        if g.ally_save_reroll(tgt, abil, dc, src, ctx):
            credit(g, "protect", ctx.stake)
            return True
    return False


# ----- damage ------------------------------------------------------------------------

def deal(tgt, dmg, src, ctx):
    """Apply a {type: amount} packet to tgt. Returns the damage it took."""
    if tgt.dead:
        return 0
    # 1. Intercepting Guard: an ally steps in and takes it, halved.
    if src and src.side != tgt.side and not ctx.intercepted:
        for g in tgt.allies():
            if g.intercept(tgt, dmg, src, ctx):
                credit(g, "protect", sum(max(0, n) for n in dmg.values()))
                tgt, ctx = g, replace(ctx, intercepted=True)
                break
    # 2. Flat reduction (Reinforced Plating), then resistance.
    before = sum(max(0, n) for n in dmg.values())
    dmg = tgt.reduce_damage(dict(dmg), src, ctx)
    tgt.mitigated += max(0, before - sum(max(0, n) for n in dmg.values()))
    out = {}
    for dtype, n in dmg.items():
        n = max(0, n)
        if ctx.intercepted or tgt.resists(dtype, ctx, impact.is_nonmagical(ctx, dtype)):
            tgt.mitigated += n - n // 2
            n //= 2
        out[dtype] = n
    # 3. Reactions: its own (Runic Bulwark), then allies' on its behalf.
    before = sum(out.values())
    out = tgt.damage_reaction(out, src, ctx)
    tgt.mitigated += max(0, before - sum(out.values()))
    for g in tgt.allies():
        before = sum(out.values())
        out = g.ally_damage_reaction(tgt, out, src, ctx)
        credit(g, "protect", before - sum(out.values()))
    total = sum(out.values())
    if total <= 0:
        return 0
    # 4. Temporary HP, then HP.
    room = tgt.hp + tgt.thp
    soak = min(tgt.thp, total)
    tgt.thp -= soak
    if tgt.thp_src is not tgt:
        credit(tgt.thp_src, "protect", soak)
    tgt.hp -= total - soak
    tgt.taken += total
    if src and src.side != tgt.side:
        src.dealt += total
        src.dealt_hp += min(total, room)
        src.on_damage_dealt(tgt, total, ctx)
    for w in tgt.fight.watchers:
        w.witness_damage(tgt, total, src)
    # 5. Going down (unless something holds it at 1 HP), or keeping concentration.
    if tgt.hp <= 0:
        savior = next((g for g in [tgt] + tgt.allies() if g.save_from_death(tgt)), None)
        if savior:
            if savior is not tgt:
                credit(savior, "protect", 1 - tgt.hp)   # the damage past 1 HP
            tgt.hp = 1
            return total
        tgt.hp = 0
        tgt.dead = True
        tgt.drop_conc()
        if src and src.side != tgt.side:
            src.kills += 1
            src.on_kill(tgt)
        return total
    if tgt.conc:
        dis = tgt.has("crash") or ctx.powder
        if d20(False, dis) + tgt.save_bonus("con") < max(10, total // 2):
            tgt.drop_conc()
    return total
