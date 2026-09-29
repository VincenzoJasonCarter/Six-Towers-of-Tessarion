// The Threadmint Memoria: the museum's rooms as sections of lit display
// cases, kept the way the library keeps its shelves and the bestiary its cells.
//
// DATA and LIVE come from the inline script in template.html, which core.py
// fills in from data/memoria.yaml. Each room is a brass nameplate on a rail,
// its wall text, and a row of vitrines; each vitrine opens its placard.

const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const rich = s => esc(s).replace(/\*([^*]+)\*/g, "<i>$1</i>").replace(/█+/g, m => `<span class="redact">${m}</span>`);
const paras = s => String(s || "").split(/\n+/).map(p => p.trim()).filter(Boolean).map(p => `<p>${rich(p)}</p>`).join("");
const plain = s => String(s || "").replace(/\*/g, "");

function storage(key, val) {
  try {
    if (val === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, val);
  } catch { return null; }
}

const WINGS = DATA.wings || [];
const ITEMS = DATA.items || [];
const wingOf = Object.fromEntries(WINGS.map(w => [w.id, w]));
const itemOf = Object.fromEntries(ITEMS.map(i => [i.id, i]));
const itemsIn = id => ITEMS.filter(i => i.wing === id);
const ROTUNDA = WINGS.find(w => w.kind === "rotunda");
const CRYPT = WINGS.find(w => w.kind === "crypt");
const GALLERIES = WINGS.filter(w => (w.kind || "wing") === "wing");
const CENTRE = ROTUNDA && itemsIn(ROTUNDA.id).find(i => i.place === "centre");

const state = { q: "", room: "all", animate: storage("memoria.animate") !== "off" };

if (DATA.error) {
  $("#error").textContent = `${DATA.error}\n\nFix the file and save; this page reloads itself.`;
  $("#error").hidden = false;
}

/* ================= the exhibits, drawn small ================= */

const typeOf = it => (it.model && it.model.type) || "empty";
const MOUNT = { banner: "wall", frame: "wall", plate: "wall", tidemarker: "wall", blade: "wall", mirror: "floor", chair: "floor", strikeplate: "floor", sink: "floor", armour: "floor" };
const mountOf = it => (typeOf(it) === "document" && it.model.framed) ? "wall" : MOUNT[typeOf(it)] || "case";

