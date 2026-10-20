# EVE Industry Management

A personal, local web tool for running EVE Online industry across several characters: skills, jobs, assets, prices, build planning, reactions, PI, orders, logistics (jump freighters), forecasts. Built with Claude in claude.ai; continued here.

## The shape of the project
- **One file is the app:** `EVE Industry Management.html` (~7.5k lines, ~870 KB: HTML + CSS + vanilla JS, no build step, no dependencies, a few base64 images inline). Keep it a single self-contained file: that is how it's used and shared.
- **Launchers** serve it at `http://localhost:8642/` (required: it's the EVE SSO callback URL registered in the user's ESI application) and add a `/proxy?url=` endpoint for pages the browser can't fetch directly (CCP static data zip, supplier sheets):
  - `start-eve-industry-management.sh` (macOS/Linux, Python 3), `Start EVE Industry Management.bat` (Windows, PowerShell). Change both together.
- **Data lives in the user's browser** (localStorage + IndexedDB), never on a server. Export/Import backup (Settings) moves it between browsers. Login tokens never leave the browser and are not in backups.

## Commands
- Syntax check: `scripts/check.sh`
- Smoke test (fake data, Playwright): `python3 tests/e2e_smoke.py` → exit 1 on any page JS error; read the printed values for regressions. See `tests/README.md`.
- Run for real: `./start-eve-industry-management.sh` then open http://localhost:8642/

## Read before changing things
- `docs/ARCHITECTURE.md` — code map (section markers to grep), state & storage, shared helpers (pricing, rigs, hauling, jumps), page/tab system, ESI.
- `docs/FEATURES.md` — what every page does and the rules agreed with the user (they are deliberate; don't "simplify" them away).
- `docs/ROADMAP.md` — known issues, limits, and ideas not built yet.

## The user's standing preferences (apply everywhere)
- **Game data first:** prefer CCP's own data (ESI, the static data export at developers.eveonline.com) over third parties. EVE Ref (`ref-data.everef.net`) is still used for many type/blueprint lookups; moving a lookup to CCP data is welcome, keep EVE Ref only as a fallback.
- **Tables sorted alphabetically by default**; sorting is done by clicking column headers (no "sort by" dropdowns).
- **Panels hideable/collapsible; long pages get a left navigation rail** (the `plan-layout` / `plan-rail` / `plan-nav` pattern, sub-items with ellipsis, active item tracked on scroll).
- **New tools read other pages' data but never write into them**, unless the user explicitly asks for a link (e.g. Reactions/PI → Forecast activity was requested).
- **Prices are never invented:** a citadel pricing only returns that citadel's own orders; an item without a price is empty ("no price"), never 0 and never another market's price. Totals leave it out and say so (`noPriceNote`), and results that depend on it (margins, profits, breakeven) show as unknown.
- **Same rules everywhere:** structure/rig bonuses always via `rigBonus` (and `sciBonus` for laboratories); hauling via the shared JF/freight logic; pricings via the shared pricing system (Settings → Pricings).
- **Jump fatigue:** after a jump fatigue = max(10, F) × (1 + ly) capped at 300 min; activation timer = max(1 + ly, F / 10) capped at 30 min. Fatigue under 10 min acts as 10, so waiting it lower never helps.
- **UI copy:** plain English, short, sentence case, no jargon the game doesn't use. Numbers via `isk()`, dates via `fmtDate`, durations via `fmtDur`.
- **Deliverables:** the user wants the updated HTML (and launchers only when they change), plus a short summary of what changed. Don't rename the HTML file (the launchers serve it by name).

## Working conventions in the code
- Global `state` object; per-feature settings under `state.misc.<feature>` saved with `saveMisc()`; Forecast under `state.forecast` (`saveForecast()`); fittings `state.fits` (`saveFits()`).
- Rendering is string templates into `innerHTML`; always escape with `esc()`.
- Events are delegated on `document` with `data-*` attributes (e.g. `data-rx-sort`, `data-pi`, `data-sc-plan`); each feature keeps its own attribute prefix.
- Pages: `<div id="page-<key>" class="page">`, a button `data-tab="<key>"` in `nav.tabs` (grouped in `.tabgrp` menus), an entry in `PAGES` (hash slug) and a hook in `showPage()`.
- Config objects carry a version (`v`) and migrate old saves in their `xxCfg()` accessor — keep migrations when changing shapes.
- Long lines are normal in this file; match the surrounding style rather than reformatting (diffs stay readable).
