// DATA and LIVE come from the inline script in template.html, which core.py fills in.

const $ = s => document.querySelector(s);
const items = DATA.items;
const byId = Object.fromEntries(items.map(i => [i.id, i]));
const byName = Object.fromEntries(items.map(i => [i.name, i]));

// The market's aisles, in the order they stand, each under a numbered sign
// (`sign` is what the sign says is down it). An item goes to the first aisle
// that takes its kind; a kind no aisle takes ends up in "Other", at the end.
const AISLES = [
  { id: "arms", name: "Arms", kinds: ["weapon", "ammunition"], sign: "Blades · Bows · Guns · Shot",
    blurb: "Blades, bows, clubs and the arrows to go with them." },
  { id: "armour", name: "Armour & Shields", kinds: ["shield", "armor"], sign: "Shields · Coats · Hoods · Boots",
    blurb: "Things to stand behind, and things to wear." },
  { id: "provisions", name: "Provisions", kinds: ["utility"], sign: "Rations · Rope · Light",
    blurb: "Food, rope and fire for the road." },
  { id: "stock", name: "Raw Stock", kinds: ["material"], sign: "Ingots · Timber · Hide · Cord",
    blurb: "What the crafting codices build everything else from." },
  { id: "workshop", name: "The Workshop", kinds: ["tool", "service"], untiered: "Tools & Hire", sign: "Tools · Forge hire",
    blurb: "The tools every recipe in the Crafting Book asks for, and a forge by the day." },
];
const OTHER = { id: "other", name: "Other", kinds: [], sign: "Odds & ends", blurb: "" };
const aisleOf = item => AISLES.find(s => s.kinds.includes(item.kind)) || OTHER;
// The aisles with anything in them, numbered as they stand.
const aisles = [...AISLES, OTHER].filter(s => items.some(i => aisleOf(i) === s));
aisles.forEach((s, n) => { s.n = n + 1; });
const EMOJI = { weapon: "🗡️", ammunition: "🏹", shield: "🛡️", armor: "🧥", utility: "🎒", material: "📦", tool: "🔨", service: "🔥" };

// Ch.9, Economy of Tessarion: the Guild's coins against the Trade Unit, how
// a total is rounded at a Guild market or a local stall, and the markup each
// kind of local market puts on the Official Value.
const COINS = [
  ["Crownsblood", 1.00, "Humans (Chartered Cities)"],
  ["Lifesap", 1.10, "Elves (Skyloom)"],
  ["Hearthmark", 1.05, "Dwarves (Northreach)"],
  ["Hellglass", 0.95, "Tieflings (Emberweave)"],
  ["Tuskmark", 0.90, "Orcs (Iron-Tusk)"],
  ["Crimson Seal", 1.30, "Sangrith (Ritual States)"],
];
const MARKETS = {
  guild: { name: "Guild market", rule: "The total is rounded to the nearest CB, halves up, and every purchase costs at least 1 CB.",
    round: x => x > 0 ? Math.max(1, Math.floor(x + .5)) : 0 },
  local: { name: "Local market", rule: "The Official Value times the markup, always rounded up. A markup can be haggled down (never below × 1), or raised by insult or an obvious need.",
    round: x => Math.ceil(x - 1e-9) },
};
const LOCAL = [
  ["loft", "Loft Market", 2],
  ["street", "Street stall", 3],
  ["frontier", "Frontier trader", 4],
  ["underweave", "Underweave outlet", 5],
];
const SCARCE = 2;  // goods the region has to bring in from elsewhere

// One aisle is walked at a time (the last one is remembered); a search looks down all of them.
const state = { q: "", aisle: storage("market.aisle"), tier: "all" };
if (!aisles.some(s => s.id === state.aisle)) state.aisle = aisles[0].id;
let tally = load("market.tally", {});
let market = MARKETS[storage("market.kind")] ? storage("market.kind") : "guild";
let local = { kind: "street", markup: 3, scarce: false, ...load("market.local", {}) };
let coin = COINS.some(c => c[0] === storage("market.coin")) ? storage("market.coin") : "Crownsblood";

