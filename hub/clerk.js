// Hessa Vane, the clerk behind the reception desk: scripted small talk.
// Loaded after app.js, whose $, status, motion, currentView and ringBell it uses.
//
// A conversation is a walk through TALK. Each node has a line (what Hessa
// says, as [mood, text]; mood is the face she makes) and replies (the buttons
// under it, as [label, next], where next is another node or a function).
// Lines can be a list (one is picked at random), a bag (like a list, but no
// repeats until it runs out) or a function of the moment (time, tool status).

const pick = list => list[Math.floor(Math.random() * list.length)];
function bag(list) {
  let left = [];
  return () => {
    if (!left.length) left = [...list].sort(() => Math.random() - .5);
    return left.pop();
  };
}
const toolState = app => status && status.apps[app] ? status.apps[app].state : null;
const isOpen = app => ["ready", "external"].includes(toolState(app));

const visits = (() => {
  const n = (Number(stored("hub.clerk.visits")) || 0) + 1;
  stored("hub.clerk.visits", String(n));
  return n;
})();
let introduced = stored("hub.clerk.introduced") === "yes";

/* ---------- what she says ---------- */

function greeting() {
  if (!introduced) {
    introduced = true;
    stored("hub.clerk.introduced", "yes");
    return ["surprised", "Oh! A visitor. Welcome to the Threadmint. I'm Hessa, front desk. The halls are behind me; I'm what you get before them."];
  }
  if (visits >= 12 && Math.random() < .3)
    return ["smug", `Visit number ${visits}. I've started a file on you. Don't worry, everyone gets a file.`];
  const h = new Date().getHours();
  if (h >= 23 || h < 5) return pick([
    ["flat", "It's late. The Threadmint never closes, but I would like it to."],
    ["flat", "Past midnight. The Bestiary gets louder around now. Don't ask me why. Well, you can ask."],
  ]);
  if (h < 12) return pick([
    ["smile", "Morning. The Library's quiet, the Bestiary isn't, and the coffee's gone."],
    ["flat", "Morning. You're the first one in. Second, if you count whatever's in the Bestiary."],
  ]);
  if (h < 18) return pick([
    ["smile", "Afternoon. What can I do for you?"],
    ["flat", "Afternoon. If you're here about the Spire audit, I know nothing, and it's redacted."],
  ]);
  return pick([
    ["smile", "Evening. Running a session tonight?"],
    ["smile", "Evening. The lamps are lit, the halls are open, and I'm nearly off shift."],
  ]);
}

const GOSSIP = bag([
  ["smug", "Someone at the Stormwake docks is selling \"genuine Spire fragments\". It's gravel. Crownweave gravel, to be fair, so it has provenance."],
  ["flat", "The Loom Council sat for nine hours yesterday. The minutes are one line long. The line is redacted."],
  ["smile", "An Emberweave courier asked me the way to the Verdant Tower. I told him to keep walking until it's yesterday."],
  ["flat", "Thal'vireth sent over their copy of the Hollow Archive. It's less redacted than ours, so we redacted it on arrival. Policy."],
  ["smug", "The Crucible filed a complaint about the noise from the Bestiary. The complaint was very loud."],
  ["flat", "Somebody asked for clarification on Seal SF-WA again. It's been logged. Everything is logged. Nothing is answered."],
  ["surprised", "Skyloom lost a cartographer last week. Not the person. The whole office. It's just not above the same bit of ground any more."],
  ["smile", "Northreach sent a crate of crystals marked \"processed, inert\". It hummed all night. I have moved my desk twice."],
  ["frown", "There's a debt collector from the Crimson Thread House who keeps asking for a library card. We don't know what it would do with one. We have said no in writing."],
]);

