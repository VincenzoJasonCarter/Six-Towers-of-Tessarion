// All game rules live in Python (api.py and friends). This file only renders
// the state the server returns and posts user actions back to it.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const store = {
  get(key, fallback) {
    try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(key, value); } catch { /* private mode etc. */ }
  },
};

const CHARACTER_NAME = /^[A-Za-z0-9_-]{1,40}$/;
const BAND_CLASS = {
  "Resonant Apex": "band-apex",
  "Full Resonance": "band-full",
  "Threshold": "band-threshold",
  "Dim Resonance": "band-dim",
  "Fractured Emergence": "band-fractured",
  "Rejection": "band-rejection",
};

let state = null;
let character = store.get("tessarion.character", "default");
if (!CHARACTER_NAME.test(character)) character = "default";

const workshop = { category: "All", search: "", sort: "craftable", craftableOnly: false };
let marketType = "guild";
const forge = { pr: 1, posture: "single" };
const rollHistory = [];
let previewSeq = 0;

// ---------- helpers ----------

function esc(value) {
  return String(value).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function fmtNum(n) {
  return String(parseFloat(Number(n).toFixed(4)));
}

function fmtCB(n) {
  if (n === null || n === undefined) return "—";
  return Math.abs(n % 1) < 1e-9 ? `${n.toFixed(0)} CB` : `${n.toFixed(2)} CB`;
}

function fmtSigned(n) {
  return (n >= 0 ? "+" : "−") + fmtNum(Math.abs(n));
}

function fmtHrs(h) {
  if (h >= 24) {
    const d = h / 24;
    return `${fmtNum(d)} day${d === 1 ? "" : "s"}`;
  }
  return `${fmtNum(h)} hr${h === 1 ? "" : "s"}`;
}

function fmtTime(iso) {
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString();
}

let toastTimer = null;
function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), isError ? 4200 : 2600);
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
  const res = await fetch(path, options);
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

async function loadState() {
  try {
    state = await api(`/api/state?character=${encodeURIComponent(character)}`);
    renderAll();
  } catch (e) {
    toast(e.message, true);
  }
}