/* ---------- helpers ---------- */
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// Prices to two places at most, without trailing zeros: 1, 0.3, 1.15.
const num = n => String(+(+n).toFixed(2));
const cb = n => n == null ? "—" : `${num(n)} CB`;
const cents = n => Math.round(n * 100) / 100;
const tierOf = item => +(String(item.category || "").match(/Tier (\d+)/) || [])[1] || null;
const ROMAN = ["", "I", "II", "III", "IV", "V", "VI"];
// An untiered shelf is named by its aisle ("Tools & Hire"), or "Supplies".
const tierName = (t, aisle) => t ? `Tier ${ROMAN[t] || t}` : (aisle && aisle.untiered) || "Supplies";
// "Tier 2 Armor" on a tag that already shows its tier reads as just "Armor".
const kindOf = item => String(item.category || "").replace(/^Tier \d+\s*/, "");
const hours = h => h % 24 === 0 ? `${h / 24} day${h === 24 ? "" : "s"}` : `${h} hour${h === 1 ? "" : "s"}`;

function storage(key, val) {
  try {
    if (val === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, val);
  } catch (_) { return null; }
}
function load(key, fallback) {
  try { return JSON.parse(storage(key)) || fallback; } catch (_) { return fallback; }
}

function picture(item, cls = "plate") {
  const inner = item.image
    ? `<img src="${esc(item.image)}" alt="" loading="lazy">`
    : `<span class="emoji">${esc(item.emoji || EMOJI[item.kind] || "📦")}</span>`;
  return `<span class="${cls}">${inner}</span>`;
}

// What an item's materials cost bought at the market; `missing` lists any
// the market doesn't price, which leaves the total short.
function recipeCost(item) {
  let cost = 0;
  const missing = [];
  for (const [name, qty] of item.materials || []) {
    const m = byName[name];
    if (!m || m.market_value == null) missing.push(name);
    else cost += m.market_value * qty;
  }
  return { cost: cents(cost), missing };
}

// The items whose recipes use this one, and those it upgrades into.
const usedIn = item => items.filter(i => (i.materials || []).some(([n]) => n === item.name));
const upgradesTo = item => items.filter(i => i.upgrade_from === item.name);
// The recipes a set of tools works: those whose tools line names it.
const worksWith = item => item.kind === "tool" ? items.filter(i => (i.tools || "").toLowerCase().includes(item.name.toLowerCase())) : [];

function haystack(i) {
  return [i.name, i.category, i.kind, i.stat, i.power, i.tools, ...(i.properties || []), ...(i.materials || []).map(m => m[0])]
    .filter(Boolean).join(" ").toLowerCase();
}
items.forEach(i => { i._hay = haystack(i); });

/* ---------- the market floor ---------- */

function chips(name, options, current) {
  return `<div class="chips" role="group" aria-label="${esc(name)}">${options.map(([v, label]) =>
    `<button type="button" data-${name}="${esc(v)}" aria-pressed="${String(v) === String(current)}">${esc(label)}</button>`).join("")}</div>`;
}

function card(item) {
  const priced = item.market_value != null;
  const tier = tierOf(item);
  return `<article class="item${priced ? "" : " unpriced"}" data-tier="${tier || 0}">
    <a class="item-link" href="#${esc(item.id)}" data-open="${esc(item.id)}">
      ${picture(item)}
      <span class="tag-body">
        <small class="cat">${tier ? `<i class="tier-pill">T${tier}</i>` : ""}${esc(kindOf(item))}</small>
        <b>${esc(item.name)}</b>
        ${item.stat ? `<span class="stat">${esc(item.stat)}</span>` : ""}
      </span>
      <span class="price">${priced ? `<i class="coin" aria-hidden="true"></i>${esc(cb(item.market_value))}` : "Not stocked"}</span>
    </a>
    ${priced ? `<button class="add" type="button" data-add="${esc(item.id)}" aria-label="Add ${esc(item.name)} to the tally" title="Add to the tally">+</button>` : ""}
  </article>`;
}