const LORE = bag([
  ["smile", "Crownweave is six peoples in one city, held together by the Charter of the Six and a great deal of paperwork. I'm some of the paperwork."],
  ["flat", "The Towers aren't ours. Nobody built them, officially. Authorship is, and I quote the treaty, \"undetermined\"."],
  ["flat", "In Thal'vireth they farm time. Stand too long near the Verdant Tower and you come home before you left. Or after your funeral."],
  ["smile", "Soulstone forms where the dead fall. Most of Tessarion cuts it and sells it. The elves refused. Cutting a memory, they say, kills it twice."],
  ["smug", "The market value of almost everything is in the Library, chapter ten. The market value of my patience is not listed."],
  ["flat", "Skyloom governs from above. Literally above. Their tax notices arrive by falling."],
  ["flat", "The Meridian Spire sits in the middle of Crownweave, and the city grew around it like a callus. The lower schematics were withdrawn. Don't ask me why. I'm not allowed to know either."],
  ["smile", "Emberweave is the southern gate: hot roads, quick tempers, excellent bread. Two out of three is a good average."],
  ["flat", "Stormwake is the harbour to the east, the one door the Union leaves open to the outside world. It's also where most of our lost property turns up."],
]);

const WORK = bag([
  ["flat", "Quiet. Someone tried to return a book to the Bestiary. It came back with teeth marks."],
  ["flat", "I stamped four hundred forms this morning. Three of them were forms requesting more forms."],
  ["frown", "The Bestiary's restless. It's always restless, but today it's restless in a new direction."],
  ["smile", "Fine, honestly. The candle and I have an understanding. It doesn't go out; I don't complain."],
]);

const HALLS = {
  library: {
    name: "The Library", app: "library",
    line: ["smile", "Every volume of the lore-book, shelved by subject, colour by colour. Pull one off the shelf and it opens for you. Please put it back."],
  },
  roster: {
    name: "The Roster", app: "roster",
    line: ["smug", "My records room, right behind me. One sheet per adventurer, kept in your own browser and nowhere else, so take a copy home. Keep your hit points honest."],
  },
  bestiary: {
    name: "The Bestiary", app: "bestiary",
    line: ["flat", "The register of hostile things. Portraits on cards; turn one over for the details. Some of the details are redacted for your safety. Some for ours."],
  },
};

function hallLine(id) {
  const h = HALLS[id];
  const [mood, text] = h.line;
  if (toolState(h.app) === "stopped")
    return ["frown", text + " It's shut at the moment, mind. Walk in and you can relight the lamps."];
  if (toolState(h.app) === "starting")
    return [mood, text + " They're still lighting the lamps in there; give it a moment."];
  return [mood, text];
}

// The main menu of things to ask her.
function menu() {
  return [
    asked.has("who") ? ["How's work?", "work"] : ["Who are you?", "who"],
    ["What's back there?", "halls"],
    ["Heard anything interesting?", "gossip"],
    ["Tell me about Tessarion.", "lore"],
    ["Can I see the restricted section?", "restricted"],
    ["Nothing, thanks.", "bye"],
  ];
}
const MORE = ["Something else.", "menu"], BYE = ["That's all, thanks.", "bye"];
const asked = new Set();

const TALK = {
  hello: { line: greeting, replies: menu },
  bell: { line: () => bellLine(), replies: menu },
  menu: { line: [["flat", "Anything else?"], ["smile", "Mm? What else?"], ["flat", "Go on."]], replies: menu },
  who: {
    line: ["flat", "Hessa Vane. Junior Registrar, front desk, Threadmint Library of Crownweave. Junior for eleven years now."],
    replies: [["Eleven years?", "eleven"], MORE, BYE],
  },
  eleven: {
    line: ["flat", "The Senior Registrar hasn't retired, died, or been seen since the Spire audit. Until one of those is made official, the post isn't vacant."],
    replies: [["That's grim.", "grim"], MORE],
  },
  grim: { line: ["smile", "It's paperwork. Paperwork is always a little grim."], replies: [MORE, BYE] },
  work: { line: WORK, replies: [["Anything else happen?", "gossip"], MORE, BYE] },
  gossip: { line: GOSSIP, replies: [["Go on, any more?", "gossip"], MORE, BYE] },
  lore: { line: LORE, replies: [["Tell me another.", "lore"], ["Where can I read more?", "readmore"], MORE] },
  readmore: {
    line: ["smile", "The Library, first door on the left. All of it's there, give or take the parts that aren't."],
    replies: [["Take me there.", () => go("library")], MORE],
  },
  halls: {
    line: ["flat", "Three halls. The Library on the left, the Roster behind me, the Bestiary on the right. Which one?"],
    replies: () => [...Object.entries(HALLS).map(([id, h]) => [h.name + "?", "hall:" + id]), MORE],
  },
  restricted: { line: ["flat", "No."], replies: [["Please?", "restricted2"], ["Fair enough.", "menu"]] },
  restricted2: {
    line: ["smug", "Still no. Your access tier is Public. You are, in the most literal sense, the public."],
    replies: [["I'm the DM, though.", "restricted3"], ["Fine.", "menu"]],
  },
  restricted3: {
    line: ["smug", "Then you wrote the redactions yourself, and you know perfectly well what's under them. Stop fishing."],
    replies: [["...Fair.", "menu"], BYE],
  },
  bye: {
    line: [["smile", "Mind the step."], ["flat", "Sign the ledger on your way out. Or don't. Nobody checks."],
      ["smile", "Good luck in there."], ["flat", "Go on, then."]],
    replies: [],
  },
};
for (const id of Object.keys(HALLS)) {
  TALK["hall:" + id] = { line: () => hallLine(id), replies: [["Take me there.", () => go(id)], ["What else is there?", "halls"], MORE] };
}

