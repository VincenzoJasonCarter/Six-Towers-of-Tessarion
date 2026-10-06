/**
 * The table tool's screen (DESIGN.md 7): a setup form, then the fight. One
 * tap per hero turn, undo always, a DM view with the brain's reasons and a
 * proclaim view with only what the players may hear. The fight lives in its
 * event log, kept in the browser and exportable as a file.
 */
import { ACTIONS, type Action } from "../engine/actions.ts";
import { STEPS } from "../engine/decision/temperament.ts";
import { SUBCLASSES, type SubclassId } from "../engine/subclasses.ts";
import { RECHARGE_5_6 } from "../modules/placeholder.ts";
import { append, DEFAULT_SETUP, newFight, parseLog, replay, undo, type FightLog, type RoundRecord, type TableSetup, type TableState } from "./session.ts";

const LOG_KEY = "boss-brain-table:log";
const SETUP_KEY = "boss-brain-table:setup";

const STEP_BLURBS: Record<string, string> = {
  curious: "still learning: probes, hedges, shows its hand",
  hunting: "has a read, still testing it",
  ruthless: "cold and focused: the peak, keeps its reads to itself",
  wrathful: "losing its cool: jumps to conclusions, counter-punches",
  bloodlusted: "enraged: fixes on one hero, roars, only hits",
};

let log: FightLog | null = load<FightLog>(LOG_KEY);
let draft: TableSetup = load<TableSetup>(SETUP_KEY) ?? {
  ...DEFAULT_SETUP,
  heroes: [
    { name: "", subclass: "gunman" },
    { name: "", subclass: "verdant" },
  ],
};
let showWhy = false;
let proclaim = false;
let error = "";

function load<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function save(): void {
  try {
    if (log) localStorage.setItem(LOG_KEY, JSON.stringify(log));
    else localStorage.removeItem(LOG_KEY);
    localStorage.setItem(SETUP_KEY, JSON.stringify(draft));
  } catch {
    // Storage can be off (a private window); the fight still runs, it just won't survive a reload.
  }
}

type Child = Node | string | null | undefined | false;

function h<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Record<string, unknown> = {}, ...children: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v as EventListener);
    else if (k === "class") el.className = String(v);
    else if (k === "value") (el as HTMLInputElement).value = String(v);
    else if (k === "checked") (el as HTMLInputElement).checked = Boolean(v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of children) if (c !== null && c !== undefined && c !== false) el.append(c);
  return el;
}

function act(change: () => void): void {
  try {
    change();
    error = "";
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }
  save();
  render();
}

// --- setup ---