// A picture of each kind of exhibit, 120 x 120, in the colours its model gives.
function art(it, align = "xMidYMid") {
  const m = it.model || {}, c = (k, d) => esc(m[k] || d);
  const svg = (inner, cls = "") => `<svg class="art ${cls}" viewBox="0 0 120 120" preserveAspectRatio="${align} meet" aria-hidden="true">${inner}</svg>`;
  const tower = (x, y, s, fill) => `<path transform="translate(${x} ${y}) scale(${s})" d="M-6 14 L-4 -8 L-7 -10 L-2 -12 L0 -18 L2 -12 L7 -10 L4 -8 L6 14Z" fill="${fill}"/>`;
  switch (typeOf(it)) {
    case "coin": return svg(`<circle cx="60" cy="62" r="32" fill="${c("metal", "#c9a24a")}" stroke="${c("rim", m.metal || "#a9843a")}" stroke-width="5"/>
      ${m.runes ? `<circle cx="60" cy="62" r="23" fill="none" stroke="${c("streak")}" stroke-width="2" stroke-dasharray="3 4"/>` : ""}
      ${tower(60, 62, 1.3, "#0004")}
      <path d="M34 50 Q58 68 86 54 M40 80 Q56 70 82 84" stroke="${c("streak", "#8e2a22")}" stroke-width="3" fill="none" stroke-linecap="round"/>`, m.pulse ? "pulse" : "");
    case "crystal": return svg(`<path d="M60 18 L76 44 L70 96 L50 96 L44 44Z" fill="${c("colour", "#f4f7ff")}" stroke="#0003"/>
      <path d="M60 18 L64 96 M44 44 L76 44" stroke="#fff6" stroke-width="1.5"/>${m.ledger ? `<path d="M82 88 L104 84 L104 100 L82 104Z M82 88 L64 84 L64 100 L82 104Z" fill="#efe4c8" stroke="#7a6a52"/>` : ""}
      <rect x="40" y="96" width="40" height="8" rx="2" fill="#2d2a27"/>`, m.prismatic ? "prism" : m.glow ? "glow" : "");
    case "pick": return svg(`<path d="M30 96 L86 34" stroke="${c("stain", "#e8f1ff")}" stroke-width="6" stroke-linecap="round"/><path d="M58 22 Q86 22 104 50" stroke="#3d3b39" stroke-width="7" fill="none" stroke-linecap="round"/>`);
    case "sickle": return svg(`<path d="M44 34 A30 30 0 1 0 84 70" stroke="#9aa0a3" stroke-width="${m.worn ? 2.5 : 6}" fill="none" stroke-linecap="round"/><path d="M84 70 L96 96" stroke="#5b7a4e" stroke-width="7" stroke-linecap="round"/>`);
    case "adze": return svg(`<path d="M34 98 L78 30" stroke="#8a6238" stroke-width="6" stroke-linecap="round"/><path d="M68 24 L94 40" stroke="#8d9396" stroke-width="9" stroke-linecap="round"/>`);
    case "medallion": return svg(`<path d="M44 16 L60 44 L76 16" stroke="${c("metal", "#c9a24a")}" stroke-width="2" fill="none"/><circle cx="60" cy="70" r="24" fill="${c("metal", "#c9a24a")}"/><circle cx="60" cy="70" r="11" fill="${c("stone", "#3fae7a")}"/>`, "glow");
    case "shard": return svg(`<path d="M34 96 L28 58 L42 26 L56 50 L60 96Z" fill="${c("colour", "#f3efe6")}" stroke="#0002"/>${m.scroll ? `<rect x="66" y="66" width="38" height="28" fill="#eadcb8" stroke="#8a7652"/><path d="M71 74 H99 M71 80 H95 M71 86 H97" stroke="#8a7652"/>` : ""}`);
    case "amber": return svg(`<path d="M30 70 Q28 40 56 34 Q90 30 92 62 Q94 90 60 92 Q32 94 30 70Z" fill="${c("colour", "#e8932c")}" opacity=".85"/><path d="M52 58 q8 -8 14 2 q6 10 -6 12 q-10 0 -8 -8" stroke="#1c120a" stroke-width="4" fill="none"/>`);
    case "thread": return svg(`<path d="M14 50 H106 M24 50 V100 M96 50 V100" stroke="#3a3634" stroke-width="5"/><path d="M58 50 q4 -8 8 0 q-2 10 -6 4 M60 54 q-4 20 2 34 M64 54 q6 16 2 28" stroke="${c("colour", "#d9772e")}" stroke-width="3" fill="none"/>`);
    case "cord": return svg(`<path d="M22 44 V100 M98 44 V100" stroke="#1b1719" stroke-width="6"/><path d="M22 52 H98" stroke="${c("colour", "#a3141f")}" stroke-width="3"/><circle cx="22" cy="52" r="4" fill="${c("colour", "#a3141f")}"/><circle cx="98" cy="52" r="4" fill="${c("colour", "#a3141f")}"/>`);
    case "hourglass": return svg(`<rect x="36" y="16" width="48" height="6" fill="#8a6238"/><rect x="36" y="98" width="48" height="6" fill="#8a6238"/>
      <path d="M42 22 L78 22 L62 60 L78 98 L42 98 L58 60Z" fill="#eaf6ff66" stroke="#8a6238"/><path d="M48 28 L72 28 L61 52Z M46 96 L60 76 L74 96Z" fill="${c("sand", "#c9b37a")}"/>`);
    case "document": return svg(`<rect x="28" y="14" width="64" height="88" fill="#efe3c4" stroke="${m.framed ? "#c9a24a" : "#b39a6a"}" stroke-width="${m.framed ? 5 : 2}"/>
      <path d="M38 30 H82 M38 40 H80 M38 48 H76 M38 56 H80 M38 64 H70" stroke="${c("ink", "#2a2118")}" stroke-opacity=".5"/>
      ${Array.from({ length: Math.min(m.signatures || 0, 6) }, (_, i) => `<path d="M${38 + (i % 2) * 24} ${78 + Math.floor(i / 2) * 8} q5 -5 9 0 t9 0" stroke="${(m.blood || []).includes(i) ? "#8e1512" : esc(m.ink || "#2a2118")}" stroke-width="2" fill="none"/>`).join("")}`);
    case "banner": return svg(`<path d="M14 22 H106" stroke="#c9a24a" stroke-width="4"/><path d="M18 24 H58 L62 34 L56 46 L63 58 L57 72 L62 84 L58 96 H18Z" fill="${c("left", "#7a2430")}"/>
      <path d="M58 24 H102 V96 H58 L62 84 L57 72 L63 58 L56 46 L62 34Z" fill="${c("right", "#27456b")}"/><circle cx="38" cy="56" r="10" fill="none" stroke="#d6b35c" stroke-width="3"/><path d="M80 46 V66 M70 56 H90 M73 49 L87 63 M87 49 L73 63" stroke="#d6b35c" stroke-width="3"/>`);
    case "frame": return svg(`<rect x="18" y="26" width="84" height="64" fill="#6d7985" stroke="#b8943e" stroke-width="7"/><rect x="42" y="52" width="36" height="11" fill="#f6f1e4"/><path d="M46 57.5 H74" stroke="#8c2f23" stroke-width="3"/>`);
    case "plate": return svg(`<rect x="14" y="30" width="92" height="60" fill="${c("metal", "#9c6b35")}" stroke="#0004" stroke-width="3"/>${[40, 50, 60, 70, 80].map(y => `<path d="M22 ${y} H${70 + (y % 20)}" stroke="#0005" stroke-width="2"/>`).join("")}`);
    case "tidemarker": return svg(`<path d="M6 70 H114" stroke="#1f3a4f" stroke-width="2"/><rect x="18" y="44" width="84" height="20" fill="${c("metal", "#c7a052")}"/><path d="M24 44 v6 M34 44 v4 M44 44 v6 M54 44 v4 M64 44 v6 M74 44 v4 M84 44 v6 M94 44 v4" stroke="#0006"/><rect x="18" y="80" width="26" height="20" fill="#fbfaf6" stroke="#4f6b8a"/>`);
    case "blade": return svg(`<path d="M30 62 L104 54 L110 58 L104 62 Z" fill="#aeb4b8"/><path d="M40 60 l3 -3 l3 3 l3 -3 l3 3 l3 -3 l3 3 l3 -3 l3 3 l3 -3 l3 3 l3 -3 l3 3 l3 -3 l3 3" stroke="#0005" fill="none"/><rect x="26" y="48" width="5" height="26" fill="#5b5550"/><path d="M10 61 H26" stroke="#3a2416" stroke-width="7" stroke-linecap="round"/>`);
    case "mirror": return svg(`<path d="M28 104 V30 M92 104 V30" stroke="#3f5a3c" stroke-width="5"/><ellipse cx="60" cy="56" rx="26" ry="36" fill="${c("glass", "#8fb7a4")}" stroke="${c("frame", "#4f9e76")}" stroke-width="6"/><path d="M76 20 q10 -10 14 4" stroke="#2fb58a" stroke-width="4" fill="none"/>`);
    case "chair": return svg(`<rect x="40" y="10" width="40" height="56" fill="${c("wood", "#2b1a12")}"/><rect x="48" y="20" width="24" height="36" fill="#5a1f22"/><rect x="52" y="12" width="16" height="5" fill="#b8b2a4"/>
      <rect x="34" y="64" width="52" height="8" fill="${c("wood", "#2b1a12")}"/><path d="M38 72 V106 M82 72 V106" stroke="${c("wood", "#2b1a12")}" stroke-width="5"/><circle cx="40" cy="10" r="4" fill="${c("metal", "#c9a24a")}"/><circle cx="80" cy="10" r="4" fill="${c("metal", "#c9a24a")}"/>`);
    case "strikeplate": return svg(`<path d="M20 106 V18 H100 V106" stroke="#3a2a1e" stroke-width="6" fill="none"/><rect x="32" y="32" width="56" height="40" fill="${c("metal", "#b8863b")}"/>${[[42, 42], [56, 50], [70, 40], [48, 62], [76, 60]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="4" fill="none" stroke="#0006"/>`).join("")}`);
    case "sink": return svg(`<rect x="36" y="92" width="48" height="14" fill="#55585c"/><rect x="40" y="18" width="40" height="10" fill="#55585c"/><rect x="44" y="28" width="32" height="64" fill="#eaf6ff44" stroke="#b87333"/>
      <path d="M60 34 q14 10 0 20 q-14 10 0 20 q14 8 0 14" stroke="${c("glow", "#8a4dd6")}" stroke-width="8" fill="none"/><path d="M40 48 H80 M40 62 H80 M40 76 H80" stroke="#b87333" stroke-width="2"/>`, "glow");
    case "armour": return svg(`<path d="M60 106 V84" stroke="#2d2a27" stroke-width="4"/><path d="M40 30 Q60 22 80 30 L84 50 Q80 76 72 84 H48 Q40 76 36 50Z" fill="${c("metal", "#6d6a66")}"/>
      <path d="M50 40 l4 8 l-2 8 M68 38 l-3 10 l4 6 M58 60 l3 8" stroke="${c("runes", "#ff7a3c")}" stroke-width="2" fill="none"/><ellipse cx="34" cy="32" rx="11" ry="7" fill="${c("metal", "#6d6a66")}"/><ellipse cx="86" cy="32" rx="11" ry="7" fill="${c("metal", "#6d6a66")}"/>`);
    case "absence": return svg(`<ellipse cx="60" cy="72" rx="12" ry="22" fill="#050506"/><circle cx="64" cy="44" r="9" fill="#050506"/>`, "absence");
    default: return svg("");
  }
}