// An aisle's shelving: its head board (number, name and what it's for), then
// a shelf for each tier, lowest first, with untiered supplies last.
function aisle(s, here) {
  here = here.slice().sort((a, b) => (tierOf(a) || 99) - (tierOf(b) || 99) || items.indexOf(a) - items.indexOf(b));
  const tiers = [...new Set(here.map(tierOf))].sort((a, b) => (a || 99) - (b || 99));
  return `<section class="aisle" id="aisle-${esc(s.id)}" data-aisle-of="${esc(s.id)}" aria-labelledby="aisle-${esc(s.id)}-name">
    <div class="cabinet">
      <header class="cabinet-head">
        <p class="aisle-no">Aisle ${s.n}</p>
        <h2 id="aisle-${esc(s.id)}-name"><span>${esc(s.name)}</span></h2>
        ${s.blurb ? `<p class="blurb">${esc(s.blurb)}</p>` : ""}
      </header>
      ${tiers.map(t => `<div class="shelf" data-tier="${t || 0}">
        <h3 class="tier-plate"><span>${esc(tierName(t, s))}</span></h3>
        <div class="items">${here.filter(i => tierOf(i) === t).map(card).join("")}</div>
      </div>`).join("")}
    </div>
  </section>`;
}

// The sign over an aisle; while searching, it says how many matches are down it.
function sign(s, found) {
  const on = !state.q.trim() && s.id === state.aisle;
  return `<button class="sign" type="button" data-aisle="${esc(s.id)}" aria-pressed="${on}"${found === 0 ? " disabled" : ""}>
    <i class="no">${s.n}</i><b>${esc(s.name)}</b><small>${esc(s.sign)}</small>${found == null ? "" : `<em>${found ? `${found} found` : "nothing"}</em>`}
  </button>`;
}

function render() {
  const q = state.q.trim().toLowerCase();
  const shown = items.filter(i =>
    (state.tier === "all" || tierOf(i) === +state.tier) &&
    (!q || q.split(/\s+/).every(w => i._hay.includes(w))));
  const tiers = [...new Set(items.map(tierOf).filter(Boolean))].sort();
  const down = s => shown.filter(i => aisleOf(i) === s);

  // The intro and the quartermaster's post stay put (template.html); only the
  // filters, the signs and the aisles are redrawn.
  $("#error").innerHTML = DATA.error ? `<div class="error">${esc(DATA.error)}\n\nFix the file and save; this page reloads itself.</div>` : "";
  $("#filters").innerHTML = tiers.length > 1 ? chips("tier", [["all", "All tiers"], ...tiers.map(t => [t, `Tier ${t}`])], state.tier) : "";

  let h = `<nav class="aisles" style="--n:${aisles.length}" aria-label="Aisles">${aisles.map(s => sign(s, q ? down(s).length : null)).join("")}</nav>`;
  if (q) {
    // A search walks every aisle and shows what it found down each.
    for (const s of aisles) if (down(s).length) h += aisle(s, down(s));
    if (!shown.length) h += `<p class="empty">Nothing in any aisle matches “${esc(state.q)}”.</p>`;
  } else {
    const at = aisles.findIndex(s => s.id === state.aisle), s = aisles[at];
    h += down(s).length ? aisle(s, down(s)) : `<p class="empty">Nothing down this aisle at Tier ${esc(state.tier)}.</p>`;
    // At the end of the aisle, the way on to the ones either side.
    const by = (t, cls, arrow) => t ? `<button class="walk ${cls}" type="button" data-aisle="${esc(t.id)}" data-walk>
      ${cls === "prev" ? arrow : ""}<span><small>Aisle ${t.n}</small>${esc(t.name)}</span>${cls === "next" ? arrow : ""}</button>` : "<span></span>";
    h += `<nav class="aisle-walk" aria-label="On to the next aisle">${by(aisles[at - 1], "prev", "←")}${by(aisles[at + 1], "next", "→")}</nav>`;
  }

  if (LIVE && DATA.warnings && DATA.warnings.length) {
    h += `<details class="notes"><summary>Data notes (${DATA.warnings.length}), shown on the live server only</summary>
      <p>Where data/items.yaml and Ch.10 of the lore-book disagree:</p>
      <ul>${DATA.warnings.map(w => `<li>${esc(w)}</li>`).join("")}</ul></details>`;
  }
  $("#floor").innerHTML = h;
}

