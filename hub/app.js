const $ = s => document.querySelector(s);
const TOOLS = {
  library: { app: "library", name: "The Library" },
  bestiary: { app: "bestiary", name: "The Bestiary" },
  // charasheet, hosted by its author rather than by us: always open, at this address.
  // It leaves: the hall is its own site, opened in this tab rather than a frame,
  // since in a frame the browser keeps its storage apart and its Google Drive
  // sign-in never gets back to it.
  barracks: { app: "barracks", name: "The Barracks", url: "https://charasheet.rayy.dev/", leaves: true },
  memoria: { app: "memoria", name: "The Memoria" },
};
const STATE_TEXT = { ready: "Open", external: "Open", starting: "Lighting the lamps…", stopped: "Closed" };
// Like the library's "Animate books": the hub's own setting, on unless it is
// switched off here, whatever the system's reduce-motion preference says.
let motion = stored("hub.animate") !== "off";
// On the public website (web/build.py) there is no hub server: the tools are
// static pages next to this one, in library/, bestiary/ and memoria/, and always open.
const HOSTED = "hosted" in document.body.dataset;

function stored(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch { return null; }
}

function setMotion(on) {
  motion = on;
  stored("hub.animate", on ? "on" : "off");
  document.body.classList.toggle("motion", on);
  $("#animate").checked = on;
}

let status = null;
let lastView = null;
const frames = {};

// ---------- the corridors: one-point perspective drawn into each doorway ----------
//
// World units: the corridor runs from z=1 (the doorway) to z=D (the far end),
// is 2 wide (X -1..1) and 2 high (Y 0..2). P() projects to a 200x320 picture
// from a camera standing at depth cam.cz. cam.k scales the picture: k = 1 - cz
// keeps the doorway exactly filling the picture however close the camera is.
// The resting picture is cz = 0, k = 1; walking down a corridor redraws it
// with the camera further in (see the walks below).
//
// A corridor is first described as a list of shapes, then drawn either as SVG
// (the doorways at rest, whose lamps flicker and eyes blink by CSS) or onto a
// canvas (every frame of a walk, where rebuilding SVG would be far too slow).

const D = 4.2;
const NEAR = .06;  // nothing closer to the camera than this is drawn
const cam = { cz: 0, k: 1 };
const depth = z => cam.k / Math.max(z - cam.cz, NEAR);  // how big things at depth z look
const seen = z => z - cam.cz > NEAR;
const P = (X, Y, z) => { const d = depth(z); return [100 + 100 * X * d, 160 + 160 * (1 - Y) * d]; };
// Surfaces running along the corridor are cut off where they pass the camera.
const along = (z0, z1) => { z0 = Math.max(z0, cam.cz + NEAR); return z1 > z0 ? [z0, z1] : null; };
const side = (X, z0, z1, y0, y1) => { const r = along(z0, z1); return r && [P(X, y0, r[0]), P(X, y0, r[1]), P(X, y1, r[1]), P(X, y1, r[0])]; };
const flat = (Y, x0, x1, z0, z1) => { const r = along(z0, z1); return r && [P(x0, Y, r[0]), P(x1, Y, r[0]), P(x1, Y, r[1]), P(x0, Y, r[1])]; };
const end = (x0, x1, y0, y1, z = D) => seen(z) && [P(x0, y0, z), P(x1, y0, z), P(x1, y1, z), P(x0, y1, z)];
const fade = z => 1 - (z - 1) / (D - 1) * .7;  // things further away sit in the dark
const from1 = () => Math.max(1, cam.cz + NEAR);  // where lines along the corridor start

// The shape list. A fill is a colour, or {lin: [x1, y1, x2, y2] | rad: [cx, cy, r], stops: [[offset, colour, alpha?]]},
// or {soft: colour} for a glow fading out to its edge.
let shapes = [];
const add = s => { shapes.push(s); };
const polygon = (pts, fill, alpha = 1) => { if (pts) add({ t: "poly", pts, fill, alpha }); };
const line = (a, b, stroke, width, more = {}) => add({ t: "line", a, b, stroke, width, alpha: 1, ...more });
const ellipse = (x, y, rx, ry, fill, more = {}) => add({ t: "ellipse", x, y, rx, ry, fill, alpha: 1, ...more });
const glowAt = (x, y, rx, ry, colour, alpha, more = {}) => ellipse(x, y, rx, ry, { soft: colour }, { alpha, ...more });
function group(more, draw) {
  const outer = shapes;
  shapes = [];
  draw();
  const inner = shapes;
  shapes = outer;
  add({ t: "group", shapes: inner, ...more });
}

