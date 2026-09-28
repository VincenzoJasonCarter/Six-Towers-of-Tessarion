// DATA and LIVE come from the inline script in template.html, which core.py fills in.

const KINDS = { all: "All", creature: "Creatures", rumour: "Rumoured", figure: "Factions & Figures" };
const CATEGORY = {
  minion: "Minion", elite: "Elite", brute: "Brute", boss: "Boss", mini_boss: "Mini-boss",
  legendary_boss: "Legendary", hazard_unit: "Hazard unit", encounter_mechanic: "Encounter hazard",
  obstacle: "Obstacle",
};
const ATTACK = {
  melee_weapon: "Melee Weapon Attack", ranged_weapon: "Ranged Weapon Attack",
  ranged_spell: "Ranged Spell Attack", ranged: "Ranged Attack", melee_unarmed: "Melee Unarmed Attack",
};
const ABILS = ["str", "dex", "con", "int", "wis", "cha"];

const entries = DATA.entries;
const byId = Object.fromEntries(entries.map(e => [e.id, e]));
const state = { q: "", kind: "all", animate: storage("bestiary.animate") !== "off" };

/* ---------- helpers ---------- */
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const text = s => esc(s).replace(/█+/g, m => `<span class="redact" title="Redacted">${m}</span>`);
const label = k => k.replace(/_/g, " ").replace(/^\w/, c => c.toUpperCase());
const cap = s => String(s).charAt(0).toUpperCase() + String(s).slice(1);
const signed = n => (typeof n === "number" && n >= 0 ? "+" : "") + n;
const mod = score => signed(Math.floor((score - 10) / 2));
const REGION_HUE = { Crownweave: 38, Skyloom: 205, Northreach: 12, Emberweave: 28, Stormwake: 185, "Thal'vireth": 140 };
const regionTop = e => (e.region || "Unplaced").split("·")[0].trim();
const paras = s => String(s || "").split(/\n+/).filter(Boolean);

function value(v) {
  if (v == null) return '<span class="muted">—</span>';
  if (Array.isArray(v)) return v.length ? `<ul>${v.map(x => `<li>${value(x)}</li>`).join("")}</ul>` : "none";
  if (typeof v === "object")
    return `<dl class="kv">${Object.entries(v).map(([k, x]) => `<dt>${esc(label(k))}</dt><dd>${value(x)}</dd>`).join("")}</dl>`;
  if (typeof v === "string" && byId[v] && v.includes("_")) return link(v);
  return text(v);
}
const link = id => byId[id] ? `<a href="#${esc(id)}">${esc(byId[id].name)}</a>` : esc(id);
const section = (title, body) => body ? `<h4>${esc(title)}</h4>${body}` : "";
const listOf = arr => arr && arr.length ? `<ul>${arr.map(x => `<li>${value(x)}</li>`).join("")}</ul>` : "";

function storage(key, val) {
  try {
    if (val === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, val);
  } catch (_) { return null; }
}

/* ---------- search + list ---------- */
function haystack(e) {
  const l = e.lore || {};
  return [e.name, e.local_name, ...(e.aliases || []), e.region, e.faction, e.type,
    l.classification, l.habitat, l.entry, ...(l.field_notes || [])].filter(Boolean).join(" ").toLowerCase();
}
entries.forEach(e => { e._hay = haystack(e); });

function visible() {
  const words = state.q.toLowerCase().split(/\s+/).filter(Boolean);
  return entries.filter(e => (state.kind === "all" || e.kind === state.kind) && words.every(w => e._hay.includes(w)));
}

function grouped(list) {
  const groups = new Map();
  for (const e of list) {
    const r = regionTop(e);
    if (!groups.has(r)) groups.set(r, []);
    groups.get(r).push(e);
  }
  return groups;
}

const tabs = () => Object.entries(KINDS)
  .map(([k, v]) => `<button type="button" data-kind="${k}" aria-pressed="${state.kind === k}">${v}</button>`).join("");

function initials(name) {
  const core = name.split(/:\s*/).pop().split(/\s*[,/]\s*/)[0].replace(/^The\s+/i, "");
  return core.split(/[\s-]+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join("");
}

function hue(e) {
  const r = regionTop(e);
  if (r in REGION_HUE) return REGION_HUE[r];
  return [...r].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 0);
}

