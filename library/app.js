// DATA and LIVE come from the inline script in template.html, which core.py fills in.

const KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/";

/* ---------- helpers ---------- */
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const hash = s => [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const plural = (n, w, many = w + "s") => `${n} ${n === 1 ? w : many}`;

function roman(n) {
  const R = [[1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"], [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]];
  let s = "";
  for (const [v, r] of R) while (n >= v) { s += r; n -= v; }
  return s;
}

function luminance(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
  if (!m) return 0;
  const [r, g, b] = [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16) / 255)
    .map(c => (c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4));
  return .2126 * r + .7152 * g + .0722 * b;
}

function storage(key, val) {
  try {
    if (val === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, val);
  } catch (_) { return null; }
}

const books = DATA.books;
const shelves = DATA.shelves;
const shelfById = Object.fromEntries(shelves.map(s => [s.id, s]));
const bySlug = Object.fromEntries(books.map(b => [b.slug, b]));
books.forEach(b => { b._hay = (b.title + " " + b.text).toLowerCase(); });
const shelfOf = b => shelfById[b.shelf] || { id: b.shelf, name: b.shelf, colour: "#7a7166" };
const parentOf = s => (s.part_of && shelfById[s.part_of]) || null;

const state = {
  q: "",
  shelf: null,
  arrange: storage("library.arrange") === "order" ? "order" : "subject",
  mode: storage("library.mode") === "scroll" ? "scroll" : "pages",
  fs: clamp(+storage("library.fs") || 18, 14, 24),
  animate: storage("library.animate") !== "off",
};
const words = () => state.q.toLowerCase().split(/\s+/).filter(w => w.length > 1);
const matches = b => words().every(w => b._hay.includes(w));
const inShelf = b => !state.shelf || b.shelf === state.shelf || shelfOf(b).part_of === state.shelf;

/* ---------- the library ---------- */
// Thicker books for longer chapters; heights vary a little, like a real shelf.
const spineSize = b => ({ w: Math.round(clamp(30 + Math.sqrt(b.words) * .6, 36, 76)), h: 196 + hash(b.slug) % 36 });

function spine(b) {
  const s = shelfOf(b), parent = parentOf(s);
  const { w, h } = spineSize(b);
  const cls = ["spine", luminance(s.colour) > .22 && "light", parent && "banded", !(inShelf(b) && matches(b)) && "dim"].filter(Boolean).join(" ");
  const where = parent ? `${s.name}, ${parent.name}` : s.name;
  return `<a class="${cls}" href="#${esc(b.slug)}" data-slug="${esc(b.slug)}"
    style="--cloth:${esc(s.colour)};--band:${esc(parent ? parent.colour : "transparent")};--w:${w}px;--h:${h}px"
    title="${esc(`${b.title} (Vol. ${roman(b.num)}, ${where})`)}" aria-label="${esc(`Volume ${b.num}: ${b.title}. ${where}.`)}">
    <span class="t">${esc(b.spine)}</span><span class="no">${roman(b.num)}</span></a>`;
}

// Odds and ends for the free end of each bay, dealt out in turn. Crystals take
// the colour of the bay's cloth.
const PROPS = [
  ["globe", `<svg viewBox="0 0 70 108" width="70" height="108">
    <ellipse cx="35" cy="104" rx="22" ry="4" class="pd"/><rect x="32" y="82" width="6" height="22" class="pb"/>
    <circle cx="35" cy="44" r="28" class="sea"/>
    <g class="land" transform="rotate(-20 35 44)"><path d="M18 30c6-6 14-5 17 0s-2 9 3 13-4 10-10 6-3-8-9-9-6-6-1-10z"/>
      <path d="M42 22c5-2 12 2 14 8s-3 5-6 4-9-1-9-6 0-5 1-6z"/><path d="M40 52c6-2 12 1 12 6s-6 10-11 9-5-4-3-7-4-6 2-8z"/></g>
    <circle cx="35" cy="44" r="28" fill="none" stroke="rgb(0 0 0 / .3)" stroke-width="7" stroke-dasharray="0 44 88 44" transform="rotate(20 35 44)"/>
    <path d="M35 8a36 36 0 0 1 0 72" class="ring" stroke-width="3"/><circle cx="35" cy="8" r="3" class="pb"/><path d="M29 80h12v4H29z" class="pb"/></svg>`],
  ["crystals", `<svg viewBox="0 0 78 86" width="78" height="86">
    <path d="M36 84 30 30 40 4l10 26-4 54z" class="gem"/><path d="M40 4l10 26-4 54h-6z" class="gem3"/>
    <path d="M20 84 10 50l8-16 11 18 2 32z" class="gem2"/><path d="M18 34l11 18 2 32h-6z" class="gem3"/>
    <path d="M50 84l3-40 10-14 6 22-8 32z" class="gem2"/><path d="M63 30l6 22-8 32h-4z" class="gem3"/>
    <path d="M6 84 4 68l6-8 6 12v12z" class="gem"/>
    <path d="M0 86q9-9 22-5 16-7 32 0 12-5 24 5z" class="rock"/></svg>`],
  ["stack", `<svg viewBox="0 0 100 66" width="100" height="66">
    <rect x="1" y="46" width="96" height="20" rx="2" fill="#5b2b22"/><rect x="1" y="46" width="96" height="20" rx="2" fill="none" stroke="rgb(0 0 0 / .35)"/>
    <path d="M10 49v14M14 49v14M84 49v14M88 49v14" stroke="#d9bb70" stroke-width="1.4" opacity=".75"/>
    <rect x="8" y="29" width="84" height="17" rx="2" fill="#27463a"/><rect x="8" y="29" width="84" height="17" rx="2" fill="none" stroke="rgb(0 0 0 / .35)"/>
    <rect x="36" y="33" width="28" height="9" rx="1" fill="#d9bb70" opacity=".8"/>
    <rect x="3" y="15" width="78" height="14" rx="2" fill="#6d5230"/><rect x="3" y="15" width="78" height="14" rx="2" fill="none" stroke="rgb(0 0 0 / .35)"/>
    <path d="M11 17v10M73 17v10" stroke="#d9bb70" stroke-width="1.4" opacity=".75"/>
    <path d="M58 15c0-6 6-10 10-10h16c3 0 3 4 0 4H69c-3 0-5 3-5 6z" fill="#e8dcc0"/></svg>`],
  ["candle", `<svg viewBox="0 0 48 120" width="48" height="120">
    <ellipse cx="22" cy="114" rx="20" ry="5" class="pd"/><ellipse cx="22" cy="112" rx="19" ry="4" class="pb"/>
    <circle cx="42" cy="107" r="5" class="ring" stroke-width="2.5"/><path d="M13 101h18l-2 10H15z" class="pd"/>
    <rect x="15" y="46" width="14" height="57" rx="1.5" class="wax"/><path d="M15 48q0 12 3 14 2-1 2-9 3 0 3-5z" class="wax2"/>
    <rect x="21.4" y="38" width="1.2" height="9" fill="#2a1d0f"/>
    <path class="flame" d="M22 14c5 10 6 16 0 26-6-10-5-16 0-26z"/><path d="M22 28c2 4 2 7 0 10-2-3-2-6 0-10z" fill="#fff4d2"/></svg>`],
  ["hourglass", `<svg viewBox="0 0 50 96" width="50" height="96">
    <path d="M9 8c0 26 13 32 13 40S9 62 9 88h32c0-26-13-32-13-40s13-14 13-40z" class="glass"/>
    <path d="M13 27c2 10 10 16 11 20h2c1-4 9-10 11-20z" class="sand"/><rect x="24.4" y="47" width="1.2" height="26" class="sand"/>
    <path d="M11 88c2-11 9-16 14-17 5 1 12 6 14 17z" class="sand"/>
    <rect x="4" y="8" width="3" height="80" class="pd"/><rect x="43" y="8" width="3" height="80" class="pd"/>
    <rect x="1" y="1" width="48" height="8" rx="2" class="pb"/><rect x="1" y="87" width="48" height="8" rx="2" class="pb"/></svg>`],
];

function bookcase(label, list, id, i, colour) {
  const [kind, svg] = PROPS[i % PROPS.length];
  return `<section class="case" data-group="${esc(id)}" aria-label="${esc(label)}">
    <div class="case-head"><span class="plate">${esc(label)}</span></div>
    <div class="row">${list.map(spine).join("")}<span class="bookend" aria-hidden="true"></span>
      <span class="prop ${kind}" style="--gem:${esc(colour || "#3d7bb0")}" aria-hidden="true">${svg}</span></div></section>`;
}

function bookcases() {
  if (state.arrange === "order") return bookcase("The Complete Lore, in Chapter Order", books, "all", 3);
  return shelves.filter(s => !parentOf(s)).map(g => {
    const ids = new Set(shelves.filter(s => s === g || s.part_of === g.id).map(s => s.id));
    return { g, list: books.filter(b => ids.has(b.shelf)) };
  }).filter(x => x.list.length).map(({ g, list }, i) => bookcase(g.plank || g.name, list, g.id, i, g.colour)).join("");
}

function legend() {
  const used = new Set(books.map(b => b.shelf));
  const keys = shelves.filter(s => used.has(s.id) || shelves.some(c => c.part_of === s.id && used.has(c.id)));
  return `<button type="button" class="key all" data-shelf="" aria-pressed="${!state.shelf}">All subjects</button>` +
    keys.map(s => `<button type="button" class="key" data-shelf="${esc(s.id)}" aria-pressed="${state.shelf === s.id}" title="${esc(s.blurb || "")}"><i style="background:${esc(s.colour)}"></i>${esc(s.name)}</button>`).join("");
}

function snippet(b, ws) {
  const lower = b.text.toLowerCase();
  const at = lower.indexOf(ws[0]);
  if (at < 0) return "";
  const a = Math.max(0, b.text.lastIndexOf(" ", Math.max(0, at - 90)) + 1), z = Math.min(b.text.length, at + 140);
  const re = new RegExp(ws.map(w => reEsc(esc(w))).join("|"), "gi");
  return (a ? "…" : "") + esc(b.text.slice(a, z)).replace(re, "<mark>$&</mark>") + (z < b.text.length ? "…" : "");
}

function results() {
  const ws = words();
  if (!ws.length) return "";
  const hits = books.filter(b => inShelf(b) && matches(b));
  if (!hits.length) return `<p class="empty">No volume mentions “${esc(state.q)}”.</p>`;
  return `<h2>Found in ${plural(hits.length, "volume")}</h2><ul class="hits">` + hits.map(b =>
    `<li><a href="#${esc(b.slug)}"><i style="background:${esc(shelfOf(b).colour)}"></i><b>${esc(b.title)}</b><small>Vol. ${roman(b.num)} · ${esc(shelfOf(b).name)}</small><span>${snippet(b, ws)}</span></a></li>`).join("") + "</ul>";
}

function banners() {
  let h = "";
  if (DATA.error) h += `<div class="error">${esc(DATA.error)}\n\nFix the file and save; this page reloads itself.</div>`;
  if (DATA.warnings && DATA.warnings.length) h += `<div class="error">${DATA.warnings.map(esc).join("\n")}</div>`;
  return h;
}

function renderFront() {
  const subjects = new Set(books.map(b => (parentOf(shelfOf(b)) || shelfOf(b)).id)).size;
  return banners() + `<div class="front">
    <div class="intro">
      <p class="tier">THREADMINT LIBRARY · CROWNWEAVE · ACCESS TIER: PUBLIC</p>
      <h1>The Lore of Tessarion</h1>
      <p>Every volume of the lore-book, shelved by subject. A book's binding tells you what it concerns; the key below names each cloth.
      The Weaves of Crownweave share their mother city's shelf, and each carries a band of Crownweave gold at the head of its spine. Take a volume down to read it.</p>
      <p class="tier">${plural(books.length, "volume")} · ${plural(subjects, "shelf", "shelves")}</p>
    </div>
    <div class="controls">
      <div class="legend" role="group" aria-label="Highlight a subject">${legend()}</div>
      <div class="options">
        <label class="switch"><input type="checkbox" id="animate"${state.animate ? " checked" : ""}> Animate books</label>
        <div class="seg" role="group" aria-label="Arrange the books">
          <button type="button" data-arrange="subject" aria-pressed="${state.arrange === "subject"}">By subject</button>
          <button type="button" data-arrange="order" aria-pressed="${state.arrange === "order"}">In chapter order</button>
        </div>
      </div>
    </div>
    <div class="bookcase"><div class="crown"></div><div class="cases ${state.arrange}">${bookcases()}</div><div class="plinth"></div></div>
    <div class="results" id="results">${results()}</div>
  </div>`;
}

/* ---------- the reader ---------- */
let R = null;  // the open book: { b, n, stride, cols, spreads, spread, titleCol, heads, marks }

function whereOf(b) {
  const s = shelfOf(b), parent = parentOf(s);
  return parent ? `${s.name} · ${parent.name}` : s.name;
}

const titlePage = b => `<section class="titlepage">
    <div class="lib">Threadmint Library · Volume ${roman(b.num)}</div>
    <div class="orn"></div>
    <div class="bt">${esc(b.title)}</div>
    <div class="orn"></div>
    <div class="sub">${esc(whereOf(b))}</div>
  </section>`;

const EXPLATE = `<div class="explate"><small>Ex Libris</small><b>Threadmint Library</b>Crownweave</div>`;

function readerHTML(b) {
  const i = books.indexOf(b), next = books[i + 1];
  const where = whereOf(b);
  const body = b.words ? b.html : `<p class="unwritten">The pages of this volume are still blank. Its account has yet to be set down.</p>`;
  return `<div class="rbar">
      <a class="back" href="#">← Library</a>
      <div class="rtitle"><span class="sw"></span><div><b>${esc(b.title)}</b><small>Vol. ${roman(b.num)} · ${esc(where)}</small></div></div>
      <div class="rtools">
        <span class="hitbar" hidden></span>
        <button type="button" class="btn" data-act="toc" aria-expanded="false">Contents</button>
        <div class="seg" role="group" aria-label="Reading mode">
          <button type="button" data-mode="pages" aria-pressed="${state.mode === "pages"}">Pages</button>
          <button type="button" data-mode="scroll" aria-pressed="${state.mode === "scroll"}">Scroll</button>
        </div>
        <div class="seg" role="group" aria-label="Text size">
          <button type="button" data-fs="-1" aria-label="Smaller text">A−</button>
          <button type="button" data-fs="1" aria-label="Larger text">A+</button>
        </div>
      </div>
      <nav class="toc" hidden aria-label="Contents"></nav>
    </div>
    <div class="stage">
      <button type="button" class="turn" data-go="-1" aria-label="Previous page">‹</button>
      <div class="book">
        <div class="sheet l"><span class="rh"></span><span class="folio"></span>${EXPLATE}</div>
        <div class="sheet r"><span class="rh"></span><span class="folio"></span></div>
        <div class="viewport"><div class="flow">
          <div class="endspacer"></div>
          ${titlePage(b)}
          ${body}
          <div class="finis"><div class="orn"></div><p>Here ends <i>${esc(b.title)}</i>.</p>
            ${next ? `<a href="#${esc(next.slug)}">Next: Vol. ${roman(next.num)}, ${esc(next.title)} →</a>` : `<a href="#">Return to the library</a>`}</div>
          <div class="end-mark"></div>
        </div></div>
      </div>
      <button type="button" class="turn" data-go="1" aria-label="Next page">›</button>
    </div>
    <div class="scrub">
      <button type="button" class="turn" data-go="-1" aria-label="Previous page">‹</button>
      <input type="range" min="0" max="0" value="0" aria-label="Turn to page">
      <span class="where"></span>
      <button type="button" class="turn" data-go="1" aria-label="Next page">›</button>
    </div>`;
}

function slugify(t, used) {
  let id = t.toLowerCase().replace(/[’']/g, "").replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "") || "section";
  let k = id, n = 2;
  while (used.has(k)) k = `${id}-${n++}`;
  used.add(k);
  return k;
}

function prepare(flow) {
  // Heading anchors and the contents list.
  const used = new Set();
  const hs = [...flow.querySelectorAll("h1, h2, h3")].filter(h => h.textContent.trim());
  hs.forEach(h => { h.id = slugify(h.textContent.trim(), used); });
  const top = hs.filter(h => h.tagName !== "H3");
  const listed = hs.length <= 40 || top.length < 4 ? hs : top;
  R.heads = top.length ? top : hs;
  $(".toc").innerHTML = `<p>Contents</p><a href="#" data-to="">Title page</a>` + listed.map(h =>
    `<a href="#" data-to="${esc(h.id)}" class="${h.tagName === "H3" && top.length ? "l3" : ""}">${esc(h.textContent.trim())}</a>`).join("");

  // Images come from the pool (static export) or the live server.
  flow.querySelectorAll("img[data-ref]").forEach(img => {
    const src = DATA.images[img.dataset.ref] || (LIVE ? "images/" + img.dataset.ref : "");
    if (!src) {
      img.outerHTML = `<span class="missing">[${esc(img.dataset.ref)} is missing]</span>`;
      return;
    }
    img.loading = "eager";
    img.addEventListener("load", relayoutSoon);
    img.src = src;
  });

  // Google Docs tables use a row with only its first cell filled as a
  // sub-heading ("WEAPONS (TIER I)"); let that cell span the row.
  flow.querySelectorAll("tr").forEach(tr => {
    const [first, ...rest] = tr.children;
    const blank = c => !c.textContent.trim() && !c.querySelector("img");
    if (rest.length && !blank(first) && rest.every(blank)) {
      first.colSpan = rest.length + 1;
      rest.forEach(c => c.remove());
      tr.classList.add("band");
    }
  });

  // Drop cap on the first real paragraph.
  const first = [...flow.children].find(el => el.tagName === "P" && el.textContent.trim().length > 140 && /^[A-Za-z]/.test(el.textContent.trim()));
  if (first) first.classList.add("opening");

  if (flow.querySelector(".math")) {
    if (window.katex) typeset(flow);
    else ensureKatex().then(() => { if (R && R.flow === flow) { typeset(flow); relayoutSoon(); } }, () => {});
  }
  R.marks = highlight(flow);
}

let katexLoading = null;
function ensureKatex() {
  if (!katexLoading) {
    const load = (tag, attrs) => new Promise((ok, fail) => {
      const el = Object.assign(document.createElement(tag), attrs, { onload: ok, onerror: fail });
      document.head.append(el);
    });
    katexLoading = Promise.all([
      load("link", { rel: "stylesheet", href: KATEX + "katex.min.css" }),
      load("script", { src: KATEX + "katex.min.js" }),
    ]);
  }
  return katexLoading;
}

function typeset(root) {
  root.querySelectorAll(".math:not(.done)").forEach(el => {
    try {
      katex.render(el.textContent, el, { throwOnError: false, strict: false });
      el.classList.add("done");
    } catch (_) { /* leave the TeX source showing */ }
  });
}

function highlight(flow) {
  const ws = words();
  if (!ws.length) return [];
  const re = new RegExp(ws.map(reEsc).join("|"), "gi");
  const walker = document.createTreeWalker(flow, NodeFilter.SHOW_TEXT, {
    acceptNode: n => n.parentElement.closest(".math, .titlepage, .finis, .redact") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  const marks = [];
  for (const node of nodes) {
    const t = node.nodeValue;
    re.lastIndex = 0;
    if (!re.test(t)) continue;
    re.lastIndex = 0;
    const frag = document.createDocumentFragment();
    let last = 0, m;
    while ((m = re.exec(t))) {
      frag.append(t.slice(last, m.index));
      const mk = document.createElement("mark");
      mk.textContent = m[0];
      frag.append(mk);
      marks.push(mk);
      last = m.index + m[0].length;
    }
    frag.append(t.slice(last));
    node.replaceWith(frag);
  }
  return marks;
}

/* Pagination: the text flows through CSS columns exactly one page wide and
   one page tall, so extra pages overflow sideways; showing a spread shifts the
   strip left to it. Turning a page (flip, below) animates over the top. */
function colOf(el, last) {
  const rects = el.getClientRects();
  if (!rects.length) return null;
  const r = last ? rects[rects.length - 1] : rects[0];
  return Math.max(0, Math.floor((r.left - R.flow.getBoundingClientRect().left + 2) / R.stride));
}

function currentAnchor() {
  if (!R || !R.laidOut) return null;
  const kids = [...R.flow.children];
  if (state.mode === "scroll") {
    const top = $(".rbar").getBoundingClientRect().bottom + 4;
    return kids.find(el => el.getBoundingClientRect().bottom > top) || null;
  }
  const firstCol = R.spread * R.n;
  return kids.find(el => (colOf(el, true) ?? -1) >= firstCol) || null;
}

function layout(target) {
  if (!R) return;
  if (target === undefined) target = currentAnchor();
  const book = $(".book"), flow = R.flow;
  const scroll = state.mode === "scroll";
  document.body.classList.toggle("scrollmode", scroll);
  book.classList.toggle("scroll", scroll);
  flow.classList.toggle("flat", scroll);
  flow.style.setProperty("--fs", state.fs + "px");
  if (scroll) {
    book.removeAttribute("style");
    book.classList.remove("single");
    flow.style.transform = "";
    R.laidOut = true;
    if (target && target !== flow.firstElementChild) target.scrollIntoView({ block: "start" });
    else window.scrollTo(0, 0);
    updateChrome();
    return;
  }

  const narrow = innerWidth < 700;
  const B = narrow ? 8 : 14, O = narrow ? 20 : 46, I = 34, HEAD = narrow ? 34 : 46, FOOT = narrow ? 34 : 44;
  const stage = $(".stage");
  const availW = stage.clientWidth - (innerWidth <= 900 ? 12 : 2 * 58 + 12);
  const availH = innerHeight - $(".rbar").offsetHeight - $(".scrub").offsetHeight - (narrow ? 16 : 40);
  const n = availW >= 880 ? 2 : 1;
  const ph = Math.round(clamp(availH - 2 * B - HEAD - FOOT, 300, 920));
  const fit = n === 2 ? (availW - 2 * B - 2 * (O + I)) / 2 : availW - 2 * B - 2 * O;
  const pw = Math.floor(Math.max(200, Math.min(fit, ph * .74, state.fs * 34)));
  const gap = n === 2 ? 2 * I : 2 * O;
  const sw = n === 2 ? O + pw + I : O + pw + O;
  const vars = { "--b": B, "--o": O, "--head": HEAD, "--foot": FOOT, "--pw": pw, "--ph": ph, "--gap": gap, "--vw": n * pw + (n - 1) * gap, "--sw": sw };
  book.removeAttribute("style");
  for (const [k, v] of Object.entries(vars)) book.style.setProperty(k, v + "px");
  book.style.setProperty("--n", n);
  book.style.width = 2 * B + n * sw + "px";
  book.style.height = 2 * B + HEAD + ph + FOOT + "px";
  book.classList.toggle("single", n === 1);

  R.n = n;
  R.stride = pw + gap;
  R.titleCol = n === 2 ? 1 : 0;
  flow.style.transform = "none";
  R.cols = (colOf($(".end-mark", flow)) ?? 0) + 1;
  R.spreads = Math.max(1, Math.ceil(R.cols / n));
  R.headCols = R.heads.map(h => [colOf(h) ?? 0, h.textContent.trim()]);
  R.laidOut = true;
  const col = target ? colOf(target) : 0;
  go(Math.floor((col ?? 0) / n), true);
}

function go(s, instant) {
  if (!R) return;
  if (state.mode === "scroll") return;
  endFlip();  // a page still turning lands at once
  const from = R.spread;
  R.spread = clamp(s, 0, R.spreads - 1);
  R.flow.style.transform = `translateX(${-R.spread * R.n * R.stride}px)`;
  if (!instant && R.spread !== from && motionOK()) flip(from, R.spread);
  updateChrome();
  save();
}

/* ---------- turning a page ----------
   The book underneath already shows the new spread. Over it go the page being
   turned (the leaf) and, until the leaf lands, the old page it will land on.
   The leaf bends like paper: it is a chain of narrow strips, each hinged to the
   one before, and every frame each strip is turned a little further than its
   neighbour nearer the spine. The outer edge leads, as if lifted by a finger,
   and the spine side follows; each strip is shaded by how far it has turned
   from the light, and the leaf's shadow sweeps across the pages beneath. */
const STRIPS = 12;
const FLIP_MS = 850;
const LAG = .3;  // how far the spine side trails the outer edge
let flipping = null;

// Just the text on one column: the flow's children that reach it, laid out
// exactly as in the book by standing a spacer in for everything before them.
function pageText(col) {
  const flow = R.flow, kids = [...flow.children];
  const text = flow.cloneNode(false);
  const i = kids.findIndex(el => (colOf(el, true) ?? -1) >= col);
  if (i < 0) return text;
  const first = kids[i], startCol = colOf(first) ?? col;
  let j = i + 1;
  for (; j < kids.length; j++) {
    const c = colOf(kids[j]);
    if (c !== null && c > col) break;
  }
  const copies = kids.slice(i, j).map(k => k.cloneNode(true));
  const y = first.getClientRects()[0].top - flow.getBoundingClientRect().top;
  const mt = parseFloat(getComputedStyle(first).marginTop) || 0;
  const pad = document.createElement("div");
  if (y < mt + .5) {
    copies[0].style.marginTop = "0px";  // its margin was swallowed by the column break
    pad.style.height = `${Math.max(0, y)}px`;
  } else {
    pad.style.height = `${y - mt}px`;
  }
  text.append(pad, ...copies);
  text.style.transform = `translateX(${-(col - startCol) * R.stride}px)`;
  return text;
}

// A page dressed as a sheet of paper: running head, folio and text.
function face(col, side) {
  const el = document.createElement("div");
  el.className = `sheet ${side} face`;
  if (col === null) {
    // the back of the only page in one-page mode
  } else if (R.n === 2 && side === "l" && col === 0) {
    el.classList.add("endpaper");
    el.innerHTML = EXPLATE;
  } else {
    const front = col <= R.titleCol, blank = col >= R.cols;
    const rh = front || blank ? "" : (R.n === 2 && side === "l" ? R.b.title : sectionAt(col));
    el.innerHTML = `<span class="rh">${esc(rh)}</span><span class="folio">${front || blank ? "" : pageNo(col)}</span><div class="fview"></div>`;
    $(".fview", el).append(pageText(col));
  }
  return el;
}

function flip(from, to) {
  const book = $(".book"), two = R.n === 2, fwd = to > from;
  const rightOf = s => (two ? 2 * s + 1 : s);
  // Forward: the old right page lifts, showing the new left page on its back,
  // and lands on the old left page. Backward: the old left page lifts, showing
  // the new right page, and lands on the old right page.
  const still = fwd ? (two ? face(2 * from, "l") : null) : face(rightOf(from), "r");
  const front = face(rightOf(fwd ? from : to), "r");
  const back = face(two ? 2 * (fwd ? to : from) : null, "l");

  const leaf = document.createElement("div");
  leaf.className = "leaf";
  const cast = document.createElement("div");
  cast.className = "cast";
  if (still) {
    still.classList.add("still");
    book.append(still);
  }
  book.append(cast, leaf);

  // Build the chain of strips, each carrying its slice of both sides.
  const W = leaf.getBoundingClientRect().width, w = W / STRIPS;
  const strips = [];
  let parent = leaf;
  for (let i = 0; i < STRIPS; i++) {
    const strip = document.createElement("div");
    strip.className = "strip";
    strip.style.width = `${w + .6}px`;  // a hair of overlap hides the seams
    strip.style.left = i ? `${w}px` : "0";
    const slice = (page, x, cls) => {
      const s = document.createElement("div");
      s.className = `slice ${cls}`;
      page.style.left = `${x}px`;
      s.append(page, Object.assign(document.createElement("i"), { className: "shade" }));
      return s;
    };
    strip.append(slice(i === STRIPS - 1 ? front : front.cloneNode(true), -i * w, "sf"),
      slice(i === STRIPS - 1 ? back : back.cloneNode(true), -(W - (i + 1) * w), "sb"));
    parent.append(strip);
    strips.push({ el: strip, shades: strip.querySelectorAll(":scope > .slice > .shade") });
    parent = strip;
  }

  // The leaf's angle at distance u from the spine (0) to the outer edge (1),
  // at time g: 0 is lying flat on the right, -180 lying flat on the left.
  const ease = x => x * x * (3 - 2 * x);
  const angleAt = (u, g) => {
    const q = Math.min(1, Math.max(0, (g - LAG * (1 - u)) / (1 - LAG)));
    return fwd ? -180 * ease(q) : -180 * (1 - ease(q));
  };
  const spineX = two ? book.clientWidth / 2 : parseFloat(getComputedStyle(book).getPropertyValue("--b"));

  const draw = g => {
    let prev = 0, edge = 0;
    strips.forEach((s, i) => {
      const a = angleAt(i / STRIPS, g);
      s.el.style.transform = `rotateY(${(a - prev).toFixed(2)}deg)`;
      // Lit face-on, darker as it turns edge-on, darker still where it bends.
      const shade = (1 - Math.abs(Math.cos(a * Math.PI / 180))) * .5 + Math.min(.25, Math.abs(a - prev) * .012);
      s.shades.forEach(el => { el.style.opacity = shade.toFixed(3); });
      edge += w * Math.cos(a * Math.PI / 180);
      prev = a;
    });
    // The shadow falls just beyond the leaf's outer edge, strongest mid-turn.
    // It is a fixed soft band slid along and faded on the GPU, never repainted.
    cast.style.transform = `translate3d(${(spineX + edge - 80).toFixed(1)}px, 0, 0)`;
    cast.style.opacity = Math.sin(Math.PI * g).toFixed(3);
    // With one page there is nothing beside it to land on, so it fades as it goes.
    if (!two) leaf.style.opacity = (fwd ? 1 - Math.max(0, (g - .55) / .45) : Math.min(1, g / .45)).toFixed(3);
  };

  draw(0);
  let raf = 0;
  const start = performance.now();
  const frame = now => {
    const g = Math.min(1, (now - start) / FLIP_MS);
    draw(g);
    if (g < 1) raf = requestAnimationFrame(frame);
    else if (flipping === me) endFlip();
  };
  const me = { done() { cancelAnimationFrame(raf); leaf.remove(); cast.remove(); if (still) still.remove(); } };
  flipping = me;
  raf = requestAnimationFrame(frame);
}

function endFlip() {
  if (!flipping) return;
  const f = flipping;
  flipping = null;
  f.done();
}

const pageNo = c => c - R.titleCol;
function sectionAt(c) {
  let name = R.b.title;
  for (const [hc, t] of R.headCols || []) { if (hc <= c) name = t; else break; }
  return name;
}

function updateChrome() {
  if (!R) return;
  const scroll = state.mode === "scroll";
  document.querySelectorAll(".turn[data-go='-1']").forEach(b => { b.disabled = scroll || R.spread <= 0; });
  document.querySelectorAll(".turn[data-go='1']").forEach(b => { b.disabled = scroll || R.spread >= R.spreads - 1; });
  if (scroll) return;
  const cols = R.n === 2 ? [R.spread * 2, R.spread * 2 + 1] : [R.spread];
  const sheets = R.n === 2 ? [$(".sheet.l"), $(".sheet.r")] : [$(".sheet.r")];
  $(".sheet.l").classList.toggle("endpaper", R.n === 2 && R.spread === 0);
  sheets.forEach((sh, k) => {
    const c = cols[k], front = c <= R.titleCol, blank = c >= R.cols;
    $(".rh", sh).textContent = front || blank ? "" : (R.n === 2 && k === 0 ? R.b.title : sectionAt(c));
    $(".folio", sh).textContent = front || blank ? "" : pageNo(c);
  });
  const total = pageNo(R.cols - 1);
  const shown = cols.filter(c => c > R.titleCol && c < R.cols).map(pageNo);
  $(".scrub .where").textContent = !shown.length ? `Title page · ${plural(Math.max(total, 0), "page")}`
    : shown.length === 2 ? `Pages ${shown[0]}–${shown[1]} of ${total}` : `Page ${shown[0]} of ${total}`;
  const range = $(".scrub input");
  range.max = R.spreads - 1;
  range.value = R.spread;
}

function save() {
  if (!R || !R.laidOut) return;
  const a = currentAnchor();
  if (a) storage("library.at." + R.b.slug, String([...R.flow.children].indexOf(a)));
}

let relayoutTimer = 0;
function relayoutSoon() {
  clearTimeout(relayoutTimer);
  relayoutTimer = setTimeout(() => layout(), 90);
}

function goTo(el) {
  if (!el) return;
  if (state.mode === "scroll") el.scrollIntoView({ block: "start", behavior: "smooth" });
  else go(Math.floor((colOf(el) ?? 0) / R.n));
}

function nextHit() {
  if (!R || !R.marks.length) return;
  let i;
  if (state.mode === "scroll") {
    const y = $(".rbar").getBoundingClientRect().bottom + 10;
    i = R.marks.findIndex(m => m.getBoundingClientRect().top > y + 5);
  } else {
    const lastCol = R.spread * R.n + R.n - 1;
    i = R.marks.findIndex(m => colOf(m) > lastCol);
  }
  goTo(R.marks[i < 0 ? 0 : i]);
}

// hidden: lay the reader out invisibly under the library (see pullOut).
function openBook(b, section, hidden) {
  const s = shelfOf(b);
  if (!hidden) {
    document.body.classList.remove("home", "opening");
    document.body.classList.add("reading");
  }
  const reader = $("#reader");
  reader.style.setProperty("--cloth", s.colour);
  reader.innerHTML = readerHTML(b);
  R = { b, flow: $(".flow", reader), n: 1, stride: 1, cols: 1, spreads: 1, spread: 0, titleCol: 0, heads: [], marks: [], laidOut: false };
  prepare(R.flow);
  document.title = `${b.title} · Threadmint Library`;
  const hits = $(".hitbar");
  if (R.marks.length) {
    hits.hidden = false;
    hits.innerHTML = `${plural(R.marks.length, "match", "matches")} for “${esc(state.q)}” <button type="button" class="btn" data-act="next-hit">Next ↓</button><button type="button" class="btn" data-act="clear-q" aria-label="Clear search">✕</button>`;
  }

  let target = null;
  if (section) target = document.getElementById(section);
  else if (R.marks.length) target = R.marks[0];
  else {
    const at = storage("library.at." + b.slug);
    if (at !== null) target = R.flow.children[+at] || null;
  }
  if (!hidden) window.scrollTo(0, 0);
  layout(target);
}

/* ---------- taking a book off the shelf ----------
   The reader opens invisibly underneath first, so the 3D book knows exactly
   where to land: it slides out of the shelf, flies there turning from spine
   to cover, and opens onto the endpaper and title page the reader shows. */
let pulling = null;   // the animation in progress: { anims, skip, ov }
let libraryY = 0;     // where the library was scrolled when a book was taken
const motionOK = () => state.animate && "animate" in Element.prototype;
const spineK = () => (matchMedia("(max-width: 900px)").matches ? .84 : 1);  // matches .case --k
const at = (x, y, z, sc, ry) => `translate3d(${x}px, ${y}px, ${z}px) scale3d(${sc}, ${sc}, ${sc}) rotateY(${ry}deg)`;

// Where the closed cover sits when the book lies open: the right half of the
// reader's spread, or the whole page on a phone.
function landing() {
  const bookEl = $(".book"), br = bookEl.getBoundingClientRect();
  const B = parseFloat(bookEl.style.getPropertyValue("--b")) || 14;
  const single = bookEl.classList.contains("single");
  let to;
  if (state.mode === "scroll") {
    const h = Math.min(innerHeight * .72, 680), w = Math.min(h * .72, innerWidth * .46);
    to = { left: innerWidth / 2, top: (innerHeight - h) / 2, width: w, height: h };
  } else if (single) to = br;
  else to = { left: br.left + br.width / 2, top: br.top, width: br.width / 2, height: br.height };
  return { to, B, single };
}

// The 3D book: spine, cover (gilt outside, endpaper inside), title page and
// back board, built at its open-book size. sw x sh is the spine on the shelf.
function buildPull(b, sw, sh, k, { to, B, single }) {
  const s = shelfOf(b), parent = parentOf(s), light = luminance(s.colour) > .22;
  const W = to.width, H = to.height, f = H / sh, T = sw * f;
  const ov = document.createElement("div");
  ov.className = "pull";
  ov.innerHTML = `<div class="pull-bg"></div>
    <div class="pbook" style="--cloth:${esc(s.colour)};--b:${B}px;left:${to.left}px;top:${to.top}px;width:${W}px;height:${H}px;font-size:${H / 30}px;transform-origin:50% 50% ${-T / 2}px">
      <div class="pboard"></div>
      <div class="ppages" style="inset:${B}px ${B}px ${B}px ${single ? B : 0}px;font-size:${state.fs}px">${titlePage(b)}</div>
      <div class="spine pspine${light ? " light" : ""}${parent ? " banded" : ""}"
        style="--cloth:${esc(s.colour)};--band:${esc(parent ? parent.colour : "transparent")};--w:${sw / k}px;--h:${sh / k}px;--k:${k * f};left:${-T}px">
        <span class="t">${esc(b.spine)}</span><span class="no">${roman(b.num)}</span></div>
      <div class="pcover">
        <div class="pc-front${light ? " light" : ""}"><div class="pc-no">VOLUME ${roman(b.num)}</div><div class="orn"></div>
          <div class="pc-title">${esc(b.title)}</div><div class="orn"></div><div class="pc-shelf">${esc(whereOf(b))}</div></div>
        <div class="pc-inside"><div class="ep">${EXPLATE}</div></div>
      </div>
    </div>`;
  const me = pulling = { anims: [], skip: false, ov };
  ov.addEventListener("click", () => { me.skip = true; me.anims.forEach(a => a.finish()); });
  const run = (el, frames, ms, easing, delay = 0) => {
    const a = el.animate(frames, { duration: me.skip ? 0 : ms, delay: me.skip ? 0 : delay, easing, fill: "forwards" });
    me.anims.push(a);
    return a.finished;
  };
  // Where the book stands on the shelf, relative to its open position. Turned
  // spine-on, the spine sits W/2 in front of the pivot, hence the z shift.
  const shelved = from => {
    const s0 = sh / H, dx = from.left + sw / 2 - (to.left + W / 2), dy = from.top + sh / 2 - (to.top + H / 2);
    return { home: at(dx, dy, -W / 2 * s0, s0, 90), lifted: at(dx, dy - sh * .1, -W / 2 * s0, s0 * 1.14, 90) };
  };
  return { me, ov, run, shelved, pb: $(".pbook", ov), cover: $(".pcover", ov), bg: $(".pull-bg", ov) };
}

// Taking a book down: the reader opens invisibly underneath first, so the 3D
// book knows exactly where to land. It slides off the shelf, flies there
// turning from spine to cover, and opens onto the endpaper and title page.
async function pullOut(sp) {
  const b = bySlug[sp.dataset.slug];
  if (!b) return;
  const from = sp.getBoundingClientRect();
  const k = parseFloat(getComputedStyle(sp).getPropertyValue("--k")) || 1;
  libraryY = window.scrollY;
  lastBook = b.slug;
  history.pushState(null, "", "#" + b.slug);
  document.body.classList.add("opening");
  openBook(b, null, true);

  const { me, ov, run, shelved, pb, cover, bg } = buildPull(b, from.width, from.height, k, landing());
  const { home, lifted } = shelved(from);
  document.body.append(ov);
  sp.style.visibility = "hidden";
  try {
    await run(pb, [{ transform: home }, { transform: lifted }], 320, "cubic-bezier(.2, .7, .3, 1)");
    await Promise.all([
      run(pb, [{ transform: lifted }, { transform: at(0, 0, 0, 1, 0) }], 760, "cubic-bezier(.5, 0, .2, 1)"),
      run(bg, [{ opacity: 0 }, { opacity: 1 }], 600, "ease"),
    ]);
    await run(cover, [{ transform: "rotateY(0deg)" }, { transform: "rotateY(-180deg)" }], 760, "cubic-bezier(.45, .05, .25, 1)", 60);
    if (pulling !== me) return;
    document.body.classList.remove("opening", "home");
    document.body.classList.add("reading");
    window.scrollTo(0, 0);
    layout();
    await run(ov, [{ opacity: 1 }, { opacity: 0 }], 260, "ease");
  } catch (_) {
    return;  // cancelled by abortPull()
  }
  ov.remove();
  if (pulling === me) pulling = null;
}

// Putting it back is the same film run backwards: the open book fades in over
// the page, the library is laid out underneath, and the book closes, turns
// spine-on and slides back into its gap.
async function putBack(b) {
  const k = spineK(), { w, h } = spineSize(b);
  const { me, ov, run, shelved, pb, cover, bg } = buildPull(b, w * k, h * k, k, landing());
  cover.style.transform = "rotateY(-180deg)";
  bg.style.opacity = 1;
  ov.style.opacity = 0;
  document.body.append(ov);
  let sp = null;
  try {
    await run(ov, [{ opacity: 0 }, { opacity: 1 }], 220, "ease");
    if (pulling !== me) return;
    showLibrary();
    window.scrollTo(0, libraryY);
    sp = document.querySelector(`.spine[data-slug="${CSS.escape(b.slug)}"]`);
    if (!sp) throw new Error("no spine");
    const r = sp.getBoundingClientRect();
    if (r.top < 0 || r.bottom > innerHeight) sp.scrollIntoView({ block: "center" });
    sp.style.visibility = "hidden";
    const { home, lifted } = shelved(sp.getBoundingClientRect());
    await run(cover, [{ transform: "rotateY(-180deg)" }, { transform: "rotateY(0deg)" }], 680, "cubic-bezier(.45, .05, .25, 1)");
    await Promise.all([
      run(pb, [{ transform: at(0, 0, 0, 1, 0) }, { transform: lifted }], 760, "cubic-bezier(.5, 0, .2, 1)"),
      run(bg, [{ opacity: 1 }, { opacity: 0 }], 640, "ease", 80),
    ]);
    await run(pb, [{ transform: lifted }, { transform: home }], 300, "cubic-bezier(.4, 0, .6, 1)");
  } catch (_) {
    if (pulling === me) { ov.remove(); pulling = null; render(); }
    return;  // cancelled by abortPull(), or the spine is gone
  }
  sp.style.visibility = "";
  ov.remove();
  if (pulling === me) pulling = null;
  sp.focus({ preventScroll: true });
}

// Navigating mid-animation (Back, Esc, live reload) drops it on the spot.
function abortPull() {
  if (!pulling) return;
  pulling.anims.forEach(a => a.cancel());
  if (pulling.ov) pulling.ov.remove();
  pulling = null;
  document.body.classList.remove("opening");
}

/* ---------- routing ---------- */
let lastBook = null;
const hashBook = () => bySlug[decodeURIComponent(location.hash.slice(1)).split("/")[0]];

function render() {
  const [slug, section] = decodeURIComponent(location.hash.slice(1)).split("/");
  const b = bySlug[slug];
  if (b) {
    lastBook = b.slug;
    openBook(b, section);
    return;
  }
  showLibrary();
}

function showLibrary() {
  R = null;
  document.body.classList.remove("reading", "scrollmode", "opening");
  document.body.classList.add("home");
  $("#reader").innerHTML = "";
  $("#main").innerHTML = renderFront();
  document.title = "Threadmint Library";
}

function refreshFront() {
  const y = window.scrollY;
  $("#main").innerHTML = renderFront();
  window.scrollTo(0, y);
}

window.addEventListener("hashchange", () => {
  abortPull();
  if (R && R.laidOut && !hashBook() && motionOK() && document.body.classList.contains("reading")) {
    putBack(R.b);
    return;
  }
  const wasReading = !!R;
  render();
  if (!R && wasReading && lastBook) {
    const sp = document.querySelector(`.spine[data-slug="${CSS.escape(lastBook)}"]`);
    if (sp) { sp.scrollIntoView({ block: "center" }); sp.focus({ preventScroll: true }); }
  }
});

const qBox = document.getElementById("q");
qBox.addEventListener("input", () => { state.q = qBox.value; refreshFront(); });

document.addEventListener("click", ev => {
  const t = ev.target;
  if (pulling || t.closest(".pull")) return;
  const sp = t.closest("a.spine");
  if (sp && ev.button === 0 && !(ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.altKey) && motionOK()) {
    ev.preventDefault();
    pullOut(sp);
    return;
  }
  const key = t.closest(".key");
  if (key) { state.shelf = key.dataset.shelf || null; refreshFront(); return; }
  const arr = t.closest("[data-arrange]");
  if (arr) { state.arrange = arr.dataset.arrange; storage("library.arrange", state.arrange); refreshFront(); return; }
  if (!R) return;

  const toc = $(".toc");
  const act = t.closest("[data-act]")?.dataset.act;
  if (act === "toc") {
    toc.hidden = !toc.hidden;
    $("[data-act='toc']").setAttribute("aria-expanded", !toc.hidden);
    return;
  }
  if (!toc.hidden && !t.closest(".toc")) { toc.hidden = true; $("[data-act='toc']").setAttribute("aria-expanded", "false"); }
  if (act === "next-hit") return nextHit();
  if (act === "clear-q") { state.q = qBox.value = ""; openBook(R.b); return; }
  const to = t.closest("[data-to]");
  if (to) {
    ev.preventDefault();
    toc.hidden = true;
    goTo(to.dataset.to ? document.getElementById(to.dataset.to) : R.flow.firstElementChild);
    if (!to.dataset.to && state.mode === "scroll") window.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }
  const turn = t.closest("[data-go]");
  if (turn) return go(R.spread + +turn.dataset.go);
  const mode = t.closest("[data-mode]");
  if (mode && mode.dataset.mode !== state.mode) {
    const a = currentAnchor();
    state.mode = mode.dataset.mode;
    storage("library.mode", state.mode);
    document.querySelectorAll("[data-mode]").forEach(b => b.setAttribute("aria-pressed", b.dataset.mode === state.mode));
    layout(a);
    return;
  }
  const fs = t.closest("[data-fs]");
  if (fs) {
    const a = currentAnchor();
    state.fs = clamp(state.fs + +fs.dataset.fs, 14, 24);
    storage("library.fs", String(state.fs));
    layout(a);
    return;
  }
  // Tap the outer part of the page to turn it on touch screens.
  if (state.mode === "pages" && t.closest(".viewport") && !t.closest("a, button") && matchMedia("(pointer: coarse)").matches) {
    const r = $(".viewport").getBoundingClientRect(), x = (ev.clientX - r.left) / r.width;
    if (x > .66) go(R.spread + 1);
    else if (x < .34) go(R.spread - 1);
  }
});

document.addEventListener("input", ev => {
  if (ev.target.id === "animate") {
    state.animate = ev.target.checked;
    storage("library.animate", state.animate ? "on" : "off");
  }
  // Dragging the slider jumps straight there; flipping every page on the way would lag.
  if (R && ev.target.matches(".scrub input")) go(+ev.target.value, true);
});

document.addEventListener("keydown", ev => {
  if (!R || ev.target.closest("input, textarea") || ev.altKey || ev.ctrlKey || ev.metaKey) return;
  if (ev.key === "Escape") {
    const toc = $(".toc");
    if (!toc.hidden) { toc.hidden = true; return; }
    location.hash = "";
    return;
  }
  if (state.mode !== "pages") return;
  const step = { ArrowRight: 1, PageDown: 1, " ": 1, ArrowLeft: -1, PageUp: -1 }[ev.key];
  if (step) { ev.preventDefault(); go(R.spread + (ev.shiftKey && ev.key === " " ? -1 : step)); }
  else if (ev.key === "Home") { ev.preventDefault(); go(0); }
  else if (ev.key === "End") { ev.preventDefault(); go(R.spreads - 1); }
});

let touchX = null;
document.addEventListener("touchstart", ev => { touchX = ev.target.closest(".viewport") ? ev.touches[0].clientX : null; }, { passive: true });
document.addEventListener("touchend", ev => {
  if (!R || touchX === null || state.mode !== "pages") return;
  const dx = ev.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 50) go(R.spread + (dx < 0 ? 1 : -1));
  touchX = null;
});

let resizeTimer = 0, scrollTimer = 0;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (R && state.mode === "pages") layout(); }, 120);
});
window.addEventListener("scroll", () => {
  if (!R || state.mode !== "scroll") return;
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(save, 250);
}, { passive: true });
if (document.fonts) document.fonts.ready.then(() => { if (R) layout(); });

// Live mode: reload when a chapter / catalogue / template changes, keeping
// the search, highlighted subject and scroll position across the reload.
let place = null;
try {
  place = JSON.parse(sessionStorage.getItem("library.place"));
  sessionStorage.removeItem("library.place");
} catch (_) {}
if (place) {
  state.q = qBox.value = place.q || "";
  state.shelf = shelfById[place.shelf] ? place.shelf : null;
}
render();
if (place && !R) window.scrollTo(0, place.y || 0);

if (LIVE) {
  setInterval(async () => {
    try {
      const { version } = await (await fetch("/version", { cache: "no-store" })).json();
      if (version === DATA.version) return;
      save();
      try { sessionStorage.setItem("library.place", JSON.stringify({ q: state.q, shelf: state.shelf, y: window.scrollY })); } catch (_) {}
      location.reload();
    } catch (_) { /* server stopped or restarting; try again next tick */ }
  }, 1500);
}