// Coming back through the desk from one of the halls.
const BACK_FROM = {
  library: [["smug", "Back from the Library. Did you put the book back where you found it? ...You didn't, did you."],
    ["smile", "Find what you were looking for? Nobody ever finds exactly what they were looking for."]],
  bestiary: [["smile", "You're back. All your limbs? Good. It makes the paperwork easier."],
    ["flat", "Anything in there look at you funny? They all do. Don't take it personally."]],
  roster: [["smug", "Back from the Roster. Did you level up, or did you just write that you did?"],
    ["flat", "Sheet in order? Good. Hit points are not a suggestion, whatever your cleric says."]],
};

const IDLE = bag([
  ["flat", "(Hessa turns a page of the ledger, reads it, and turns it back.)"],
  ["frown", "Someone's left the Bestiary door open again. I can hear it from here."],
  ["flat", "...four hundred and twelve. Four hundred and thirteen."],
  ["smile", "(She straightens the bell by about a millimetre.)"],
  ["flat", "If you're waiting for someone to tell you where to go: the doors. Any of them."],
]);

/* ---------- the bell ---------- */

let rings = [], confiscated = false;
function bellLine() {
  const n = rings.length;
  if (n <= 1) return ["surprised", "I'm right here. You don't need the bell."];
  if (n === 2) return ["flat", "Yes. Still here."];
  if (n === 3) return ["frown", "The bell is for emergencies, and for people who can't see me."];
  if (n === 4) return ["frown", "..."];
  return ["frown", "One more and it's confiscated."];
}
function onBell(kbd) {
  if (confiscated) return;
  ringBell();
  const now = Date.now();
  rings = rings.filter(t => now - t < 12000);
  rings.push(now);
  if (rings.length < 6) return show("bell", kbd);
  confiscated = true;
  rings = [];
  const bell = $("#bell"), tent = $(".tent"), was = tent.textContent;
  bell.hidden = true;
  tent.textContent = "Bell confiscated. Ask nicely.";
  speak(["smug", "Confiscated."], [], false);
  setTimeout(() => {
    confiscated = false;
    bell.hidden = false;
    tent.textContent = was;
    if (currentView() === "desk" && !talking) speak(["flat", "Fine. Have your bell back. Behave."], [], false);
  }, 30000);
}

/* ---------- saying it ---------- */

const clerk = $("#clerk"), bubble = $("#bubble"), sayEl = $("#bubble .say"), repliesEl = $("#bubble .replies"), srEl = $("#clerk-sr");
let talking = false;   // a conversation (with replies) is open
let typer = null, hideTimer = null, current = [], finishTyping = null;

function lineOf(node) {
  const l = typeof node.line === "function" ? node.line() : node.line;
  return typeof l[0] === "string" ? l : pick(l);  // a single [mood, text], or a list of them
}

function show(id, kbd) {
  asked.add(id);
  const node = TALK[id];
  const replies = typeof node.replies === "function" ? node.replies() : node.replies;
  speak(lineOf(node), replies, kbd);
  if (id === "bye") talking = false;
}