// images/<id>.png (or .jpg/.webp/...) replaces the placeholder automatically.
function avatar(e) {
  const inner = e.image
    ? `<img src="${esc(e.image)}" alt="" loading="lazy">`
    : `<span aria-hidden="true">${esc(initials(e.name))}</span>`;
  return `<div class="avatar ${e.kind}" style="--h:${hue(e)}">${inner}</div>`;
}

/* ---------- front page ---------- */
function renderFront() {
  const list = visible();
  const counts = Object.keys(KINDS).slice(1).map(k => `${entries.filter(e => e.kind === k).length} ${KINDS[k].toLowerCase()}`).join(" · ");
  let h = `<div class="front"><div class="intro">
    <p class="tier">THREADMINT LIBRARY · ACCESS TIER: RESTRICTED</p>
    <h1>A Register of Hostile Things</h1>
    <p>Compiled from Watch reports, Loomwarden incident summaries, Crucible filings and the testimony of those who lived to give it.
    Entries marked <i>Rumoured</i> rest on accounts the Library has been unable to confirm. Where the record has been redacted, the redaction is preserved.</p>
    <p class="tier">${counts}</p></div>
    <div class="tabs">${tabs()}</div>`;
  for (const [region, items] of grouped(list)) {
    h += `<h2>${esc(region)}</h2><div class="cards">`;
    h += items.map(e => `<a class="card${e.id === openId ? " lifted" : ""}" href="#${esc(e.id)}" data-id="${esc(e.id)}">${avatar(e)}<div class="body">
      <b>${esc(e.name)}</b><small>${esc((e.lore || {}).classification || "")}</small>
      ${e.category ? `<span class="chip cat">${esc(CATEGORY[e.category] || label(e.category))}</span>` : ""}
      ${e.kind === "rumour" ? `<span class="chip">Rumoured</span>` : ""}</div></a>`).join("");
    h += `</div>`;
  }
  if (!list.length) h += '<p class="empty">Nothing in the register matches.</p>';
  return h + "</div>";
}

/* ---------- stat blocks ---------- */
function speed(s) {
  if (s == null || typeof s !== "object") return text(s);
  return Object.entries(s).filter(([k]) => k !== "hover")
    .map(([k, v]) => (k === "walk" ? "" : k + " ") + v + " ft." + (k === "fly" && s.hover ? " (hover)" : "")).join(", ");
}
const saves = o => Object.entries(o).map(([k, v]) => `${cap(k)} ${signed(v)}`).join(", ");
const dc = o => typeof o === "object" ? `DC ${o.dc} ${cap(o.ability)}` : text(o);

function damage(d) {
  if (typeof d === "object") return Object.entries(d).map(([k, v]) => `${esc(label(k))}: ${esc(v)}`).join("; ");
  return esc(d);
}

function action(a) {
  let h = `<p class="act"><b><i>${esc(a.name)}</i>${a.recharge ? ` (Recharge ${esc(a.recharge)})` : ""}.</b> `;
  const bits = [];
  if (a.to_hit != null) bits.push(`${signed(a.to_hit)} to hit`);
  if (a.reach_ft != null) bits.push(`reach ${esc(a.reach_ft)} ft.`);
  if (a.range_ft != null) bits.push(`range ${esc(a.range_ft)} ft.`);
  if (a.targets != null) bits.push(a.targets === 1 ? "one target" : esc(a.targets) + (typeof a.targets === "number" ? " targets" : ""));
  if (a.kind) h += `<i>${esc(ATTACK[a.kind] || label(a.kind))}:</i> `;
  if (bits.length) h += bits.join(", ").replace(/\.?$/, ". ");
  if (a.area) h += `<i>Area:</i> ${esc(a.area)}. `;
  if (a.damage) h += `<i>Hit:</i> ${damage(a.damage)}${a.damage_type ? " " + esc(a.damage_type) + " damage" : ""}. `;
  if (a.save) h += `${dc(a.save)} saving throw. `;
  for (const [k, t] of [["on_fail", "On a failure"], ["on_success", "On a success"], ["effect", ""], ["description", ""], ["note", "Note"]])
    if (a[k]) h += (t ? `<i>${t}:</i> ` : "") + text(a[k]) + " ";
  return h + "</p>";
}

