# Repository-Prüfung und behutsame Strukturierung

Stand: 30.10.2026. Geprüfte Basis: `8e1d45d`; aktuelle main-Änderungen an Paper-Berichten/Konten werden nicht überschrieben.

## Ergebnis

Alle bestehenden Python-Module, Testdateien, drei Workflows, Abhängigkeiten, Dokumentationen und gespeicherten JSON-/CSV-/Markdown-Berichte wurden inventarisiert. Keine Datei ist anhand der Import- und CLI-Verknüpfungen sicher als entbehrlich nachgewiesen; deshalb keine Löschung oder Verschiebung. Historische Ergebnisse bleiben an ihren bestehenden Pfaden.

Die Abhängigkeiten ccxt (öffentlicher Marktzugriff), NumPy und pandas (Berechnung) werden benötigt. Python-Tests verwenden unittest. Neue Node-Abhängigkeiten sind ausschließlich Entwicklungswerkzeuge der isolierten Worker-Anwendung; kein UI-Framework und keine Runtime-Indikatorbibliothek.

## Zuständigkeiten

| Bereich | Bestehender Pfad / neuer Bereich |
|---|---|
| Python-CLI/Handel/Forschung | Root; bestehende Einstiegspunkte bleiben kompatibel |
| Historische Berichte und Konten | Root-Berichte und daten/; unverändert erhalten |
| Bestehende Tests | test_*.py und tests/ |
| Neue Cloud-Anwendung | cloudflare/src, public, migrations, tests, scripts |
| Neue Architektur-/Betriebsdokumentation | docs/PHASE_A.md |

## Vollständiges Inventar der Ausgangsbasis