// keeper.js listens for these: an item's slip opening, the tally redrawn, and
// something added to (or taken off) the tally.
const announce = (name, detail) => document.dispatchEvent(new CustomEvent(name, { detail }));

/* ---------- an item's slip ---------- */

function power(text) {
  const at = text.indexOf(" — ");
  if (at < 0) return esc(text);
  const rest = text.slice(at + 3);
  return `<b>${esc(text.slice(0, at))}.</b> ${esc(rest.charAt(0).toUpperCase() + rest.slice(1))}`;
}
const itemLink = (item, extra = "") => `<a href="#${esc(item.id)}" data-open="${esc(item.id)}">${esc(item.name)}</a>${extra}`;

function recipe(item) {
  const rows = (item.materials || []).map(([name, qty]) => {
    const m = byName[name], unit = m ? m.market_value : null;
    return `<tr><td>${m ? itemLink(m) : esc(name)}</td><td class="n">× ${num(qty)}</td>
      <td class="n">${esc(cb(unit))}</td><td class="n">${unit == null ? "—" : esc(cb(cents(unit * qty)))}</td></tr>`;
  }).join("");
  const { cost, missing } = recipeCost(item);
  let verdict = "";
  if (missing.length) {
    verdict = `<p class="note">The market doesn't stock ${missing.map(esc).join(", ")}, so the materials cost at least ${esc(cb(cost))}.</p>`;
  } else if (item.market_value != null) {
    const diff = cents(item.market_value - cost);
    verdict = `<p class="note">Bought at the market, the materials come to <b>${esc(cb(cost))}</b>: ${diff > 0
      ? `<b>${esc(cb(diff))} less</b> than buying it made`
      : diff < 0 ? `<b>${esc(cb(-diff))} more</b> than buying it made` : "the same as buying it made"}.</p>`;
  }
  return `<h3>Recipe</h3>
    <table class="recipe"><thead><tr><th>Material</th><th class="n">Qty</th><th class="n">Each</th><th class="n">Cost</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td colspan="3">Materials${missing.length ? " (priced ones)" : ""}</td><td class="n">${esc(cb(cost))}</td></tr></tfoot></table>
    <dl class="facts">
      ${item.tools ? `<dt>Tools</dt><dd>${esc(item.tools)}</dd>` : ""}
      ${item.craft_time_hrs ? `<dt>Craft time</dt><dd>${esc(hours(item.craft_time_hrs))}</dd>` : ""}
    </dl>${verdict}`;
}