const V_DONE = new Set(["label", "source", "count", "role", "ac", "ac_note", "hp", "hp_note", "hit_dice", "speed",
  "abilities", "saving_throws", "damage_vulnerabilities", "damage_resistances", "weaknesses", "vulnerabilities_note",
  "attack_bonus", "save_dc", "primary_weapon", "position", "items", "combat_objective", "traits", "actions",
  "reactions", "special_mechanic", "phases", "tactics", "dm_tips"]);

function statBlock(v) {
  const row = (k, val) => !val ? "" : `<p class="row"><b>${k}</b> ${val}</p>`;
  let h = v.source ? `<p class="src">${esc(v.source)}</p>` : "";
  h += row("Role", v.role && text(v.role));
  h += row("Count", v.count != null && esc(v.count));
  h += row("Armor Class", v.ac != null && esc(v.ac) + (v.ac_note ? ` (${esc(v.ac_note)})` : ""));
  h += row("Hit Points", v.hp != null ? esc(v.hp) + (v.hit_dice ? ` (${esc(v.hit_dice)})` : "") : v.hp_note && text(v.hp_note));
  h += row("Speed", v.speed != null && speed(v.speed));
  if (v.abilities) {
    h += `<hr><div class="abil">${ABILS.map(a => `<div><b>${a.toUpperCase()}</b>${v.abilities[a] ?? "—"}${v.abilities[a] != null ? ` (${mod(v.abilities[a])})` : ""}</div>`).join("")}</div><hr>`;
  }
  h += row("Saving Throws", v.saving_throws && saves(v.saving_throws));
  h += row("Damage Vulnerabilities", v.damage_vulnerabilities?.length && esc(v.damage_vulnerabilities.join(", ")));
  h += row("Damage Resistances", v.damage_resistances?.length && esc(v.damage_resistances.join(", ")));
  h += row("Weaknesses", v.weaknesses && text(v.weaknesses));
  h += row("Vulnerability", v.vulnerabilities_note && text(v.vulnerabilities_note));
  h += row("Attack Bonus", v.attack_bonus != null && signed(v.attack_bonus));
  h += row("Save DC", v.save_dc && dc(v.save_dc));
  h += row("Primary Weapon", v.primary_weapon && text(v.primary_weapon));
  h += row("Position", v.position && text(v.position));
  h += row("Items", v.items && esc(v.items.join(", ")));
  h += row("Objective", v.combat_objective && text(v.combat_objective));
  if (v.traits?.length) h += `<h5>Traits</h5>` + v.traits.map(t => `<p class="act"><b><i>${esc(t.name)}.</i></b> ${t.description ? text(t.description) : ""}</p>`).join("");
  if (v.actions?.length) h += `<h5>Actions</h5>` + v.actions.map(action).join("");
  if (v.reactions?.length) h += `<h5>Reactions</h5>` + v.reactions.map(r => `<p class="act"><b><i>${esc(r.name)}.</i></b> ${r.trigger ? `<i>Trigger:</i> ${text(r.trigger)} ` : ""}${text(r.effect || "")}</p>`).join("");
  if (v.special_mechanic) {
    const m = v.special_mechanic, o = m.objects;
    h += `<h5>${esc(m.name || "Special Mechanic")}</h5><p class="act">${o ? `<i>${esc(o.count)} object${o.count === 1 ? "" : "s"}, AC ${esc(o.ac)}, HP ${esc(o.hp)}.</i> ` : ""}${text(m.effect || "")}</p>`;
  }
  if (v.phases?.length) h += `<h5>Phases</h5>` + v.phases.map(p => `<p class="act"><b><i>Phase ${esc(p.phase)}.</i></b> ${text(p.description)}</p>`).join("");
  if (v.tactics) h += `<h5>Tactics</h5><p>${text(v.tactics)}</p>`;
  if (v.dm_tips) h += `<h5>DM Tips</h5><p>${text(v.dm_tips)}</p>`;
  for (const [k, x] of Object.entries(v)) if (!V_DONE.has(k)) h += `<h5>${esc(label(k))}</h5>${value(x)}`;
  return h;
}

/* ---------- DM panel ---------- */
const E_DONE = new Set(["kind", "_hay", "id", "name", "local_name", "aliases", "category", "faction", "type", "size",
  "description", "region", "lore", "versions", "appearances", "dm_tips", "notes", "trivia", "loot", "theme",
  "mechanics", "opening_line", "raw_note", "interpreted", "role", "race_class", "combat_notes", "quirks",
  "applies_to", "see_also", "effect", "counterplay", "encounter_mechanics", "encounter_options_for_players",
  "social_encounter", "offer"]);