| Datei | Prüfung / Rolle |
|---|---|
| `.github/workflows/master-paper.yml` | Aktiver Workflow; vollständig erhalten |
| `.github/workflows/mtf-schedule.yml` | Aktiver Workflow; vollständig erhalten |
| `.github/workflows/mtf-tests.yml` | Aktiver Workflow; vollständig erhalten |
| `.gitignore` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `BACKTEST_MASTER.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `DIAGNOSE_MASTER.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `Diagnosebericht_GitHub_Actions_2026-10-29.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `NETZWERK.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `README.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `TRADING_STATUS.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `TRAILING_STATUS.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `V15_VALIDIERUNG.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `VERGLEICH_MASTER.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `ZEITFENSTER.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `backtest_master.py` | Historical *diagnostic* replay of the unchanged master and the paper engine.; Imports: __future__, argparse, collections, csv, datetime, market, math, net_master, pathlib, trade_broker, trade_engine |
| `compare_report.py` | Mobile reports for the isolated fixed-stop / trailing-stop paper portfolios.; Imports: __future__, collections, datetime, math, trade_report |
| `daten/master_backtest_kurve.csv` | Historisches Forschungsergebnis; Header: signal_day_utc,fill_day_utc,master_eur,passiv_eur,cash_eur,positions,halt_new_buys |
| `daten/master_backtest_trades.csv` | Historisches Forschungsergebnis; Header: day,symbol,side,qty,fill_price_eur,gross_eur,fee_eur,slippage_eur,realized_pnl_eur,reason,type |
| `daten/master_paper_state.json` | JSON geprüft; Kontohistorie: schreibgeschützt |
| `daten/master_trailing_state.json` | JSON geprüft; Kontohistorie: schreibgeschützt |
| `daten/master_v13_entry.csv` | Historisches Forschungsergebnis; Header: coin,signal_day,master_action,failed_gates,forward_7d_open_to_open_pct |
| `daten/master_v13_kurven.csv` | Historisches Forschungsergebnis; Header: signal_day_utc,fill_day_utc,Master unveraendert,ATR-Stopp 2x,"ATR-Trailing 2,5x",Ohne Volumen-Veto,EMA20/SMA50 (Master-L |
| `daten/master_v13_trades.csv` | Historisches Forschungsergebnis; Header: coin,entry_signal_day,entry_fill_day,exit_signal_day,exit_fill_day,bars_held,open,entry_price_eur,exit_price_eur,net_rea |
| `daten/netzwerk_analysen.json` | JSON geprüft; gespeicherte Ergebnisse / Prüfreferenz |
| `daten/zeitfenster_analysen.json` | JSON geprüft; gespeicherte Ergebnisse / Prüfreferenz |
| `docs/SAFETY_v1.5.2.md` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `market.py` | Public daily Kraken spot prices. No API key, no private trading endpoints.; Imports: __future__, ccxt, datetime, numpy, pandas |
| `mtf_analysis.py` | Read-only Multi-Timeframe CLI. Demo has no network and writes only demo artifacts.; Imports: argparse, json, mtf_data, net_timeframe_bot, pathlib |
| `mtf_data.py` | Isolated public OHLCV reader and fail-closed quality gate; no trading imports.; Imports: ccxt, datetime, numpy, pandas |
| `mtf_momentum.py` | RSI14 (Wilder smoothing) and MACD12/26/9, causal EMA seed at first value.; Imports:  |
| `mtf_snapshot.py` | Operational MTF wrapper: fresh artifacts and allowlisted, fast-forward publication.; Imports: argparse, datetime, json, mtf_analysis, mtf_data, os, pathlib, subprocess, sys, tempfile |
| `mtf_trend.py` | Causal trend specialist; never reads future rows.; Imports:  |
| `mtf_volatility.py` | ATR is magnitude, not market direction; threshold is a heuristic veto.; Imports: pandas |
| `net_core.py` | Common, transparent output protocol for independent analysis agents.; Imports: __future__, dataclasses, math, numpy, pandas |
| `net_data_bot.py` | Market data quality specialist. Determines whether downstream analysis may run.; Imports: __future__, market, net_core, numpy, pandas |
| `net_levels_bot.py` | Distance to prior 60-day support and resistance, without look-ahead.; Imports: net_core |
| `net_liquidity_bot.py` | Optional public L2 order-book SNAPSHOT. Not evidence of lasting order flow.; Imports: net_core |
| `net_master.py` | Master integrates analysis in transparent, non-ML, fail-closed conditions.; Imports: __future__, datetime, json, market, net_core, net_data_bot, net_levels_bot, net_liquidity_bot, net_momentum_bot, net_regime_bot, net_relative_bot, net_risk_bot, net_setup_bot, net_structure_bot, net_trend_bot, net_volatility_bot, net_volume_bot, pathlib |
| `net_momentum_bot.py` | Independent RSI and MACD momentum specialist.; Imports: net_core |
| `net_regime_bot.py` | Market regime agent: ADX14 for trend strength, directional index only descriptive.; Imports: net_core, numpy, pandas |
| `net_relative_bot.py` | BTC market comparison / correlation; descriptive cross-asset risk context.; Imports: net_core |
| `net_risk_bot.py` | Hard veto for stale data, anomalous risk, unreliable volume, wide order book.; Imports: net_core |
| `net_setup_bot.py` | Potential trade geometry: NOT executable entry levels or guaranteed price targets.; Imports: net_core |
| `net_structure_bot.py` | Price action / market structure specialist. No fictitious liquidity levels.; Imports: net_core |
| `net_timeframe_bot.py` | Independent observation agent; no connection to either paper engine.; Imports: mtf_data, mtf_momentum, mtf_trend, mtf_volatility |
| `net_trend_bot.py` | Independent 1-day / completed 1-week trend specialist.; Imports: net_core, pandas |
| `net_volatility_bot.py` | ATR, bands, and risk regime; not a price-direction vote.; Imports: net_core |
| `net_volume_bot.py` | Volume confirmation using relative OHLCV volume and on-balance volume.; Imports: net_core, numpy |
| `paper_publish.py` | Allowlisted paper transaction, rebuilt on fetched branch; no merges or force push.; Imports: argparse, json, os, pathlib, subprocess, sys, tempfile, trade_engine |
| `requirements.txt` | Dokumentation / Konfiguration geprüft; bestehende Links und Pfade erhalten |
| `research_master.py` | v1.3: purely historical entry/exit research. NEVER reads or writes a live account.; Imports: __future__, argparse, backtest_master, collections, copy, csv, datetime, market, math, pathlib, trade_engine, trailing_engine |
| `test_master_backtest.py` | unittest-Regression; Imports: backtest_master, copy, market, net_master, pathlib, tempfile, trade_broker, trade_engine, unittest |
| `test_mtf.py` | unittest-Regression; Imports: copy, hashlib, json, mtf_analysis, mtf_data, net_timeframe_bot, numpy, os, pathlib, tempfile, unittest, unittest.mock |
| `test_mtf_schedule.py` | unittest-Regression; Imports: contextlib, datetime, hashlib, json, mtf_analysis, mtf_snapshot, os, pathlib, subprocess, tempfile, unittest, unittest.mock |
| `test_netzwerk.py` | unittest-Regression; Imports: datetime, json, market, net_core, net_data_bot, net_liquidity_bot, net_master, net_risk_bot, net_trend_bot, numpy, pandas, pathlib, tempfile, unittest |
| `test_paper_publish.py` | unittest-Regression; Imports: json, paper_publish, pathlib, tempfile, test_trading, trade_engine, unittest, unittest.mock |
| `test_research_master.py` | unittest-Regression; Imports: backtest_master, collections, copy, market, net_master, pandas, pathlib, research_master, tempfile, trade_engine, unittest |
| `test_safety_v152.py` | unittest-Regression; Imports: copy, datetime, hashlib, json, market, net_data_bot, os, pandas, pathlib, research_master, tempfile, test_trailing_v14, trade_engine, trading, trailing_engine, unittest, unittest.mock |
| `test_trading.py` | unittest-Regression; Imports: copy, json, pathlib, tempfile, trade_broker, trade_engine, trading, unittest, unittest.mock |
| `test_trailing_v14.py` | unittest-Regression; Imports: __future__, compare_report, copy, json, os, pathlib, tempfile, trade_broker, trade_engine, trading, trailing_engine, unittest, unittest.mock |
| `tests/mtf_protected_sha256.json` | JSON geprüft; gespeicherte Ergebnisse / Prüfreferenz |
| `trade_broker.py` | Exchange boundary. Public order book only. No credential or private endpoint access.; Imports: __future__, dataclasses, datetime, math |
| `trade_engine.py` | Deterministic spot-only Paper Trading engine. EUR cash, no margin or shorting.; Imports: __future__, copy, datetime, math, trade_broker |
| `trade_report.py` | One concise Markdown mobile dashboard; all values from persisted paper state.; Imports: __future__, datetime, trade_engine |
| `trading.py` | Master network entry point. Only analysis, paper, demo, tests. NO live orders.; Imports: __future__, argparse, compare_report, datetime, json, market, net_master, os, pathlib, tempfile, trade_broker, trade_engine, trade_report, trailing_engine |
| `trailing_engine.py` | Standalone, strictly simulated 2.5x ATR trailing-exit paper engine.; Imports: __future__, copy, math, trade_broker, trade_engine |

## Spätere separate Aufgaben

- Python-Paketstruktur nur mit CLI-Kompatibilitätsschicht und separater Workflow-/Pfadmigration ändern.
- Überschneidungen zwischen net_core und den isolierten MTF-Indikatoren nicht zusammenführen: Parameter-/Rundungsunterschiede erst separat prüfen.
- Historische v1.3/v1.4-Forschungsergebnisse bleiben auditierbar; Korrekturhinweise aus SAFETY_v1.5.2 beachten.
- Erst nach expliziter Paper-Migration bestehende Berichtspfade oder Schreiber ändern.