function setupScreen(): HTMLElement {
  const subclassOptions = (selected: SubclassId) =>
    (Object.keys(SUBCLASSES) as SubclassId[]).map((id) => h("option", { value: id, selected: id === selected }, SUBCLASSES[id].name));
  const sig = draft.fitting.signature ?? { uses: 3 };
  const recharge = "recharge" in sig;

  return h(
    "main",
    { class: "setup" },
    h("h1", {}, "Boss Brain"),
    h("p", { class: "lede" }, "The Placeholder Boss, draped over your monster. Record each hero's main action; the brain plans the boss's move each round."),
    h(
      "section",
      {},
      h("h2", {}, "Party, in initiative order"),
      ...draft.heroes.map((hero, i) =>
        h(
          "div",
          { class: "row" },
          h("input", {
            placeholder: `Hero ${i + 1}`,
            value: hero.name,
            oninput: (e: Event) => {
              draft = { ...draft, heroes: draft.heroes.map((x, j) => (j === i ? { ...x, name: (e.target as HTMLInputElement).value } : x)) };
              save();
            },
          }),
          h(
            "select",
            {
              onchange: (e: Event) =>
                act(() => {
                  draft = { ...draft, heroes: draft.heroes.map((x, j) => (j === i ? { ...x, subclass: (e.target as HTMLSelectElement).value as SubclassId } : x)) };
                }),
            },
            ...subclassOptions(hero.subclass),
          ),
          h("button", { class: "quiet", title: "Remove", onclick: () => act(() => (draft = { ...draft, heroes: draft.heroes.filter((_, j) => j !== i) })) }, "✕"),
        ),
      ),
      h("button", { onclick: () => act(() => (draft = { ...draft, heroes: [...draft.heroes, { name: "", subclass: "unknown" }] })) }, "+ Add hero"),
    ),
    h(
      "section",
      {},
      h("h2", {}, "The monster"),
      h(
        "label",
        { class: "row" },
        "Strike is worth",
        h("select", { onchange: (e: Event) => act(() => (draft = { ...draft, fitting: { ...draft.fitting, strike: Number((e.target as HTMLSelectElement).value) } })) },
          h("option", { value: 1, selected: (draft.fitting.strike ?? 1) === 1 }, "1 (one attack)"),
          h("option", { value: 2, selected: draft.fitting.strike === 2 }, "2 (Multiattack, two attacks)"),
        ),
      ),
      h(
        "label",
        { class: "row" },
        h("input", { type: "checkbox", checked: draft.fitting.interrupt !== false, onchange: (e: Event) => act(() => (draft = { ...draft, fitting: { ...draft.fitting, interrupt: (e.target as HTMLInputElement).checked } })) }),
        "It has a reaction to ready (Interrupt)",
      ),
      h(
        "label",
        { class: "row" },
        "Its limited ability (Signature):",
        h("select", {
          onchange: (e: Event) =>
            act(() => {
              const v = (e.target as HTMLSelectElement).value;
              draft = { ...draft, fitting: { ...draft.fitting, signature: v === "recharge" ? { recharge: RECHARGE_5_6 } : { uses: 3 } } };
            }),
        },
          h("option", { value: "uses", selected: !recharge }, "a number of uses"),
          h("option", { value: "recharge", selected: recharge }, "Recharge 5–6"),
        ),
        !recharge &&
          h("input", {
            type: "number",
            min: 0,
            max: 9,
            value: "uses" in sig ? sig.uses : 3,
            class: "short",
            onchange: (e: Event) => act(() => (draft = { ...draft, fitting: { ...draft.fitting, signature: { uses: Number((e.target as HTMLInputElement).value) } } })),
          }),
      ),
    ),
    h(
      "section",
      {},
      h("h2", {}, "Temperament"),
      ...STEPS.map((s) =>
        h(
          "label",
          { class: "row step-choice" },
          h("input", { type: "radio", name: "start", checked: draft.start === s.id, onchange: () => act(() => (draft = { ...draft, start: s.id })) }),
          h("strong", {}, s.name),
          h("span", { class: "muted" }, STEP_BLURBS[s.id] ?? ""),
        ),
      ),
      h(
        "label",
        { class: "row" },
        h("input", { type: "checkbox", checked: draft.enrage, onchange: (e: Event) => act(() => (draft = { ...draft, enrage: (e.target as HTMLInputElement).checked })) }),
        "Enrage: Wrathful below half HP, Bloodlusted below a quarter. Max HP",
        h("input", {
          type: "number",
          min: 1,
          class: "short",
          value: draft.maxHp ?? "",
          placeholder: "HP",
          onchange: (e: Event) => act(() => {
            const v = (e.target as HTMLInputElement).value;
            draft = { ...draft, maxHp: v ? Number(v) : null };
          }),
        }),
      ),
      h(
        "label",
        { class: "row" },
        h("input", { type: "checkbox", checked: draft.insult, onchange: (e: Event) => act(() => (draft = { ...draft, insult: (e.target as HTMLInputElement).checked })) }),
        "Insult: foiled three times running, one step hotter",
      ),
    ),
    error && h("p", { class: "error" }, error),
    h(
      "div",
      { class: "row actions" },
      h("button", {
        class: "primary",
        onclick: () =>
          act(() => {
            const heroes = draft.heroes.map((x, i) => ({ ...x, name: x.name.trim() || `Hero ${i + 1}` }));
            if (draft.enrage && !draft.maxHp) throw new Error("Enrage needs the boss's max HP");
            log = newFight({ ...draft, heroes, seed: Math.floor(Math.random() * 2 ** 31) });
          }),
      }, "Start the fight"),
      importButton(),
    ),
  );
}