function dmPanel(e) {
  let h = `<section class="dm" aria-label="DM material"><h2>For the DM</h2>`;
  const facts = [e.type, e.size, e.race_class].filter(Boolean).map(esc).join(" · ");
  if (facts) h += `<p><b>${facts}</b></p>`;
  if (e.role) h += `<p><i>Role:</i> ${text(e.role)}</p>`;
  if (e.theme) h += `<p><i>Theme:</i> ${text(e.theme)}</p>`;
  h += section("At the table", e.description && `<p>${text(e.description)}</p>`);
  h += section("Opening line", e.opening_line && `<p><i>${text(e.opening_line)}</i></p>`);
  h += section("Combat", e.combat_notes && `<p>${text(e.combat_notes)}</p>`);
  h += section("Effect", e.effect && `<p>${text(e.effect)}</p>`);
  h += section("Applies to", e.applies_to && `<p>${e.applies_to.map(link).join(", ")}</p>`);
  h += section("Mechanics", e.mechanics && e.mechanics.map(m => `<p><b>${esc(m.name)}.</b> ${text(m.description || "")}</p>`).join(""));
  h += section("Original note", e.raw_note && `<p><i>${text(e.raw_note)}</i></p>`);
  h += section("Read as", listOf(e.interpreted));
  h += section("Offer", e.offer && `<p>${text(e.offer)}</p>`);
  h += section("Quirks", listOf(e.quirks));

  if (e.versions?.length) {
    const vtabs = e.versions.map((v, i) => `<button type="button" role="tab" data-v="${i}" aria-selected="${i === 0}">${esc(v.label || "Version " + (i + 1))}</button>`).join("");
    const blocks = e.versions.map((v, i) => `<div class="statblock" role="tabpanel" data-v="${i}"${i ? " hidden" : ""}>${statBlock(v)}</div>`).join("");
    h += `<h4>Stat block${e.versions.length > 1 ? "s" : ""}</h4>`;
    h += e.versions.length > 1 ? `<div class="vtabs" role="tablist">${vtabs}</div>${blocks}` : blocks.replace('class="statblock"', 'class="statblock" style="border-radius:6px"');
  }

  h += section("DM tips", e.dm_tips && `<p>${text(e.dm_tips)}</p>`);
  h += section("Encounter mechanics", e.encounter_mechanics && value(e.encounter_mechanics));
  h += section("Player options", listOf(e.encounter_options_for_players));
  h += section("Counterplay", listOf(e.counterplay));
  h += section("Social encounter", listOf(e.social_encounter));
  h += section("Loot", e.loot && value(e.loot));
  h += section("Trivia", listOf(e.trivia));
  h += section("See also", e.see_also && `<p>${link(e.see_also)}</p>`);
  for (const [k, x] of Object.entries(e)) if (!E_DONE.has(k)) h += section(label(k), value(x));
  h += section("Notes & source contradictions", e.notes?.length && `<ul>${e.notes.map(n => `<li class="flag">${text(n)}</li>`).join("")}</ul>`);
  return h + "</section>";
}

/* ---------- entry ---------- */
function renderEntry(e) {
  const l = e.lore || {};
  const alt = [e.local_name, ...(e.aliases || [])].filter(a => a && a !== e.name);
  let h = `<article class="entry">`;
  h += `<div class="entry-head">${avatar(e)}<div>`;
  h += `<p class="kicker">${esc(e.region || "Unplaced")}</p><h1 id="rv-title">${esc(e.name)}</h1>`;
  if (alt.length) h += `<p class="aka">Also called ${alt.map(a => `<i>${esc(a)}</i>`).join(", ")}</p>`;
  h += `<div class="meta">`;
  if (l.classification) h += `<span class="chip">${esc(l.classification)}</span>`;
  if (e.kind === "rumour") h += `<span class="chip">Rumoured</span>`;
  if (e.faction) h += `<span class="chip">${esc(e.faction)}</span>`;
  if (e.category) h += `<span class="chip cat">${esc(CATEGORY[e.category] || label(e.category))}</span>`;
  h += `</div></div></div>`;
  if (l.habitat) h += `<p class="habitat"><b>Found</b>${text(l.habitat)}</p>`;
  h += l.entry
    ? `<div class="lore">${paras(l.entry).map(p => `<p>${text(p)}</p>`).join("")}</div>`
    : `<p class="empty">The Library holds no account of this entry yet.</p>`;
  for (const n of l.field_notes || []) {
    const cut = n.lastIndexOf(" — ");
    const [q, who] = cut > 0 ? [n.slice(0, cut), n.slice(cut + 3)] : [n, ""];
    h += `<blockquote class="note">${text(q)}${who ? `<cite>— ${text(who)}</cite>` : ""}</blockquote>`;
  }
  h += dmPanel(e);

  const { prev, next } = neighbours(e);
  h += `<nav class="pager">${prev ? `<a href="#${esc(prev.id)}">← ${esc(prev.name)}</a>` : "<span></span>"}${next ? `<a href="#${esc(next.id)}">${esc(next.name)} →</a>` : ""}</nav>`;
  return h + "</article>";
}

