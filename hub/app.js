const $ = s => document.querySelector(s);
const TOOLS = {
  library: { app: "library", name: "The Library" },
  market: { app: "market", name: "The Market" },
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
// static pages next to this one, in library/, market/, bestiary/ and memoria/, and always open.
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
// A corridor is first described as a list of shapes, then drawn onto canvases:
// once for each doorway at rest (see paintCorridor), and every frame of a walk.

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
// A glow is lamplight in the air. Walked right up to, it would fill the view (and
// cost a full-screen gradient every frame), so past half the picture's width it
// fades away.
function glowAt(x, y, rx, ry, colour, alpha, more = {}) {
  const size = Math.max(rx, ry) / 200;
  if (size < 1) ellipse(x, y, rx, ry, { soft: colour }, { alpha: alpha * Math.min(1, 2 - 2 * size), ...more });
}
// A lamp's fainter light on what is round it: a plain two-stop circle (a glow's
// three stops cost more to paint over a wide area), gone before it gets large.
function wash(x, y, r, colour, alpha) {
  const f = Math.min(1, (100 - r) / 50);
  if (f > 0) ellipse(x, y, r, r, { rad: [x, y, r], stops: [[0, colour, alpha * f], [1, colour, 0]] });
}
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
  // Where the floor meets the walls and the walls the ceiling, the light doesn't reach.
  for (const X of [-1, 1]) {
    for (const [w, a] of [[.06, .26], [.18, .14]]) {
      polygon(flat(.001, X, X * (1 - w), 1, D), "#000", a);
      polygon(side(X * .999, 1, D, 0, w * .9), "#000", a);
      polygon(side(X * .999, 1, D, 2 - w, 2), "#000", a);
    }
  }
}

// The far end's light falling back down the corridor: across the floor from
// the opening (c.door wide), and along the bottom of both walls.
function spill(c, alpha = .32) {
  const w = c.door ?? .34, z1 = Math.max(D - 2.2, cam.cz + NEAR);
  if (z1 >= D) return;
  const [, yFar] = P(0, 0, D), [, yNear] = P(0, 0, z1);
  // (Two stops only: a gradient with more is far slower to paint, and this one is painted every frame of a walk.)
  const fall = a => ({ lin: [0, yFar, 0, yNear], stops: [[0, c.glow, a], [1, c.glow, 0]] });
  polygon([P(-w, 0, D), P(w, 0, D), P(Math.min(1, w * 2.6), 0, z1), P(-Math.min(1, w * 2.6), 0, z1)], fall(alpha));
  for (const X of [-1, 1]) {
    const pts = side(X, D - 1.6, D, 0, 1.3);
    if (!pts) continue;
    const [xFar] = P(X, 0, D), [xNear] = P(X, 0, Math.max(D - 1.6, cam.cz + NEAR));
    polygon(pts, { lin: [xFar, 0, xNear, 0], stops: [[0, c.glow, alpha * .7], [1, c.glow, 0]] });
  }
}

