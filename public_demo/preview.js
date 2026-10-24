/* Pure read-only client visualization of an immutable synthetic JSON snapshot.
 * NO storage, auth, writes, external requests, AI model or production claims. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const make = (tag, className, label) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (label != null) node.textContent = label;
    return node;
  };
  const format = (date) => new Date(date).toLocaleString("ru-RU", {
    timeZone: "Europe/Moscow", day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit"
  }) + " MSK";
  let selected = 1;
  let stage = "corrected";
  let cases = [];
  const phases = [
    {key: "promise", title: "1 · Обещание"},
    {key: "overdue", title: "2 · Подтверждённая просрочка"},
    {key: "corrected", title: "3 · Исправлено поздно"}
  ];

  function renderList() {
    const list = $("case-list");
    list.replaceChildren();
    for (const item of cases) {
      const row = make("div", "case-row");
      const body = make("div", "case-body");
      body.append(make("strong", "", "Кейс #" + item.id + " · " + item.conversation_id));
      body.append(make("small", "", "До " + format(item.due_at) +
        " · " + item.manager + " · задержка " + item.late_minutes + " мин"));
      row.append(body);
      row.append(make("span", "chip good", "Отправлено поздно"));
      const button = make("button", "button outline", "Доказательства →");
      button.type = "button";
      button.setAttribute("aria-pressed", String(selected === item.id));
      button.addEventListener("click", () => {
        selected = item.id;
        stage = "corrected";
        render();
        $("detailPanel").scrollIntoView({behavior: "smooth", block: "start"});
      });
      row.append(button);
      list.append(row);
    }
  }

  function renderDetails() {
    const item = cases.find(x => x.id === selected);
    if (!item) return;
    $("detailTitle").textContent = "Кейс #" + item.id + " · " + item.conversation_id;
    const controls = $("case-actions");
    controls.replaceChildren();
    for (const phase of phases) {
      const btn = make("button", "button " + (stage === phase.key ? "primary" : "outline"), phase.title);
      btn.type = "button";
      btn.setAttribute("aria-pressed", String(stage === phase.key));
      btn.addEventListener("click", () => { stage = phase.key; renderDetails(); });
      controls.append(btn);
    }
    const root = $("detailContent");
    root.replaceChildren();
    const detail = make("div", "detail-grid");
    const left = make("div");
    const right = make("div");
    left.append(make("div", "eyebrow", "SOURCE EVIDENCE"));
    const maxEvents = stage === "promise" ? 2 : stage === "overdue" ? 2 : 3;
    for (const event of item.events.slice(0, maxEvents)) {
      const evidence = make("div", "evidence");
      evidence.append(make("small", "", event.kind + " · " + event.id + " · " + format(event.at)));
      evidence.append(make("p", "", event.message));
      left.append(evidence);
    }
    right.append(make("div", "eyebrow", "VERIFIED CONTEXT — STATIC SCENARIO"));
    const statusText = stage === "promise" ? "Обещание с явным сроком" :
      stage === "overdue" ? "Просрочка подтверждена человеком" :
      "CORRECTED_LATE — отправлено поздно";
    const summary = make("div", "evidence");
    summary.append(make("small", "", "STATUS"));
    summary.append(make("p", "", statusText));
    right.append(summary);
    const facts = [
      ["Ответственный", item.manager], ["Дедлайн", format(item.due_at)],
      ["Исходное сообщение", item.events[1].id],
      ["Источник", item.source_id + " · " + item.channel],
      ["Время задержки", item.late_minutes + " мин"],
      ["Финансовая потеря", "НЕИЗВЕСТНА"],
      ["Подтверждение доставки", "НЕТ"]
    ];
    if (stage !== "promise") {
      const review = make("div", "evidence");
      review.append(make("small", "", "HUMAN REVIEW"));
      review.append(make("p", "", item.review));
      right.append(review);
    }
    if (stage === "corrected") {
      const applied = make("div", "evidence");
      applied.append(make("small", "", "SOURCE-VERIFIED SEND"));
      applied.append(make("p", "", item.events[2].id + " · " + format(item.sent_at) +
        " · подтверждён факт отправки, НЕ доставки и НЕ оплаты"));
      right.append(applied);
    }
    for (const [label, value] of facts) {
      const para = make("p", "preview-fact");
      para.append(make("span", "", label + ": "), make("strong", "", value));
      right.append(para);
    }
    detail.append(left, right);
    root.append(detail);
    root.append(make("p", "preview-hint", "Это публичный снимок тестовых сценариев. Переключение этапов не запускает API, не изменяет состояние в PostgreSQL и не заменяет доказательства локального workflow."));
  }
  function render() { renderList(); renderDetails(); }
  fetch("./cases.json", {cache: "no-store"})
    .then(r => { if (!r.ok) throw new Error("Синтетический снимок недоступен"); return r.json(); })
    .then(x => {
      if (x.mode !== "SYNTHETIC_STATIC_PREVIEW" || !Array.isArray(x.cases) || x.cases.length !== 2)
        throw new Error("Некорректная версия снимка");
      cases = x.cases;
      render();
    })
    .catch(() => {
      $("case-list").textContent = "Не удалось загрузить тестовые данные";
      $("detailContent").textContent = "Проверьте состояние статического демостенда.";
    });
})();