/* ================= the cases ================= */

const roomVars = w => {
  const C = (w && w.colours) || {};
  return `--wall:${esc(C.wall || "#55504a")};--trim:${esc(C.trim || "#c9a24a")};--light:${esc(C.light || "#fff0d2")}`;
};
const firstSentence = s => plain(String(s || "").split(/\.\s/)[0]);
const doorLabel = g => plain((g.subtitle || g.title).replace(/\s+and\s+the\s+.*$/i, ""));
const COMPASS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"];
const compass = b => COMPASS[Math.round(((b % 360) + 360) % 360 / 45) % 8];

// Inside a case: the spotlight, the thing on its stand (or hung, or on a dais), the glass, the brass tag.
function caseInner(it, centre) {
  const mount = centre ? "centre" : mountOf(it);
  return `<span class="spot"></span>${mount === "wall" ? `<span class="lamp"></span>` : ""}
    <span class="stand"></span><span class="piece">${art(it, mount === "wall" ? "xMidYMid" : "xMidYMax")}</span>
    <span class="glass"></span>`;
}

function vitrine(it, centre) {
  const mount = centre ? "centre" : mountOf(it);
  const text = [it.name, it.accession, it.origin, it.period, it.medium, it.status, it.placard, it.note && it.note.text]
    .join(" ").toLowerCase();
  return `<button type="button" class="vitrine m-${mount}" data-item="${esc(it.id)}" data-text="${esc(text)}">
    <span class="case">${caseInner(it, centre)}<span class="tag">${esc(it.accession)}</span></span>
    <span class="body"><b>${rich(it.name)}</b><small>${rich(it.origin || "")}</small><span class="chip">${rich(firstSentence(it.status))}</span></span>
  </button>`;
}