function random(seed) {
  return () => {
    seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

function shell(c) {
  polygon(flat(2, -1, 1, 1, D), { lin: [0, 0, 0, 160], stops: [[0, c.ceil], [1, "#000"]] });
  polygon(flat(0, -1, 1, 1, D), { lin: [0, 320, 0, 160], stops: [[0, c.floor], [1, c.floorFar]] });
  polygon(side(-1, 1, D, 0, 2), { lin: [0, 0, 100, 0], stops: [[0, c.wall], [1, c.wallFar]] });
  polygon(side(1, 1, D, 0, 2), { lin: [200, 0, 100, 0], stops: [[0, c.wall], [1, c.wallFar]] });
  polygon(end(-1, 1, 0, 2), c.far);
}

// The far end's light, over everything; it grows as the camera nears it.
function farGlow(c) {
  const near = depth(D) * D;
  add({ t: "rect", x: -400, y: -400, w: 1000, h: 1120,
    fill: { rad: [100, 160 + ((c.glowY ?? 165) - 160) * near, (c.glowR ?? 80) * near], stops: [[0, c.glow, c.glowA], [1, c.glow, 0]] } });
}

// Mortar lines for stone or brick walls, courses staggered.
function masonry(course, joint, stroke, width) {
  for (const X of [-1, 1]) {
    for (let i = 0, Y = 0; Y < 2; i++, Y += course) {
      line(P(X, Y, from1()), P(X, Y, D), stroke, width);
      for (let z = 1 + (i % 2) * joint / 2; z < D; z += joint) {
        if (seen(z)) line(P(X, Y, z), P(X, Math.min(2, Y + course), z), stroke, width * 1.4 * depth(z));
      }
    }
  }
}

const CORRIDORS = {
  library() {
    const rnd = random(7);
    const books = ["#7a2e24", "#2f4d3a", "#28405e", "#6b4b1f", "#5a2f4f", "#8a6a2a", "#3b3b52", "#7d4a2a", "#9a7b3c"];
    const c = { wall: "#6b4a2e", wallFar: "#140d07", floor: "#4a3222", floorFar: "#0e0905", ceil: "#2b1d12", far: "#2a170b", glow: "#ffd98a", glowA: .55 };
    shell(c);
    polygon(end(-.36, .36, 0, 1.25), "#f6d68d");
    polygon(end(-.36, .36, 1.25, 1.33), "#4a2c16");
    polygon(end(-.03, .03, 0, 1.25), "#b08a4a");
    polygon(flat(0.002, -.34, .34, 1, D), "#6b1f1a", .85);
    line(P(-.28, 0, from1()), P(-.28, 0, D), "#caa24a", 1.2, { alpha: .7 });
    line(P(.28, 0, from1()), P(.28, 0, D), "#caa24a", 1.2, { alpha: .7 });
    for (const X of [-1, 1]) {
      for (const y of [.06, .52, .98, 1.44]) {
        for (let z = 1.02; z < D - .12;) {
          const dz = .045 + rnd() * .05;
          const h = .27 + rnd() * .13;
          polygon(side(X * .985, z, z + dz * .86, y, y + h), books[Math.floor(rnd() * books.length)], fade(z));
          z += dz;
        }
        polygon(side(X * .975, 1, D - .1, y - .035, y), "#2a170b");
      }
      for (let z = 1.02; z < D; z += .95) polygon(side(X * .975, z, z + .05, 0, 1.9), "#2a170b", fade(z));
    }
    for (const z of [1.7, 2.6, 3.5]) {
      if (!seen(z)) continue;
      const d = depth(z);
      line(P(0, 2, z), P(0, 1.78, z), "#3a2a18", 1.6 * d);
      const [x, y] = P(0, 1.73, z);
      glowAt(x, y, 26 * d, 26 * d, "#ffd98a", .6, { cls: "flicker" });
      ellipse(x, y, 7 * d, 7 * d, "#fff0c4");
    }
    farGlow(c);
  },

  bestiary() {
    const rnd = random(3);
    const c = { wall: "#3c423a", wallFar: "#060806", floor: "#2a2f28", floorFar: "#040504", ceil: "#1c201b", far: "#07120d", glow: "#57d19b", glowA: .35, glowR: 60 };
    shell(c);
    polygon(end(-.3, .3, 0, 1.15), "#123a2a");
    masonry(.28, .55, "#0b0e0b", 1.4);
    for (let i = 0; i < 12; i++) {
      const X = rnd() < .5 ? -1 : 1, z = 1.1 + rnd() * 2.4, Y = .05 + rnd() * .2;
      if (!seen(z)) continue;
      const [x, y] = P(X * .99, Y, z);
      ellipse(x, y, 18 * depth(z), 8 * depth(z), "#3f6b3a", { alpha: .35 });
    }
    for (let k = 0; k < 3; k++) {
      if (!seen(1.22 + k * .07)) continue;
      line(P(-.99, 1.36 - k * .03, 1.22 + k * .07), P(-.99, .86 - k * .03, 1.46 + k * .07), "#cfc3a4", 2.4 * depth(1.3), { alpha: .55, cap: "round" });
    }
    for (const [x, z] of [[-.5, 1.6], [.45, 2.3], [-.2, 3.2]]) {
      if (!seen(z)) continue;
      const d = depth(z);
      line(P(x, 2, z), P(x, 1.3, z), "#505a4c", 3 * d, { dash: [4 * d, 2 * d] });
    }
    const eyes = [[-.5, .55, 2.7, "#ffcf4a", 0], [.5, .95, 3.3, "#ff6a3d", -1.6], [.08, .32, 3.8, "#ffcf4a", -3.1], [-.72, 1.25, 3.1, "#9dff8a", -2.2]];
    for (const [X, Y, z, colour, delay] of eyes) {
      if (!seen(z)) continue;
      const d = depth(z);
      group({ cls: "blink", style: `animation-delay:${delay}s` }, () => {
        for (const dx of [-.07, .07]) {
          const [x, y] = P(X + dx, Y, z);
          glowAt(x, y, 12 * d, 9 * d, colour, .55);
          ellipse(x, y, 3.4 * d, 2.2 * d, colour);
        }
      });
    }
    add({ t: "rect", x: 0, y: 200, w: 200, h: 120, fill: { lin: [0, 200, 0, 320], stops: [[0, "#9fd8c0", 0], [1, "#9fd8c0", .16]] } });
    farGlow(c);
  },

  // The barracks: bunks down both walls with a footlocker at the foot of
  // each, spears racked between them, banners from the beams, lamps low.
  barracks() {
    const c = { wall: "#5f4b37", wallFar: "#120c07", floor: "#4f3a26", floorFar: "#0d0805", ceil: "#2a1d12", far: "#1d120a", glow: "#ff9a55", glowA: .5, glowY: 180 };
    shell(c);
    polygon(end(-.3, .3, 0, 1.2), "#ffc27a");
    polygon(end(-.34, .34, 1.2, 1.28), "#2e1f12");
    for (let x = -.84; x < .9; x += .28) line(P(x, 0, from1()), P(x, 0, D), "#2a1b10", .9, { alpha: .6 });
    for (const X of [-1, 1]) {
      for (let z = 1; z < D; z += .7) polygon(side(X * .995, z, z + .06, 0, 2), "#2e1f12", fade(z));
    }
    // Solid things darken with distance rather than fading (they'd turn see-through).
    const shade = (hex, f) => {
      const n = parseInt(hex.slice(1), 16), k = v => Math.round(v * f).toString(16).padStart(2, "0");
      return `#${k(n >> 16)}${k(n >> 8 & 255)}${k(n & 255)}`;
    };
    // Far to near, so the nearer bunks stand in front of the further ones.
    const blankets = ["#7a2e24", "#3d4a5c", "#5d4d2c"];
    const bunks = [1.2, 1.95, 2.7, 3.45];
    for (let i = bunks.length - 1; i >= 0; i--) {
      const z0 = bunks[i], z1 = z0 + .55, a = fade(z0);
      for (const s of [-1, 1]) {
        const inner = s * .6, blanket = blankets[(i + (s > 0 ? 1 : 0)) % blankets.length];
        // the rack between this bunk and the one before it: two spears
        const rz = z0 - .1;
        if (seen(rz)) {
          const d = depth(rz);
          for (const dz of [-.03, .03]) {
            line(P(s * .97, .02, rz + dz), P(s * .97, 1.5, rz + dz + .03), shade("#6b5a45", a), 1.6 * d);
            line(P(s * .97, 1.5, rz + dz + .03), P(s * .97, 1.66, rz + dz + .035), shade("#c9ccd1", a), 2.2 * d);
          }
        }
        // a lamp on the wall above the bunk
        const lz = z0 + .27;
        if (seen(lz)) {
          const d = depth(lz);
          const [x, y] = P(s * .96, 1.5, lz);
          glowAt(x, y, 22 * d, 22 * d, "#ffb870", .5, { cls: "flicker" });
          ellipse(x, y, 3.2 * d, 4.6 * d, "#ffe2b0");
        }
        // lower bunk: dark underneath, the frame, the blanket on top, a pillow
        polygon(side(inner, z0, z1, 0, .28), shade("#140d07", a));
        polygon(end(Math.min(inner, s), Math.max(inner, s), .28, .4, z0), shade("#3a2414", a));
        polygon(side(inner, z0, z1, .28, .4), shade("#4a2f1a", a));
        polygon(flat(.4, s, inner, z0, z1), shade(blanket, a));
        polygon(flat(.41, s * .97, s * .74, z1 - .15, z1 - .03), shade("#e8dcc2", a));
        // upper bunk, level with the eye: only its side shows
        polygon(side(inner, z0, z1, .93, 1), shade("#4a2f1a", a));
        polygon(side(inner, z0, z1, 1, 1.1), shade(blanket, a * .9));
        for (const z of [z0, z1]) {
          if (seen(z)) line(P(inner, 0, z), P(inner, 1.25, z), shade("#3a2414", a), 2.4 * depth(z));
        }
        // the footlocker in the aisle, brass lock to the front
        const f0 = z0 + .12, f1 = z0 + .43;
        polygon(end(Math.min(inner, s * .48), Math.max(inner, s * .48), 0, .2, f0), shade("#5a3920", a));
        polygon(side(s * .48, f0, f1, 0, .2), shade("#6b4526", a));
        polygon(flat(.2, inner, s * .48, f0, f1), shade("#7d5431", a));
        if (seen(f0)) {
          const [x, y] = P(s * .48, .13, (f0 + f1) / 2);
          ellipse(x, y, 2 * depth(f0), 2.4 * depth(f0), shade("#d9bb70", a));
        }
      }
    }
    // Beams across the ceiling, a banner on every other one; far to near again.
    [3.8, 3.05, 2.3, 1.55].forEach((z, i) => {
      if (!seen(z)) return;
      const f = fade(z);
      polygon(flat(1.9, -1, 1, z, z + .07), shade("#24170d", f));
      polygon(end(-1, 1, 1.9, 2, z), shade("#2e1f12", f));
      if (i % 2) return;
      polygon([P(-.13, 1.9, z), P(.13, 1.9, z), P(.13, 1.46, z), P(0, 1.38, z), P(-.13, 1.46, z)], shade("#7a2e24", f));
      line(P(-.13, 1.84, z), P(.13, 1.84, z), shade("#d9bb70", f), 1.4 * depth(z));
      const [x, y] = P(0, 1.63, z);
      ellipse(x, y, 5 * depth(z), 5 * depth(z), shade("#d9bb70", f));
    });
    farGlow(c);
  },

  // The Memoria: a marble gallery with glass cases on plinths down both
  // walls, columns between them, and the rotunda's daylight at the far end.
  memoria() {
    const c = { wall: "#d9cfbb", wallFar: "#241f18", floor: "#d3c8b0", floorFar: "#1c1813", ceil: "#8f846f", far: "#3a3226", glow: "#fff2d0", glowA: .6, glowR: 90 };
    shell(c);
    const shade = (hex, f) => {
      const n = parseInt(hex.slice(1), 16), k = v => Math.round(v * f).toString(16).padStart(2, "0");
      return `#${k(n >> 16)}${k(n >> 8 & 255)}${k(n & 255)}`;
    };
    polygon(end(-.42, .42, 0, 1.38), "#fff4dc");
    polygon(end(-.47, .47, 1.38, 1.48), "#b89a5a");
    polygon(end(-.06, .06, 0, .5), "#e9e2d3");  // the Empty Case's plinth, seen through the arch
    polygon(end(-.08, .08, .5, .56), "#c9a24a");
    for (let x = -.75; x < .8; x += .25) line(P(x, 0, from1()), P(x, 0, D), "#a89878", .8, { alpha: .45 });
    polygon(flat(.002, -.05, .05, 1, D), "#c9a24a", .8);
    // Columns along both walls, far to near.
    for (const z of [3.95, 3.25, 2.5, 1.75, 1.05]) {
      if (!seen(z)) continue;
      const f = fade(z);
      for (const X of [-1, 1]) polygon(side(X * .985, z, z + .1, 0, 2), shade("#ece5d6", f));
      polygon(flat(1.94, -1, 1, z, z + .1), shade("#c9a24a", f));
    }
    // The cases: a plinth, a glass box, something small and bright inside.
    const inside = ["#8fd1a7", "#e0714f", "#e3a53c", "#c49be8"];
    [3.45, 2.7, 1.95, 1.2].forEach((z0, i) => {
      const z1 = z0 + .32, a = fade(z0);
      for (const s of [-1, 1]) {
        const inner = s * .56, outer = s * .88, lo = Math.min(inner, outer), hi = Math.max(inner, outer);
        polygon(side(inner, z0, z1, 0, .52), shade("#cfc5b0", a));
        polygon(end(lo, hi, 0, .52, z0), shade("#bdb29c", a));
        polygon(flat(.52, inner, outer, z0, z1), shade("#c9a24a", a));
        polygon(side(inner, z0, z1, .53, .84), "#eaf6ff", .16 * a);
        polygon(end(lo, hi, .53, .84, z0), "#eaf6ff", .1 * a);
        if (!seen(z0)) continue;
        const d = depth(z0);
        line(P(inner, .84, z0), P(inner, .84, z1), shade("#c9a24a", a), 1.2 * d);
        line(P(inner, .53, z0), P(inner, .84, z0), shade("#c9a24a", a), 1 * d);
        const [x, y] = P((inner + outer) / 2, .62, (z0 + z1) / 2);
        glowAt(x, y, 14 * d, 12 * d, inside[(i + (s > 0 ? 2 : 0)) % inside.length], .45 * a, { cls: "flicker" });
        ellipse(x, y, 3.2 * d, 3.8 * d, inside[(i + (s > 0 ? 2 : 0)) % inside.length], { alpha: a });
      }
    });
    farGlow(c);
  },

};

// Describe a corridor as seen from depth cz (default: standing in reception).
function describe(theme, cz = 0, k = 1) {
  cam.cz = cz;
  cam.k = k;
  shapes = [];
  try {
    CORRIDORS[theme]();
    return shapes;
  } finally {
    cam.cz = 0;
    cam.k = 1;
  }
}

// ---- drawing the shapes as SVG ----

const n1 = v => (Math.round(v * 10) / 10).toString();
function toSVG(list, id) {
  let defs = "", count = 0;
  const stops = s => s.map(([o, c, a = 1]) => `<stop offset="${o}" stop-color="${c}" stop-opacity="${a}"/>`).join("");
  const paint = f => {
    if (typeof f === "string") return f;
    const g = `${id}-${count++}`;
    if (f.lin) defs += `<linearGradient id="${g}" gradientUnits="userSpaceOnUse" x1="${f.lin[0]}" y1="${f.lin[1]}" x2="${f.lin[2]}" y2="${f.lin[3]}">${stops(f.stops)}</linearGradient>`;
    else if (f.rad) defs += `<radialGradient id="${g}" gradientUnits="userSpaceOnUse" cx="${n1(f.rad[0])}" cy="${n1(f.rad[1])}" r="${n1(f.rad[2])}">${stops(f.stops)}</radialGradient>`;
    else defs += `<radialGradient id="${g}">${stops([[0, f.soft], [.45, f.soft, .55], [1, f.soft, 0]])}</radialGradient>`;
    return `url(#${g})`;
  };
  const extra = s => `${s.alpha !== 1 ? ` opacity="${s.alpha.toFixed(2)}"` : ""}${s.cls ? ` class="${s.cls}"` : ""}${s.style ? ` style="${s.style}"` : ""}`;
  const one = s => {
    switch (s.t) {
      case "poly": return `<polygon points="${s.pts.map(([x, y]) => `${n1(x)},${n1(y)}`).join(" ")}" fill="${paint(s.fill)}"${extra(s)}/>`;
      case "line": return `<line x1="${n1(s.a[0])}" y1="${n1(s.a[1])}" x2="${n1(s.b[0])}" y2="${n1(s.b[1])}" stroke="${s.stroke}" stroke-width="${s.width.toFixed(2)}"${s.dash ? ` stroke-dasharray="${s.dash.map(n1).join(" ")}"` : ""}${s.cap ? ` stroke-linecap="${s.cap}"` : ""}${extra(s)}/>`;
      case "ellipse": return `<ellipse cx="${n1(s.x)}" cy="${n1(s.y)}" rx="${n1(s.rx)}" ry="${n1(s.ry)}" fill="${paint(s.fill)}"${extra(s)}/>`;
      case "rect": return `<rect x="${s.x}" y="${s.y}" width="${s.w}" height="${s.h}" fill="${paint(s.fill)}"/>`;
      case "path": return `<path d="${s.d}" fill="${s.fill}"${s.at ? ` transform="translate(${s.at[0]} ${s.at[1]}) scale(${s.at[2]} ${s.at[3]})"` : ""}${s.stroke ? ` stroke="${s.stroke}" stroke-width="${s.width}" stroke-opacity="${s.strokeAlpha}"` : ""}${extra(s)}/>`;
      case "group": return `<g${s.cls ? ` class="${s.cls}"` : ""}${s.style ? ` style="${s.style}"` : ""}>${s.shapes.map(one).join("")}</g>`;
    }
    return "";
  };
  const body = list.map(one).join("");
  return `<defs>${defs}</defs>${body}`;
}

// ---- drawing the shapes on a canvas ----

function rgba(hex, a = 1) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${n >> 8 & 255},${n & 255},${a})`;
}

// Paint the 200x320 picture onto a canvas the way preserveAspectRatio="xMidYMid
// slice" would, with the canvas backing store `density` pixels per CSS pixel.
function toCanvas(canvas, list, density, bob = 0) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const scale = Math.max(w / 200, h / 320);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1;
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, w, h);
  ctx.setTransform(scale, 0, 0, scale, (w - 200 * scale) / 2, (h - 320 * scale) / 2 + bob * density);
  const paint = f => {
    if (typeof f === "string") return f;
    let g;
    if (f.lin) g = ctx.createLinearGradient(...f.lin);
    else if (f.rad) g = ctx.createRadialGradient(f.rad[0], f.rad[1], 0, f.rad[0], f.rad[1], Math.max(f.rad[2], .001));
    else {
      g = ctx.createRadialGradient(0, 0, 0, 0, 0, 1);
      g.addColorStop(0, rgba(f.soft));
      g.addColorStop(.45, rgba(f.soft, .55));
      g.addColorStop(1, rgba(f.soft, 0));
      return g;
    }
    for (const [o, c, a = 1] of f.stops) g.addColorStop(o, rgba(c, a));
    return g;
  };
  const one = s => {
    ctx.globalAlpha = s.alpha ?? 1;
    switch (s.t) {
      case "poly":
        ctx.beginPath();
        ctx.moveTo(...s.pts[0]);
        for (let i = 1; i < s.pts.length; i++) ctx.lineTo(...s.pts[i]);
        ctx.closePath();
        ctx.fillStyle = paint(s.fill);
        ctx.fill();
        break;
      case "line":
        ctx.beginPath();
        ctx.moveTo(...s.a);
        ctx.lineTo(...s.b);
        ctx.strokeStyle = s.stroke;
        ctx.lineWidth = s.width;
        ctx.lineCap = s.cap || "butt";
        ctx.setLineDash(s.dash || []);
        ctx.stroke();
        break;
      case "ellipse":
        if (s.fill.soft) {
          // A glow: a unit radial gradient stretched to the ellipse.
          ctx.save();
          ctx.translate(s.x, s.y);
          ctx.scale(Math.max(s.rx, .001), Math.max(s.ry, .001));
          ctx.fillStyle = paint(s.fill);
          ctx.beginPath();
          ctx.arc(0, 0, 1, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        } else {
          ctx.beginPath();
          ctx.ellipse(s.x, s.y, Math.max(s.rx, .001), Math.max(s.ry, .001), 0, 0, Math.PI * 2);
          ctx.fillStyle = paint(s.fill);
          ctx.fill();
        }
        break;
      case "rect":
        ctx.fillStyle = paint(s.fill);
        ctx.fillRect(s.x, s.y, s.w, s.h);
        break;
      case "path": {
        ctx.save();
        if (s.at) {
          ctx.translate(s.at[0], s.at[1]);
          ctx.scale(s.at[2], s.at[3]);
        }
        const p = new Path2D(s.d);
        ctx.fillStyle = s.fill;
        ctx.fill(p);
        if (s.stroke) {
          ctx.globalAlpha = s.strokeAlpha;
          ctx.strokeStyle = s.stroke;
          ctx.lineWidth = s.width;
          ctx.setLineDash([]);
          ctx.stroke(p);
        }
        ctx.restore();
        break;
      }
      case "group":
        s.shapes.forEach(one);
        break;
    }
  };
  list.forEach(one);
}

document.querySelectorAll(".corridor").forEach((svg, i) => {
  svg.dataset.id = `c${i}`;
  svg.innerHTML = toSVG(describe(svg.dataset.theme), svg.dataset.id);
});

// ---------- views ----------

function currentView() {
  const v = location.hash.slice(1);
  return v in TOOLS ? v : "desk";
}

async function post(path, body) {
  const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// Reception to a hall walks in; a hall back to reception walks out. The walk
// applies the view itself partway through, then calls render() again to catch
// up with anything that changed meanwhile.
function render() {
  if (walking) return;
  const view = currentView();
  const from = lastView;
  lastView = view;
  const walksIn = motion && from === "desk" && view !== "desk";
  if (TOOLS[view] && TOOLS[view].leaves && !walksIn) return leave(view);
  if (walksIn) return walkIn(view);
  if (motion && from !== null && from !== "desk" && view === "desk") return walkOut(from);
  applyView(view, from !== null && from !== view);
}

function applyView(view, fadeIn) {
  for (const a of document.querySelectorAll(".bar .nav a")) {
    if (a.dataset.view === view) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  // Reception is never taken down, only covered: laying it out again (or a
  // tool's page, which shares this page's thread) would stall a walk.
  $("#view-desk").classList.toggle("covered", view !== "desk");
  // With a tool open, this page must not scroll or bounce under it: on iOS
  // Safari a touch on the bar that moved this page left the tool's frame
  // unable to scroll.
  document.documentElement.classList.toggle("in-tool", view !== "desk");

  const tool = TOOLS[view];
  const app = tool && status ? status.apps[tool.app] : null;
  const live = app && (app.state === "ready" || app.state === "external");

  if (live) frameFor(view);
  for (const [name, frame] of Object.entries(frames)) {
    frame.classList.toggle("off", name !== view || !live);
  }
  if (live && frames[view].dataset.stale) {
    frames[view].src = app.url;
    delete frames[view].dataset.stale;
  }

  const pop = $("#pop");
  pop.hidden = !live;
  if (live) pop.href = app.url;

  $("#view-wait").hidden = !tool || live;
  if (tool && !live) {
    const stopped = app && app.state === "stopped";
    $("#waitTitle").textContent = stopped ? `${tool.name} is closed` : `Lighting the lamps in ${tool.name}…`;
    $("#waitText").textContent = stopped
      ? "Its server stopped. The last thing it printed is below."
      : "Its server is starting up. This page switches over as soon as it answers.";
    $("#waitStart").hidden = !stopped;
    $("#waitLog").hidden = !(stopped && app.log && app.log.length);
    $("#waitLog").textContent = stopped && app.log ? app.log.join("\n") : "";
  }

  // Hopping straight from one hall to another fades rather than cuts.
  if (fadeIn && motion) {
    const shown = view === "desk" ? $("#view-desk") : live ? frames[view] : $("#view-wait");
    shown.classList.remove("arrive");
    void shown.offsetWidth;
    shown.classList.add("arrive");
  }
  document.title = tool ? `${tool.name} · Threadmint` : "Threadmint Reception";
}

// A tool's page, created (and so loaded) the first time it is needed. It
// stays loaded afterwards, hidden while another view is showing.
function frameFor(view) {
  if (!frames[view]) {
    const frame = document.createElement("iframe");
    frame.className = "frame off";
    frame.title = TOOLS[view].name;
    frame.src = status.apps[TOOLS[view].app].url;
    frames[view] = frame;
    $("#frames").append(frame);
  }
  return frames[view];
}

// Load every running tool quietly in the background once reception is up,
// so no walk has to wait for a page to load.
let preloaded = false;
function preload() {
  if (preloaded || !status || Object.values(status.apps).some(a => a.state === "starting")) return;
  preloaded = true;
  setTimeout(() => {
    for (const [view, tool] of Object.entries(TOOLS)) {
      if (tool.leaves) continue;
      const s = status.apps[tool.app].state;
      if (s === "ready" || s === "external") frameFor(view);
    }
  }, 800);
}

function renderStatus() {
  const states = Object.fromEntries(Object.entries(status.apps).map(([k, v]) => [k, v.state]));
  for (const dot of document.querySelectorAll("[data-dot]")) dot.className = `dot ${states[dot.dataset.dot]}`;
  for (const el of document.querySelectorAll("[data-state]")) el.textContent = STATE_TEXT[states[el.dataset.state]] || "";
  // A tool that went down and came back needs its page reloaded.
  for (const [view, frame] of Object.entries(frames)) {
    const s = status.apps[TOOLS[view].app].state;
    if (s !== "ready" && s !== "external") frame.dataset.stale = "1";
  }
}

// The hub server only knows the tools it starts; a tool with its own url is
// hosted elsewhere and always open there.
function withRemote(s) {
  for (const t of Object.values(TOOLS)) if (t.url) s.apps[t.app] = { state: "ready", url: t.url };
  return s;
}

async function poll() {
  if (HOSTED) {
    status = withRemote({ apps: Object.fromEntries(Object.values(TOOLS).map(t => [t.app, { state: "ready", url: `${t.app}/` }])) });
    renderStatus();
    render();
    preload();
    return;
  }
  try {
    status = withRemote(await (await fetch("/api/status", { cache: "no-store" })).json());
    renderStatus();
    render();
    preload();
  } catch {
    // The hub itself stopped; keep whatever is on screen.
  }
  const settling = !status || Object.values(status.apps).some(a => a.state === "starting");
  setTimeout(poll, settling ? 1200 : 4000);
}

// ---------- walking into a hall, and back out ----------
//
// One camera move, from standing in reception (cz = 0) to most of the way down
// the corridor (cz = WALK_TO). While the camera is still in reception, the
// hall is zoomed towards the doorway at exactly the rate a camera at that
// depth would see it (the wall is at z = 1, so it looks 1 / (1 - cz) times
// bigger), and the corridor inside the doorway is redrawn from the same
// camera, so near parts rush past faster than far ones. Once the doorway fills
// the screen, a full-screen copy of the corridor (the "tunnel") takes over at
// the same scale and the walk carries on towards the light at the far end.
// Only once the camera has stopped and the light fills the view does it fade
// into the tool: showing a tool's page can cost the GPU a moment, and a held
// light hides that where a frozen stride would not. Walking out plays the
// same path backwards. Every frame of a walk is drawn on a canvas; see toCanvas().

const GLOW = { library: "#ffd98a", bestiary: "#57d19b", barracks: "#ff9a55", memoria: "#fff2d0" };
const WALK_TO = 3.75;
const WALK_MS = 1900;
const REVEAL_MS = 420;  // the light fading into the tool (or back into the corridor)
// The doorway canvas is magnified with the hall; past this zoom it stops
// gaining pixels (you are nearly through, and moving fast).
const SHARP_UP_TO = 2.5;
let walking = false;
// The canvases are made once and reused: allocating a full-screen canvas
// mid-walk costs the GPU a visible pause.
let tunnelEl = null;
const doorwayCanvases = new Map();

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
// Starts from standing, picks up pace, and eases off as the light takes over.
const cameraAt = t => WALK_TO * (t < .5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2);

function screenRect() {
  const top = Math.max(0, $(".bar").getBoundingClientRect().bottom);
  return { left: 0, top, width: innerWidth, height: innerHeight - top };
}

// Where the doorway is, and how far the camera has to come for it to fill
// the screen. (Reception is only ever covered, so it can always be measured.)
function measure(door) {
  const a = door.querySelector(".arch").getBoundingClientRect();
  const hall = $("#hall").getBoundingClientRect();
  const scr = screenRect();
  const fill = Math.max(scr.width / 200, scr.height / 320) / Math.max(a.width / 200, a.height / 320);
  const cx = a.left + a.width / 2, cy = a.top + a.height / 2;
  return {
    ok: a.width > 0 && fill > 1,
    handoff: 1 - 1 / fill,  // camera depth at which the doorway fills the screen
    width: a.width, height: a.height,
    origin: `${cx - hall.left}px ${cy - hall.top}px`,
    shift: [scr.left + scr.width / 2 - cx, scr.top + scr.height / 2 - cy],
  };
}

function walker(view) {
  const door = document.querySelector(`.door[href="#${view}"]`);
  const arch = door.querySelector(".arch");
  const svg = arch.querySelector(".corridor");
  const theme = svg.dataset.theme;
  const hall = $("#hall");
  const dpr = devicePixelRatio || 1;
  let geo = measure(door);
  let doorway = null, tunnel = null;
  // Which door, for style.css (Hessa stands in front of the Barracks' and the Memoria's).
  hall.dataset.walk = view;

  return {
    ok: geo.ok,
    handoff: geo.handoff,
    remeasure() { geo = measure(door); },

    // Turn the hall into one cached layer while it is still at rest, so the
    // zoom moves it on the GPU instead of repainting it every frame.
    settle() { hall.classList.add("walking"); },

    // The camera is still in reception, heading for the doorway (and sliding
    // across to line up with it as it goes).
    approach(cz) {
      const zoom = 1 / (1 - cz);
      if (!doorway) {
        hall.classList.add("walking");
        doorway = doorwayCanvases.get(arch);
        if (!doorway) {
          doorway = document.createElement("canvas");
          doorway.className = "doorway";
          arch.append(doorway);
          doorwayCanvases.set(arch, doorway);
        }
        doorway.style.visibility = "visible";
      }
      // Keep enough pixels for the zoom, growing in steps rather than every frame.
      const need = Math.min(zoom, SHARP_UP_TO) * dpr;
      if (!doorway.density || need > doorway.density * 1.15 || need < doorway.density / 2) {
        doorway.density = Math.min(need * 1.4, SHARP_UP_TO * dpr);
        doorway.width = Math.round(geo.width * doorway.density);
        doorway.height = Math.round(geo.height * doorway.density);
      }
      const along = 1 - (1 - cz / geo.handoff) / (1 - cz);
      hall.style.transformOrigin = geo.origin;
      hall.style.transform = `translate(${geo.shift[0] * along}px, ${geo.shift[1] * along}px) scale(${zoom})`;
      toCanvas(doorway, describe(theme, cz, 1 - cz), doorway.density);
    },

    // Put the hall back at rest (it stays paused until leaveHall).
    resetHall() {
      hall.style.transform = hall.style.transformOrigin = "";
      if (doorway) doorway.style.visibility = "hidden";
      doorway = null;
    },

    leaveHall() {
      this.resetHall();
      hall.classList.remove("walking");
      delete hall.dataset.walk;
    },

    // The camera is through the doorway: draw the corridor full screen.
    inside(cz, t) {
      if (!tunnel) {
        const r = screenRect();
        if (!tunnelEl) {
          tunnelEl = document.createElement("div");
          tunnelEl.className = "tunnel";
          tunnelEl.innerHTML = `<canvas></canvas><i class="light"></i>`;
          document.body.append(tunnelEl);
        }
        tunnel = tunnelEl;
        tunnel.style.cssText = `left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;--light:${GLOW[view]}`;
        const c = tunnel.firstElementChild, w = Math.round(r.width * dpr), h = Math.round(r.height * dpr);
        if (c.width !== w || c.height !== h) {
          c.width = w;
          c.height = h;
        }
        tunnel.style.visibility = "visible";
      }
      const u = cz / WALK_TO;
      const c = tunnel.firstElementChild;
      toCanvas(c, describe(theme, cz, 1 - geo.handoff), dpr);
      // A step's gentle rise and fall, strongest mid-stride (moved on the GPU).
      c.style.transform = `translate3d(0, ${(Math.sin(cz * 11) * 5 * Math.sin(Math.PI * t)).toFixed(2)}px, 0)`;
      tunnel.lastElementChild.style.opacity = smooth(.55, 1, u).toFixed(3);
    },

    // Fade the tunnel (and its light) over the view underneath, or away from it.
    // A GPU animation, so it keeps its pace even while the page is busy.
    fadeTunnel(from, to) {
      return tunnel.animate([{ opacity: from }, { opacity: to }], { duration: REVEAL_MS, easing: "ease-in-out", fill: "forwards" }).finished;
    },

    closeTunnel() {
      if (tunnel) {
        tunnel.getAnimations().forEach(a => a.cancel());
        tunnel.style.visibility = "hidden";
      }
      tunnel = null;
    },
  };
}

// Run step(t) every frame for t from 0 to 1. If the browser stalls, the walk
// pauses and carries on from where it was, rather than jumping ahead: a
// brief pause reads as a held breath, a jump as a stutter.
function travel(ms, step) {
  return new Promise(done => {
    let last = null, elapsed = 0;
    const frame = now => {
      if (last !== null) elapsed += Math.min(now - last, 34);
      last = now;
      const t = Math.min(1, elapsed / ms);
      step(t);
      if (t < 1) requestAnimationFrame(frame);
      else done();
    };
    requestAnimationFrame(frame);
  });
}

// Wait for the browser to have drawn a couple of frames.
const settled = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

function walkIn(view) {
  return walk(view, async w => {
    let through = false;
    await travel(WALK_MS, t => {
      const cz = cameraAt(t);
      if (cz < w.handoff) return w.approach(cz);
      if (!through) {
        through = true;
        w.inside(cz, t);  // the tunnel covers the screen, then the hall can rest
        w.resetHall();
      }
      w.inside(cz, t);
    });
    if (TOOLS[view].leaves) return leave(view, w);
    // Only now, with the camera stopped and the light filling the view, is the
    // tool switched on underneath (the GPU may need a moment for it), then
    // the light fades into it.
    applyView(view, false);
    await settled();
    await w.fadeTunnel(1, 0);
  });
}

// A hall that is a site of its own (a tool with leaves): go there in this tab,
// in place of its entry in the history, so Back comes out at reception. After
// a walk the light stays up until the site arrives, so the walk never ends.
let leaving = null;
function leave(view, w = null) {
  leaving = { w };
  location.replace(TOOLS[view].url);
  return new Promise(() => {});
}

// Back from such a site, the browser may hand over this page as it was left,
// light and all: put reception back, as if the visitor had walked out.
addEventListener("pageshow", () => {
  if (!leaving) return;
  const { w } = leaving;
  leaving = null;
  if (w) {
    w.closeTunnel();
    w.leaveHall();
  }
  walking = false;
  lastView = null;
  dispatchEvent(new HashChangeEvent("hashchange"));  // render(), and a word from Hessa
});

function walkOut(view) {
  return walk(view, async w => {
    // The light gathers over the tool first, with the camera still at the far end.
    w.inside(WALK_TO, 0);
    await w.fadeTunnel(0, 1);
    applyView("desk", false);  // reception goes back underneath the tunnel
    w.settle();
    if (matchMedia("(max-width: 760px)").matches) document.querySelector(`.door[href="#${view}"]`).scrollIntoView({ block: "center" });
    w.remeasure();
    await settled();  // let reception be drawn while the light holds still
    let out = false;
    await travel(WALK_MS, p => {
      const t = 1 - p, cz = cameraAt(t);
      if (cz >= w.handoff) return w.inside(cz, t);
      if (!out) {
        out = true;
        w.approach(cz);
        w.closeTunnel();
      }
      w.approach(cz);
    });
  });
}

// Whatever happens during the walk, the page ends up showing the view the
// address bar asks for.
async function walk(view, moves) {
  walking = true;
  const w = walker(view);
  try {
    if (w.ok) await moves(w);
  } catch (e) {
    console.error("walk animation failed:", e);
  } finally {
    w.closeTunnel();
    w.leaveHall();
    walking = false;
    render();
  }
}

// ---------- the notice board ----------
// balance-patch.md (at the repo root, served next to this page) is pinned to
// the board. Its first "## " heading names the newest patch; until that patch
// has been opened in this browser, the board's seal glows and Hessa mentions
// it (clerk.js, which listens for the "notice" event).

let notice = null;  // { id, title, date, html } once loaded

const escapeHTML = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
// [buff], [nerf], [new] and [change] in the notes become arrowed badges.
const TAGS = { buff: "▲ Buff", nerf: "▼ Nerf", new: "✦ New", change: "◆ Change" };
const inlineMd = s => escapeHTML(s)
  .replace(/`([^`]+)`/g, "<code>$1</code>")
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/\*(.+?)\*/g, "<em>$1</em>")
  .replace(/\[(buff|nerf|new|change)\]/gi, (_, t) => `<span class="tag ${t.toLowerCase()}">${TAGS[t.toLowerCase()]}</span>`);

// A list item written "old → new" shows the old part dimmed, after any badge.
function mdItem(text) {
  const [, tag = "", rest] = text.match(/^(\[(?:buff|nerf|new|change)\]\s*)?([\s\S]*)$/i);
  const at = rest.indexOf(" → ");
  if (at < 0) return inlineMd(text);
  return `${inlineMd(tag)}<span class="was">${inlineMd(rest.slice(0, at))}</span> <span class="to">→</span> ${inlineMd(rest.slice(at + 3))}`;
}

function mdTable(rows) {
  const cells = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => inlineMd(c.trim()));
  const [head, , ...body] = rows;
  return `<div class="table"><table><thead><tr>${cells(head).map(c => `<th>${c}</th>`).join("")}</tr></thead>`
    + `<tbody>${body.map(r => `<tr>${cells(r).map(c => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

// Just enough markdown for the patch notes: headings, paragraphs, lists,
// tables, block quotes, rules, and bold, italic and code inline.
function renderMd(src) {
  const lines = src.replace(/\r/g, "").split("\n"), out = [];
  const starts = /^(#{1,4}\s|-{3,}\s*$|\||>|[-*]\s)/;
  const run = test => { const got = []; while (i < lines.length && test(lines[i])) got.push(lines[i++]); return got; };
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    let m;
    if (!l.trim()) i++;
    else if ((m = l.match(/^(#{1,4})\s+(.*)/))) { out.push(`<h${m[1].length}>${inlineMd(m[2])}</h${m[1].length}>`); i++; }
    else if (/^-{3,}\s*$/.test(l)) { out.push("<hr>"); i++; }
    else if (l.startsWith("|")) out.push(mdTable(run(x => x.startsWith("|"))));
    else if (l.startsWith(">")) out.push(`<blockquote>${renderMd(run(x => x.startsWith(">")).map(x => x.replace(/^>\s?/, "")).join("\n"))}</blockquote>`);
    else if (/^[-*]\s/.test(l)) out.push(`<ul>${run(x => /^[-*]\s/.test(x)).map(x => `<li>${mdItem(x.replace(/^[-*]\s+/, ""))}</li>`).join("")}</ul>`);
    else out.push(`<p>${inlineMd(run(x => x.trim() && !starts.test(x)).join(" "))}</p>`);
  }
  return out.join("\n");
}

const noticeUnread = () => !!notice && stored("hub.notice.seen") !== notice.id;

function showNoticeState() {
  const board = $("#guildboard"), unread = noticeUnread();
  board.classList.toggle("unread", unread);
  board.setAttribute("aria-label", `Guild notices: ${notice.title}${notice.date ? `, ${notice.date}` : ""}${unread ? " (unread)" : ""}`);
}

function openNotice() {
  if (!notice) return;
  stored("hub.notice.seen", notice.id);
  showNoticeState();
  $("#patchBody").scrollTop = 0;
  $("#patchnotes").showModal();
}

async function loadNotice() {
  try {
    const res = await fetch("balance-patch.md", { cache: "no-store" });
    if (!res.ok) return;
    const src = await res.text();
    const latest = src.match(/^##\s+(.+)$/m);
    if (!latest) return;
    const [title, when = ""] = latest[1].split(/\s+[—–-]\s+/);
    const day = new Date(when.trim());
    const date = isNaN(day) ? when.trim() : day.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
    const heading = src.match(/^#\s+(.+)$/m);
    // The page's own title replaces the file's "# " heading.
    notice = { id: latest[1].trim(), title: title.trim(), date, html: renderMd(src.replace(/^#\s+.+$/m, "")) };
    if (heading) $("#patchHead").textContent = heading[1].trim();
    $("#patchBody").innerHTML = notice.html;
    $('[data-board="title"]').textContent = notice.title;
    $('[data-board="date"]').textContent = notice.date;
    $("#guildboard").hidden = false;
    showNoticeState();
    dispatchEvent(new Event("notice"));
  } catch { /* no notes to pin; the board stays away */ }
}

$("#guildboard").addEventListener("click", openNotice);
$("#patchClose").addEventListener("click", () => $("#patchnotes").close());
// A click on the dimmed backdrop (the dialog itself, outside its contents) closes it.
$("#patchnotes").addEventListener("click", ev => { if (ev.target === ev.currentTarget) ev.currentTarget.close(); });

// ---------- the desk bell ----------
// Rung by clerk.js, which also decides what Hessa says about it.

let audio = null;
function ringBell() {
  const bell = $("#bell");
  bell.classList.remove("ring");
  void bell.offsetWidth;
  bell.classList.add("ring");
  try {
    audio = audio || new AudioContext();
    const now = audio.currentTime;
    for (const [freq, level] of [[1760, .18], [2640, .07], [4400, .03]]) {
      const osc = audio.createOscillator(), gain = audio.createGain();
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(level, now);
      gain.gain.exponentialRampToValueAtTime(.0001, now + 1.4);
      osc.connect(gain).connect(audio.destination);
      osc.start(now);
      osc.stop(now + 1.5);
    }
  } catch { /* no audio, just the wobble */ }
}

$("#waitStart").addEventListener("click", async () => {
  const tool = TOOLS[currentView()];
  if (!tool) return;
  status = await post("/api/start", { app: tool.app }).then(withRemote).catch(() => status);
  renderStatus();
  render();
});
$("#animate").addEventListener("change", e => setMotion(e.target.checked));
addEventListener("hashchange", render);
setMotion(motion);

render();
poll();
// After clerk.js has run too, so she hears about the notice.
addEventListener("DOMContentLoaded", loadNotice);
