# Krypto Master Network – ATR-Trailing-Demokonto

**NUR PAPER TRADING – ECHTGELD TECHNISCH GESPERRT.**

Aktualisierungszeit: 30.10.2026 13:39 UTC  
Letzter verarbeiteter Börsentag: **2026-10-29**  
Kontolauf: **bereits verarbeitet – keine Doppelbuchung**

## ATR-Trailing-Demokonto (2,5× ATR14)

- **Depotwert:** 1.000,00 €
- **Gewinn/Verlust seit Beginn:** 0,00 € (+0.00 %)
- **EUR-Reserve:** 1.000,00 €
- **Wert der Coins:** 0,00 €
- **Ausführungen gesamt:** 0
- **Gebühren:** 0,00 €; **modellierte Zusatz-Slippage:** 0,00 €
- **Neue Käufe blockiert (Drawdown):** NEIN

## Coin-Bestände

| Coin | Menge | Wert nach letzter Quote |
|:--|--:|--:|
| Keine offenen Positionen | — | — |

## Master-Entscheidungen

| Coin | Entscheidung | Begründung |
|:--|:--|:--|
| BTC/EUR | **HOLD** | ABWARTEN |
| ETH/EUR | **HOLD** | ABWARTEN |
| NEAR/EUR | **HOLD** | ABWARTEN |
| SOL/EUR | **HOLD** | ABWARTEN |

## Letzte simulierte Orders

| Tag (UTC) | Coin | Aktion | Wert inkl. Kosten / netto | Grund |
|:--|:--|:--|--:|:--|
| Noch keine virtuellen Ausführungen | — | — | — | — |

## Markt-Analysen

Die ausführliche Bewertung der Spezial-Bots steht in [`NETZWERK.md`](NETZWERK.md).

## Technische Hinweise

- Simulierte Orderfüllung: öffentliches Kraken-Orderbuch (Bid/Ask) + 0.1 % Zusatz-Slippage und 0.4 % Gebühren je Ausführung.
- Kauf-/Stoppregeln verwenden abgeschlossene UTC-Tageskurse; Ausführung und Bewertung erfolgen zu später abgerufenen Geld-/Briefkursen.
- Keine garantierten Stopps: bei Kurslücken, API-Problemen oder verzögerten GitHub-Läufen kann ein Stopp erst später geprüft werden.
- Ein virtuelles Limit reduziert Risiken, verhindert aber keine Verluste.
- Das System ist kein Hochfrequenz- oder 24/7-Orderüberwachungsdienst.
- Die Renditeangaben sind nicht steuer- oder börsenspezifisch garantiert.

Transaktionsbuch im separaten `daten/master_trailing_state.json`.


## Nachgezogene Stopps

| Coin | Höchster gespeicherter Schlusskurs | Aktueller ATR-Stopp |
|:--|--:|--:|
| Keine offenen Positionen | — | — |

Der Stopp wird **erst nach erfolgreicher Tagesverarbeitung** neu berechnet und ist **kein börsenseitig gesetzter Stop-Auftrag**. Eine Kurslücke kann deutlich größere Verluste verursachen.