// The Hall of Absences' dated cases: nothing to open.
function undated(date) {
  return `<div class="vitrine m-case undated" data-text="${esc(String(date).toLowerCase())}">
    <span class="case"><span class="spot"></span><span class="stand"></span><span class="glass"></span><span class="tag">—</span></span>
    <span class="body"><b>Undescribed</b><small>${rich(date)}</small></span>
  </div>`;
}

function roomHTML(w) {
  const items = itemsIn(w.id);
  const ordered = CENTRE && w === ROTUNDA ? [CENTRE, ...items.filter(i => i !== CENTRE)] : items;
  const lede = String(w.intro || "").split(/\n+/).map(p => p.trim()).filter(Boolean)[0] || "";
  const where = (w.kind || "wing") === "wing" && typeof w.bearing === "number" ? ` · to the ${compass(w.bearing)} of the Rotunda` : "";
  return `<section class="room kind-${esc(w.kind || "wing")}" id="room-${esc(w.id)}" data-room="${esc(w.id)}" style="${roomVars(w)}">
    <h2><span>${rich(w.title)}</span></h2>
    <p class="room-sub">${rich(w.subtitle || "")}${where}</p>
    <p class="room-text">${rich(lede)} <button type="button" class="link" data-wall="${esc(w.id)}">Read the wall text ›</button></p>
    <div class="cases">${ordered.map(it => vitrine(it, it === CENTRE)).join("")}${w.kind === "crypt" ? (w.dates || []).map(undated).join("") : ""}</div>
  </section>`;
}

