# EVE Industry Management

A personal, local web tool for running EVE Online industry across several characters: skills, jobs, assets, prices, build planning, reactions, PI, orders, logistics (jump freighters), forecasts. Built with Claude in claude.ai; continued here.

## The shape of the project
- **One file is the app:** `EVE Industry Management.html` (~7.5k lines, ~870 KB: HTML + CSS + vanilla JS, no build step, no dependencies, a few base64 images inline). Keep it a single self-contained file: that is how it's used and shared.
- **Launchers** serve it at `http://localhost:8642/` (required: it's the EVE SSO callback URL registered in the user's ESI application) and add a `/proxy?url=` endpoint for pages the browser can't fetch directly (CCP static data zip, supplier sheets):
  - `start-eve-industry-management.sh` (macOS/Linux, Python 3), `Start EVE Industry Management.bat` (Windows, PowerShell). Change both together.
- **Data lives in the user's browser** (localStorage + IndexedDB), never on a server. Export/Import backup (Settings) moves it between browsers. Login tokens never leave the browser and are not in backups.

## Commands
- Syntax check: `scripts/check.sh`
- End-to-end tests (fake data, Playwright): `python3 tests/e2e_smoke.py [words…]` → independent scenarios with assertions, exit 1 when one fails (a failed check or a page JS error); `-v` prints the values read, `--list` the scenarios. Add a scenario (with checks) for new features. See `tests/README.md`.
- ESI market reads go through `esiMarket` (one shared budget), never `fetch`/`fetchRetry` directly.
- Run for real: `./start-eve-industry-management.sh` then open http://localhost:8642/

## Read before changing things
- `docs/ARCHITECTURE.md` — code map (section markers to grep), state & storage, shared helpers (pricing, rigs, hauling, jumps), page/tab system, ESI.
- `docs/FEATURES.md` — what every page does and the rules agreed with the user (they are deliberate; don't "simplify" them away).
- `docs/ROADMAP.md` — known issues, limits, and ideas not built yet.

## The user's standing preferences (apply everywhere)
- **Game data first:** prefer CCP's own data (ESI, the static data export at developers.eveonline.com) over third parties. Item/blueprint/group lookups are written `getJSON(REF + "/types/<id>")` etc. and answered from CCP's static data (an index built once per game build, `ccpGet`); EVE Ref (`ref-data.everef.net`) only answers when CCP's data can't be read. New lookups should go through `getJSON` the same way.
- **Every table sorts by clicking its column headers** (no "sort by" dropdowns), A→Z by the first column by default; a table whose order means something (by date, value, cheapest first…) keeps it and marks it `data-sorted="<col>:<1|-1>"` (`""` = as rendered). The shared sorter (`tableDecorate`/`tableSort`) does this after every render; give cells whose text doesn't sort right (dates, levels) a `data-v`; totals rows are `tr.total`. Tables that page their rows sort in the renderer (`sortHead`/`sortRows`, e.g. Assets).
- **Grouped tables fold like Reactions' kinds:** `tr.group` / `tr.subgroup` rows (▾/▸, "· n hidden", remembered in `state.misc.folds`); rows sort inside their group. Use them for any table with categories.
- **Every panel folds from its title** (`state.misc.panels`); **long pages get a left navigation rail** (`plan-layout` / `plan-rail` / `plan-nav`; `navRender(navId, items)`, or `data-auto` to list the page's panels plus `data-nav-sub` sub-items).
- **Page notes:** how a page's numbers are worked out goes in `HOWTO[page]` (folded under the page), not in panel text.
- **New tools read other pages' data but never write into them**, unless the user explicitly asks for a link (e.g. Reactions/PI → Forecast activity was requested).
- **Prices are never invented:** a citadel pricing only returns that citadel's own orders; an item without a price is empty ("no price"), never 0 and never another market's price. Totals leave it out and say so (`noPriceNote`), and results that depend on it (margins, profits, breakeven) show as unknown.
- **Same rules everywhere:** structure/rig bonuses always via `rigBonus` (and `sciBonus` for laboratories); hauling via the shared JF/freight logic; pricings via the shared pricing system (Settings → Pricings).
- **Ships fly every leg:** a hauler's trip always starts where its last trip ended (it flies back empty if nothing rides the return); never plan a trip from somewhere the ship isn't. Plan hauling globally (the whole plan scored at once, `scSolve`), never one trip at a time.
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
