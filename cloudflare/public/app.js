const $ = (id) => document.getElementById(id);
const el = (tag, text, cls) => {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
};
const time = (n) =>
  n
    ? new Date(n).toISOString().replace("T", " ").replace(".000Z", " UTC")
    : "Noch nicht vorhanden";
const card = (title, value, detail) => {
  const n = el("article", undefined, "card");
  n.append(
    el("small", title),
    el("div", value, "value"),
    el("p", detail, "muted"),
  );
  return n;
};
async function get(path) {
  const r = await fetch("/api/" + path, { cache: "no-store" });
  if (!r.ok) throw Error("HTTP " + r.status);
  return r.json();
}
function details(title, data) {
  const d = el("details");
  d.append(el("summary", title), el("pre", JSON.stringify(data, null, 2)));
  return d;
}
async function refresh() {
  try {
    const [s, m, accounts, runs, history] = await Promise.all(
      ["status", "markets", "accounts", "runs", "history"].map(get),
    );
    $("connection").textContent = s.stale
      ? "BLOCKIERT · Heartbeat fehlt oder veraltet"
      : "Verbunden · " + m.snapshot_utc;
    $("connection").className = s.stale ? "blocked" : "ok";
    $("status").replaceChildren(
      card(
        "BOT-STATUS",
        s.stale ? "BLOCKIERT" : "Heartbeat aktuell",
        "Reine Beobachtung",
      ),
      card(
        "LETZTER ERFOLG",
        time(s.last_success?.finished),
        "Erfolgreiche Arbeitseinheit",
      ),
      card(
        "LETZTER TAKT",
        time(s.heartbeat?.scheduled),
        "Jede Minute geplant; keine Garantie",
      ),
    );
    $("markets").replaceChildren();
    $("analysis").replaceChildren();
    for (const a of m.assets) {
      $("markets").append(
        card(a.symbol, a.classification, "15m / 1h / 4h / 1d"),
      );
      const box = el("article", undefined, "card"),
        frames = el("div", undefined, "frames");
      box.append(el("h3", a.symbol));
      for (const [tf, f] of Object.entries(a.timeframes)) {
        const n = el("div", undefined, "frame");
        n.append(
          el("small", tf),
          el(
            "h3",
            f.classification,
            f.classification === "BLOCKIERT" ? "blocked" : "ok",
          ),
          el("p", "Kerzenschluss: " + time(f.candle_close)),
          el("p", "Berechnet: " + time(f.calculated)),
          el("p", f.stale ? "BLOCKIERT · veraltet / fehlt" : f.quality.reason),
        );
        for (const [name, agent] of Object.entries(f.agents)) {
          n.append(
            el("p", name + ": " + agent.signal + " · " + agent.reason),
            details("Indikatorwerte", agent.indicators),
          );
        }
        frames.append(n);
      }
      box.append(frames);
      $("analysis").append(box);
    }
    $("accounts").replaceChildren();
    if (!accounts.length)
      $("accounts").append(
        card(
          "KEIN IMPORT",
          "Nicht eingerichtet",
          "Privaten Lese-Snapshot nach Anleitung importieren.",
        ),
      );
    for (const a of accounts) {
      const p = JSON.parse(a.payload),
        n = card(
          a.account === "master7" ? "Master · 7-%-Stopp" : "Master · ATR 2,5×",
          p.last_equity_eur + " EUR",
          "Stand: " + p.last_processed_day + " · Import: " + a.imported_utc,
        );
      n.append(
        el("p", "Cash: " + p.cash_eur + " EUR"),
        el("small", "SHA-256: " + a.source_sha256),
        details("Positionen", p.positions),
        details("Simulierte Trades", p.trades),
        details("Entwicklung", p.equity_history),
      );
      $("accounts").append(n);
    }
    const table = el("table"),
      head = el("tr");
    ["Geplant / UTC", "Status", "Markt / Fenster", "Diagnose"].forEach((x) =>
      head.append(el("th", x)),
    );
    table.append(head);
    runs.forEach((r, i) => {
      const tr = el("tr");
      [
        time(r.scheduled),
        r.status,
        (r.symbol ?? "—") + " " + (r.timeframe ?? ""),
        r.error ?? "—",
      ].forEach((x) => tr.append(el("td", String(x))));
      table.append(tr);
      if (runs[i + 1] && r.scheduled - runs[i + 1].scheduled > 90000) {
        const gap = el("tr");
        gap.append(
          el(
            "td",
            "AUSGEFALLENE TAKTE: " +
              Math.max(
                1,
                Math.round((r.scheduled - runs[i + 1].scheduled) / 60000) - 1,
              ),
          ),
        );
        table.append(gap);
      }
    });
    $("runs").replaceChildren(table);
    $("history").replaceChildren(
      ...history.map((h) =>
        details(
          h.symbol + " " + h.timeframe + " · " + time(h.calculated),
          JSON.parse(h.payload),
        ),
      ),
    );
    $("system-data").replaceChildren(
      el("p", "Version: " + s.version),
      el("p", "Verbindung: D1 erreichbar"),
      el(
        "p",
        "Cloudflare-Free CPU-Nachweis: OFFEN · keine echte Runtime-Messung",
      ),
      el("p", "Letztes Ergebnis: " + (s.heartbeat?.status ?? "Kein Lauf")),
      el("p", "Fehler: " + (s.heartbeat?.error ?? "Keine gemeldet")),
    );
  } catch (e) {
    $("connection").textContent =
      "BLOCKIERT · Verbindung unterbrochen / Anmeldung erforderlich · " +
      String(e);
    $("connection").className = "blocked";
    [
      "status",
      "markets",
      "analysis",
      "accounts",
      "runs",
      "history",
      "system-data",
    ].forEach((id) =>
      $(id).replaceChildren(
        el("p", "Anzeige gesperrt: keine aktuellen bestätigten Daten."),
      ),
    );
  }
}
refresh();
setInterval(refresh, 60000);
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js");