// The far end's light, over everything; it grows as the camera nears it.
function farGlow(c) {
  spill(c, c.spillA);
  const near = depth(D) * D, y = 160 + ((c.glowY ?? 165) - 160) * near, r = (c.glowR ?? 80) * near;
  // Only the square round its circle: outside that it is clear, and painting
  // clear pixels over the whole picture every frame of a walk is not free.
  add({ t: "rect", x: 100 - r, y: y - r, w: 2 * r, h: 2 * r, fill: { rad: [100, y, r], stops: [[0, c.glow, c.glowA], [1, c.glow, 0]] } });
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
    const c = { wall: "#6b4a2e", wallFar: "#140d07", floor: "#4a3222", floorFar: "#0e0905", ceil: "#2b1d12", far: "#2a170b", glow: "#ffd98a", glowA: .55, door: .36 };
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
      // the lamp's light on the shelves either side, and its pool on the carpet
      // (held still: only the lamps themselves flicker, which keeps repainting cheap)
      wash(x, y + 50 * d, 105 * d, "#ffc978", .16);
      const [fx, fy] = P(0, 0, z);
      glowAt(fx, fy, 90 * d, 22 * d, "#ffd98a", .22);
      glowAt(x, y, 26 * d, 26 * d, "#ffd98a", .7, { cls: "flicker" });
      ellipse(x, y, 7 * d, 7 * d, "#fff0c4");
    }
    farGlow(c);
  },

  bestiary() {
    const rnd = random(3);
    const c = { wall: "#3c423a", wallFar: "#060806", floor: "#2a2f28", floorFar: "#040504", ceil: "#1c201b", far: "#07120d", glow: "#57d19b", glowA: .35, glowR: 60, door: .3, spillA: .26 };
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
          glowAt(x, y, 16 * d, 11 * d, colour, .6);
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
    const c = { wall: "#5f4b37", wallFar: "#120c07", floor: "#4f3a26", floorFar: "#0d0805", ceil: "#2a1d12", far: "#1d120a", glow: "#ff9a55", glowA: .5, glowY: 180, door: .3 };
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
          wash(x, y + 30 * d, 80 * d, "#ffa860", .26);
          glowAt(x, y, 22 * d, 22 * d, "#ffb870", .6, { cls: "flicker" });
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

  // The market: a covered arcade of stalls down both walls, each a counter
  // of goods under a striped awning with a lantern hung from its edge,
  // bunting strung across overhead, and the lit square at the far end.
  market() {
    const c = { wall: "#8a5a32", wallFar: "#130b05", floor: "#5a4632", floorFar: "#0d0905", ceil: "#2e1e10", far: "#2a1608", glow: "#ffc46b", glowA: .55, glowY: 172, door: .34 };
    shell(c);
    polygon(end(-.34, .34, 0, 1.3), "#ffd58a");
    polygon(end(-.38, .38, 1.3, 1.38), "#3a2414");
    // Cobbles: runs along the floor, joints across it.
    for (let x = -.8; x < .9; x += .4) line(P(x, 0, from1()), P(x, 0, D), "#2f2418", .8, { alpha: .5 });
    for (let z = 1.15; z < D; z += .3) if (seen(z)) line(P(-1, 0, z), P(1, 0, z), "#2f2418", .9 * depth(z), { alpha: .45 });
    const shade = (hex, f) => {
      const n = parseInt(hex.slice(1), 16), k = v => Math.round(v * f).toString(16).padStart(2, "0");
      return `#${k(n >> 16)}${k(n >> 8 & 255)}${k(n & 255)}`;
    };
    const awnings = ["#9b3a2a", "#3d5f86", "#4f7a45", "#b08a2e"];
    const goods = ["#b8432e", "#d98a2b", "#d9bb70", "#6f8fb8", "#8fae5a"];

    function stall(z0, i) {
      const z1 = z0 + .6, a = fade(z0);
      for (const s of [-1, 1]) {
        const inner = s * .62, lo = Math.min(inner, s), hi = Math.max(inner, s);
        const stripe = awnings[(i + (s > 0 ? 2 : 0)) % awnings.length];
        // the counter: its end towards us, its front to the aisle, its top
        polygon(end(lo, hi, 0, .45, z0), shade("#4a2f1a", a));
        polygon(side(inner, z0, z1, 0, .45), shade("#6b4526", a));
        polygon(flat(.45, s, inner, z0, z1), shade("#8a5a32", a));
        // goods heaped along it
        for (let k = 0; k < 4; k++) {
          const z = z0 + .1 + k * .13;
          if (!seen(z)) continue;
          const d = depth(z), [x, y] = P(s * .8, .47, z);
          ellipse(x, y, 10 * d, 5.5 * d, shade(goods[(i * 3 + k + (s > 0 ? 1 : 0)) % goods.length], a));
        }
        // posts up to the awning
        for (const z of [z0, z1]) if (seen(z)) line(P(inner, .45, z), P(s * .6, 1.15, z), shade("#3a2414", a), 2.2 * depth(z));
        // the awning, sloping down from the wall, in stripes along its length
        for (let z = z0, k = 0; z < z1 - 1e-6; z += .1, k++) {
          const r = along(z, Math.min(z + .1, z1));
          if (r) polygon([P(s, 1.42, r[0]), P(s, 1.42, r[1]), P(s * .6, 1.15, r[1]), P(s * .6, 1.15, r[0])], shade(k % 2 ? "#efe3c8" : stripe, a));
        }
        polygon(side(s * .6, z0, z1, 1.07, 1.15), shade(stripe, a * .85));
        // a lantern hung from the awning's edge
        const lz = z0 + .3;
        if (seen(lz)) {
          const d = depth(lz), [x, y] = P(s * .6, .98, lz);
          line(P(s * .6, 1.07, lz), P(s * .6, 1.01, lz), shade("#3a2414", a), 1.2 * d);
          wash(x, y + 24 * d, 58 * d, "#ffb860", .3);
          glowAt(x, y, 22 * d, 22 * d, "#ffc46b", .6, { cls: "flicker" });
          ellipse(x, y, 3.4 * d, 4.6 * d, "#ffe2a8");
        }
      }
    }

    // A string of pennants across the arcade, sagging in the middle.
    function bunting(z, i) {
      if (!seen(z)) return;
      const d = depth(z), f = fade(z), sag = X => 1.84 - .14 * (1 - X * X);
      for (let X = -1; X < 1; X += .25) line(P(X, sag(X), z), P(X + .25, sag(X + .25), z), shade("#3a2414", f), 1 * d);
      for (let k = 0; k < 9; k++) {
        const x0 = -.92 + k * .2, x1 = x0 + .15, xm = (x0 + x1) / 2;
        polygon([P(x0, sag(x0), z), P(x1, sag(x1), z), P(xm, sag(xm) - .13, z)], shade(awnings[(k + i) % awnings.length], f));
      }
    }

    // Far to near, so nearer things stand in front of further ones.
    const parts = [[3.5, 2.75, 2, 1.25].map((z, i) => [z, () => stall(z, i)]), [3.95, 3.15, 2.35, 1.55].map((z, i) => [z, () => bunting(z, i)])].flat();
    parts.sort((p, q) => q[0] - p[0]).forEach(([, draw]) => draw());
    farGlow(c);
  },

  // The Memoria: a marble gallery with glass cases on plinths down both
  // walls, columns between them, and the rotunda's daylight at the far end.
  memoria() {
    const c = { wall: "#d9cfbb", wallFar: "#241f18", floor: "#d3c8b0", floorFar: "#1c1813", ceil: "#8f846f", far: "#3a3226", glow: "#fff2d0", glowA: .5, glowR: 90, door: .42, spillA: .22 };
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

// ---- drawing the shapes on a canvas ----

function rgba(hex, a = 1) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${n >> 8 & 255},${n & 255},${a})`;
}

// Paint the 200x320 picture onto a canvas the way preserveAspectRatio="xMidYMid
// slice" would, with the canvas backing store `density` pixels per CSS pixel.
function toCanvas(canvas, list, density, bob = 0, clear = false) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const scale = Math.max(w / 200, h / 320);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1;
  ctx.fillStyle = "#000";
  if (clear) ctx.clearRect(0, 0, w, h);
  else ctx.fillRect(0, 0, w, h);
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

// A doorway at rest: its corridor drawn once (and again if the doorway changes
// size). What holds still becomes a plain image, with the lamps' glow at most
// of its strength; on top, a canvas holds the rest of the glow, and flickers,
// and one for each pair of eyes blinks. Flickering and blinking are opacity
// animations of whole canvases (style.css) that the GPU plays on its own, so
// nothing is redrawn while they run. (As SVG, with the lamps animated inside it,
// every doorway was redrawn every frame.) On a walk the canvases are hidden:
// as layers of their own they would make the hall costly to zoom; the image,
// part of the hall's own drawing, zooms with it for nothing.
const STEADY = .78;  // how much of a lamp's glow stays when its flicker is at its dimmest
function paintCorridor(view, i) {
  const r = view.getBoundingClientRect(), density = devicePixelRatio || 1;
  const w = Math.round(r.width * density), h = Math.round(r.height * density);
  if (!w || !h || view.dataset.size === `${w}x${h}`) return;
  view.dataset.size = `${w}x${h}`;
  const shapes = describe(view.dataset.theme);
  const lamps = shapes.filter(s => s.cls === "flicker");
  const share = k => lamps.map(s => ({ ...s, alpha: s.alpha * k }));
  const canvas = (list, cls = "", style = "") => {
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    c.className = cls;
    c.style.cssText = style;
    toCanvas(c, list, density, 0, true);
    return c;
  };
  const still = canvas([...shapes.filter(s => !s.cls), ...share(STEADY)]);
  // Each doorway's lamps flicker out of step with the others'.
  const layers = lamps.length ? [canvas(share(1 - STEADY), "flicker", `animation-delay:${-i * .9}s`)] : [];
  for (const g of shapes.filter(s => s.cls === "blink")) layers.push(canvas([g], "blink", g.style || ""));
  // Shown as a canvas until its image is ready, so the doorway is never empty.
  view.replaceChildren(still, ...layers);
  still.toBlob(blob => {
    if (!blob || !still.isConnected) return;
    const img = new Image();
    img.alt = "";
    img.onload = () => { if (still.isConnected) still.replaceWith(img); URL.revokeObjectURL(img.src); };
    img.src = URL.createObjectURL(blob);
  });
}
const corridors = [...document.querySelectorAll(".corridor")];
const repaint = new ResizeObserver(entries => entries.forEach(e => paintCorridor(e.target, corridors.indexOf(e.target))));
corridors.forEach(view => repaint.observe(view));

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
  // Back at reception, the hall just left is the one standing (on a phone).
  if (view === "desk" && TOOLS[from]) {
    const i = doorList.findIndex(d => d.dataset.go === from);
    if (i >= 0) doorRow.scrollLeft = i * doorRow.clientWidth;
  }
}

function applyView(view, fadeIn) {
  for (const a of document.querySelectorAll(".bar .nav a")) {
    if (a.dataset.view === view) { a.setAttribute("aria-current", "page"); showTab(a); }
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

// On a phone the bar's tabs don't all fit, so they scroll sideways: the
// current one is scrolled into sight, and an edge with more tabs past it fades.
function showTab(a) {
  const nav = a.parentElement;
  if (nav.scrollWidth <= nav.clientWidth) return;
  const left = a.offsetLeft - nav.offsetLeft, right = left + a.offsetWidth;
  if (left < nav.scrollLeft + 24) nav.scrollLeft = left - 24;
  else if (right > nav.scrollLeft + nav.clientWidth - 24) nav.scrollLeft = right - nav.clientWidth + 24;
}
function navEdges() {
  const nav = $(".bar .nav");
  nav.classList.toggle("more-l", nav.scrollLeft > 2);
  nav.classList.toggle("more-r", nav.scrollLeft + nav.clientWidth < nav.scrollWidth - 2);
}
$(".bar .nav").addEventListener("scroll", navEdges, { passive: true });
addEventListener("resize", navEdges);
navEdges();

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

const GLOW = { library: "#ffd98a", market: "#ffc46b", bestiary: "#57d19b", barracks: "#ff9a55", memoria: "#fff2d0" };
const WALK_TO = 3.75;
const WALK_MS = 1900;
const REVEAL_MS = 420;  // the light fading into the tool (or back into the corridor)
// The doorway canvas is magnified with the hall; past this zoom it stops
// gaining pixels (you are nearly through, and moving fast).
const SHARP_UP_TO = 2.5;
// Walk frames are drawn at no more than one pixel per CSS pixel, however fine
// the screen: in motion the difference doesn't show, and on a 1.5x or 2x
// screen it is two to four times fewer pixels to draw and hand over each frame.
const WALK_DPR = Math.min(devicePixelRatio || 1, 1);
let walking = false;
// Frames spent bringing reception up to the doorway's zoom before a walk out (see walkOut).
const ZOOM_UP_FRAMES = 10;
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
  const theme = arch.querySelector(".corridor").dataset.theme;
  const hall = $("#hall");
  const dpr = WALK_DPR;
  let geo = measure(door);
  let doorway = null, tunnel = null;
  // Which door, for style.css (Hessa stands in front of the Barracks').
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
          tunnelEl.innerHTML = `<canvas></canvas><i class="lens"></i><i class="light"></i>`;
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
    if (matchMedia("(max-width: 760px)").matches) document.querySelector(`.door[href="#${view}"]`).scrollIntoView({ block: "center", inline: "center" });
    w.remeasure();
    // While the light still covers it, bring reception up to the doorway's
    // zoom a step at a time. Shown at that zoom all at once, it would be drawn
    // afresh at that size, and zooming out would stall for seconds as more of
    // it came into view; grown into, it keeps the drawing it has.
    const fill = 1 / (1 - w.handoff);
    for (let i = 1; i <= ZOOM_UP_FRAMES; i++) {
      w.approach(1 - 1 / (1 + (fill - 1) * i / (ZOOM_UP_FRAMES + 1)));
      await settled();
    }
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
    light();  // in case the window changed size mid-walk
  }
}

// ---------- reception's lighting ----------
// The hall has no light of its own: it is lit by what is in it, each doorway's
// corridor and a sconce between each pair of doorways. light() measures the
// doorways and lays that out. The lightmap is a canvas of shade (--shade) over
// the room with the light cut out of it where it reaches; the bloom puts the
// light itself on top (a pool on the floor in front of each doorway, a halo
// round each sconce). The desk, nearest of all, has its candle instead
// (style.css). On narrow screens the hall isn't a room and none of this shows.
// Nothing here blends: plain transparency is all a walk can afford to zoom.

const SPILL = { library: "#ffd9a0", market: "#ffcf8f", bestiary: "#9fe8c4", barracks: "#ffb27a", memoria: "#fff1d6" };

function light() {
  if (walking || matchMedia("(max-width: 760px)").matches) return;
  const hall = $("#hall").getBoundingClientRect();
  if (!hall.width) return;
  const px = n => `${Math.round(n)}px`;
  const arches = [...document.querySelectorAll(".door")].map(door => {
    const r = door.querySelector(".arch").getBoundingClientRect();
    return { view: door.dataset.go, x: r.left - hall.left, y: r.top - hall.top, w: r.width, h: r.height };
  });
  // Soft light needs few pixels: the map is drawn at half size and stretched.
  // It is drawn on a canvas but shown as an image: a canvas is a layer of its
  // own, which would make the hall costly to zoom on a walk.
  const map = document.createElement("canvas"), ctx = map.getContext("2d"), res = .5;
  map.width = Math.ceil(hall.width * res);
  map.height = Math.ceil(hall.height * res);
  ctx.scale(res, res);
  ctx.fillStyle = getComputedStyle($("#lightmap")).getPropertyValue("--shade");
  ctx.fillRect(0, 0, hall.width, hall.height);
  // An oval of light: with stops [offset, how much] it takes that much of the
  // shade away (or, given a colour, lays that much of the colour on).
  const pool = (x, y, rx, ry, stops, colour) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(rx, ry);
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, 1);
    for (const [o, a] of stops) g.addColorStop(o, rgba(colour || "#000000", a));
    ctx.fillStyle = g;
    ctx.fillRect(-1, -1, 2, 2);
    ctx.restore();
  };
  const sconceAt = [];
  for (let i = 1; i < arches.length; i++) {
    const l = arches[i - 1], r = arches[i];
    sconceAt.push({ x: (l.x + l.w + r.x) / 2, y: r.y + r.h * .05, gap: r.x + r.w / 2 - (l.x + l.w / 2) });
  }
  ctx.globalCompositeOperation = "destination-out";
  for (const a of arches) {
    const cx = a.x + a.w / 2, base = a.y + a.h;
    pool(cx, base - a.h * .36, a.w * .64, a.h * .66, [[0, 1], [.7, 1], [1, 0]]);  // the doorway, lit from inside
    pool(cx, base, a.w * .95, hall.height * .2, [[0, .85], [1, 0]]);  // its light out across the floor
    pool(cx, a.y - a.h * .07, a.w * .34, a.h * .08, [[0, .55], [.5, .55], [1, 0]]);  // the plaque over it, catching the sconces
  }
  for (const s of sconceAt) pool(s.x, s.y + s.gap * .1, s.gap * .42, s.gap * .66, [[0, 1], [.25, .85], [1, 0]]);
  ctx.globalCompositeOperation = "source-over";
  // The light's colour: each doorway's on the floor before it, the sconces' warm.
  for (const a of arches) pool(a.x + a.w / 2, a.y + a.h, a.w * .9, hall.height * .18, [[0, .14], [1, 0]], SPILL[a.view]);
  for (const s of sconceAt) pool(s.x, s.y + s.gap * .1, s.gap * .42, s.gap * .66, [[0, .12], [1, 0]], "#ffb060");
  map.toBlob(blob => {
    if (!blob) return;
    const img = $("#lightmap"), old = img.src;
    img.src = URL.createObjectURL(blob);
    if (old.startsWith("blob:")) URL.revokeObjectURL(old);
  });

  const bloom = [], sconces = [];
  for (const a of arches) {
    const cx = a.x + a.w / 2, base = a.y + a.h, tint = SPILL[a.view];
    bloom.push(`<i class="spill" data-for="${a.view}" style="left:${px(cx)};top:${px(base)};width:${px(a.w * 1.5)};height:${px(hall.height * .34)};--c:${tint}"></i>`);
  }
  // A sconce where each pair of arches part.
  for (const { x, y, gap } of sconceAt) {
    sconces.push(`<span class="sconce" style="left:${px(x)};top:${px(y)}"></span>`);
    bloom.push(`<i class="halo" style="left:${px(x)};top:${px(y)};width:${px(gap * .9)};height:${px(gap * 1.1)}"></i>`);
  }
  $("#bloom").innerHTML = bloom.join("");
  $("#sconces").innerHTML = sconces.join("");
}

// Relaid whenever the hall or a doorway changes size (the plaques' font arriving, say).
const relight = new ResizeObserver(light);
relight.observe($("#hall"));
document.querySelectorAll(".arch").forEach(a => relight.observe(a));
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", light);
// A doorway pointed at (or focused) throws more light out onto the floor.
for (const door of document.querySelectorAll(".door")) {
  for (const [type, on] of [["pointerenter", true], ["pointerleave", false], ["focus", true], ["blur", false]]) {
    door.addEventListener(type, () => $(`.spill[data-for="${door.dataset.go}"]`)?.classList.toggle("lit", on));
  }
}

// On a phone the halls stand one at a time in a row that scrolls sideways
// (style.css): the arrows step through them, round from the last to the
// first, and the dots under them jump straight to one.
const doorRow = $(".doors"), doorList = [...doorRow.querySelectorAll(".door")];
const hallShown = () => Math.round(doorRow.scrollLeft / (doorRow.clientWidth || 1));
function pickHall(i) {
  i = (i + doorList.length) % doorList.length;
  doorRow.scrollTo({ left: i * doorRow.clientWidth, behavior: motion ? "smooth" : "auto" });
}
for (const [i, door] of doorList.entries()) {
  const dot = document.createElement("button");
  dot.type = "button";
  dot.setAttribute("aria-label", door.querySelector(".plaque b").textContent);
  dot.addEventListener("click", () => pickHall(i));
  $(".pick-dots").append(dot);
}
function markHall() {
  const i = hallShown();
  $(".pick-dots").querySelectorAll("button").forEach((b, j) => b.setAttribute("aria-current", i === j));
}
$(".pick.prev").addEventListener("click", () => pickHall(hallShown() - 1));
$(".pick.next").addEventListener("click", () => pickHall(hallShown() + 1));
doorRow.addEventListener("scroll", markHall, { passive: true });
markHall();

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

// ---------- the map on the easel ----------
// hub/atlas.py draws the Union of Crownweave from the Azgaar save and the
// lore-book into atlas/: terrain.webp (land and sea, as one picture) and
// crownweave.json (borders, rivers, roads, towns with their gazetteer entries,
// and labels). The easel shows the picture; opened, the rest is drawn over it
// in SVG, to drag and zoom, and a town chosen shows its entry beside the map.
// Markers and names stay the same size on screen however far in you zoom
// (--u is map units per screen pixel), and the smaller places' names only
// appear once there is room for them.

let atlas = null;  // crownweave.json, once loaded
const atlasView = { x: 0, y: 0, w: 1, h: 1 };
const SVGNS = "http://www.w3.org/2000/svg";
const KIND = { capital: "City", city: "City", town: "Town", village: "Village", hamlet: "Hamlet", fort: "Fort",
  caravanserai: "Caravanserai", trading_post: "Trading post", monastery: "Monastery" };
const HAS = { walls: "walled", citadel: "a citadel", temple: "a temple", plaza: "a market square", shanty: "a shanty-quarter", port: "a harbour" };
const atlasLayers = [["roads", "Roads"], ["rivers", "Rivers"], ["borders", "Borders"], ["names", "Names"]];

// A smooth line through the points (Catmull-Rom, as Azgaar draws its routes).
function curvePath(pts) {
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(i - 1, 0)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(i + 2, pts.length - 1)];
    const c = (a, b, k) => (a + (b * k)).toFixed(2);
    d += `C${c(p1[0], (p2[0] - p0[0]) / 6, 1)} ${c(p1[1], (p2[1] - p0[1]) / 6, 1)} ${c(p2[0], -(p3[0] - p1[0]) / 6, 1)} ${c(p2[1], -(p3[1] - p1[1]) / 6, 1)} ${p2[0]} ${p2[1]}`;
  }
  return d;
}

function svgEl(tag, attrs = {}, parent = null) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (parent) parent.append(el);
  return el;
}

function townMarker(t, g) {
  const seat = t.seat || t.group === "capital";
  if (seat) svgEl("rect", { x: -4.2, y: -4.2, width: 8.4, height: 8.4, class: "pin" }, g);
  else if (t.group === "fort") svgEl("path", { d: "M0 -4L4 0 0 4-4 0Z", class: "pin" }, g);
  else if (t.group === "caravanserai" || t.group === "trading_post") svgEl("path", { d: "M0 -4L3.8 3H-3.8Z", class: "pin" }, g);
  else svgEl("circle", { r: { city: 4.4, town: 3.4, village: 2.5, hamlet: 1.9 }[t.group] || 2.5, class: "pin" }, g);
}

function drawAtlas() {
  const d = atlas, svg = $("#atlasSvg"), [x, y, w, h] = d.terrainBox || d.viewBox;
  svg.replaceChildren();
  svgEl("image", { href: d.terrain, x, y, width: w, height: h, preserveAspectRatio: "none" }, svg);
  const layer = name => svgEl("g", { class: `layer ${name}` }, svg);
  const borders = layer("borders"), rivers = layer("rivers"), roads = layer("roads"), names = layer("names"), towns = layer("towns");
  for (const line of d.provinceBorders) svgEl("path", { d: curvePath(line), class: "border" }, borders);
  for (const r of d.rivers) svgEl("path", { d: curvePath(r.pts), class: "river", "stroke-width": (r.w * 2.4).toFixed(2) }, rivers);
  const order = { searoutes: 0, trails: 1, roads: 2 };
  for (const r of [...d.routes].sort((a, b) => order[a.group] - order[b.group])) {
    const path = svgEl("path", { d: curvePath(r.pts), class: `route ${r.group}` }, roads);
    if (r.name) svgEl("title", {}, path).textContent = r.name;
  }
  for (const l of d.labels) {
    const g = svgEl("g", { transform: `translate(${l.x} ${l.y})` }, names);
    svgEl("text", { class: (l.kind === "prov" ? "plabel" : "llabel") + (l.small ? " small" : ""), "text-anchor": "middle" }, svgEl("g", { class: "mk" }, g)).textContent = l.text;
  }
  // Biggest last, so the cities sit on top of the villages round them.
  const rank = { hamlet: 0, fort: 1, village: 1, caravanserai: 1, trading_post: 1, town: 2, city: 3, capital: 4 };
  const list = d.towns.map((t, i) => ({ ...t, i })).sort((a, b) => (rank[a.group] ?? 1) - (rank[b.group] ?? 1));
  for (const t of list) {
    const g = svgEl("g", { transform: `translate(${t.x} ${t.y})`, class: `town ${t.group}${t.seat ? " seat" : ""}${t.union ? "" : " abroad"}`,
      tabindex: 0, role: "button", "data-i": t.i, "aria-label": `${t.name}, ${KIND[t.group] || "Settlement"}${t.prov ? `, ${t.prov}` : ""}` }, towns);
    const mk = svgEl("g", { class: "mk" }, g);
    townMarker(t, mk);
    svgEl("text", { x: 6, y: 4, class: "tname" }, mk).textContent = t.name;
  }
  $("#atlasTowns").innerHTML = d.towns.filter(t => t.union).map(t => `<option value="${escapeHTML(t.name)}">`).sort().join("");
}

// The view: a rectangle of the map, shown as the svg's viewBox.
function atlasPPU() {
  const r = $("#atlasSvg").getBoundingClientRect();
  return Math.min(r.width / atlasView.w, r.height / atlasView.h) || 1;
}
function setAtlasView() {
  const [x, y, w, h] = atlas.viewBox, v = atlasView;
  v.w = Math.min(Math.max(v.w, w / 16), w);
  v.h = v.w * h / w;
  // The view's middle stays over the island.
  v.x = Math.min(Math.max(v.x, x - v.w / 2), x + w - v.w / 2);
  v.y = Math.min(Math.max(v.y, y - v.h / 2), y + h - v.h / 2);
  const svg = $("#atlasSvg"), ppu = atlasPPU();
  svg.setAttribute("viewBox", `${v.x} ${v.y} ${v.w} ${v.h}`);
  svg.style.setProperty("--u", (1 / ppu).toFixed(4));
  svg.dataset.zoom = ppu < 1.6 ? "tiny" : ppu < 4.2 ? "far" : ppu < 7.5 ? "mid" : "near";
}
function fitAtlas() {
  const [x, y, w, h] = atlas.viewBox;
  Object.assign(atlasView, { x, y, w, h });
  setAtlasView();
}
function zoomAtlas(factor, cx, cy) {
  const v = atlasView;
  if (cx === undefined) { cx = v.x + v.w / 2; cy = v.y + v.h / 2; }
  const nw = Math.min(Math.max(v.w / factor, atlas.viewBox[2] / 16), atlas.viewBox[2]), k = nw / v.w;
  Object.assign(v, { x: cx - (cx - v.x) * k, y: cy - (cy - v.y) * k, w: nw });
  setAtlasView();
}
function atlasPoint(ev) {  // the map point under the pointer
  const svg = $("#atlasSvg"), pt = svg.createSVGPoint();
  pt.x = ev.clientX; pt.y = ev.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

const people = n => n >= 1000 ? `about ${n.toLocaleString("en-GB")} people` : n > 0 ? `about ${n} people` : "a handful of people";
const listing = items => items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;

function atlasLegend() {
  const toggles = atlasLayers.map(([key, label]) =>
    `<label><input type="checkbox" data-layer="${key}" ${$("#atlasSvg").classList.contains(`no-${key}`) ? "" : "checked"}> ${label}</label>`).join("");
  $("#atlasCard").innerHTML = `
    <p class="atlas-intro">One island in the middle sea. The Crown stands at its heart, ringed by the Crownlands and the Everstorm; Skyloom lies west, Northreach north, Stormwake east and Emberweave south. Choose any town for what the Compendium says of it.</p>
    <ul class="atlas-key">
      <li><i class="k seat"></i>Seat of a Weave</li><li><i class="k city"></i>City</li><li><i class="k town"></i>Town</li>
      <li><i class="k village"></i>Village or hamlet</li><li><i class="k fort"></i>Fort or stormgate</li><li><i class="k cara"></i>Caravanserai or trading post</li>
      <li><i class="k road"></i>Road</li><li><i class="k trail"></i>Trail</li><li><i class="k sea"></i>Sea lane</li><li><i class="k border"></i>Prefecture border</li>
    </ul>
    <div class="atlas-layers">${toggles}</div>
    <p class="atlas-src">Surveyed from ${escapeHTML(atlas.source.replace(/\.map$/, ""))}.</p>`;
}

function showTown(i, fly) {
  const t = atlas.towns[i], svg = $("#atlasSvg");
  svg.querySelector(".town.sel")?.classList.remove("sel");
  const g = svg.querySelector(`.town[data-i="${i}"]`);
  g?.classList.add("sel");
  if (fly) {
    const w = Math.min(atlasView.w, atlas.viewBox[2] / 4);
    Object.assign(atlasView, { w, x: t.x - w / 2, y: t.y - (w * atlas.viewBox[3] / atlas.viewBox[2]) / 2 });
    setAtlasView();
  }
  const lore = t.lore || {};
  const kind = t.name === "The Crown" ? "Heart of the Union" : t.seat ? `Seat of ${t.prov}` : KIND[t.group] || "Settlement";
  const has = listing(t.has.map(k => HAS[k]).filter(Boolean));
  $("#atlasCard").innerHTML = `
    <button class="atlas-back" type="button">← The whole Union</button>
    <p class="kicker">${escapeHTML(t.prov || "Beyond the Union")}</p>
    <h3>${escapeHTML(t.name)}</h3>
    ${lore.epithet ? `<p class="epithet">${escapeHTML(lore.epithet)}</p>` : ""}
    <p class="meta">${escapeHTML(kind)} · ${people(t.pop)}${has ? ` · ${escapeHTML(has)}` : ""}</p>
    ${lore.text ? `<p>${escapeHTML(lore.text)}</p><p class="atlas-src">From <i>${escapeHTML(lore.chapter)}</i>. <a href="#library" data-close>Read on in the Library →</a></p>`
      : `<p class="atlas-src">The Compendium has no entry for ${escapeHTML(t.name)} yet.</p>`}`;
}

function openAtlas() {
  if (!atlas) return;
  if (!$("#atlasSvg").firstChild) { drawAtlas(); atlasLegend(); }
  $("#atlas").showModal();
  requestAnimationFrame(fitAtlas);
}

async function loadAtlas() {
  try {
    const res = await fetch("atlas/crownweave.json");
    if (!res.ok) return;
    atlas = await res.json();
    $("#mapstand").hidden = false;
    dispatchEvent(new Event("atlas"));
  } catch { /* no map drawn yet (uv run hub/atlas.py); the easel stays away */ }
}

{
  // The svg captures the pointer so a drag can leave it, which also sends it
  // the click: so a town is chosen by the press and release, not the click.
  const svg = $("#atlasSvg"), pointers = new Map();
  let moved = 0, pinch = 0, pressed = null;
  svg.addEventListener("wheel", ev => {
    ev.preventDefault();
    const p = atlasPoint(ev);
    zoomAtlas(Math.exp(-ev.deltaY * (ev.deltaMode ? .05 : .0018)), p.x, p.y);
  }, { passive: false });
  svg.addEventListener("pointerdown", ev => {
    pressed = pointers.size ? null : ev.target.closest(".town");
    pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
    svg.setPointerCapture(ev.pointerId);
    moved = 0;
    if (pointers.size === 2) { const [a, b] = pointers.values(); pinch = Math.hypot(a.x - b.x, a.y - b.y); }
  });
  svg.addEventListener("pointermove", ev => {
    const last = pointers.get(ev.pointerId);
    if (!last) return;
    const dx = ev.clientX - last.x, dy = ev.clientY - last.y;
    pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
    moved += Math.abs(dx) + Math.abs(dy);
    if (pointers.size === 2) {
      const [a, b] = pointers.values(), dist = Math.hypot(a.x - b.x, a.y - b.y);
      const mid = atlasPoint({ clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 });
      if (pinch) zoomAtlas(dist / pinch, mid.x, mid.y);
      pinch = dist;
    } else {
      const ppu = atlasPPU();
      atlasView.x -= dx / ppu; atlasView.y -= dy / ppu;
      setAtlasView();
    }
    svg.classList.toggle("dragging", moved > 4);
  });
  const lift = ev => {
    if (ev.type === "pointerup" && pressed && moved < 5) showTown(+pressed.dataset.i);
    pointers.delete(ev.pointerId); pinch = 0; pressed = null;
    if (!pointers.size) svg.classList.remove("dragging");
  };
  svg.addEventListener("pointerup", lift);
  svg.addEventListener("pointercancel", lift);
  svg.addEventListener("keydown", ev => {
    const g = ev.target.closest?.(".town");
    if (g && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); showTown(+g.dataset.i); return; }
    const pan = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[ev.key];
    if (pan && !g) { ev.preventDefault(); atlasView.x += pan[0] * atlasView.w * .1; atlasView.y += pan[1] * atlasView.h * .1; setAtlasView(); }
    if (ev.key === "+" || ev.key === "=") zoomAtlas(1.4);
    if (ev.key === "-") zoomAtlas(1 / 1.4);
  });
  for (const b of document.querySelectorAll("[data-zoom]"))
    b.addEventListener("click", () => b.dataset.zoom === "fit" ? fitAtlas() : zoomAtlas(b.dataset.zoom === "in" ? 1.6 : 1 / 1.6));
  new ResizeObserver(() => { if (atlas && $("#atlas").open) setAtlasView(); }).observe($("#atlasMap"));
  $("#atlasCard").addEventListener("click", ev => {
    if (ev.target.closest(".atlas-back")) { svg.querySelector(".town.sel")?.classList.remove("sel"); atlasLegend(); }
    if (ev.target.closest("[data-close]")) $("#atlas").close();
  });
  $("#atlasCard").addEventListener("change", ev => {
    const key = ev.target.dataset.layer;
    if (key) svg.classList.toggle(`no-${key}`, !ev.target.checked);
  });
  $("#atlasFind").addEventListener("change", ev => {
    const name = ev.target.value.trim().toLowerCase(), i = atlas.towns.findIndex(t => t.name.toLowerCase() === name);
    if (i >= 0) { showTown(i, true); ev.target.value = ""; }
  });
  $("#mapstand").addEventListener("click", openAtlas);
  $("#atlasClose").addEventListener("click", () => $("#atlas").close());
  $("#atlas").addEventListener("click", ev => { if (ev.target === ev.currentTarget) ev.currentTarget.close(); });
}

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
// After clerk.js has run too, so she hears about the notice and the map.
addEventListener("DOMContentLoaded", loadNotice);
addEventListener("DOMContentLoaded", loadAtlas);