function slip(item) {
  const priced = item.market_value != null;
  const from = item.upgrade_from;
  const into = upgradesTo(item);
  const uses = usedIn(item);
  let body = "";
  if (item.stat) body += `<p class="statline">${esc(item.stat)}</p>`;
  if (item.properties && item.properties.length) body += `<p class="props">${item.properties.map(p => `<span>${esc(p)}</span>`).join("")}</p>`;
  if (item.power) body += `<p class="power">${power(item.power)}</p>`;
  if (from || into.length) {
    body += `<h3>Upgrade path</h3><p>`;
    if (from) body += `Upgrades from ${byName[from] ? itemLink(byName[from]) : `${esc(from)} <span class="muted">(not stocked yet)</span>`}. `;
    if (into.length) body += `Upgrades into ${into.map(i => itemLink(i)).join(", ")}.`;
    body += `</p>`;
  }
  if (item.materials && item.materials.length) body += recipe(item);
  const works = worksWith(item);
  if (works.length) body += `<h3>Works</h3><p>${works.map(i => itemLink(i)).join(", ")}.</p>`;
  if (uses.length) {
    body += `<h3>Used in</h3><ul class="uses">${uses.map(i => {
      const qty = i.materials.find(([n]) => n === item.name)[1];
      return `<li>${itemLink(i)} <span class="muted">× ${num(qty)}</span></li>`;
    }).join("")}</ul>`;
  }

  return `<header class="slip-head">
      ${picture(item, "plate big")}
      <div class="slip-title">
        <p class="kicker">${esc(item.category || "")}</p>
        <h2 id="slipTitle">${esc(item.name)}</h2>
        <p class="slip-price">${priced ? `<i class="coin" aria-hidden="true"></i>${esc(cb(item.market_value))}` : `<span class="muted">Not stocked at the Guild market</span>`}</p>
      </div>
      <button class="close" type="button" data-close aria-label="Close"><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M2 2l10 10M12 2 2 12"/></svg></button>
    </header>
    <div class="slip-body">${body}</div>
    <footer class="slip-foot">${priced
      ? `<button class="btn" type="button" data-add="${esc(item.id)}">Add to the tally</button><span class="muted" data-incart="${esc(item.id)}">${inTally(item.id)}</span>`
      : `<span class="muted">Not for sale here: craft it, or ask the DM for a price.</span>`}</footer>`;
}

const inTally = id => tally[id] ? `${tally[id]} on the tally` : "";

// Opened from a tag here: Back (or closing it) returns to the market floor.
let pushed = false;
function showSlip(id) {
  const item = byId[id], dlg = $("#slip");
  if (!item) return dlg.open && dlg.close();
  dlg.innerHTML = slip(item);
  dlg.scrollTop = 0;
  if (!dlg.open) dlg.showModal();
  dlg.querySelector(".close").focus();
  announce("market:slip", item);
}
function closeSlip() {
  if (!byId[location.hash.slice(1)]) return void $("#slip").close();
  if (pushed) {
    pushed = false;
    history.back();
  } else {
    // Opened from a link: replaceState fires no hashchange, so close it here.
    history.replaceState(null, "", location.pathname + location.search);
    route();
  }
}
function route() {
  const id = decodeURIComponent(location.hash.slice(1));
  if (byId[id]) showSlip(id);
  else if ($("#slip").open) $("#slip").close();
}

/* ---------- the tally ---------- */

function tallyLines() {
  return Object.entries(tally).filter(([id, n]) => byId[id] && byId[id].market_value != null && n > 0)
    .map(([id, n]) => ({ item: byId[id], n, cost: cents(byId[id].market_value * n) }));
}
function totals() {
  const lines = tallyLines();
  const sub = cents(lines.reduce((s, l) => s + l.cost, 0));
  const factor = market === "local" ? local.markup * (local.scarce ? SCARCE : 1) : 1;
  const priced = cents(sub * factor);
  return { lines, count: lines.reduce((s, l) => s + l.n, 0), sub, factor, priced, due: MARKETS[market].round(priced) };
}

function saveTally() {
  storage("market.tally", JSON.stringify(tally));
  const t = totals();
  $("#tallySum").textContent = t.count ? `${t.count} item${t.count === 1 ? "" : "s"} · ${t.due} CB` : "empty";
  $("#tallyBtn").classList.toggle("has", t.count > 0);
  document.querySelectorAll("[data-incart]").forEach(el => { el.textContent = inTally(el.dataset.incart); });
  if ($("#tally").open) renderTally();
}

function add(id, by = 1) {
  tally[id] = Math.max(0, (tally[id] || 0) + by);
  if (!tally[id]) delete tally[id];
  saveTally();
  announce("market:add", { item: byId[id], by });
}

