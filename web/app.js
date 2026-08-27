/* Articulate — local frontend. Vanilla JS, no build step. */

const $main = document.getElementById("main");
const $who = document.getElementById("who");
const $llmBadge = document.getElementById("llm-badge");

let player = localStorage.getItem("articulate_player") || "";
let levelCache = null;   // current level payload
let itemIdx = 0;
let itemResults = {};    // item_id -> true/false this session

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail || res.statusText;
    throw new Error(detail);
  }
  return res.json();
}

const post = (path, body) => api(path, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

/* ---------------------------------------------------------------- home -- */

function askName() {
  $main.replaceChildren();
  const panel = el("div", "item-panel");
  panel.append(el("div", "item-meta", "new hire paperwork"));
  panel.append(el("div", "prompt", "Welcome to Whetstone & Company. What should we call you?"));
  const input = el("input");
  input.type = "text";
  input.placeholder = "your name";
  const btn = el("button", "btn", "Start work");
  btn.style.marginTop = "12px";
  btn.onclick = () => {
    if (!input.value.trim()) return;
    player = input.value.trim();
    localStorage.setItem("articulate_player", player);
    home();
  };
  input.onkeydown = (e) => { if (e.key === "Enter") btn.click(); };
  panel.append(input, btn);
  $main.append(panel);
  input.focus();
}

async function home() {
  if (!player) return askName();
  $main.replaceChildren(el("div", "loading", "Pulling the file…"));
  let state;
  try {
    state = await api(`/api/state?player=${encodeURIComponent(player)}`);
  } catch (e) {
    $main.replaceChildren(el("div", "error", `Server error: ${e.message}`));
    return;
  }
  $who.replaceChildren(el("span", null, `analyst: ${player} · `));
  const switchLink = el("a", null, "switch");
  switchLink.onclick = () => { localStorage.removeItem("articulate_player"); player = ""; askName(); };
  $who.append(switchLink);
  $llmBadge.className = `badge ${state.llm}`;
  $llmBadge.textContent = state.llm === "live" ? "claude: live" : "llm: offline mock";

  $main.replaceChildren();
  $main.append(el("h1", null, "The Desk"));
  $main.append(el("div", "tagline", "Five weeks. Master each one to earn the next."));
  for (const lv of state.levels) {
    const card = el("button", "level-card" + (lv.unlocked ? "" : " locked"));
    const row = el("div", "row");
    row.append(el("span", "band", `WEEK ${lv.ordinal} · BAND ${lv.band}`));
    if (lv.completed) row.append(el("span", "done", "✓ mastered"));
    else if (!lv.unlocked) row.append(el("span", "locktext", "locked"));
    card.append(row);
    card.append(el("div", "title", lv.title));
    card.append(el("div", "tag", lv.tagline));
    const meter = el("div", "meter");
    const fill = el("div");
    fill.style.width = `${Math.round(lv.mastery * 100)}%`;
    meter.append(fill);
    card.append(meter);
    card.append(el("div", "meter-label",
      `mastery ${(lv.mastery * 100).toFixed(0)}% · coverage ${(lv.coverage * 100).toFixed(0)}%`));
    if (lv.unlocked) card.onclick = () => openLevel(lv.id);
    $main.append(card);
  }
  if (state.daily_items > 0) {
    const card = el("button", "level-card");
    const row = el("div", "row");
    row.append(el("span", "band", "DAILY FILING"));
    card.append(row);
    card.append(el("div", "title", "Guess the company"));
    card.append(el("div", "tag", "One anonymized real filer. Six clues. Name it."));
    card.onclick = openDaily;
    $main.append(card);
  }
}

/* --------------------------------------------------------------- level -- */

async function openLevel(levelId) {
  $main.replaceChildren(el("div", "loading", "Opening the folder…"));
  try {
    levelCache = await api(`/api/level/${levelId}?player=${encodeURIComponent(player)}`);
  } catch (e) {
    $main.replaceChildren(el("div", "error", e.message));
    return;
  }
  itemResults = {};
  // resume at first item without a correct attempt
  itemIdx = levelCache.items.findIndex(it => !levelCache.progress[it.id]);
  if (itemIdx === -1) itemIdx = 0;

  $main.replaceChildren();
  const crumb = el("div", "crumb", "← back to the desk");
  crumb.onclick = home;
  $main.append(crumb);
  $main.append(el("h1", null, levelCache.level.title));
  $main.append(el("div", "tagline", levelCache.level.tagline));
  $main.append(el("div", "narrative", levelCache.level.narrative_intro));
  const begin = el("button", "btn", "Get to work");
  begin.onclick = () => renderItem();
  $main.append(begin);
}

function dots() {
  const wrap = el("div", "progress-dots");
  levelCache.items.forEach((it, i) => {
    const d = el("div", "dot");
    const res = itemResults[it.id] !== undefined ? itemResults[it.id] : levelCache.progress[it.id];
    if (res === true) d.classList.add("hit");
    else if (res === false) d.classList.add("miss");
    if (i === itemIdx) d.classList.add("now");
    d.title = it.item_type;
    d.onclick = () => { itemIdx = i; renderItem(); };
    wrap.append(d);
  });
  return wrap;
}

function renderItem() {
  const item = levelCache.items[itemIdx];
  if (!item) return levelOutro();
  $main.replaceChildren();
  const crumb = el("div", "crumb", `← ${levelCache.level.title}`);
  crumb.onclick = () => levelCache.level.id ? openLevel(levelCache.level.id) : home();
  $main.append(crumb);
  $main.append(dots());

  const panel = el("div", "item-panel");
  panel.append(el("div", "item-meta",
    `${item.item_type.replace("_", " ")} · difficulty ${"▮".repeat(item.difficulty)}${"▯".repeat(5 - item.difficulty)} · ${itemIdx + 1}/${levelCache.items.length}`));

  let collect;   // () => submitted payload or null
  const p = item.payload;
  if (p.intro) panel.append(el("div", "prompt", p.intro));
  if (p.prompt) panel.append(el("div", "prompt", p.prompt));
  if (p.context) panel.append(el("div", "context", p.context));

  if (item.grader === "choice") collect = renderChoice(panel, item);
  else if (item.grader === "numeric") collect = renderNumeric(panel, item);
  else if (item.grader === "grid") collect = renderGrid(panel, item);
  else if (item.grader === "mapping") collect = renderMapping(panel, item);
  else collect = renderFreeText(panel, item);

  const controls = el("div", "controls");
  const submit = el("button", "btn", "Submit");
  let hintsUsed = 0;
  const hintBtn = el("button", "btn ghost small", `Hint (${item.hint_count})`);
  const hintBox = el("div", "hint-box");
  hintBtn.disabled = item.hint_count === 0;
  hintBtn.onclick = async () => {
    try {
      const h = await api(`/api/item/${item.id}/hint/${hintsUsed}`);
      hintsUsed += 1;
      hintBox.append(el("div", null, `→ ${h.text}`));
      hintBtn.textContent = `Hint (${item.hint_count - hintsUsed})`;
      if (hintsUsed >= item.hint_count) hintBtn.disabled = true;
    } catch { hintBtn.disabled = true; }
  };
  submit.onclick = async () => {
    const submitted = collect();
    if (submitted === null) return;
    submit.disabled = true;
    hintBtn.disabled = true;
    if (item.grader === "llm_rubric") submit.textContent = "Marion is reading it…";
    try {
      const out = await post("/api/attempt",
        { player, item_id: item.id, submitted, hints_used: hintsUsed });
      itemResults[item.id] = out.result.correct;
      showFeedback(panel, item, submitted, out);
      $main.replaceChildren($main.firstChild, dots(), panel); // refresh dots
    } catch (e) {
      submit.disabled = false;
      panel.append(el("div", "error", e.message));
    }
  };
  controls.append(submit, hintBtn);
  panel.append(controls, hintBox);
  if (item.item_type === "cfo_question" && p.scenario_id) {
    const callBtn = el("button", "btn ghost small", "☎ Take the live call first");
    callBtn.onclick = () => openCall(p.scenario_id, () => renderItem());
    controls.append(callBtn);
  }
  $main.append(panel);
}

/* per-grader renderers: each returns collect() */

function renderChoice(panel, item) {
  let selected = null;
  const buttons = item.payload.choices.map((choice, i) => {
    const b = el("button", "choice-btn", choice);
    b.onclick = () => {
      selected = i;
      buttons.forEach(x => x.classList.remove("selected"));
      b.classList.add("selected");
    };
    panel.append(b);
    return b;
  });
  panel._choiceButtons = buttons;
  return () => selected === null ? null : { index: selected };
}

function renderNumeric(panel, item) {
  const row = el("div", "numeric-row");
  const input = el("input");
  input.type = "text";
  input.placeholder = "your number";
  row.append(input, el("span", "unit", item.payload.unit || ""));
  panel.append(row);
  return () => {
    const v = parseFloat(input.value.replace(/,/g, ""));
    return Number.isFinite(v) ? { value: v } : null;
  };
}

function renderGrid(panel, item) {
  const inputs = {};
  for (const stmt of item.payload.statements) {
    const table = el("table", "stmt");
    const caption = el("caption", null, stmt.name);
    table.append(caption);
    for (const row of stmt.rows) {
      const tr = el("tr", row.subtotal ? "subtotal" : "");
      const label = el("td", row.indent ? `indent${Math.min(row.indent, 2)}` : "", row.label);
      const num = el("td", "num");
      if (row.blank) {
        num.classList.add("blank");
        const input = el("input");
        input.type = "text";
        input.placeholder = "?";
        num.append(input);
        inputs[row.key] = { input, cell: num };
      } else {
        num.textContent = row.value === null ? "" : fmt(row.value);
      }
      tr.append(label, num);
      table.append(tr);
    }
    panel.append(table);
  }
  if (item.payload.identities?.length) {
    panel.append(el("div", "context", "Identities in play:\n" +
      item.payload.identities.map(x => `  · ${x}`).join("\n")));
  }
  panel._gridInputs = inputs;
  return () => {
    const cells = {};
    for (const [key, { input }] of Object.entries(inputs)) {
      const v = parseFloat(input.value.replace(/,/g, ""));
      if (!Number.isFinite(v)) return null;
      cells[key] = v;
    }
    return { cells };
  };
}

function renderMapping(panel, item) {
  const selects = {};
  for (const left of item.payload.left) {
    const row = el("div", "map-row");
    const box = el("div", "map-left");
    box.append(el("div", null, left.label));
    const stats = el("div", "stats");
    for (const s of (left.stats || [])) stats.append(el("div", null, `${s.name}: ${s.value}`));
    box.append(stats);
    const sel = el("select");
    sel.append(new Option("— pick one —", ""));
    item.payload.right.forEach((r, i) => sel.append(new Option(r, String(i))));
    selects[left.key] = sel;
    row.append(box, sel);
    panel.append(row);
  }
  return () => {
    const map = {};
    for (const [key, sel] of Object.entries(selects)) {
      if (sel.value === "") return null;
      map[key] = parseInt(sel.value, 10);
    }
    return { map };
  };
}

function renderFreeText(panel, item) {
  const ta = el("textarea");
  ta.placeholder = item.payload.response_guidance || "your answer";
  panel.append(ta);
  return () => ta.value.trim() ? { text: ta.value.trim() } : null;
}

/* feedback */

function fmt(n) {
  return Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function showFeedback(panel, item, submitted, out) {
  const r = out.result;
  const fb = el("div", `feedback ${r.correct ? "good" : "bad"}`);
  fb.append(el("div", "verdict", r.correct ? "TIES OUT" : "DOESN'T TIE"));
  const f = r.feedback;

  if (item.grader === "choice" && panel._choiceButtons) {
    panel._choiceButtons.forEach((b, i) => {
      b.disabled = true;
      if (i === f.correct_index) b.classList.add("right");
      else if (submitted.index === i) b.classList.add("wrong");
    });
    if (f.why_wrong) fb.append(el("div", "explanation", f.why_wrong));
  }
  if (item.grader === "numeric" && !r.correct) {
    fb.append(el("div", "explanation", `The number: ${fmt(f.value)}`));
  }
  if (item.grader === "grid" && panel._gridInputs) {
    for (const [key, verdict] of Object.entries(f.cells)) {
      const slot = panel._gridInputs[key];
      if (!slot) continue;
      slot.input.disabled = true;
      slot.cell.classList.add(verdict.correct ? "right" : "wrong");
      if (!verdict.correct) slot.input.value = `${slot.input.value} → ${fmt(verdict.expected)}`;
    }
    fb.append(el("div", "explanation", `${fmt(r.score)} of ${fmt(r.max_score)} cells tie.`));
  }
  if (item.grader === "mapping") {
    for (const [key, verdict] of Object.entries(f.assignments)) {
      const line = el("div", "explanation",
        `${key}: ${verdict.correct ? "✓" : "✗"} ${verdict.expected}` +
        (verdict.tell ? ` — ${verdict.tell}` : ""));
      fb.append(line);
    }
  }
  if (item.grader === "llm_rubric") {
    const list = el("ul", "rubric-list");
    for (const c of f.rubric) {
      const li = el("li", c.hit ? "hit" : "", `${c.description} (${c.points} pt)`);
      list.append(li);
    }
    fb.append(list);
    if (f.judge_feedback) fb.append(el("div", "explanation", f.judge_feedback));
    const ma = el("div", "model-answer");
    ma.append(el("strong", null, "Marion's answer: "));
    ma.append(document.createTextNode(f.model_answer));
    fb.append(ma);
  }
  if (out.explanation) fb.append(el("div", "explanation", out.explanation));

  const controls = el("div", "controls");
  const next = el("button", "btn", itemIdx + 1 < levelCache.items.length ? "Next" : "Finish the week");
  next.onclick = () => { itemIdx += 1; itemIdx < levelCache.items.length ? renderItem() : levelOutro(); };
  if (!r.correct) {
    const retry = el("button", "btn ghost", "Try again");
    retry.onclick = () => renderItem();
    controls.append(retry);
  }
  controls.append(next);
  const lv = out.levels.find(x => x.id === levelCache.level.id);
  if (lv) controls.append(el("span", "mastery-flash", `mastery ${(lv.mastery * 100).toFixed(0)}%`));
  fb.append(controls);
  panel.append(fb);
  fb.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function levelOutro() {
  if (!levelCache.level.id) return home();
  const state = await api(`/api/state?player=${encodeURIComponent(player)}`);
  const mine = state.levels.find(x => x.id === levelCache.level.id);
  $main.replaceChildren();
  $main.append(el("h1", null, levelCache.level.title));
  $main.append(el("div", "narrative", levelCache.level.narrative_outro ||
    "That's the week."));
  const stats = el("div", "context",
    `mastery ${(mine.mastery * 100).toFixed(0)}% · coverage ${(mine.coverage * 100).toFixed(0)}%\n` +
    (mine.completed ? "Week mastered. The next folder is on your desk."
      : "Not mastered yet — Marion suggests another pass at the ones that didn't tie."));
  $main.append(stats);
  const back = el("button", "btn", "Back to the desk");
  back.onclick = home;
  $main.append(back);
}

/* --------------------------------------------------------- earnings call -- */

async function openCall(scenarioId, onDone) {
  $main.replaceChildren();
  const crumb = el("div", "crumb", "← hang up");
  crumb.onclick = onDone;
  $main.append(crumb);
  $main.append(el("h1", null, "Earnings call"));
  $main.append(el("div", "tagline", "Truthful but evasive. Press where the numbers point."));
  const chat = el("div", "chat");
  const askRow = el("div", "ask-row");
  const input = el("input");
  input.type = "text";
  input.placeholder = "your question for the CFO";
  const btn = el("button", "btn", "Ask");
  const remain = el("div", "meter-label");
  askRow.append(input, btn);
  $main.append(chat, askRow, remain);

  const addMsg = (role, name, text) => {
    const m = el("div", `msg ${role}`);
    m.append(el("div", "speaker", name));
    m.append(el("div", "bubble", text));
    chat.append(m);
    chat.scrollTop = chat.scrollHeight;
  };

  btn.onclick = async () => {
    const q = input.value.trim();
    if (!q) return;
    input.value = "";
    addMsg("analyst", player.toUpperCase() + " (you)", q);
    btn.disabled = true;
    try {
      const out = await post(`/api/call/${scenarioId}/ask`, { player, question: q });
      addMsg("cfo", out.cfo_name.toUpperCase() + " (CFO)", out.reply);
      remain.textContent = `${out.questions_remaining} question${out.questions_remaining === 1 ? "" : "s"} left`;
      if (out.questions_remaining === 0) {
        const d = await api(`/api/call/${scenarioId}/debrief?player=${encodeURIComponent(player)}`);
        const wrap = el("div");
        wrap.append(el("h2", null, `Debrief — coverage ${(d.coverage * 100).toFixed(0)}%`));
        for (const issue of d.issues) {
          wrap.append(el("div", `debrief-issue ${issue.uncovered ? "uncovered" : "missed"}`,
            `${issue.uncovered ? "✓ surfaced" : "✗ missed"} — ${issue.summary}`));
        }
        $main.append(wrap);
        askRow.remove();
      } else {
        btn.disabled = false;
      }
    } catch (e) {
      addMsg("cfo", "OPERATOR", e.message);
      btn.disabled = false;
    }
    input.focus();
  };
  input.onkeydown = (e) => { if (e.key === "Enter") btn.click(); };
  input.focus();
}

/* --------------------------------------------------------------- daily -- */

async function openDaily() {
  const data = await api(`/api/daily?player=${encodeURIComponent(player)}`);
  levelCache = {
    level: { id: null, title: "Daily Filing", tagline: "Name the company from its numbers.",
             narrative_intro: "", narrative_outro: "Same time tomorrow." },
    items: data.items,
    progress: {},
  };
  itemResults = {};
  itemIdx = 0;
  renderItem();
}

home();
