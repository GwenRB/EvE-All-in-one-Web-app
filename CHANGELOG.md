# Changelog

What changed in EVE Industry Management, newest first. The README describes the tool as it is now; this file is its history.

How entries are kept:
- New work goes under **Unreleased** as it's done, sorted into **Added**, **Changed**, **Fixed**, **Removed**, in plain words (what a user notices, not code names).
- When it's committed, Unreleased becomes a dated heading with the commit: `## 2026-10-21 · 67e84ed — short title`.
- Detailed rules for each page stay in `docs/FEATURES.md`; known limits in `docs/ROADMAP.md`.

---

## 2026-10-25 — Server status, skill queues, calendar, LP store, Corporation, Intel and customs taxes

### Added
- **Server status** in the header (online, players, VIP mode), with the time the server came back up, to the minute, in EVE time. During the daily downtime, syncs and market reads wait and prices keep what they had.
- **Upcoming events** from every pilot's in-game calendar, with each pilot's answer; also on the Overview's calendar.
- **Skill queues** on Skills (training now, queue end, time left; pilots not training are in their own group, shown when you tick "Show pilots not training"), on pilot cards, and as "skill queues to fill" on To-Do with a count on the tab (pilots idle for more than 7 days only when ticked there).
- **Time to fly a fitting** for every pilot who can't fly it yet: the date their queue gets there, or the training time left. Folded by default, like Required skills.
- **Empty job slots** on To-Do: a table with a column per kind of slot (manufacturing, science, reactions) and finished jobs to deliver; a tick box (off by default) counts them on the To-Do tab.
- **Kills in the last hour** on the Map, with a danger level you set; supply chain legs through dangerous systems are flagged, by gate or jumping into them (the cyno there can be caught).
- Skill check: saved blueprints can be removed from their list (✕).
- **Market history** on the Trading board: 24 h / 7 day changes right away, sold per day and ISK per day.
- **In-game deliveries** in Contract management: contracts your pilots made to a client (also those made for the corporation) are found and can be recorded as sent in one click; failed ones are flagged. If the client plays under another name, link that character to the order. The box always says what it looked for and when contracts were last read.
- **Public contracts vs building** in Build planning: whether buying on contracts beats building, and blueprint copies vs inventing.
- **LP store** page: your loyalty points, and any NPC store in one list ranked by ISK per LP, with how fast items sell.
- **Corporation** page: structure fuel (blocks per day, ISK per month, refuel warning on To-Do), moon extractions, who mined what.
- **Intel** page: in-game notifications in plain lines (attacks, reinforcements, fuel, moon chunks, wars), with a "needs attention" count on the tab.
- **Customs office taxes** read from your corporation's offices, used by PI Management when its tax field is empty and shown under each colony on Planets.
- Trading board: market watch tables can be put in your own order with the ↑ / ↓ buttons on each table.

### Changed
- Build planning, ore instead of minerals: left-over minerals are now worth what buying them would cost and come off the build cost; ore is always hauled compressed; your own ore is reprocessed in the system where its minerals are used, at your best refinery there.
- Settings: the reprocessing yield is now only used for Assets and mined ore values (Build planning uses the reprocessing places).
- Build planning, your own ore: in a system where no refinery is known, the ore is no longer reprocessed at a guessed 50% yield; the plan warns "No refinery detected" in that system instead.
- Tab bar: Profit and loss and LP store are now in the Market menu; Corporation is in the Tools menu, renamed **Other**.
- Map: the map, its legend, the system panel and the box shown when you hover a system now use the same icons and colours (your citadels show their type's icon on the map too); the hover box had old symbols.

---

## 2026-10-25 · 718ec3f — README and changelog

### Added
- This changelog, and how to keep it (also in `CLAUDE.md`).

### Changed
- README rewritten: getting started, how the tool works, every page, the rules that apply everywhere, where the data comes from.

---

## 2026-10-21 · 67e84ed — To-Do PI list, Forecast planned orders, PI Remaining, contracts and asset search

### Added
- **Buy for PI** on To-Do: PI Management's shopping list (P1 and P2), with ticks.
- **Planned orders** on the Forecast: each build not done counts on the day it should be finished, with a tile for the total and the next finish.
- PI Management's shopping shows **Remaining** (how long current stock lasts at the planets' use, red under a day).
- Assets search finds items in your **open contracts** and **outside the hangars** (ship cargo, deliveries, containers, asset safety…), shown but never counted.
- Contract management: the opened contract's title is the client's name (click to copy); **Open in Janice**.

### Changed
- Orders and client contracts are listed oldest first.
- PI shopping no longer shows an m³ column.

---

## 2026-10-20 · d42f45c — Supply chain horizon and fleets, ore places and leftovers, market budget, scenario tests

### Added
- **Profit and loss** page: real ISK in and out of every wallet, sorted by activity, history kept beyond ESI's 30 days, joined when a backup is imported; actual profit on the Forecast.
- Supply chain: **several ships per pilot** (a pilot flies one at a time, changing by shuttle or jump clone), a **planning horizon** (3 days to 8 weeks: reaction cycles and PI refills planned ahead), **whole-plan optimisation** (lowest fuel or fastest delivery), moves **marked done from assets** (with Undo), trips no ship can do listed for a freight service.
- Build planning: **ore instead of minerals** over several reprocessing places, with left-overs.
- **One shared budget for ESI market reads**, so several big builds wait instead of being refused.
- Overview: EvE News channels, Upcoming fleets panel, Time zones.
- The same table and panel behaviour on every page: sorting by any column header, folding groups and panels, left navigation rails on long pages, "How this page works" notes.
- CCP's static data as the first source for game data (EVE Ref only as fallback).
- Tests rewritten as independent scenarios with assertions on fake EVE data.

### Changed
- The Forecast page became the **Overview** (old `#forecast` links still work).

---

## 2026-10-20 · dcc79e4 — First version in this repository

The app as built in claude.ai, with launchers, docs and a smoke test:
- **Forecast**, **To-Do**, **Map** with jump planner and a first supply chain.
- **Industry:** PI Management, Reactions management, Build planning (with invention), Orders management, Jobs.
- **Planets**, **Market** (Prices, Trading board, Suppliers, Contract management, Shortages), **Stock** (Assets), **Pilots** (Characters, Skills, Omega, Fittings), **Misc**, **Settings**, **Notes**.
- Windows and macOS/Linux launchers serving the page at http://localhost:8642/ with a `/proxy` for pages the browser can't read.
