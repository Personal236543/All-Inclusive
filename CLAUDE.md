# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Selenium (Chrome) automation for All Inclusive Outlet (AIO). It pulls bookings from the AIO admin commission report (`tprofile.allinclusiveoutlet.com`), saves invoice PDFs, marks the commission as registered in AIO, then re-enters those bookings into each hotel chain's travel-agent rewards portal (Karisma, Iberostar, Jamaica, Dominican, Palladium, Lomas…). `vax/` is a separate flow that reconciles VAX weekly summary CSVs against AIO. Code, comments, logs and variable names are mostly in Spanish (`RUTA_*` = path, `pendientes` = failed/pending, `done` = processed).

## Running

There are no tests, linter or build. Python 3.11, deps: `pip install -r requirements.txt`.

**Secrets:** all credentials come from `.env` (copy `.env.example`), loaded by `utils/config.py` at import time; Iberostar agents come from a JSON file (`IBEROSTAR_AGENTES_FILE`, see `hoteles/iberostar/agentes.example.json`). Never hardcode credentials, and never commit `.env`, `agentes.json`, or run data (`json/`, `logs/`, `invoices/`, CSV/XLSX) — they contain real customer PII. This repo is public. Sample inputs live in `examples/`.

Everything runs through one entry point, configured by editing constants at the top of `script_runner.py` (there is no CLI):

```bash
python script_runner.py
```

Key switches in `script_runner.py`:
- `EJECUTABLE` — which flow: a folder name under `hoteles/` (e.g. `"karisma"`), or `"vax"` / `"vax2"`.
- `ALL_INCLUSIVE_DEPARTURE_DATE_FROM/TO`, `ALL_INCLUSIVE_TO_PROCESS` — AIO search window and cap.
- `CORRER_EJECUTABLE` — whether the hotel module's `main()` actually runs after the AIO scrape.
- `*_CLICK` — when `True` the scripts click real "REGISTER"/submit buttons on live sites. Set to `False` to dry-run.
- `LIMPIAR_BOOKINGS_PROCESADOS` — runs `utils/act.py` to remove `done` bookings from `bookings.json` (with a timestamped backup).
- `EJECUTABLE_CLEAR_*` / `ALL_INCLUSIVE_CLEAR_*` — run `utils/clear_runs.py` to wipe logs/jsons/invoices before a run.

Individual modules can also be run directly (`python -m hoteles.karisma.karisma` from repo root) but they still import `script_runner` for `EJECUTABLE`.

## Architecture

**Pipeline for a hotel run** (`script_runner.main`):
1. `clear_runs.main()` cleans the selected hotel's `logs/`, `json/`, `invoices/`.
2. `all_inclusive.main()` logs into AIO, filters bookings (status Reviewed, Registered = No, commission rule = the hotel module's `COMMISSION_RULE`, departure window), and for each booking scrapes passengers/hotels/airline into `hoteles/<EJECUTABLE>/json/bookings.json`, prints the invoice to PDF into `hoteles/<EJECUTABLE>/invoices/` (Chrome kiosk-printing prefs), and clicks REGISTER on the matching commission row.
3. If `CORRER_EJECUTABLE`, `hoteles/<EJECUTABLE>/<EJECUTABLE>.py:main()` reads that `bookings.json` and registers each booking on the hotel portal.
4. `utils/act.py` prunes processed bookings; a row is appended to `script_execution_log.csv`.

**Configuration via module globals.** Every module defines uppercase constants (`CLICK`, `SLEEP_TIME`, `TO_PROCESS`, `HEADLESS`, `USERNAME`, `PASSWORD`, `COMMISSION_RULE`, `RUTA_*`). `script_runner` overrides some of them by assignment (`module.CLICK = ...`) before calling `main()`. Path constants are computed at import time from `script_runner.EJECUTABLE`, so `EJECUTABLE` must be changed in `script_runner.py`, not at runtime. Modules import `script_runner` (circular import) — keep `script_runner`'s top level free of side effects outside `if __name__ == "__main__"`.

**Hotel module contract** (`hoteles/<name>/`): `<name>.py` exposes `COMMISSION_RULE` (must match the AIO commission rule text exactly, normalized) and `main()`; `<name>_mapping.py` exports `hotels`, a dict keyed by the AIO hotel name, each value a dict with `"name"` (portal's hotel name) plus AIO room type → portal room type entries. `utils.mapping.map_pair(HOTELS, hotel, room)` returns `(None, None)`/`(name, None)` when unmapped; the booking is then written to `json/pendientes.json` via `utils.register_pending` and skipped. Adding a new room/hotel usually means only editing the mapping file. Some modules also map airlines (`AERO`, `aerolineas`).

**Per-flow runtime state** (git-ignored, created at runtime): `json/bookings.json`, `json/done.json`, `json/pendientes.json`, `logs/<name>.log`, `invoices/`. JSON files are lists appended via `utils/register1.register1`. `done.json` entries may be a booking number string, a full booking dict, or `{booking_no: message}` — `utils/act.obtener_booking_number` handles all three.

**Booking shape** (produced by `all_inclusive.process_booking`): `Booking Number`, `Client Name`, `Date Entered`, `Departure Date` (`%m/%d/%Y`), `Return Date`, `Supplier`, `Destination`, `Supplier Price`, `Airline`, `Passengers: [{First Name, Last Name, Age, Type}]`, `Hotels: [{Hotel Name, Room Type, Duration}]`. Hotel modules split passengers evenly across `Hotels` entries (one form per room).

**Shared helpers** in `utils/utils.py`: `normalize_string` (used for all text comparisons against the page), `robust_type` (slow per-char typing for flaky autocomplete inputs), pending/done registration, CSV/booking filtering helpers.

**VAX** (`vax/vax.py`, `vax/vax2.py`): reads summary CSVs from `vax/sumaries/`, compares each against AIO search results, writes updated CSVs (processed ones live in `vax/processed_sumaries/<year>/`). `vax2` additionally filters by receive date.

**Iberostar** differs from the rest: it distributes bookings across several agent accounts (`AGENTES` dict in `iberostar.py`), logging in/out per agent, and has its own `act.py`.

## Gotchas

- `chromedriver.exe` at the repo root must match the installed Chrome version (download from https://googlechromelabs.github.io/chrome-for-testing/). All modules point `RUTA_DRIVER` there, but a few (`lomas`, `palladium`, `karisma/read_csv.py`) build the path with a single `os.pardir` and resolve to `hoteles/chromedriver.exe` instead.
- `SLEEP_TIME` comments ("No menos de 2", "No mas de 70") are empirical limits for hotel portals — lower values cause flaky failures/blocks.
- Selectors are mostly absolute XPaths and positional indexes (`tds[3]`, `tabs[3]`); a portal UI change breaks them silently and bookings land in `pendientes.json`.
- `developing/` holds one-off scripts for building mapping files (not part of the pipeline). `SOLO_LIMPIAR_BOOKINGS_PROCESADOS` and `HOTEL_A_LIMPIAR` in `script_runner.py` are currently unused.