/* ================= the placard ================= */

let openId = null, openedFrom = null;  // an item id, or "wall:<room id>"

function placardHTML(it) {
  const w = wingOf[it.wing] || {};
  const meta = [["Origin", it.origin], ["Period", it.period], ["Medium", it.medium]]
    .filter(([, v]) => v).map(([k, v]) => `<dt>${k}</dt><dd>${rich(v)}</dd>`).join("");
  const note = it.note ? `<div class="note"><h3>${rich(it.note.heading || "")}</h3>${paras(it.note.text)}</div>` : "";
  const mount = it === CENTRE ? "centre" : mountOf(it);
  return `<div class="pl-top">
      <span class="case m-${mount}">${caseInner(it, it === CENTRE)}</span>
      <div><p class="acc">${esc(it.accession)} · ${rich(w.title || "")}</p><h2 id="pl-name">${rich(it.name)}</h2>
      ${meta ? `<dl class="meta">${meta}</dl>` : ""}</div>
    </div>
    <div class="text">${paras(it.placard)}</div>${note}
    ${it.status ? `<p class="status">${rich(it.status)}</p>` : ""}`;
}

function wallHTML(w) {
  const list = itemsIn(w.id).map(i => `<li><span class="acc">${esc(i.accession)}</span><button type="button" class="link" data-item="${esc(i.id)}">${rich(i.name)}</button></li>`).join("");
  return `<p class="acc">Wall text</p>
    <h2 id="pl-name">${rich(w.title)}</h2>
    <p class="sub">${rich(w.subtitle || "")}</p>
    <div class="text">${paras(w.intro)}</div>
    ${list ? `<ul class="in-wing">${list}</ul>` : ""}`;
}

function setHash(h) {
  history.replaceState(null, "", h ? `#${h}` : location.pathname + location.search);
}

function showPlacard(id) {
  const wall = id.startsWith("wall:") ? wingOf[id.slice(5)] : null;
  const it = wall ? null : itemOf[id];
  if (!wall && !it) return;
  if (!openId) openedFrom = document.activeElement;
  openId = id;
  const reveal = $("#reveal");
  reveal.setAttribute("style", roomVars(wall || wingOf[it.wing]));
  $("#pl-body").innerHTML = wall ? wallHTML(wall) : placardHTML(it);
  $("#pl-body").scrollTop = 0;
  reveal.hidden = false;
  document.body.classList.add("reading");
  $("#pl-close").focus({ preventScroll: true });
  setHash(id.replace(":", "-"));
  // Behind it, bring its case into view, so closing it leaves you there.
  const card = it ? document.querySelector(`.vitrine[data-item="${CSS.escape(it.id)}"]`) : document.getElementById(`room-${wall.id}`);
  if (card && !card.hidden) card.scrollIntoView({ block: it ? "center" : "start" });
}

function closePlacard() {
  if ($("#reveal").hidden) return;
  $("#reveal").hidden = true;
  document.body.classList.remove("reading");
  openId = null;
  setHash("");
  if (openedFrom && openedFrom.focus) openedFrom.focus({ preventScroll: true });
}