function importButton(): HTMLElement {
  const input = h("input", {
    type: "file",
    accept: "application/json,.json",
    class: "hidden",
    onchange: async (e: Event) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const text = await file.text();
      act(() => (log = parseLog(text)));
    },
  });
  return h("label", { class: "button" }, "Import a fight log", input);
}

// --- fight ---

const pctText = (p: number) => `${Math.round(p * 100)}%`;
const stepName = (id: string) => STEPS.find((s) => s.id === id)?.name ?? id;

function outcome(r: RoundRecord): string {
  if (!r.resolution) return "the boss did nothing";
  const lethal = r.resolution.utility.lethal ?? 0;
  const bet = r.resolution.bets[0];
  const verdict = bet ? (bet.fulfilled ? "read right" : "read wrong") : lethal > 0 ? "landed" : "guarded";
  return `${r.described}: ${verdict}${lethal > 0 ? `, ${lethal.toFixed(2).replace(/\.?0+$/, "")} lethal` : ""}`;
}

function fightScreen(s: TableState): HTMLElement {
  const current = s.turn < s.heroes.length ? s.turn : -1;
  const lastShift = s.shifts.at(-1);
  return h(
    "main",
    { class: "fight" },
    h(
      "header",
      {},
      h("div", { class: "round" }, `Round ${s.round}`),
      h("div", { class: `badge step-${s.step}` }, stepName(s.step), lastShift && lastShift.round === s.round && h("span", { class: "why" }, ` (${lastShift.reason})`)),
      s.setup.maxHp !== null && hpControl(s),
      h("div", { class: "spacer" }),
      h("button", { onclick: () => act(() => (proclaim = true)), title: "P" }, "Proclaim"),
      h("button", { disabled: !log || log.events.length === 0, onclick: () => act(() => (log = undo(log!))), title: "U" }, "Undo"),
      h("button", { onclick: exportLog }, "Export"),
      h("button", { class: "quiet", onclick: () => act(() => { if (confirm("End this fight? Export it first if you want to keep it.")) log = null; }) }, "End fight"),
    ),
    error && h("p", { class: "error" }, error),
    planCard(s),
    h("section", { class: "heroes" }, ...s.heroes.map((hv, i) => heroRow(hv, i, current))),
    historyList(s),
  );
}

function hpControl(s: TableState): HTMLElement {
  const input = h("input", { type: "number", class: "short", value: s.hp ?? "", min: 0 });
  return h(
    "form",
    {
      class: "hp",
      onsubmit: (e: Event) => {
        e.preventDefault();
        const hp = Number(input.value);
        if (!Number.isFinite(hp)) return;
        act(() => (log = append(log!, { type: "hp", hp }).log));
      },
    },
    "HP ",
    input,
    ` / ${s.setup.maxHp} `,
    h("button", { type: "submit" }, "Record"),
  );
}

function planCard(s: TableState): HTMLElement {
  if (!s.plan) return h("section", { class: "plan" }, h("p", {}, "The boss has no move this round."));
  const p = s.plan;
  const canOverrule = s.turn === 0;
  return h(
    "section",
    { class: "plan" },
    h("div", { class: "label" }, p.overruled ? "This round (overruled by the DM)" : "This round the boss will"),
    h("div", { class: "move" }, p.described),
    h("div", { class: "label" }, "Tell the table"),
    h("div", { class: "say" }, p.announcement.text || "Nothing. Keep it to yourself."),
    h("button", { class: "quiet", onclick: () => act(() => (showWhy = !showWhy)) }, showWhy ? "Hide why" : "Why?"),
    showWhy &&
      h(
        "ol",
        { class: "ranked" },
        ...p.ranked.slice(0, 10).map((r, i) =>
          h(
            "li",
            { class: r.chosen ? "chosen" : "" },
            h("span", { class: "eu" }, r.eu.toFixed(2)),
            " ",
            r.described,
            canOverrule && !r.chosen && h("button", { class: "quiet small", onclick: () => act(() => (log = append(log!, { type: "overrule", option: i }).log)) }, "use this"),
          ),
        ),
      ),
  );
}

