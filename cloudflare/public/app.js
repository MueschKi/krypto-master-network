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
    const [s, m, accounts, runs, history, gaps] = await Promise.all(
      ["status", "markets", "accounts", "runs", "history", "gaps"].map(get),
    );
    const mtfReady =
      !s.stale &&
      m.assets.length === 4 &&
      m.assets.every(
        (a) =>
          a.classification !== "BLOCKIERT" &&
          Object.values(a.timeframes).length === 4 &&
          Object.values(a.timeframes).every(
            (f) => !f.stale && f.quality.status === "OK",
          ),
      );
    $("connection").textContent =
      (mtfReady ? "MTF aktuell" : "MTF BLOCKIERT / UNVOLLSTÄNDIG") +
      " · " +
      m.snapshot_utc;
    $("connection").className = mtfReady ? "ok" : "blocked";
    $("status").replaceChildren(
      card(
        "TAKTSTATUS",
        s.stale ? "Heartbeat veraltet" : "Heartbeat aktuell",
        "Letzter Takt: " +
          (s.heartbeat?.status ?? "Kein Lauf") +
          " · keine vollständige MTF-Freigabe",
      ),
      card(
        "MTF-DATENFREIGABE",
        mtfReady ? "Aktuell" : "BLOCKIERT / UNVOLLSTÄNDIG",
        "Alle 16 Fenster müssen gültig, aktuell und ohne Veto sein.",
      ),
      card(
        "LETZTER EINZELJOB",
        time(s.last_success?.finished),
        "Erfolgreiche Arbeitseinheit; kein Gesamterfolg.",
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
          s.accounts_access === "DISABLED_PENDING_AUTH_HARDENING"
            ? "Öffentliche Kontolesestände gesperrt; Authentifizierung und PWA-Abnahme offen."
            : "Privaten Lese-Snapshot lokal nach Anleitung importieren.",
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
    for (const g of gaps) {
      const tr = el("tr");
      [
        time(g.observed),
        "MISSED",
        g.symbol + " " + g.timeframe,
        g.missing_count +
          " fehlende Abschlüsse im Bereich " +
          time(g.first_close) +
          " bis " +
          time(g.last_close),
      ].forEach((x) => tr.append(el("td", x)));
      table.append(tr);
    }
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