// The entries either side of e, in the order the grid shows them.
function neighbours(e) {
  const list = [...grouped(visible().some(x => x.id === e.id) ? visible() : entries).values()].flat();
  const i = list.findIndex(x => x.id === e.id);
  return { prev: list[i - 1], next: list[i + 1] };
}

// The back of the card: a bar in the region's colour, then the whole entry.
function cardBack(e) {
  const { prev, next } = neighbours(e);
  const step = (x, d, t) => x
    ? `<a class="rv-step" href="#${esc(x.id)}" title="${esc(x.name)}" aria-label="${t}: ${esc(x.name)}">${d}</a>`
    : `<span class="rv-step" aria-hidden="true">${d}</span>`;
  return `<div class="rv-bar"><a class="rv-close" href="#">← All entries</a>
    <label class="switch"><input type="checkbox" class="dm-box"${document.body.classList.contains("dm-on") ? " checked" : ""}> DM material</label>
    <span class="rv-steps">${step(prev, "‹", "Previous")}${step(next, "›", "Next")}</span></div>
    <div class="rv-scroll">${renderEntry(e)}</div>`;
}

/* ---------- routing ---------- */
const currentEntry = () => byId[decodeURIComponent(location.hash.slice(1))];
const errorBanner = () => DATA.error ? `<div class="error">${esc(DATA.error)}\n\nFix the file and save; this page reloads itself.</div>` : "";

function render() {
  document.getElementById("main").innerHTML = errorBanner() + renderFront();
}

/* ---------- turning a card over ----------
   Clicking a card lifts it out of the grid and, in one movement, flies it to
   the middle of the screen while turning it over; its back grows into the full
   entry as the turn finishes. Closing runs the same film backwards into its
   gap. The clone that flies is the "flyer"; the entry (.rv-card) takes over
   from it at the moment both are edge-on in the middle of the screen, starting
   shrunk to the flyer's height. The flight slows as it arrives while the turn
   speeds up, so the card is edge-on just as it gets there and the turn carries
   straight on at the same speed. */
const $ = s => document.querySelector(s);
const reveal = $("#reveal"), rvCard = $(".rv-card"), rvBg = $(".rv-backdrop");
const P = "perspective(1600px) ";
let openId = null;  // the entry on the table (or on its way there)
let anims = [];
let seq = 0;        // bumped by every open/close/turn, so a superseded one stops
const motionOK = () => state.animate && "animate" in Element.prototype;

function run(el, frames, ms, easing, delay = 0) {
  const a = el.animate(frames, { duration: ms, delay, easing, fill: "forwards" });
  anims.push(a);
  return a.finished;
}

// Stop whatever is playing. A cancelled animation rejects, which ends the
// open/close/turn that was waiting on it.
function settle() {
  seq++;
  anims.forEach(a => a.cancel());
  anims = [];
  document.querySelectorAll(".flyer").forEach(f => f.remove());
}

// Put the page in its resting state with e on the table, or none.
function setOpen(e) {
  openId = e ? e.id : null;
  reveal.hidden = !e;
  rvCard.style.visibility = "";
  document.body.classList.toggle("revealing", !!e);
  $(".top").inert = $("#main").inert = !!e;
  document.querySelectorAll(".card").forEach(c => c.classList.toggle("lifted", c.dataset.id === openId));
  document.title = e ? `${e.name} · Threadmint Bestiary` : "Threadmint Bestiary";
  if (e) {
    rvCard.style.setProperty("--h", hue(e));
    rvCard.innerHTML = cardBack(e);
    $(".rv-scroll").scrollTop = 0;
  }
}