// Say one line, typed out while her mouth moves, then offer the replies. A
// line with no replies closes itself after a while.
function speak([mood, text], replies, kbd) {
  clearInterval(typer);
  clearTimeout(hideTimer);
  talking = replies.length > 0;
  current = replies;
  clerk.dataset.mood = mood;
  bubble.classList.add("show");
  bubble.setAttribute("aria-hidden", "false");
  repliesEl.innerHTML = "";
  srEl.textContent = "";
  srEl.textContent = `Hessa: ${text}`;
  const done = () => {
    clearInterval(typer);
    typer = null;
    sayEl.textContent = text;
    clerk.classList.remove("talking");
    repliesEl.innerHTML = replies.map(([label], i) => `<button type="button" data-i="${i}">${label}</button>`).join("");
    if (kbd && replies.length) repliesEl.querySelector("button").focus({ preventScroll: true });
    if (!replies.length) hideTimer = setTimeout(hide, Math.max(2600, text.length * 55));
  };
  if (!motion) return done();
  let i = 0;
  sayEl.textContent = "";
  clerk.classList.add("talking");
  typer = setInterval(() => {
    i += 2;
    sayEl.textContent = text.slice(0, i);
    if (i >= text.length) done();
  }, 28);
  finishTyping = done;
}

function hide() {
  clearInterval(typer);
  clearTimeout(hideTimer);
  typer = null;
  talking = false;
  bubble.classList.remove("show");
  bubble.setAttribute("aria-hidden", "true");
  clerk.classList.remove("talking");
  clerk.dataset.mood = "flat";
}

function go(view) {
  hide();
  location.hash = view;
}

/* ---------- wiring ---------- */

// kbd: started from the keyboard, so the first reply takes the focus.
clerk.addEventListener("click", ev => {
  if (talking) return hide();
  show("hello", ev.detail === 0);
});
$("#bell").addEventListener("click", ev => onBell(ev.detail === 0));
bubble.addEventListener("click", ev => {
  const b = ev.target.closest("button[data-i]");
  if (b) {
    const next = current[Number(b.dataset.i)][1];
    const kbd = ev.detail === 0;
    return typeof next === "function" ? next() : show(next, kbd);
  }
  if (typer) finishTyping();  // a click on the text finishes typing it
});
// A click anywhere else ends the conversation. (The path, not the target: a
// reply button is already gone, replaced by the next replies, by now.)
document.addEventListener("click", ev => {
  const inside = ev.composedPath().some(n => n === bubble || n === clerk || n === $("#bell"));
  if (bubble.classList.contains("show") && !inside) hide();
});
document.addEventListener("keydown", ev => {
  if (ev.key === "Escape" && bubble.classList.contains("show")) {
    const wasTalking = talking;
    hide();
    if (wasTalking) clerk.focus({ preventScroll: true });
  }
});

// Her eyes follow whichever doorway you point at (the one behind her, she ignores).
document.querySelectorAll(".door").forEach(door => {
  door.addEventListener("pointerenter", () => {
    const d = door.getBoundingClientRect(), c = clerk.getBoundingClientRect();
    const dx = d.left + d.width / 2 - (c.left + c.width / 2);
    if (Math.abs(dx) < c.width / 2) delete clerk.dataset.look;
    else clerk.dataset.look = dx < 0 ? "left" : "right";
  });
  door.addEventListener("pointerleave", () => { delete clerk.dataset.look; });
});

// A word when you come back out of a hall.
let prevView = currentView();
addEventListener("hashchange", () => {
  const view = currentView(), from = prevView;
  prevView = view;
  if (view !== "desk") { hide(); return; }
  if (from !== "desk" && BACK_FROM[from] && Math.random() < .7) {
    setTimeout(() => {
      if (currentView() === "desk" && !talking) speak(pick(BACK_FROM[from]), [], false);
    }, motion ? 2400 : 300);
  }
  idleSoon();
});

// Left alone at the desk for a while, she mutters. Now and then; not forever.
let idleTimer = null, mutters = 0;
function idleSoon() {
  clearTimeout(idleTimer);
  if (mutters >= 4) return;
  idleTimer = setTimeout(() => {
    if (currentView() === "desk" && !document.hidden && !bubble.classList.contains("show")) {
      mutters++;
      speak(IDLE(), [], false);
    }
    idleSoon();
  }, mutters ? 70000 + Math.random() * 40000 : 28000);
}
["pointerdown", "keydown"].forEach(t => addEventListener(t, idleSoon, { passive: true }));
idleSoon();