function renderTally() {
  drawTally();
  announce("market:tally");
}
function drawTally() {
  const t = totals(), m = MARKETS[market];
  if (!t.lines.length) {
    $("#tallyBody").innerHTML = `<p class="empty">Nothing on the tally yet. Add items with the <b>+</b> on their tags.</p>`;
    return;
  }
  const [, tu] = COINS.find(c => c[0] === coin);
  const inCoin = t.due / tu;
  $("#tallyBody").innerHTML = `
    <table class="lines">
      <tbody>${t.lines.map(l => `<tr>
        <td>${picture(l.item, "plate tiny")}</td>
        <td class="what">${itemLink(l.item)}<small>${esc(cb(l.item.market_value))} each</small></td>
        <td class="qty"><button type="button" data-dec="${esc(l.item.id)}" aria-label="One fewer">−</button><span>${l.n}</span><button type="button" data-inc="${esc(l.item.id)}" aria-label="One more">+</button></td>
        <td class="n">${esc(cb(l.cost))}</td>
      </tr>`).join("")}</tbody>
    </table>
    <dl class="sum">
      <dt>Subtotal at the Official Value</dt><dd>${esc(cb(t.sub))}</dd>
    </dl>
    <div class="market-kind" role="radiogroup" aria-label="Where you're buying">
      ${Object.entries(MARKETS).map(([k, v]) => `<label><input type="radio" name="mk" value="${k}"${k === market ? " checked" : ""}> ${esc(v.name)}</label>`).join("")}
    </div>
    ${market === "local" ? localControls(t) : ""}
    <p class="rule">${esc(m.rule)}</p>
    <p class="due"><span>To pay</span><b><i class="coin" aria-hidden="true"></i>${t.due} CB</b></p>
    <label class="paying">Paying in
      <select id="coin">${COINS.map(([name, , who]) => `<option value="${esc(name)}"${name === coin ? " selected" : ""}>${esc(name)} · ${esc(who)}</option>`).join("")}</select>
    </label>
    ${coin === "Crownsblood" ? "" : `<p class="rule">That's <b>${num(inCoin)} ${esc(coin)}</b> at the official Trade Unit rate (${num(tu)} TU to the coin). The Guild's changers charge 2–3% on top; district changers may charge a good deal more.</p>`}
    <div class="tally-actions">
      <button class="btn ghost" type="button" id="copyTally">Copy as text</button>
      <button class="btn ghost" type="button" id="clearTally">Clear</button>
    </div>`;
}

function localControls(t) {
  const kind = LOCAL.find(([k]) => k === local.kind);
  return `<div class="local">
      <label>Kind of market
        <select id="localKind">${LOCAL.map(([k, name, x]) => `<option value="${k}"${k === local.kind ? " selected" : ""}>${esc(name)} · × ${x}</option>`).join("")}</select>
      </label>
      <label>Markup ×
        <input id="markup" type="number" min="1" step="0.5" value="${num(local.markup)}" inputmode="decimal">
      </label>
      <label class="check"><input type="checkbox" id="scarce"${local.scarce ? " checked" : ""}> Scarce here (× ${SCARCE}): goods the region brings in from elsewhere</label>
    </div>
    <p class="rule">${esc(cb(t.sub))} × ${num(local.markup)}${kind && kind[2] === local.markup ? ` (${esc(kind[1].toLowerCase())})` : " (haggled)"}${local.scarce ? ` × ${SCARCE} (scarce)` : ""} = <b>${esc(cb(t.priced))}</b></p>`;
}

function saveLocal() {
  storage("market.local", JSON.stringify(local));
  saveTally();
}

function tallyText() {
  const t = totals();
  return `${t.lines.map(l => `${l.n}× ${l.item.name} (${cb(l.cost)})`).join(", ")}. `
    + `Subtotal ${cb(t.sub)}; ${market === "local" ? `local market at × ${num(t.factor)}` : "Guild market"} total ${t.due} CB.`;
}

/* ---------- events ---------- */