// ‹ Previous / Next › go through each room's wall text, then its cases.
const ORDER = WINGS.flatMap(w => [`wall:${w.id}`, ...itemsIn(w.id).map(i => i.id)]);
function step(by) {
  if (!openId) return;
  const i = ORDER.indexOf(openId);
  showPlacard(ORDER[(i + by + ORDER.length) % ORDER.length]);
}

$("#pl-close").addEventListener("click", closePlacard);
$("#rv-backdrop").addEventListener("click", closePlacard);
$("#pl-prev").addEventListener("click", () => step(-1));
$("#pl-next").addEventListener("click", () => step(1));
$("#pl-body").addEventListener("click", ev => {
  const b = ev.target.closest("[data-item]");
  if (b) showPlacard(b.dataset.item);
});
document.addEventListener("keydown", ev => {
  if ($("#reveal").hidden) return;
  if (ev.key === "Escape") closePlacard();
  if (ev.key === "ArrowLeft" && !ev.target.closest("input")) step(-1);
  if (ev.key === "ArrowRight" && !ev.target.closest("input")) step(1);
});

/* ================= the plan ================= */

// The building from above, north up: the rotunda, a wing out toward each
// nation (longer for more cases), the stair, and the crypt's outline beneath.
function planSVG() {
  const R = 13, out = [];
  const pt = (b, r) => [Math.sin(b * Math.PI / 180) * r, -Math.cos(b * Math.PI / 180) * r];
  const f = n => n.toFixed(1);
  if (CRYPT) out.push(`<g class="p-room p-crypt" data-room="${esc(CRYPT.id)}"><title>${esc(plain(CRYPT.title))}</title><circle r="${R + 5}"/></g>`);
  for (const g of GALLERIES) {
    const b = g.bearing ?? 0, C = g.colours || {};
    const len = Math.min(28, 12 + itemsIn(g.id).length * 2.8);
    // The label sits just past the wing's end, reading away from it.
    const [lx, ly] = pt(b, R + len + 4);
    const side = Math.sin(b * Math.PI / 180), anchor = side > .35 ? "start" : side < -.35 ? "end" : "middle";
    out.push(`<g class="p-room" data-room="${esc(g.id)}"><title>${esc(plain(g.title))}: ${esc(plain(g.subtitle || ""))}</title>
      <g transform="rotate(${b})"><rect x="-5.5" y="${f(-(R + len))}" width="11" height="${f(len + 3)}" rx="1.2" style="fill:${esc(C.wall || "#666")};stroke:${esc(C.trim || "#c9a24a")}"/>
      <path d="M0 ${f(-(R + len - 2.4))} l-2 5 h4z" style="fill:${esc(C.trim || "#c9a24a")}"/></g>
      <text x="${f(lx)}" y="${f(ly + 1.5 + (anchor === "middle" ? Math.sign(ly) * 2.5 : 0))}" text-anchor="${anchor}">${esc(doorLabel(g).replace(/^The /, ""))}</text></g>`);
  }
  if (ROTUNDA) {
    const C = ROTUNDA.colours || {};
    const [sx, sy] = pt(36, 8);
    out.push(`<g class="p-room p-rot" data-room="${esc(ROTUNDA.id)}"><title>${esc(plain(ROTUNDA.title))}</title>
      <circle r="${R}" style="fill:${esc(C.wall || "#e6ddca")};stroke:${esc(C.trim || "#c9a24a")}"/>
      <circle r="${R - 2.2}" class="p-ring"/><circle r="1.8" class="p-centre"/>
      ${CRYPT ? `<rect x="-1.6" y="-4" width="3.2" height="8" transform="translate(${f(sx)} ${f(sy)}) rotate(36)" class="p-stair"/>` : ""}
      <text y="6.5">Rotunda</text></g>`);
  }
  out.push(`<g class="p-north" transform="translate(52 -52)"><path d="M0 -6 L3 4 L0 2 L-3 4Z"/><text y="10">N</text></g>`);
  return out.join("");
}