const gridCard = id => document.querySelector(`.card[data-id="${CSS.escape(id)}"]`);

// Curves over t = 0..1. in/out are matched (both end or start at twice the
// average speed), so an in-turn followed by an out-turn of the same length
// looks like one turn.
const EASE = {
  in: t => t * t,
  out: t => 1 - (1 - t) ** 2,
  out3: t => 1 - (1 - t) ** 3,
  inOut: t => t < .5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2,
};
// Keyframes sampled from f(t), so the movement, size and turn in one transform
// can each follow their own curve. Play them with linear easing.
const film = (f, n = 30) => Array.from({ length: n + 1 }, (_, i) => ({ transform: f(i / n), offset: i / n }));

// The card's place on the grid, and how to get it to the middle of the screen
// at reading size: move m (0..1 of the way there) turned a degrees. k shrinks
// the open entry to the height of the card in the middle.
function flight(card) {
  const r = card.getBoundingClientRect();
  const s = Math.min(innerHeight * .6 / r.height, innerWidth * .8 / r.width, 2.4);
  const dx = innerWidth / 2 - (r.left + r.width / 2), dy = innerHeight / 2 - (r.top + r.height / 2);
  return {
    r, k: r.height * s / rvCard.getBoundingClientRect().height,
    at: (m, a) => `translate(${dx * m}px, ${dy * m}px) ${P}scale(${1 + (s - 1) * m}) rotateY(${a}deg)`,
  };
}
const entryAt = (sc, a) => `${P}scale(${sc}) rotateY(${a}deg)`;
const FLY = 500;  // each half of the turn, ms