// Into an aisle (or, while searching, down to what was found in it). From the
// far end of one, the page goes back up to the signs. kbd: chosen from the
// keyboard, so its sign keeps the focus once redrawn.
function walkTo(id, kbd, fromEnd) {
  if (state.q.trim()) {
    const at = document.getElementById(`aisle-${id}`);
    if (at) at.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  state.aisle = id;
  storage("market.aisle", id);
  render();
  if (kbd) document.querySelector(`.sign[data-aisle="${CSS.escape(id)}"]`).focus({ preventScroll: true });
  const signs = $(".aisles");
  if (fromEnd || signs.getBoundingClientRect().top < 0) signs.scrollIntoView({ block: "start" });
  announce("market:aisle", aisles.find(s => s.id === id));
}

$("#q").addEventListener("input", e => { state.q = e.target.value; render(); });
document.addEventListener("click", e => {
  const t = e.target.closest("[data-open], [data-add], [data-aisle], [data-tier], [data-inc], [data-dec], [data-close]");
  if (!t) {
    // A click on a dialog's dimmed backdrop (the dialog itself, outside its contents) closes it.
    if (e.target === $("#slip")) closeSlip();
    if (e.target === $("#tally")) $("#tally").close();
    return;
  }
  if (t.dataset.open) {
    e.preventDefault();
    if ($("#tally").open) $("#tally").close();
    if (location.hash.slice(1) === t.dataset.open) return;
    // Within an open slip, hop to the linked item in place of this one.
    if (byId[location.hash.slice(1)]) history.replaceState(null, "", `#${t.dataset.open}`);
    else { history.pushState(null, "", `#${t.dataset.open}`); pushed = true; }
    route();
  } else if (t.dataset.add) {
    add(t.dataset.add);
    t.classList.remove("bump");
    void t.offsetWidth;
    t.classList.add("bump");
  } else if (t.dataset.inc) add(t.dataset.inc);
  else if (t.dataset.dec) add(t.dataset.dec, -1);
  else if (t.dataset.aisle) walkTo(t.dataset.aisle, e.detail === 0, t.dataset.walk !== undefined);
  else if (t.dataset.tier) { state.tier = t.dataset.tier; render(); }
  else if (t.dataset.close !== undefined) {
    if (t.closest("#slip")) closeSlip();
    else t.closest("dialog").close();
  }
});
// Esc closes the slip by itself; put the address back to match.
$("#slip").addEventListener("cancel", e => { e.preventDefault(); closeSlip(); });

$("#tallyBtn").addEventListener("click", () => { renderTally(); $("#tally").showModal(); });
$("#tally").addEventListener("change", e => {
  if (e.target.name === "mk") { market = e.target.value; storage("market.kind", market); saveTally(); }
  if (e.target.id === "coin") { coin = e.target.value; storage("market.coin", coin); renderTally(); }
  if (e.target.id === "localKind") { local.kind = e.target.value; local.markup = LOCAL.find(([k]) => k === local.kind)[2]; saveLocal(); }
  if (e.target.id === "markup") { local.markup = Math.max(1, +e.target.value || 1); saveLocal(); }
  if (e.target.id === "scarce") { local.scarce = e.target.checked; saveLocal(); }
});
$("#tally").addEventListener("click", async e => {
  if (e.target.id === "clearTally") { tally = {}; saveTally(); }
  if (e.target.id === "copyTally") {
    try {
      await navigator.clipboard.writeText(tallyText());
      e.target.textContent = "Copied";
    } catch (_) {
      e.target.textContent = "Couldn't copy";
    }
    setTimeout(() => { e.target.textContent = "Copy as text"; }, 1600);
  }
});
addEventListener("popstate", () => { pushed = false; route(); });
addEventListener("hashchange", route);

/* ---------- start ---------- */

try {
  const place = JSON.parse(sessionStorage.getItem("market.place") || "null");
  if (place) {
    sessionStorage.removeItem("market.place");
    Object.assign(state, place.state);
    $("#q").value = state.q;
    requestAnimationFrame(() => scrollTo(0, place.y));
  }
} catch (_) {}
render();
saveTally();
route();

if (LIVE) {
  setInterval(async () => {
    try {
      const { version } = await (await fetch("/version", { cache: "no-store" })).json();
      if (version === DATA.version) return;
      try { sessionStorage.setItem("market.place", JSON.stringify({ state, y: window.scrollY })); } catch (_) {}
      location.reload();
    } catch (_) { /* server stopped or restarting; try again next tick */ }
  }, 1500);
}