async function act(path, body) {
  try {
    const res = await api(path, { character, ...body });
    state = res.state;
    renderAll();
    toast(res.message);
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------- rendering ----------

function renderAll() {
  renderHeader();
  renderWorkshop();
  renderMarket();
  renderSidebar();
  renderForgeItems();
  if (!$("#prRow").children.length) {
    renderPrRow();
    updatePreview();
  }
}

function renderHeader() {
  $("#purseValue").textContent = fmtNum(state.inventory.currency_cb);
  $("#charSelect").innerHTML = state.characters
    .map(c => `<option value="${esc(c)}"${c === state.character ? " selected" : ""}>${esc(c)}</option>`)
    .join("");
}

function renderWorkshop() {
  const chips = $("#categoryChips");
  if (!chips.children.length) {
    const cats = ["All", ...new Set(state.items.map(it => it.category))];
    chips.innerHTML = cats
      .map(c => `<button class="chip${c === workshop.category ? " active" : ""}" data-category="${esc(c)}">${esc(c)}</button>`)
      .join("");
  }

  const term = workshop.search;
  let items = state.items.filter(it => {
    if (workshop.category !== "All" && it.category !== workshop.category) return false;
    if (workshop.craftableOnly && !it.craftable) return false;
    if (!term) return true;
    const hay = [it.name, ...it.materials.map(m => m.name)].join(" ").toLowerCase();
    return hay.includes(term);
  });

  const byName = (a, b) => a.name.localeCompare(b.name);
  const sorters = {
    craftable: (a, b) => (b.craftable - a.craftable) || byName(a, b),
    name: byName,
    craftTime: (a, b) => a.craft_time_hrs - b.craft_time_hrs,
    materialCost: (a, b) => a.material_cost - b.material_cost,
    margin: (a, b) => (b.margin ?? -999) - (a.margin ?? -999),
  };
  items = [...items].sort(sorters[workshop.sort]);

  $("#itemGrid").innerHTML = items.map(cardHtml).join("");
  $("#noResults").hidden = items.length > 0;
}

function cardHtml(it) {
  const rows = it.materials.map(m => {
    const short = m.have < m.qty;
    const cost = m.unit_cost === null ? "no OTMV" : fmtCB(m.unit_cost * m.qty);
    return `<tr class="${short ? "short" : ""}">
      <td>${esc(m.name)}</td>
      <td class="num">${fmtNum(m.have)} / ${fmtNum(m.qty)}</td>
      <td class="num">${cost}</td>
    </tr>`;
  }).join("");

  let marginTag = `<span class="tag tag-muted">no market value</span>`;
  if (it.margin !== null) {
    marginTag = it.margin >= 0
      ? `<span class="tag tag-good">+${fmtCB(it.margin)} if sold</span>`
      : `<span class="tag tag-bad">${fmtCB(it.margin)} if sold</span>`;
  }

  const status = it.craftable
    ? `<div class="craft-status ok">✅ Can craft ×${it.max_craftable}</div>`
    : `<div class="craft-status no">🚫 Missing ${Object.entries(it.missing).map(([m, q]) => `${esc(m)} ×${fmtNum(q)}`).join(", ")}</div>`;

  const upgrade = it.upgrade_from
    ? `<div class="stat-line">⬆ Upgrade of ${esc(it.upgrade_from)}${it.upgrade_gap ? " (no recipe for it in Ch.7)" : ""}</div>`
    : "";

  return `<div class="card${it.craftable ? " craftable" : ""}">
    <div class="card-head">
      <div class="card-title"><span class="emoji">${esc(it.emoji)}</span><span>${esc(it.name)}</span></div>
      <span class="badge">${esc(it.category)}</span>
    </div>
    <div class="stat-line">${esc(it.stat)}</div>
    <div class="power-note"><b>Power:</b> ${esc(it.power)}</div>
    <table class="recipe">${rows}</table>
    <div class="meta-row"><span>🛠️ ${esc(it.tools)}</span><span>⏱️ ${fmtHrs(it.craft_time_hrs)}</span></div>
    <div class="meta-row">
      <span>${fmtCB(it.material_cost)}${it.cost_gap ? "+" : ""} → ${fmtCB(it.market_value)}</span>
      ${marginTag}
    </div>
    ${upgrade}
    ${status}
    ${it.owned ? `<div class="stat-line">Owned ×${it.owned}</div>` : ""}
    <div class="craft-row">
      <input type="number" class="craft-qty" min="1" max="${Math.max(1, it.max_craftable)}" value="1" aria-label="Quantity">
      <button class="btn btn-primary craft-btn" data-item="${esc(it.name)}"${it.craftable ? "" : " disabled"}>Craft</button>
    </div>
  </div>`;
}

function quote(unit, qty, market) {
  const raw = Math.round(unit * qty * 10000) / 10000;
  const rounded = market === "guild" ? Math.floor(raw + 0.5) : Math.ceil(raw);
  return { raw, charged: Math.max(rounded, 1) };
}

function renderMarket() {
  $("#marketHint").textContent = marketType === "guild"
    ? "Merchant's Guild accounting (Ch.9 §IV): the total is rounded, below .5 down and .5 or above up, with a 1 CB minimum charge."
    : "Street and local traders (Ch.9 §IV): the total always rounds up, since risk and scarcity are priced in.";

  const body = $("#marketBody");
  const prevQty = {};
  $$("tr[data-unit]", body).forEach(tr => { prevQty[tr.dataset.material] = $(".buy-qty", tr).value; });

  body.innerHTML = state.materials.map(m => {
    const have = state.inventory.materials[m.name] ?? 0;
    const qty = prevQty[m.name] ?? "1";
    if (m.unit_cost === null) {
      return `<tr data-material="${esc(m.name)}">
        <td>${esc(m.name)}</td><td class="num">—</td><td class="num">${fmtNum(have)}</td>
        <td colspan="3" class="price-raw">Not sold: no OTMV in Ch.10. Add it from loot in the inventory panel.</td>
      </tr>`;
    }
    return `<tr data-material="${esc(m.name)}" data-unit="${m.unit_cost}">
      <td>${esc(m.name)}</td>
      <td class="num">${fmtCB(m.unit_cost)}</td>
      <td class="num">${fmtNum(have)}</td>
      <td><input type="number" class="buy-qty" min="1" max="999" step="1" value="${esc(qty)}" aria-label="Quantity"></td>
      <td class="num price-cell"></td>
      <td><button class="btn buy-btn">Buy</button></td>
    </tr>`;
  }).join("");

  $$("tr[data-unit]", body).forEach(updateMarketRow);
}

function updateMarketRow(tr) {
  const qty = parseInt($(".buy-qty", tr).value, 10);
  const cell = $(".price-cell", tr);
  const btn = $(".buy-btn", tr);
  if (!Number.isInteger(qty) || qty < 1) {
    cell.innerHTML = "—";
    btn.disabled = true;
    return;
  }
  const { raw, charged } = quote(parseFloat(tr.dataset.unit), qty, marketType);
  cell.innerHTML = `<b>${charged} CB</b> <span class="price-raw">(${fmtNum(raw)} raw)</span>`;
  btn.disabled = charged > state.inventory.currency_cb;
}

function renderSidebar() {
  const inv = state.inventory;

  const mats = Object.entries(inv.materials).sort(([a], [b]) => a.localeCompare(b));
  $("#materialList").innerHTML = mats.length
    ? mats.map(([m, q]) => `<li><span>${esc(m)}</span><span>${fmtNum(q)}</span></li>`).join("")
    : `<li class="none">No materials yet. Buy some at the Market.</li>`;

  const lootSel = $("#lootMaterial");
  const selected = lootSel.value;
  lootSel.innerHTML = state.materials
    .map(m => `<option value="${esc(m.name)}">${esc(m.name)}</option>`)
    .join("");
  if (selected) lootSel.value = selected;

  const owned = Object.entries(inv.items).sort(([a], [b]) => a.localeCompare(b));
  $("#ownedList").innerHTML = owned.length
    ? owned.map(([n, q]) => `<li><span>${esc(n)}</span><span>×${q}</span></li>`).join("")
    : `<li class="none">Nothing crafted yet.</li>`;

  $("#craftLog").innerHTML = inv.crafted_log.length
    ? inv.crafted_log.map(e => `<li>${esc(e.item)} ×${esc(e.qty)}<time>${esc(fmtTime(e.at))}</time></li>`).join("")
    : `<li class="none">No crafts yet.</li>`;
}

// ---------- forge ----------

function renderPrRow() {
  const { dc, rarity } = state.resonance;
  $("#prRow").innerHTML = [1, 2, 3, 4, 5, 6].map(pr =>
    `<button type="button" class="seg${pr === forge.pr ? " active" : ""}" data-pr="${pr}">
      PR ${pr}<small>${esc(rarity[pr])}</small><small>DC ${dc[pr]}</small>
    </button>`
  ).join("");
}

function renderForgeItems() {
  const sel = $("#forgeItem");
  const selected = sel.value;
  sel.innerHTML = state.items
    .map(it => `<option value="${esc(it.name)}">${esc(it.emoji)} ${esc(it.name)}${it.owned ? ` (owned ×${it.owned})` : ""}</option>`)
    .join("");
  if (selected) sel.value = selected;
}

function forgePayload(rolls) {
  return {
    pr: forge.pr,
    posture: forge.posture,
    soulstone: $("#soulstone").value,
    tool_prof: $("#toolProf").checked,
    expert_tools: $("#expertTools").checked,
    mixed_binding: $("#mixedBinding").checked,
    fractured: $("#fractured").checked,
    location_bonus: parseInt($("#locationBonus").value, 10),
    prior_crafts: Math.max(0, Math.min(5, parseInt($("#priorCrafts").value, 10) || 0)),
    rolls,
  };
}

async function updatePreview() {
  $("#locationValue").textContent = `+${$("#locationBonus").value}`;
  const seq = ++previewSeq;
  let r;
  try {
    r = await api("/api/resonate", forgePayload(0));
  } catch (e) {
    toast(e.message, true);
    return;
  }
  if (seq !== previewSeq) return;

  const maxDice = r.dice_count * 20;
  const need = r.dc - r.total_modifier;
  let needText = `≥ ${need} on ${r.dice_count}d20`;
  if (need > maxDice) needText = `${need}, which is impossible (max ${maxDice})`;
  else if (need <= r.dice_count) needText = "automatic (any roll clears it)";

  const rows = r.breakdown.length
    ? r.breakdown.map(b => `<div class="row"><span>${esc(b.label)}</span><span class="num">${fmtSigned(b.value)}</span></div>`).join("")
    : `<div class="row"><span>No modifiers</span><span class="num">+0</span></div>`;

  $("#forgePreview").innerHTML = `
    <div class="row"><span>Dice pool</span><span class="num">${r.dice_count}d20 (avg ${fmtNum(r.dice_count * 10.5)}, max ${maxDice})</span></div>
    <div class="row"><span>Resonance DC · ceiling</span><span class="num">${r.dc} · ${esc(r.rarity)}</span></div>
    ${rows}
    <div class="row total"><span>Total modifier</span><span class="num">${fmtSigned(r.total_modifier)}</span></div>
    <div class="row"><span>Needed on the dice to reach DC</span><span class="num">${needText}</span></div>
    <div class="row"><span>Fractured Emergence begins at</span><span class="num">DC ${r.fractured_emergence_start} (${forge.posture})</span></div>
  `;
}

async function roll() {
  const btn = $("#rollBtn");
  btn.disabled = true;
  try {
    const r = await api("/api/resonate", forgePayload(1));
    const res = r.result;
    const itemName = $("#forgeItem").value;
    const dice = res.dice.map((d, i) =>
      `<div class="die${d === 20 ? " nat20" : d === 1 ? " nat1" : ""}" style="animation-delay:${i * 60}ms">${d}</div>`
    ).join("");

    $("#rollResult").innerHTML = `
      <h2>Roll: ${esc(itemName)}, PR ${forge.pr} (${esc(r.rarity)})</h2>
      <div class="dice">${dice}</div>
      <div class="roll-math">
        ${res.dice_sum} (dice) ${fmtSigned(r.total_modifier)} (mods) = <b>${res.total}</b> vs DC ${r.dc}
        → <b>${res.diff >= 0 ? "+" : ""}${res.diff}</b>
      </div>
      <div class="outcome ${BAND_CLASS[res.outcome]}">
        <div class="outcome-name">${esc(res.outcome)}</div>
        <div>${esc(res.info)}</div>
      </div>`;

    rollHistory.unshift({ item: itemName, pr: forge.pr, posture: forge.posture, outcome: res.outcome, diff: res.diff });
    rollHistory.length = Math.min(rollHistory.length, 12);
    $("#rollHistoryPanel").hidden = false;
    $("#rollHistory").innerHTML = rollHistory.map(h =>
      `<li><b class="${BAND_CLASS[h.outcome]}" style="background:none">${esc(h.outcome)}</b>, ${esc(h.item)} · PR ${h.pr} ${h.posture} (${h.diff >= 0 ? "+" : ""}${h.diff})</li>`
    ).join("");
  } catch (e) {
    toast(e.message, true);
  } finally {
    btn.disabled = false;
  }
}

async function simulate() {
  const btn = $("#simBtn");
  btn.disabled = true;
  try {
    const r = await api("/api/resonate", forgePayload(10000));
    const bars = state.resonance.order.map(band => {
      const pct = r.distribution[band];
      return `<div class="bar-row">
        <span>${esc(band)}</span>
        <div class="bar-track"><div class="bar-fill ${BAND_CLASS[band]}" style="width:${pct}%"></div></div>
        <span class="bar-pct">${pct.toFixed(1)}%</span>
      </div>`;
    }).join("");
    $("#simResult").innerHTML = `
      <h2>Odds: PR ${forge.pr} ${forge.posture}, ${fmtSigned(r.total_modifier)} mods vs DC ${r.dc}</h2>
      <p class="hint">${r.rolls.toLocaleString()} simulated attempts with this exact build.</p>
      <div class="bars">${bars}</div>`;
  } catch (e) {
    toast(e.message, true);
  } finally {
    btn.disabled = false;
  }
}

// ---------- events ----------

function showTab(name) {
  $$(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
  $$(".tab-panel").forEach(p => { p.hidden = p.id !== `tab-${name}`; });
  store.set("tessarion.tab", name);
}

$$(".tab").forEach(t => t.addEventListener("click", () => showTab(t.dataset.tab)));

$("#charSelect").addEventListener("change", e => {
  character = e.target.value;
  store.set("tessarion.character", character);
  loadState();
});

$("#newCharForm").addEventListener("submit", e => {
  e.preventDefault();
  const name = $("#newCharInput").value.trim();
  if (!CHARACTER_NAME.test(name)) {
    toast("Use letters, numbers, - or _ (max 40 characters).", true);
    return;
  }
  character = name;
  store.set("tessarion.character", character);
  $("#newCharInput").value = "";
  loadState().then(() => toast(`Switched to ${name}. Their inventory file is created on the first change.`));
});

$("#search").addEventListener("input", e => {
  workshop.search = e.target.value.trim().toLowerCase();
  renderWorkshop();
});
$("#sortSelect").addEventListener("change", e => { workshop.sort = e.target.value; renderWorkshop(); });
$("#craftableOnly").addEventListener("change", e => { workshop.craftableOnly = e.target.checked; renderWorkshop(); });
$("#categoryChips").addEventListener("click", e => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  workshop.category = chip.dataset.category;
  $$(".chip").forEach(c => c.classList.toggle("active", c === chip));
  renderWorkshop();
});
$("#itemGrid").addEventListener("click", e => {
  const btn = e.target.closest(".craft-btn");
  if (!btn || btn.disabled) return;
  const qty = parseInt($(".craft-qty", btn.closest(".card")).value, 10);
  if (!Number.isInteger(qty) || qty < 1) {
    toast("Quantity must be a whole number of at least 1.", true);
    return;
  }
  act("/api/craft", { item: btn.dataset.item, qty });
});

$("#marketToggle").addEventListener("click", e => {
  const seg = e.target.closest(".seg");
  if (!seg) return;
  marketType = seg.dataset.market;
  $$("#marketToggle .seg").forEach(s => s.classList.toggle("active", s === seg));
  renderMarket();
});
$("#marketBody").addEventListener("input", e => {
  const tr = e.target.closest("tr[data-unit]");
  if (tr) updateMarketRow(tr);
});
$("#marketBody").addEventListener("click", e => {
  const btn = e.target.closest(".buy-btn");
  if (!btn || btn.disabled) return;
  const tr = btn.closest("tr");
  act("/api/buy", { material: tr.dataset.material, qty: parseInt($(".buy-qty", tr).value, 10), market: marketType });
});

$("#cbForm").addEventListener("submit", e => {
  e.preventDefault();
  const amount = parseFloat($("#cbAmount").value);
  if (!Number.isFinite(amount) || amount === 0) {
    toast("Enter a positive or negative CB amount.", true);
    return;
  }
  $("#cbAmount").value = "";
  act("/api/inventory/cb", { amount });
});

$("#lootForm").addEventListener("submit", e => {
  e.preventDefault();
  const qty = parseFloat($("#lootQty").value);
  if (!Number.isFinite(qty) || qty === 0) {
    toast("Enter a non-zero quantity.", true);
    return;
  }
  act("/api/inventory/add", { material: $("#lootMaterial").value, qty });
});

$("#prRow").addEventListener("click", e => {
  const seg = e.target.closest(".seg");
  if (!seg) return;
  forge.pr = parseInt(seg.dataset.pr, 10);
  $$("#prRow .seg").forEach(s => s.classList.toggle("active", s === seg));
  updatePreview();
});
$("#postureToggle").addEventListener("click", e => {
  const seg = e.target.closest(".seg");
  if (!seg) return;
  forge.posture = seg.dataset.posture;
  $$("#postureToggle .seg").forEach(s => s.classList.toggle("active", s === seg));
  updatePreview();
});
$("#forgeForm").addEventListener("input", e => {
  if (e.target.id !== "forgeItem") updatePreview();
});
$("#forgeForm").addEventListener("submit", e => e.preventDefault());
$("#rollBtn").addEventListener("click", roll);
$("#simBtn").addEventListener("click", simulate);

const savedTab = store.get("tessarion.tab", "workshop");
showTab(["workshop", "market", "forge"].includes(savedTab) ? savedTab : "workshop");
loadState();
