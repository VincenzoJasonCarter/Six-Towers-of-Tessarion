// Talvender Prolyman, the stall's quartermaster: scripted talk, a word on each
// item's slip, and opinions about your tally. Loaded after app.js, whose $,
// esc, num, tally, totals, market, local, coin, LOCAL and storage it uses,
// and whose "market:slip", "market:tally" and "market:add" events it hears.
//
// The format is the hub's clerk.js: a line is [mood, text] (the mood is the
// face he makes: flat, smile, smug, frown, surprised, laugh), a conversation
// is a walk through TALK, and a node's line can be a list (one picked at
// random), a bag (no repeats until it runs out) or a function of the moment.
(() => {
const pick = list => list[Math.floor(Math.random() * list.length)];
function bag(list) {
  let left = [];
  return () => {
    if (!left.length) left = [...list].sort(() => Math.random() - .5);
    return left.pop();
  };
}
const motion = !matchMedia("(prefers-reduced-motion: reduce)").matches;

const visits = (() => {
  const n = (Number(storage("market.keeper.visits")) || 0) + 1;
  storage("market.keeper.visits", String(n));
  return n;
})();
let introduced = storage("market.keeper.introduced") === "yes";

/* ---------- what he says on the floor ---------- */

function greeting() {
  if (!introduced) {
    introduced = true;
    storage("market.keeper.introduced", "yes");
    return ["smile", "Welcome to the Guild's stall. Talvender Prolyman, quartermaster. Twenty-two years on the road, eleven behind this counter. Ask me before you buy something stupid."];
  }
  if (visits >= 10 && Math.random() < .3)
    return ["smug", `Back again. That's ${visits} visits. At this rate I'll start charging you rent.`];
  const h = new Date().getHours();
  if (h >= 23 || h < 5) return pick([
    ["flat", "We're closed. ...We're never closed. But it's late, and I'm counting rivets."],
    ["flat", "Midnight shopping. Either you've a job at dawn or you're running from one."],
  ]);
  if (h < 12) return pick([
    ["smile", "Morning. Fresh stock in from the Crucible, same as yesterday's stock, at the same price. The Guild loves a sure thing."],
    ["flat", "Morning. Coffee's mine. Everything else is for sale."],
  ]);
  if (h < 18) return pick([
    ["smile", "Afternoon. Looking, or buying? Looking's free. I've checked."],
    ["flat", "Afternoon. What are you after?"],
  ]);
  return pick([
    ["smile", "Evening. Kitting out for a session?"],
    ["smile", "Evening. Last orders before the road, is it?"],
  ]);
}

const WORK = bag([
  ["smile", "Steady. Rope sells. Rope always sells. Nobody thinks they'll need rope, and everybody needs rope."],
  ["flat", "Slow morning. Sold one dagger and gave one lecture on skinning knives. The lecture was free."],
  ["smile", "Good. Party of four came in, bought swords, came back an hour later for the shields I told them to buy."],
  ["frown", "Some lad tried to return a Crude Greatsword. Said it was faulty. It isn't faulty. It's crude. It says so on the tag."],
]);

const GOSSIP = bag([
  ["smug", "There's an Underweave outlet charging five times Official Value for rope. Five. Some fool will pay it. Some fool always does."],
  ["flat", "A purser bought forty tins of rations this morning. Thirty-four-day sail west, he said. Thal'vireth. Rather him than me."],
  ["flat", "Northreach is buying timber again. A plain staff costs you six at a Northreach street stall. Wood's scarce up there; they land it from the Frost Coast."],
  ["smug", "Somebody tried to pay in Tuskmark at an elven changer. Got eighty on the hundred and a lecture on manners."],
  ["frown", "A Loft Market stall in Skyloom is selling 'storm-proof' lighters. Storm-proof until the first storm."],
  ["flat", "Flint-and-Steel's powder went up at the street stalls again. Not here. The Guild never moves. That's the whole point of the Guild."],
  ["smile", "The Crucible's tinned rations survive soaking, fire and being sat on. I can vouch for the third. Not on purpose."],
  ["flat", "Hearthmark's up a hair against Hellglass this week. Ask a dwarf why, then ask a tiefling, then average the two lies."],
  ["smug", "A Crimson Seal is worth one-thirty at the Guild's changers. I've never held one. Nobody I'd want to know has either."],
  ["flat", "Someone at the docks is selling 'genuine Spire fragments'. Hessa at the front desk says it's gravel. Hessa's usually right."],
]);

const STORIES = bag([
  ["smile", "Caravan guard on the White Road, then the Adventurers' Guild, then whatever paid. I've carried every item on these shelves. Broken most of them."],
  ["laugh", "My first job I had a Crude Bow and ten arrows. Rolled badly, snapped three, ran dry by the second wolf. Bought iron-tipped after that. You get half back. Half's a lot, in the dark."],
  ["flat", "The Forge Run, in Northreach. We escorted a crate that hummed. We did not ask what was in it. We were paid triple not to ask."],
  ["frown", "The ear? Emberweave. A tiefling broker bit it. We'd agreed a price. Then, apparently, we hadn't."],
  ["smug", "The scar's from a Crude Greatsword. Mine. Missed by a mile and it took me with it. That's what 'Overweight Blade' means, rookie."],
  ["flat", "Why'd I retire? A door in Pekion. I kicked it in. It was load-bearing. In Northreach they put that on a bronze plate in the Chapel of Tolerances. My name's on the plate."],
  ["smile", "Went into the Underweave once. Paid five times Official Value for a lantern. Best money I ever spent. You'll understand when you're down there."],
  ["frown", "Never trust a musket you didn't clean yourself. And never trust a Gunman who says the misfire 'wasn't the gun'."],
]);

const NEW_STOCK = bag([
  ["smug", "Talk of Crucible steel. Proper martial work, not this iron. Not on my shelves yet, and not for anyone who still needs a Crude Sword."],
  ["flat", "Word is the Crucible's working a new grade of steel. My word is: survive Iron first."],
  ["smile", "There's always something coming. The trick is being alive when it gets here."],
]);

// Advice by calling. Each is what he'd tell a friend, rules and all.
const ADVICE = {
  aegis: ["smile", "Shield first. Rusty if you're skint, but a Rusty Shield gives you nothing against a crit; the Iron one holds. Then the Tunic. Then the heaviest thing you can swing. You're going to be hit. That's the job."],
  archer: ["flat", "A Crude Crossbow before a Crude Bow: the bow halves your feet every time you loose. And arrows. More than you think. Iron-tipped ones don't break, and half come back after a fight."],
  gunman: ["frown", "Your musket's the loudest thing in the room: everything within three hundred feet knows where you are. Buy Paper Cartridges before your first storm, not after. And powder's scarce outside Northreach."],
  mage: ["smug", "Leather Tunic, a Basic Dagger, rations. The dagger's for skinning and cutting rope; you get advantage on those. You're not swinging a greatsword with those arms, and we both know it."],
  rookie: ["smile", "Rations, rope, a lighter, a weapon you can actually use. A short rest and a day's rations put you right after any fight, so buy rations like you'll fight a lot. You will."],
};

function menu() {
  return [
    asked.has("who") ? ["How's business?", "work"] : ["Who are you?", "who"],
    ["What should I buy?", "advice"],
    ["How do prices work here?", "prices"],
    ["Heard anything?", "gossip"],
    ["Tell me a story.", "story"],
    ["Anything new coming in?", "newstock"],
    ["Just looking, thanks.", "bye"],
  ];
}
const MORE = ["Something else.", "menu"], BYE = ["That's all, thanks.", "bye"];
const asked = new Set();

const TALK = {
  hello: { line: greeting, replies: menu },
  menu: { line: [["flat", "What else?"], ["smile", "Go on."], ["flat", "Mm?"]], replies: menu },
  who: {
    line: ["smile", "Talvender Prolyman. Quartermaster of the Guild's chartered stall. Before that, twenty-two years carrying this stuff into places it shouldn't go."],
    replies: [["Why'd you stop?", "retired"], ["Tell me a story.", "story"], MORE],
  },
  retired: {
    line: ["flat", "A door in Pekion. I kicked it in. It was load-bearing. Long story, short ceiling."],
    replies: [["...And?", "retired2"], MORE],
  },
  retired2: {
    line: ["laugh", "And now I sell doors' worth of rope to people who'll kick in their own. It's a living. A safer one."],
    replies: [MORE, BYE],
  },
  work: { line: WORK, replies: [["Heard anything?", "gossip"], MORE, BYE] },
  advice: {
    line: ["flat", "Depends what you are. What are you?"],
    replies: [["Aegisbound.", "adv:aegis"], ["An Archer.", "adv:archer"], ["A Gunman.", "adv:gunman"],
      ["A crystal mage.", "adv:mage"], ["Just starting out.", "adv:rookie"], MORE],
  },
  prices: {
    line: ["flat", "Every tag's the Official Value: the Guild's price, in Crownsblood. Add it up, round to the nearest coin, halves up. Nothing costs less than one CB. Same in every Guild stall from Caer Veyn to Phais."],
    replies: [["And outside the Guild?", "prices2"], MORE],
  },
  prices2: {
    line: ["frown", "Outside, they start from my price and multiply. Twice at a Loft Market, three times at a street stall, four on the frontier, five in the Underweave. Double again if the thing's scarce there. And they always round up."],
    replies: [["Can I haggle with you?", "haggle"], MORE],
  },
  haggle: {
    line: ["smug", "With me? No. That's the Guild's whole bargain: you never get robbed, and you never get a deal. Haggle out there. Never below their cost, mind; they'll laugh you out."],
    replies: [MORE, BYE],
  },
  gossip: { line: GOSSIP, replies: [["Any more?", "gossip"], MORE, BYE] },
  story: { line: STORIES, replies: [["Another.", "story"], MORE, BYE] },
  newstock: { line: NEW_STOCK, replies: [MORE, BYE] },
  bye: {
    line: [["smile", "Mind the tally."], ["flat", "Buy rope."], ["smile", "Come back alive. Customers who don't are terrible for repeat business."],
      ["flat", "Go on, then."]],
    replies: [],
  },
};
for (const [id, line] of Object.entries(ADVICE)) {
  TALK["adv:" + id] = { line, replies: [["What about someone else?", "advice"], MORE, BYE] };
}

const IDLE = bag([
  ["flat", "(Talvender slides a bead along the abacus, frowns at it, and slides it back.)"],
  ["smile", "(He tests a bowstring with his thumb. It twangs. He nods at it, approvingly.)"],
  ["flat", "Rope. Get rope. I'm only saying."],
  ["flat", "(He polishes the brass scales and squints at his reflection in the pan.)"],
  ["smug", "Staring at a sword doesn't make it cheaper. I've tested that too."],
]);

/* ---------- a word on an item's slip ---------- */

// What he says about each item, by id; a kind's line covers anything newer.
const ON_ITEM = {
  "crude-sword": ["flat", "Starter blade. Roll a 1 and you wobble for a turn. Everyone starts here; nobody stays."],
  "crude-bow": ["frown", "It shoots. Your feet don't: half speed every time you loose. Plant yourself and pray."],
  "arrow-bundle": ["flat", "Ten arrows. A 1 snaps one. Buy two bundles. Three, if you're me."],
  "crude-greatsword": ["smug", "Big. Heavy. Miss by five and you go nowhere. See this eyebrow? That's this sword."],
  "rusty-shield": ["frown", "Two AC, right up until someone lands a crit. Then nothing. 'Rusty' is the honest word on that tag."],
  "basic-dagger": ["smile", "Best thing on the shelf for a copper of brains: skinning, cutting rope, opening crates. Don't throw it; it lands soft."],
  "quarterstaff-husk": ["flat", "Hollow. Hit something hard enough and it snaps. Good for walking. Mostly for walking."],
  "crude-battle-axe": ["flat", "The biggest one-handed die on the Tier I shelf. Swing wide and it drags you off your feet."],
  "club": ["laugh", "Cheapest weapon here. Its real job's doors: advantage on breaking them, and I've never met a door that didn't deserve it."],
  "crude-crossbow": ["smile", "Hits harder than the bow and leaves your legs alone. A bad pull costs you a whole turn re-spanning, though."],
  "bolt-bundle": ["flat", "Bolts. Same deal as arrows: a 1 snaps one."],
  "matchlock-musket": ["frown", "Biggest die in the book. Also the loudest thing in the room: everything within three hundred feet knows exactly where you are."],
  "crude-handgun": ["flat", "One hand free, a smaller bang. Still loud. Still fouls on a 1."],
  "shot-and-powder": ["frown", "Loose powder in a horn. Go swimming and you're carrying ten damp promises until a short rest dries them."],
  "iron-sword": ["smile", "Honest iron. One more damage, and a bad roll only costs you five feet. This is what a sword should be."],
  "seasoned-bow": ["smile", "No penalty at long range, and you keep your legs. If you move a lot, this is your bow."],
  "composite-bow": ["flat", "Hits harder and reaches as far as anything. Heavy draw: half speed when you shoot. Choose your bow by your feet."],
  "iron-mace": ["smug", "Cracks armour. Against a plated knight it's a bargain. Against a cultist in a bathrobe it's a stick."],
  "iron-greatsword": ["smile", "The Crude Greatsword without the bit where it ruins your face. Miss by five and you lose five feet, not ten."],
  "iron-shield": ["smile", "Holds on a crit, one point anyway. I'd buy this before a better sword. I did, eventually. Took me two scars."],
  "iron-battle-axe": ["flat", "Forward-heavy. Hits like a decision. Miss badly and it pulls you a step."],
  "iron-dagger": ["smile", "No drawback at all. 'Refined simplicity', the Guild calls it. I call it a good knife."],
  "quarterstaff": ["smug", "Solid core, no more snapping, and a hit rattles them for their next swing. One CB. Steal of the shelf, and I'm not supposed to say that."],
  "iron-shod-club": ["flat", "Light, so it rides in the off hand. Crit and they may go down. Still opens doors."],
  "iron-tipped-arrow-bundle": ["smile", "These don't break, and half come back after a fight. Over a season they pay for themselves twice."],
  "iron-crossbow": ["smile", "Steel prod. When the latch slips it's a bonus action to fix, not your whole turn."],
  "iron-bolt-bundle": ["flat", "Half back after a fight. Count them. The Guild doesn't refund the ones you leave in a goblin."],
  "black-powder-rifle": ["smile", "Flint-and-Steel's pride. Eighty feet, two hundred long, and a misfire clears with a bonus action. Twelve CB and worth every coin."],
  "heavy-handgun": ["frown", "For when the thing reaches you anyway. And it will."],
  "paper-cartridges": ["smug", "Waxed paper: your powder stays dry whatever happens to you. Buy these before your first storm, not after."],
  "leather-tunic": ["smile", "The one piece I'd tell anyone to buy. Even mages. Especially mages."],
  "leather-leggings": ["flat", "A Dex save or a few feet of speed. You choose once and you're stuck with it, so choose for the party you've got."],
  "leather-hood": ["smile", "A hood that notices ambushes. I've had worse friends."],
  "leather-boots": ["laugh", "Speed or not falling over. I chose speed. I still fell over, only faster."],
  "riveted-brigandine": ["flat", "One more AC than leather, and it turns the worst blow of a fight. It clinks, though. If your friends sneak, you wait outside."],
  "riveted-leggings": ["flat", "Doubles down on whatever your leggings already chose. Pick right the first time."],
  "riveted-coif": ["flat", "Sharper eyes, or a quicker start if you went for ambushes. Initiative's the only number a helmet should give you."],
  "riveted-boots": ["smile", "Speed that won't be dragged down, or feet that won't be shoved. Pairs nicely with any blade that slows you on a miss."],
  "impure-ingot": ["flat", "Low-grade smelt, high impurity. Fine for a first sword. Not for a second."],
  "fabric": ["flat", "Linen or wool, untreated. Padding, wadding, bandages, and the occasional flag of surrender."],
  "wood-bundle": ["smug", "Ten handles' worth of lumber. Cheap here. A Northreach stall will charge you double for it, and smile."],
  "cord-bundle": ["flat", "Plant fibre. Holds a hilt together. Doesn't hold a grudge."],
  "iron-ingot": ["flat", "Industry-standard iron. Everything on the Tier II shelf starts as a few of these."],
  "cured-hide": ["flat", "Kiln-dried, treated. Every bit of leather armour starts here."],
  "seasoned-timber": ["flat", "Kiln-dried and cut true. Bows, hafts, stocks."],
  "treated-leather-strip": ["flat", "Oil-treated and tension-set. Grips that don't slip when your hands sweat. They will sweat."],
  "iron-rivets": ["flat", "Thirty rivets. Riveted armour eats more of them than you'd think."],
  "binding-fiber": ["flat", "Sinew and fibre, for bows and boots."],
  "animal-oil-resin": ["smile", "Tar, glue, lamp oil, lighter fuel. Cheapest useful thing in the shop."],
  "soft-lining": ["flat", "Cloth or fur for under a helmet. Your scalp will thank you."],
  "black-powder": ["frown", "Flint-and-Steel's, under Guild seal, and scarce outside Northreach. Keep it dry or keep it useless."],
  "rations": ["smile", "A day's food. A short rest and a day's rations and you're on your feet again. Fight a lot? Eat a lot."],
  "rope": ["smug", "Nobody thinks they'll need rope. Everybody needs rope."],
  "compression-lighter": ["frown", "Spring striker, resin chamber. Works, except in wind. Or rain. Or when you need it."],
  "crucible-tinned-rations": ["smile", "Never spoil. Same price a day as plain rations, so they're not cheaper, they're surer. That matters on a long sail."],
  "tarred-rope-grapnel": ["smile", "Throw it thirty feet and climb with advantage. Turns rope from a thing you tie into a way up."],
  "storm-lighter": ["smile", "Lights in wind and rain, first try, and a pot of resin refills it. The lighter I wish I'd had for twenty years."],
  "hooded-lantern": ["flat", "Thirty feet of light, both hands free, and a hood to shut it when something's looking back. Northreach knows its dark."],
  "smiths-tools": ["flat", "Hammers, tongs, a hardy. You'll still need a forge: hire one by the day."],
  "leatherworkers-tools": ["smile", "One CB and you can mend your own armour. Do."],
  "carpenters-tools": ["flat", "Saw, adze, planes. Clubs, staves, bows."],
  "bowyers-kit": ["flat", "Bows and crossbows and nothing else, but it does those properly."],
  "fletchers-tools": ["smile", "An archer who makes their own arrows never runs out. Well. Runs out less."],
  "tinkers-tools": ["flat", "The dearest kit here, because it's the gunsmith's. Locks, lanterns, lighters, guns."],
  "weavers-tools": ["smug", "Turn cord into rope and you'll feel very clever for about a minute."],
  "forge-hire": ["flat", "A day at a chartered forge. Bring your own tools. They won't lend you theirs, and I don't blame them."],
  // Tier 3, Crownweave steel.
  "steel-longsword": ["smile", "Crucible steel, a real martial blade at last, and it answers back when they miss you. I'd have killed for this at your age. I did kill, actually, with worse."],
  "sabre": ["smug", "Hybrid: aim with your eye, cut with your arm, both count. First blade on these shelves a nimble sort can live by. Mind the 1s; it bends."],
  "spear": ["smile", "Two hands, ten feet of reach. Just don't let them inside the point, or you're poking at air."],
  "steel-capped-staff": ["laugh", "Knocks people flat. Four CB. I keep telling the Guild it's underpriced. They keep not listening."],
  "steel-greatsword": ["smile", "Even a miss bites. Two scars I'd not have if they'd made these when I started."],
  "halberd": ["flat", "Hook them in, shove them off a ledge. Useless in a tunnel; I learned that the hard way, under Pekion."],
  "bearded-axe": ["smug", "Hooks the shield aside for whoever swings next. Teamwork, in axe form."],
  "steel-warhammer": ["flat", "Against plate it's a can-opener. Against a bathrobe it's still a stick."],
  "watchmans-cudgel": ["smile", "The Watch's favourite. Doesn't kill quick. Makes the other fellow miss. Most fights, that's the same thing."],
  "stiletto": ["flat", "Finds the gap. Crits on a 19. Still skins a rabbit."],
  "steel-kite-shield": ["smile", "Holds on a crit and covers the friend beside you. Heavy, though. Eat your porridge first."],
  "buckler": ["smug", "For people who'd rather not be hit than survive being hit. I was never one of them. Look at my face."],
  "steel-backed-longbow": ["smile", "As strong as the heavy bows and you keep your legs. If you move, this is the one."],
  "warbow": ["flat", "Two hundred feet before the long range even starts. Wants a strong back, and you'll be standing still."],
  "arbalest": ["smile", "Punches through cover like it isn't there. Wind it, wait, and make it count."],
  "hand-crossbow": ["flat", "Small, loud enough, and it doesn't mind when they're in your face."],
  "bodkin-arrow-bundle": ["smile", "Narrow heads for the gaps in plate. Archers' old weakness, mended."],
  "bodkin-bolt-bundle": ["smile", "Bodkins for the crossbow. Same trick, heavier delivery."],
  "long-rifle": ["smile", "Cloudglass sight. You'll hit things you can barely see. They'll hear you from three hundred feet, mind."],
  "duelling-pistol": ["frown", "For when it reaches you. It always reaches you."],
  "hand-bombard": ["surprised", "That's the loudest thing I sell. Six hundred feet of everyone knowing. Brace, or it'll sit you down."],
  "crucible-cartridges": ["smile", "A primer under every ball. A 1's just a miss now. No more fouled barrels."],
  "bombard-shells": ["frown", "Four shells. Keep them dry. Keep them away from the campfire. Keep them away from me."],
  "steel-harness": ["smile", "Full plate. You'll clank, you'll sweat, and you'll live. The first crit of the fight just glances."],
  "feathersteel-jack": ["smile", "Skyloom's harness steel. Quiet as leather, and you'll fall softer. Nimble folk only; it wants your Dex."],
  "aegis-bonded-plate": ["flat", "Not mine to sell. The Infusion Forges bond it to one Aegisbound and one only. Turns spells the way plate turns steel."],
  "splinted-greaves": ["flat", "Whatever your leggings chose, more of it."],
  "steel-sallet": ["flat", "Sharper eyes, or a quicker start. Still no AC. Helmets lie about that."],
  "steel-sabatons": ["smile", "Even a spell won't slow you, or won't shift you, whichever you chose. Steel all the way down."],
  "crucible-steel-ingot": ["flat", "Crucible steel. Everything on the Tier III shelf starts here."],
  "feathersteel-strip": ["flat", "Castfield's springing steel, the stuff of flight harness."],
  "skywood-timber": ["flat", "Burtonrith's skycraft wood. Light, straight, and it doesn't warp."],
  "castfield-leather": ["flat", "Hardened and oil-sealed. Grips that don't slip, straps that don't stretch."],
  "spring-steel-coil": ["flat", "Bybdetos spring steel. Prods, locks, launchers."],
  "steel-rivets": ["flat", "Steel rivets. Plate eats them."],
  "cloudglass-lens": ["flat", "Midhurstnes cloudglass, ground true. Don't drop it."],
  "feathersteel-line-grapnel": ["smile", "Sixty feet up on a spring. I'd have saved a week of my life with this."],
  "bullseye-lantern": ["flat", "Light where you point it. Shut the hood when something points back."],
  "cloudglass-spyglass": ["smile", "See them before they see you. Most fights are won right there."],
  "signal-flares": ["flat", "Fire one and everyone for miles knows where you are. Choose 'everyone' carefully."],
};
const ON_KIND = {
  weapon: ["flat", "Haven't swung that one myself. Read the power line twice; the drawback's the part that kills you."],
  ammunition: ["flat", "Count it before you leave, and count it again after the fight."],
  shield: ["smile", "A shield. Good. More people should buy shields."],
  armor: ["flat", "Armour. Check what it costs you, not just what it gives you."],
  material: ["flat", "Raw stock. Only worth it if you've the tools and the time."],
  utility: ["flat", "Road gear. The boring things are the ones that keep you alive."],
  tool: ["flat", "Tools. Every recipe names its kit; no kit, no craft."],
  service: ["flat", "A service. Paid by the day."],
};

/* ---------- opinions about the tally ---------- */

const has = (...ids) => ids.some(id => tally[id] > 0);
const count = (...ids) => ids.reduce((s, id) => s + (tally[id] || 0), 0);
const BOWS = ["crude-bow", "seasoned-bow", "composite-bow", "steel-backed-longbow", "warbow"];
const ARROWS = ["arrow-bundle", "iron-tipped-arrow-bundle", "bodkin-arrow-bundle"];
const XBOWS = ["crude-crossbow", "iron-crossbow", "arbalest", "hand-crossbow"], BOLTS = ["bolt-bundle", "iron-bolt-bundle", "bodkin-bolt-bundle"];
const GUNS = ["matchlock-musket", "crude-handgun", "black-powder-rifle", "heavy-handgun", "long-rifle", "duelling-pistol"];
const ROUNDS = ["shot-and-powder", "paper-cartridges", "crucible-cartridges"];
const TWO_HANDED = ["crude-greatsword", "iron-greatsword", "steel-greatsword", "halberd", ...BOWS, "crude-crossbow", "iron-crossbow", "arbalest",
  "matchlock-musket", "black-powder-rifle", "long-rifle", "hand-bombard"];
const SHIELDS = ["rusty-shield", "iron-shield", "steel-kite-shield", "buckler"];
const AT_MARKET = { loft: "a Loft Market", street: "a street stall", frontier: "a frontier trader's", underweave: "an Underweave outlet" };
const COIN_TALK = {
  Lifesap: "Paying in Lifesap? Elven coin goes further here than you'd think. Don't tell them I said so.",
  Hearthmark: "Hearthmark. Check the rim for the Pydros hammer-mark; I will.",
  Hellglass: "Hellglass. It's good coin. It's just never quite as good as the tiefling says it is.",
  Tuskmark: "Tuskmark, eh. The Guild takes it at nine on the ten. An elven changer would take it at a lot less, and a lecture.",
  "Crimson Seal": "...Crimson Seals. I'm not going to ask where you got them. I'm going to count them twice.",
};

// What the tally is about right now, most pressing first: [key, mood, line].
// A key keeps the same line while it holds, so changing a quantity doesn't
// make him change his mind every click.
function tallyRemark() {
  const t = totals();
  if (!t.count) return ["empty", "flat", "Empty tally. Tagging's free. Paying's the part with money in it."];
  if (has(...BOWS) && !has(...ARROWS))
    return ["no-arrows", "smug", "A bow and no arrows. You'll be very intimidating for exactly one turn."];
  if (has(...XBOWS) && !has(...BOLTS))
    return ["no-bolts", "smug", "A crossbow and no bolts. That's a very elaborate club."];
  if (has(...GUNS) && !has(...ROUNDS))
    return ["no-shot", "frown", "A gun and nothing to put in it. Planning to throw it?"];
  if (has("hand-bombard") && !has("bombard-shells"))
    return ["no-shells", "frown", "A bombard and no shells. That's a very heavy, very expensive tube."];
  if (has(...ARROWS) && !has(...BOWS))
    return ["no-bow", "flat", "Arrows and no bow. Unless there's a bow at home, that's an expensive bundle of sticks."];
  if (has(...TWO_HANDED) && has(...SHIELDS))
    return ["hands", "laugh", "A two-handed weapon and a shield. Which hand were you planning to grow?"];
  if (has("black-powder") && !has(...GUNS, ...ROUNDS, "hand-bombard", "bombard-shells", "tinkers-tools"))
    return ["powder", "surprised", "Black powder, and nothing to fire it from or roll it into. I'm not selling you that until you tell me what it's for."];
  if (count("rations") * 2 + count("crucible-tinned-rations") * 4 >= 30)
    return ["voyage", "smile", "That's a month of food. Long sail? Take the tins. Salt air rots everything else."];
  if (has("shot-and-powder") && !has("paper-cartridges"))
    return ["damp", "flat", "Loose powder. Fine, until the first rain. Just so you've heard it from me."];
  if (market === "local") {
    const usual = (LOCAL.find(([k]) => k === local.kind) || [, , 1])[2];
    if (local.scarce) return ["scarce", "smug", "Scarce goods, local stall. Wood in Northreach, I'd wager. You'll pay through the nose and they'll call it a fair price."];
    if (local.markup < usual)
      return ["haggled", "smug", "Haggled them down, did you? Good. Just don't tell them you priced it here first."];
    return ["local:" + local.kind + local.markup, "frown", `Pricing it at ${AT_MARKET[local.kind] || "a local stall"}? Go on. Same goods, ${num(local.markup)} times my price.`];
  }
  if (coin !== "Crownsblood" && COIN_TALK[coin]) return ["coin:" + coin, "flat", COIN_TALK[coin]];
  if (t.count >= 20) return ["haul", "surprised", "Buying the whole shelf? I'll fetch a cart."];
  if (t.due >= 50) return ["rich", "surprised", "That's a serious purse. Count it out slowly; I like the sound."];
  if (t.due >= 20) return ["kit", "smile", "Now that's proper kit. You'll live longer for it."];
  if (t.due <= 1) return ["tiny", "flat", "One coin. The Guild charges at least that, whatever you buy. Even if it's string."];
  return ["fine", "smile", pick(["Sensible. I like sensible.", "Fair haul. Nothing on there I'd argue with.", "That'll do you."])];
}

/* ---------- saying it ---------- */

const keeper = $("#keeper"), bubble = $("#bubble"), sayEl = $("#bubble .say"), repliesEl = $("#bubble .replies"), srEl = $("#keeper-sr");
let talking = false, typer = null, hideTimer = null, current = [], finishTyping = null;

function lineOf(node) {
  const l = typeof node.line === "function" ? node.line() : node.line;
  return typeof l[0] === "string" ? l : pick(l);
}

function show(id, kbd) {
  asked.add(id);
  const node = TALK[id];
  const replies = typeof node.replies === "function" ? node.replies() : node.replies;
  speak(lineOf(node), replies, kbd);
  if (id === "bye") talking = false;
}

// Say one line, typed out while his mouth moves, then offer the replies. A
// line with no replies closes itself after a while.
function speak([mood, text], replies, kbd) {
  clearInterval(typer);
  clearTimeout(hideTimer);
  talking = replies.length > 0;
  current = replies;
  keeper.dataset.mood = mood;
  bubble.classList.add("show");
  bubble.setAttribute("aria-hidden", "false");
  repliesEl.innerHTML = "";
  srEl.textContent = "";
  srEl.textContent = `Talvender: ${text}`;
  const done = () => {
    clearInterval(typer);
    typer = null;
    sayEl.textContent = text;
    keeper.classList.remove("talking");
    repliesEl.innerHTML = replies.map(([label], i) => `<button type="button" data-i="${i}">${esc(label)}</button>`).join("");
    if (kbd && replies.length) repliesEl.querySelector("button").focus({ preventScroll: true });
    if (!replies.length) hideTimer = setTimeout(hide, Math.max(2800, text.length * 55));
  };
  if (!motion) return done();
  let i = 0;
  sayEl.textContent = "";
  keeper.classList.add("talking");
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
  keeper.classList.remove("talking");
  keeper.dataset.mood = "flat";
}

// He only speaks up on the floor when nothing's open over it.
const floorFree = () => !document.querySelector("dialog[open]") && !document.hidden;

// His face, small, for the slip and the tally: a copy of the big one cropped
// to the head, with the mood set on the copy.
function face(mood) {
  const svg = keeper.querySelector("svg").cloneNode(true);
  svg.setAttribute("viewBox", "38 30 84 96");
  return `<span class="kf mini" data-mood="${mood}">${svg.outerHTML}</span>`;
}
function note(mood, text) {
  return `<aside class="keeper-note">${face(mood)}<p><b class="who">Talvender</b>${esc(text)}</p></aside>`;
}

/* ---------- wiring ---------- */

keeper.addEventListener("click", ev => {
  if (talking) return hide();
  show("hello", ev.detail === 0);
});
bubble.addEventListener("click", ev => {
  const b = ev.target.closest("button[data-i]");
  if (b) {
    const next = current[Number(b.dataset.i)][1];
    return typeof next === "function" ? next() : show(next, ev.detail === 0);
  }
  if (typer) finishTyping();  // a click on the text finishes typing it
});
document.addEventListener("click", ev => {
  const inside = ev.composedPath().some(n => n === bubble || n === keeper || n === scales);
  if (bubble.classList.contains("show") && !inside) hide();
});
document.addEventListener("keydown", ev => {
  if (ev.key !== "Escape" || !bubble.classList.contains("show") || document.querySelector("dialog[open]")) return;
  const wasTalking = talking;
  hide();
  if (wasTalking) keeper.focus({ preventScroll: true });
});

// Hands off the scales.
const scales = document.querySelector(".keeper-post .scales");
scales.addEventListener("click", () => {
  scales.classList.remove("tip");
  void scales.getBoundingClientRect();
  scales.classList.add("tip");
  if (!talking) speak(pick([["frown", "Hands off the scales. Guild-calibrated, those."],
    ["smug", "They're balanced. So am I, mostly. Leave them be."]]), [], false);
});

// His eyes follow the pointer when it's near him.
const pupils = keeper.querySelector(".pupils");
addEventListener("pointermove", ev => {
  if (ev.pointerType === "touch") return;
  const r = keeper.getBoundingClientRect(), k = r.width / 160;
  const fx = r.left + 80 * k, fy = r.top + 92 * k, dx = ev.clientX - fx, dy = ev.clientY - fy, d = Math.hypot(dx, dy) || 1;
  pupils.style.transform = d < 320 * k ? `translate(${dx / d * 3.4}px, ${dy / d * 3.4}px)` : "";
}, { passive: true });

// A word on each slip, under its title.
document.addEventListener("market:slip", ({ detail: item }) => {
  const [mood, text] = ON_ITEM[item.id] || ON_KIND[item.kind] || ["flat", "Hm. Not sure about that one. Ask the DM."];
  const body = document.querySelector("#slip .slip-body");
  if (body) body.insertAdjacentHTML("afterbegin", note(mood, text));
});

// An opinion at the top of the tally, kept while its reason holds.
let lastKey = null, lastNote = "";
document.addEventListener("market:tally", () => {
  const [key, mood, text] = tallyRemark();
  if (key !== lastKey) { lastKey = key; lastNote = note(mood, text); }
  $("#tallyBody").insertAdjacentHTML("afterbegin", lastNote);
});

// Adding from the floor: now and then a word, more when the purse grows.
let lastSaid = 0, crossed = 0, firstAdd = true;
document.addEventListener("market:add", ({ detail: { item, by } }) => {
  if (by < 0 || !item || !floorFree() || talking) return;
  const due = totals().due, now = Date.now();
  let line = null;
  if (firstAdd) line = ["smile", pick(["Good. Now you're shopping.", "There we go. First thing on the tally.", "Sensible start."])];
  else if (due >= 50 && crossed < 50) line = ["surprised", "Fifty Crownsblood and climbing. Shall I fetch a chair?"];
  else if (due >= 20 && crossed < 20) line = ["smile", "Twenty CB. That's real kit now."];
  else if (now - lastSaid > 20000 && Math.random() < .3) {
    // A missing quiver or a shield with a greatsword beats a word on the item.
    const [key, mood, text] = tallyRemark();
    line = ["no-arrows", "no-bolts", "no-shot", "no-shells", "hands"].includes(key) ? [mood, text] : ON_ITEM[item.id] || null;
  }
  firstAdd = false;
  crossed = Math.max(crossed, due >= 50 ? 50 : due >= 20 ? 20 : 0);
  if (!line) return;
  lastSaid = now;
  // After this click has finished: otherwise it counts as a click away from him.
  setTimeout(() => speak(line, [], false));
});

// Left alone a while, he mutters. Now and then; not forever.
let idleTimer = null, mutters = 0;
function idleSoon() {
  clearTimeout(idleTimer);
  if (mutters >= 4) return;
  idleTimer = setTimeout(() => {
    if (floorFree() && !bubble.classList.contains("show") && scrollY < innerHeight) {
      mutters++;
      speak(IDLE(), [], false);
    }
    idleSoon();
  }, mutters ? 70000 + Math.random() * 40000 : 30000);
}
["pointerdown", "keydown"].forEach(t => addEventListener(t, idleSoon, { passive: true }));
idleSoon();
})();
