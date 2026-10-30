# Cloudflare-Free-Speicherbudget (Phase A) – vor Langzeitbetrieb verpflichtend

**Status:** Speichergrenzen und ursprünglicher Messplan. Issue #14 ergänzt lokalen Code für Normalisierung und Warn-/Stop-Gates; Details, Belege und getrennte Freigaben stehen in [CLOUDFLARE_FREE_OPERATIONS.md](CLOUDFLARE_FREE_OPERATIONS.md). **Kein Remote-Lösch- oder Migrationsauftrag**. Von dieser Datei werden keine D1-Daten verändert. Für Testbetrieb zunächst nur nichtprivate öffentliche Kraken-OHLC/MTF, keine Kontoimporte.

## Harte Cloudflare-Limits (Stand 30.10.2026)

Offizielle Referenzen:
- https://developers.cloudflare.com/d1/platform/limits/ – **500 MB maximal pro D1-Datenbank im Workers-Free-Tarif**, 5 GB Speicher gesamt pro Account. **5 GB ist keine einzelne DB!** Ferner 50 D1-Subrequests je Free-Worker-Aufruf, 2 MB pro Datenbankzeile.
- https://developers.cloudflare.com/d1/platform/pricing/ – zusätzlich tägliche D1-Lese-/Schreibquoten prüfen.
- https://developers.cloudflare.com/workers/platform/limits/ – 10 ms CPU je Cron- und HTTP-Aufruf, 100.000 Worker-Requests pro Tag.

Phase A schreibt je erfolgreichem Fensterabschluss einen JSON-Rohkerzen-Batch in **`candle_batches`** und eine historische MTF-Analyse in **`analyses`**. Solche Batches sind *volle rollierende 720-Bar-Ausschnitte*, nicht nur die neuen Kerzen. Ohne Aufbewahrungsplan wächst D1 fortlaufend.

| Zeitfenster | Abschlüsse/Tag | Vier Coins |
|---|---:|---:|
| 15m | 96 | 384 |
| 1h | 24 | 96 |
| 4h | 6 | 24 |
| 1d | 1 | 4 |
| **Gesamt** | | **508 Rohkerzen-Batches/Tag** |

**Grobe Größenordnung, keine gemessene Cloudflare-Quote:** Bei etwa 40–100 kB JSON je Roh-Batch entstehen ca. **20–50 MB reine Nutzdaten pro Tag**, zzgl. D1-Indizes, SQLite-Overhead, Laufjournal, Analysen und fehlgeschlagener Retries. Ein 500-MB-Free-Limit kann dadurch in **ein bis wenigen Wochen** erreicht sein. Exakte Größen und die reale CPU-Zeit müssen auf Cloudflare Free gemessen werden. Die weiter oben genannten 5 GB *Account-Speicher* ändern diesen Engpass nicht.

## Sofortiger Betriebsmodus vor der Freigabe einer Bereinigungsstrategie

1. **Zunächst zeitlich begrenzter Beobachtungs-/Benchmark-Test**. Keine Garantie für langfristigen kostenlosen Betrieb und keinen dauerhaften Echtgeldbetrieb versprechen.
2. Bei echtem Test mindestens **täglich** Cloudflare-D1-Metriken und die Datenbankgröße prüfen:
   - Cloudflare Dashboard → D1 SQL database → `kmn` → Metrics.
   - Oder bewusst nur lesend: `npx wrangler d1 info kmn --json`.
   - Protokolliere Größe und Wachstum pro Tag, Anzahl Transaktionen, DB-Fehler und CPU-Ausreißer.
3. **Warnwert 250 MB (50 %)**, **Stop/Neuentwurf spätestens 350 MB (70 %)**. Im neuen Code wird ab 250 MB gewarnt; ab 348 MB (2 MB Reserve vor 350 MB) oder unbekannter Größe stoppen neue Rohdaten-/Signalschreibvorgänge. Die noch unveröffentlichte Umsetzung ist im Betriebsleitfaden beschrieben. Ist der Worker bereits aktiv, muss der Betreiber Cron/Worker bewusst pausieren bzw. den Betrieb beenden. **Keine automatische Tarifumstellung**.
4. Kein Deployment als dauerhafte Anwendung freigeben, bis eine separate Aufbewahrungsstrategie, sichere Export-/Recovery-Möglichkeit und D1-Größenüberwachung implementiert und getestet sind.

## Vorschlag für eine später **separat freizugebende** Aufbewahrungsstrategie

- Rohkerzenbatches (`candle_batches`): z. B. **48–72 Stunden** abrufbar; danach archiviert oder nach ausdrücklicher Freigabe gelöscht. Es sind redundante, rollierende Kraken-Zeitfenster. Vor Löschung Export, Stichproben, nachvollziehbare Referenz zu Zeit und Signal.
- Analysen (`analyses`), MISSED-Signale (`coverage_gaps`), Paper- oder Echtgeld-Ledger: **nicht** zusammen mit Rohkerzen löschen. Retention für Analysen und Audit getrennt festlegen; Paper-/Live-Ledger später grundsätzlich gesondert und dauerhaft revisionsfähig sichern.
- Jobs (`jobs`) und Laufjournal (`runs`): definierte Recovery-/Nachverfolgbarkeitsfristen, z. B. 30 Tage, nach separatem Review. Cursor (`scheduler_state`) darf nie willkürlich zurückgesetzt werden.
- Vor jeder Datenbereinigung wiederherstellbares **Backup/Export**, nachvollziehbare Signatur/Hash und eine Lösch-/Retention-Testmatrix. Bei Quota-Unsicherheit **fail-closed**, nicht auf Paid upgraden oder ohne Protokoll Daten entfernen.
- Langfristig effizienter: eine nur einmal pro abgeschlossenem Zeitfenster gespeicherte Kerze statt ständig neuer 720-Bar-Kopien; D1-Schema und Python-Parität separat prüfen. Größere Änderungen **nicht** in den sicheren Phase-A-Prototyp hineinschmuggeln.

## Freigabekriterien

- Reale Workers-Free-Messung für die volle OHLCV-Verarbeitung (720 Bars), Kollisionszeiten und Kraken-Fehler sowie D1-Quoten;
- Datengrößenprognose aus echten Cloudflare-Messpunkten und getesteter Retention (keine stillen Löschungen);
- nachgewiesene EU-D1-Jurisdiktion (`eu`), explizite Bestätigung des **Workers-Free-Tarifs** im Dashboard, dokumentierter manueller Start;
- kein Einspielen persönlicher Paper-Konten in die öffentliche Worker-D1 bis zur separaten Authentifizierungsfreigabe.

**Umsetzung Issue #14:** Additive Normalisierung, Messung, Gates und Offline-Recovery sind vorbereitet. Reale Free-CPU-/Tagesquoten, Remote-Migration und spätere Retention bleiben gesonderte Abnahmen. Auch mit Normalisierung wachsen Audit-Journale dauerhaft weiter.