function heroRow(hv: TableState["heroes"][number], index: number, current: number): HTMLElement {
  const isCurrent = index === current;
  return h(
    "div",
    { class: `hero ${isCurrent ? "current" : ""} ${hv.acted !== null ? "done" : ""}` },
    h(
      "div",
      { class: "who" },
      h("strong", {}, hv.hero.name),
      h("span", { class: "muted" }, ` ${SUBCLASSES[hv.hero.subclass].name}`),
      hv.named && h("span", { class: "tag" }, "named"),
      hv.warned && h("span", { class: "tag warn" }, "warned"),
    ),
    h(
      "div",
      { class: "forecast" },
      ...ACTIONS.map((a, i) => h("div", { class: "bar", title: `${a.label} ${pctText(hv.forecast[i]!)}` }, h("div", { class: "fill", style: `height:${Math.round(hv.forecast[i]! * 100)}%` }), h("span", {}, `${a.label.slice(0, 2)} ${pctText(hv.forecast[i]!)}`))),
    ),
    h("div", { class: "explain muted" }, hv.explanation),
    h(
      "div",
      { class: "taps" },
      ...ACTIONS.map((a, i) =>
        h(
          "button",
          {
            class: `tap ${hv.acted === i ? "picked" : ""}`,
            disabled: !isCurrent,
            title: isCurrent ? `${i + 1}` : "",
            onclick: () => act(() => (log = append(log!, { type: "action", action: i as Action }).log)),
          },
          a.label,
        ),
      ),
    ),
  );
}

function historyList(s: TableState): HTMLElement {
  const items: HTMLElement[] = [];
  for (const r of [...s.history].reverse()) {
    for (const sh of s.shifts.filter((x) => x.round === r.round + 1)) items.push(h("li", { class: "shift" }, `Round ${sh.round}: now ${stepName(sh.to)} (${sh.reason})`));
    items.push(
      h(
        "li",
        {},
        h("span", { class: "muted" }, `R${r.round} · ${stepName(r.step)}${r.overruled ? " · overruled" : ""} · `),
        outcome(r),
        ...r.reactions.map((x) => h("div", { class: "muted" }, `after ${x.hero}: ${x.described}`)),
      ),
    );
  }
  return h("section", { class: "history" }, h("h2", {}, "So far"), items.length ? h("ul", {}, ...items) : h("p", { class: "muted" }, "Nothing yet."));
}

function proclaimView(s: TableState): HTMLElement {
  const text = s.plan?.announcement.text || "The boss says nothing.";
  return h("div", { class: "proclaim", onclick: () => act(() => (proclaim = false)) }, h("div", {}, text), h("p", { class: "hint" }, "Click or press Esc to return"));
}

function exportLog(): void {
  if (!log) return;
  const blob = new Blob([JSON.stringify(log, null, 2)], { type: "application/json" });
  const a = h("a", { href: URL.createObjectURL(blob), download: `boss-fight-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-")}.json` });
  a.click();
  URL.revokeObjectURL(a.href);
}

// --- wiring ---

function render(): void {
  const root = document.getElementById("app")!;
  let state: TableState | null = null;
  if (log) {
    try {
      state = replay(log);
    } catch (e) {
      error = `The saved fight couldn't be replayed (${e instanceof Error ? e.message : e}); it was set aside.`;
      log = null;
      save();
    }
  }
  root.replaceChildren(state ? (proclaim ? proclaimView(state) : fightScreen(state)) : setupScreen());
}

document.addEventListener("keydown", (e) => {
  if (!log || e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
  if (e.key === "Escape" && proclaim) act(() => (proclaim = false));
  else if (e.key.toLowerCase() === "p") act(() => (proclaim = !proclaim));
  else if (e.key.toLowerCase() === "u" && log.events.length > 0) act(() => (log = undo(log!)));
  else if (/^[1-5]$/.test(e.key) && !proclaim) act(() => (log = append(log!, { type: "action", action: (Number(e.key) - 1) as Action }).log));
});

render();