/* ================= the page ================= */

const M = DATA.memoria || {};
$("#brand-name").textContent = M.name || "The Threadmint Memoria";
$("#brand-sub").textContent = M.subtitle || "";
$("#tier").textContent = M.tier || "";
$("#title").textContent = M.title || M.name || "The Memoria";
$("#intro").innerHTML = paras(M.intro);
$("#count").textContent = `${ITEMS.length} exhibits · ${WINGS.length} rooms`;
$("#tabs").innerHTML = [["all", "All rooms"], ...WINGS.map(w => [w.id, plain(w.title)])]
  .map(([id, label]) => `<button type="button" data-room="${esc(id)}" aria-pressed="${id === "all"}">${esc(label)}</button>`).join("");
$("#plan").innerHTML = planSVG();
$("#rooms").innerHTML = WINGS.map(roomHTML).join("");

function applyFilter() {
  const q = state.q.trim().toLowerCase();
  let shown = 0;
  for (const sec of document.querySelectorAll(".room")) {
    const inRoom = state.room === "all" || sec.dataset.room === state.room;
    let hits = 0;
    for (const v of sec.querySelectorAll(".vitrine")) {
      const hit = inRoom && (!q || v.dataset.text.includes(q));
      v.hidden = !hit;
      if (hit) hits++;
    }
    sec.hidden = !inRoom || (q !== "" && hits === 0);
    if (!sec.hidden) shown++;
  }
  $("#no-results").hidden = shown > 0;
  for (const b of $("#tabs").children) b.setAttribute("aria-pressed", String(b.dataset.room === state.room));
  for (const g of $("#plan").querySelectorAll(".p-room")) g.classList.toggle("on", g.dataset.room === state.room);
}

$("#tabs").addEventListener("click", ev => {
  const b = ev.target.closest("button[data-room]");
  if (!b) return;
  state.room = b.dataset.room;
  applyFilter();
});
$("#plan").addEventListener("click", ev => {
  const g = ev.target.closest("[data-room]");
  if (!g) return;
  state.room = g.dataset.room;
  applyFilter();
  document.getElementById(`room-${g.dataset.room}`)?.scrollIntoView({ behavior: state.animate ? "smooth" : "auto", block: "start" });
});
$("#q").addEventListener("input", ev => { state.q = ev.target.value; applyFilter(); });
$("#rooms").addEventListener("click", ev => {
  const b = ev.target.closest("[data-item], [data-wall]");
  if (b) showPlacard(b.dataset.item || `wall:${b.dataset.wall}`);
});
$("#home").addEventListener("click", ev => {
  ev.preventDefault();
  closePlacard();
  state.room = "all";
  state.q = $("#q").value = "";
  applyFilter();
  scrollTo({ top: 0, behavior: state.animate ? "smooth" : "auto" });
});

$("#animate").checked = state.animate;
document.body.classList.toggle("still", !state.animate);
$("#animate").addEventListener("change", ev => {
  state.animate = ev.target.checked;
  storage("memoria.animate", state.animate ? "on" : "off");
  document.body.classList.toggle("still", !state.animate);
});

/* ================= starting up ================= */

function openFromHash() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (itemOf[h]) showPlacard(h);
  else if (h.startsWith("wall-") && wingOf[h.slice(5)]) showPlacard(`wall:${h.slice(5)}`);
}
applyFilter();
let place = null;
try { place = JSON.parse(sessionStorage.getItem("memoria.place") || "null"); sessionStorage.removeItem("memoria.place"); } catch { /* none */ }
if (place) scrollTo(0, place.y || 0);
openFromHash();
addEventListener("hashchange", openFromHash);

if (LIVE) {
  setInterval(async () => {
    try {
      const { version } = await (await fetch("/version", { cache: "no-store" })).json();
      if (version === DATA.version) return;
      try { sessionStorage.setItem("memoria.place", JSON.stringify({ y: scrollY })); } catch { /* private mode */ }
      location.reload();
    } catch { /* server stopped or restarting; try again next tick */ }
  }, 1500);
}
