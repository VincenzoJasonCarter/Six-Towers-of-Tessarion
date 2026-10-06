// The Failed Prophet's mind: a Bayesian guess at what each hero will do next.
//
// Each hero gets two competing models of their turn:
//   habit    what they do in general: a Dirichlet over the five actions, seeded
//            with their subclass's usual shape and updated with every turn seen.
//   pattern  what they do after what they did last: one Dirichlet per previous
//            action, seeded with the habit model, so the two agree until the
//            hero's turns start depending on the turn before.
// The Prophet's forecast mixes the two, weighted by Bayes: each time a hero
// acts, each model is credited by how likely it said that action was.
//
// The whole fight is a list of events, and everything else (the minds, the
// round, the Echo Charges, the open prophecies) is rebuilt by replaying it, so
// undo is just dropping the last event.
(function (root) {
  "use strict";

  const ACTIONS = [
    { id: "strike", label: "Strike", hint: "melee weapon attack", omen: "will raise steel against me" },
    { id: "shoot", label: "Shoot", hint: "ranged weapon attack", omen: "will loose from afar" },
    { id: "cast", label: "Cast", hint: "attack or control spell", omen: "will reach into the Weave" },
    { id: "mend", label: "Mend", hint: "heal, buff or shield an ally", omen: "will tend another's thread" },
    { id: "guard", label: "Guard", hint: "dodge, dash, hold, anything else", omen: "will flinch, and hold" },
  ];
  const K = ACTIONS.length;

  // What the Prophet assumes before it has watched anyone: the usual shape of
  // each subclass's turn, in ACTIONS order (strike, shoot, cast, mend, guard).
  const SUBCLASSES = {
    verdant: { name: "Verdant Mage", shape: [0.05, 0.05, 0.55, 0.25, 0.10] },
    warbound: { name: "Warbound Mage", shape: [0.45, 0.05, 0.35, 0.05, 0.10] },
    stonewarden: { name: "Stonewarden Mage", shape: [0.10, 0.05, 0.45, 0.15, 0.25] },
    hellbound: { name: "Hellbound Mage", shape: [0.05, 0.05, 0.70, 0.05, 0.15] },
    sanguine_mage: { name: "Sanguine Mage", shape: [0.05, 0.05, 0.55, 0.25, 0.10] },
    aether: { name: "Aether Mage", shape: [0.05, 0.05, 0.35, 0.45, 0.10] },
    sanguine_aegis: { name: "Sanguine Aegis", shape: [0.70, 0.05, 0.05, 0.10, 0.10] },
    bulwark: { name: "Bulwark Aegis", shape: [0.50, 0.05, 0.05, 0.05, 0.35] },
    warden: { name: "Warden Aegis", shape: [0.55, 0.05, 0.05, 0.05, 0.30] },
    crystal_archer: { name: "Crystal Archer", shape: [0.05, 0.75, 0.05, 0.05, 0.10] },
    gunman: { name: "Gunman", shape: [0.10, 0.70, 0.05, 0.05, 0.10] },
    unknown: { name: "Unknown", shape: [0.20, 0.20, 0.20, 0.20, 0.20] },
  };

  const DEFAULTS = {
    priorStrength: 4,   // how many turns' worth of trust the subclass shape gets
    memory: 0.9,        // each new turn, older evidence is multiplied by this (1 = never forgets)
    patternPrior: 0.35, // starting belief that a hero's turns follow on from each other
    threshold: 0.4,     // the Prophet stays silent unless some forecast is at least this sure
    perRound: 1,        // prophecies spoken each round
    rewindCost: 3,      // Echo Charges spent to unmake the last hero action
    reveal: "target",   // "target": players hear who; "full": players hear who and what
  };

  // A little doubt is kept so neither model can be ruled out for good.
  const DOUBT = 0.02;

  const zeros = () => new Array(K).fill(0);
  const normalize = (xs) => {
    const z = xs.reduce((a, b) => a + b, 0);
    return xs.map((x) => x / z);
  };

  function freshMind(hero, cfg) {
    const shape = (SUBCLASSES[hero.subclass] || SUBCLASSES.unknown).shape;
    return {
      prior: shape.map((p) => p * cfg.priorStrength),
      habit: zeros(),
      pattern: ACTIONS.map(zeros),
      last: null,
      weights: [1 - cfg.patternPrior, cfg.patternPrior],
      seen: 0,
    };
  }

  function habitOdds(m) {
    return normalize(m.prior.map((p, i) => p + m.habit[i]));
  }

  function patternOdds(m, cfg) {
    const base = habitOdds(m);
    if (m.last === null) return base;
    const row = m.pattern[m.last];
    return normalize(base.map((p, i) => p * cfg.priorStrength + row[i]));
  }

  function forecast(m, cfg) {
    const h = habitOdds(m);
    const p = patternOdds(m, cfg);
    return h.map((x, i) => m.weights[0] * x + m.weights[1] * p[i]);
  }

  function observe(m, a, cfg) {
    const h = habitOdds(m);
    const p = patternOdds(m, cfg);
    const w = normalize([m.weights[0] * h[a], m.weights[1] * p[a]]);
    m.weights = w.map((x) => x * (1 - DOUBT) + DOUBT / 2);
    m.habit = m.habit.map((c) => c * cfg.memory);
    m.habit[a] += 1;
    m.pattern = m.pattern.map((row) => row.map((c) => c * cfg.memory));
    if (m.last !== null) m.pattern[m.last][a] += 1;
    m.last = a;
    m.seen += 1;
  }

  // The Prophet speaks about whoever it reads most clearly.
  function choose(heroes, minds, cfg) {
    const picks = [];
    for (const hero of heroes) {
      if (hero.down) continue;
      const odds = forecast(minds[hero.id], cfg);
      let best = 0;
      for (let i = 1; i < K; i++) if (odds[i] > odds[best]) best = i;
      if (odds[best] >= cfg.threshold) picks.push({ hero: hero.id, action: best, p: odds[best] });
    }
    picks.sort((x, y) => y.p - x.p);
    return picks.slice(0, cfg.perRound);
  }

  // Rebuild everything from the event list. Events:
  //   {t: "round", prophecies: [{hero, action, p}]}  a new round and what was foretold for it
  //   {t: "act", hero, action}                        a hero's main action on their turn
  //   {t: "rewind"}                                   charges spent to unmake the last action
  //   {t: "fight"}                                    a new fight; the Prophet remembers what it learned
  function replay(state) {
    const cfg = { ...DEFAULTS, ...state.config };
    const minds = {};
    for (const hero of state.heroes) minds[hero.id] = freshMind(hero, cfg);
    const out = {
      cfg, minds, fight: 1, round: 0, charges: 0, prophecies: [], log: [],
      stats: { spoken: 0, fulfilled: 0, rewinds: 0 },
      lastAct: null,
    };
    const closeRound = () => {
      for (const pr of out.prophecies) {
        if (pr.status === "pending") {
          pr.status = "broken";
          out.log.push({ kind: "broken", hero: pr.hero, action: pr.action, p: pr.p, idle: true });
        }
      }
    };

    state.events.forEach((ev, index) => {
      if (ev.t === "round") {
        closeRound();
        out.round += 1;
        out.prophecies = ev.prophecies
          .filter((pr) => minds[pr.hero])
          .map((pr) => ({ ...pr, status: "pending" }));
        out.stats.spoken += out.prophecies.length;
        out.log.push({ kind: "round", round: out.round, prophecies: out.prophecies.map((pr) => ({ ...pr })) });
      } else if (ev.t === "act") {
        const m = minds[ev.hero];
        if (!m) return;
        const odds = forecast(m, cfg);
        observe(m, ev.action, cfg);
        out.lastAct = { hero: ev.hero, action: ev.action, index };
        out.log.push({ kind: "act", hero: ev.hero, action: ev.action, p: odds[ev.action] });
        const pr = out.prophecies.find((x) => x.hero === ev.hero && x.status === "pending");
        if (pr) {
          pr.status = pr.action === ev.action ? "fulfilled" : "broken";
          if (pr.status === "fulfilled") {
            out.charges += 1;
            out.stats.fulfilled += 1;
          }
          out.log.push({ kind: pr.status, hero: pr.hero, action: pr.action, p: pr.p, did: ev.action });
        }
      } else if (ev.t === "rewind") {
        out.charges -= cfg.rewindCost;
        out.stats.rewinds += 1;
        out.log.push({ kind: "rewind", undone: out.lastAct && { hero: out.lastAct.hero, action: out.lastAct.action } });
        out.lastAct = null;
      } else if (ev.t === "fight") {
        closeRound();
        out.fight += 1;
        out.round = 0;
        out.charges = 0;
        out.prophecies = [];
        out.lastAct = null;
        out.log.push({ kind: "fight", fight: out.fight });
      }
    });
    return out;
  }

  // The event that starts the next round, with the Prophet's picks for it.
  function nextRound(state) {
    const view = replay(state);
    return { t: "round", prophecies: choose(state.heroes, view.minds, view.cfg) };
  }

  const api = { ACTIONS, SUBCLASSES, DEFAULTS, freshMind, habitOdds, patternOdds, forecast, observe, choose, replay, nextRound };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Prophet = api;
})(typeof window !== "undefined" ? window : globalThis);