function makeFlyer(card, r) {
  const f = card.cloneNode(true);
  f.className = "card flyer";
  f.removeAttribute("href");
  f.setAttribute("aria-hidden", "true");
  Object.assign(f.style, { left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px" });
  document.body.append(f);
  return f;
}

async function openCard(e) {
  settle();
  const my = seq, card = gridCard(e.id);
  setOpen(e);
  try {
    if (!motionOK()) {
      // no animation
    } else if (!card) {  // opened from a link, or filtered out of the grid
      await Promise.all([
        run(rvBg, [{ opacity: 0 }, { opacity: 1 }], 250, "ease"),
        run(rvCard, [{ transform: "scale(.94)", opacity: 0 }, { transform: "none", opacity: 1 }], 280, "cubic-bezier(.2, .7, .3, 1)"),
      ]);
    } else {
      const { r, k, at } = flight(card);
      const flyer = makeFlyer(card, r);
      rvCard.style.visibility = "hidden";
      run(rvBg, [{ opacity: 0 }, { opacity: 1 }], FLY, "ease");
      await run(flyer, film(t => at(EASE.out3(t), 90 * EASE.in(t))), FLY, "linear");
      flyer.remove();
      rvCard.style.visibility = "";
      await run(rvCard, film(t => entryAt(k + (1 - k) * EASE.inOut(t), -90 * (1 - EASE.out(t)))), FLY, "linear");
    }
  } catch (_) {
    return;  // superseded
  }
  if (my !== seq) return;
  settle();
  focusCard();
}

async function closeCard() {
  const id = openId;
  if (!id) return;
  settle();
  const my = seq, card = gridCard(id);
  openId = null;
  try {
    if (!motionOK()) {
      // no animation
    } else if (!card) {
      await Promise.all([
        run(rvCard, [{ transform: "none", opacity: 1 }, { transform: "scale(.94)", opacity: 0 }], 220, "ease-in"),
        run(rvBg, [{ opacity: 1 }, { opacity: 0 }], 240, "ease"),
      ]);
    } else {
      const { r, k, at } = flight(card);
      const CLOSE = FLY * .85;
      await run(rvCard, film(t => entryAt(1 - (1 - k) * EASE.inOut(t), -90 * EASE.in(t))), CLOSE, "linear");
      rvCard.style.visibility = "hidden";
      const flyer = makeFlyer(card, r);
      await Promise.all([
        run(flyer, film(t => at(1 - EASE.inOut(t), 90 * (1 - EASE.out(t)))), CLOSE, "linear"),
        run(rvBg, [{ opacity: 1 }, { opacity: 0 }], CLOSE, "ease"),
      ]);
    }
  } catch (_) {
    return;  // superseded
  }
  if (my !== seq) return;
  settle();
  setOpen(null);
  if (card) card.focus({ preventScroll: true });
}

// Prev/next, or a link to another entry: turn the card over to the new one.
async function turnCard(e) {
  settle();
  const my = seq;
  try {
    if (motionOK()) await run(rvCard, [{ transform: P + "rotateY(0deg)" }, { transform: P + "rotateY(90deg)" }], 200, "cubic-bezier(.55, 0, 1, .45)");
    setOpen(e);
    if (motionOK()) await run(rvCard, [{ transform: P + "rotateY(-90deg)" }, { transform: P + "rotateY(0deg)" }], 280, "cubic-bezier(0, .55, .45, 1)");
  } catch (_) {
    return;  // superseded
  }
  if (my !== seq) return;
  settle();
  focusCard();
}

function focusCard() {
  const c = $(".rv-close");
  if (c) c.focus({ preventScroll: true });
}

window.addEventListener("hashchange", () => {
  const e = currentEntry();
  if (e && e.id === openId) return;
  if (e) (reveal.hidden || !openId ? openCard : turnCard)(e);
  else closeCard();
});
// Clicking the dimmed table around the card puts it back.
rvBg.addEventListener("click", () => { location.hash = ""; });

const qBox = document.getElementById("q");
qBox.addEventListener("input", () => {
  state.q = qBox.value;
  render();
});
document.addEventListener("click", ev => {
  const b = ev.target.closest(".tabs button[data-kind]");
  if (!b) return;
  state.kind = b.dataset.kind;
  render();
});
rvCard.addEventListener("click", ev => {
  const b = ev.target.closest(".vtabs button");
  if (!b) return;
  const dm = b.closest(".dm");
  dm.querySelectorAll(".vtabs button").forEach(x => x.setAttribute("aria-selected", x === b));
  dm.querySelectorAll(".statblock").forEach(x => { x.hidden = x.dataset.v !== b.dataset.v; });
});
document.addEventListener("keydown", ev => {
  if (!openId || ev.altKey || ev.ctrlKey || ev.metaKey) return;
  if (ev.key === "Escape") { ev.preventDefault(); location.hash = ""; return; }
  if (ev.target.closest("input, textarea, select")) return;
  const step = { ArrowLeft: "prev", ArrowRight: "next" }[ev.key];
  const to = step && neighbours(byId[openId])[step];
  if (to) { ev.preventDefault(); location.hash = to.id; }
});

// The DM switch is in the top bar and on the card; they move together.
function setDM(on) {
  document.body.classList.toggle("dm-on", on);
  document.querySelectorAll(".dm-box").forEach(b => { b.checked = on; });
  storage("bestiary.dm", on ? "on" : "off");
}
document.addEventListener("change", ev => {
  if (ev.target.matches(".dm-box")) setDM(ev.target.checked);
  if (ev.target.id === "animate") {
    state.animate = ev.target.checked;
    storage("bestiary.animate", state.animate ? "on" : "off");
  }
});
setDM(storage("bestiary.dm") !== "off");
document.getElementById("animate").checked = state.animate;

// Live mode: reload when enemies.yaml / template / images change, keeping
// the search, tab and scroll position across the reload.
let place = null;
try {
  place = JSON.parse(sessionStorage.getItem("bestiary.place"));
  sessionStorage.removeItem("bestiary.place");
} catch (_) {}
if (place) {
  state.q = qBox.value = place.q || "";
  state.kind = place.kind in KINDS ? place.kind : "all";
}
render();
if (place) window.scrollTo(0, place.y || 0);
if (currentEntry()) { setOpen(currentEntry()); settle(); }

if (LIVE) {
  setInterval(async () => {
    try {
      const { version } = await (await fetch("/version", { cache: "no-store" })).json();
      if (version === DATA.version) return;
      try { sessionStorage.setItem("bestiary.place", JSON.stringify({ q: state.q, kind: state.kind, y: window.scrollY })); } catch (_) {}
      location.reload();
    } catch (_) { /* server stopped or restarting; try again next tick */ }
  }, 1500);
}
