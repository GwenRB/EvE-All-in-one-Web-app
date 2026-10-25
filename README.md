# EVE Industry Management

A personal web tool for running EVE Online industry across several characters, in one place: skills, jobs, assets, prices, build planning, reactions, planetary industry (PI), client orders, jump freighter logistics, wallets and forecasts.

It is a single HTML page that runs in your browser. A small launcher serves it on your own computer; nothing is hosted anywhere and your data never leaves your browser.

> **README last updated:** 2026-10-25 · what changed and when: [CHANGELOG.md](CHANGELOG.md)

---

## Contents
- [Get started](#get-started)
- [How it works](#how-it-works)
- [Pages](#pages)
- [Rules that apply everywhere](#rules-that-apply-everywhere)
- [Where the data comes from](#where-the-data-comes-from)
- [Files in this folder](#files-in-this-folder)
- [Develop it](#develop-it)
- [Keeping this README up to date](#keeping-this-readme-up-to-date)

---

## Get started

### What you need
- A recent browser (Chrome, Edge, Firefox).
- **Windows:** nothing else (the launcher uses PowerShell, built into Windows).
- **macOS / Linux:** Python 3.

### Start it
1. Keep `EVE Industry Management.html` and the launcher in the same folder.
2. Start the launcher:
   - Windows: double-click `Start EVE Industry Management.bat` (keep its window open while you use the tool; close it to stop).
   - macOS / Linux: run `./start-eve-industry-management.sh` (Ctrl+C to stop).
3. The launcher opens http://localhost:8642/ for you.

The address has to be `http://localhost:8642/`: it is the callback EVE's login comes back to. Opening the HTML file directly also works, but logins then need an extra copy-paste step and some pages (supplier sheets, CCP's static data, news) can't be read.

### Link your characters (one-time setup)
1. On [developers.eveonline.com](https://developers.eveonline.com/applications), create an application ("Authentication & API Access") with the callback URL `http://localhost:8642/`, and add the permissions (scopes) you want to use.
2. In the tool, open **Link EVE characters** at the top of the page, tick the same permissions, and paste the application's **Client ID**. Only the Client ID is needed: never paste the secret key.
3. Click **Log in with EVE Online** and pick a character. Repeat for each character.

Every feature only needs the permissions it reads. New permissions start unticked; when you add one, add it to your EVE application too and log each pilot in again.

### Back up and move your data
Everything is stored in your browser (localStorage and IndexedDB). **Settings → Export backup** saves it to a file; **Import backup** loads it in another browser or computer. Login tokens are never put in backups (log in again after a move). Importing a backup *joins* its wallet history with what's already there.

---

## How it works

- **One page, many tabs.** The tab bar groups pages into menus (Industry, Market, Stock, Pilots, Tools). Any page except Settings can be hidden in Settings. Each page has its own web address (e.g. `#overview`, `#profit-and-loss`), so bookmarks and the back button work.
- **Sync.** Linked pilots are read from ESI (CCP's official API) when you sync: skills, queues, jobs, assets, planets, wallets, contracts, calendar, notifications… Prices and market history are read on demand, through one shared queue that stays under ESI's rate limit.
- **Downtime aware.** The header shows the server status. During the daily downtime (from 11:00 EVE time) syncs and market reads wait; prices keep what they had.
- **Pages read each other, but don't write into each other.** A new tool can use another page's data; it only changes it when you asked for that link (for example Reactions and PI feed the Forecast).
- **Prices are never invented.** An item without a price shows as "no price", never 0 and never another market's price. Totals leave it out and say so, and anything that depends on it (margins, profits) shows as unknown.

---

## Pages

Tab bar: **Overview · To-Do · Map · Industry ▾ · Planets · Market ▾ · Stock ▾ · Pilots ▾ · Tools ▾ · Settings · Notes · Profit and loss · LP store · Corporation · Intel**

### Overview
- **Forecast:** where your ISK is heading. Manual weekly activities, plus plans linked from Reactions and PI (kept up to date), planned builds from Orders management dated by their timeline, and your actual profit from Profit and loss. Omega costs are counted; click a legend line to hide it and take it out of the totals.
- **Calendar** of jobs (manufacturing, reactions, copying, invention, research) and fleets.
- **Upcoming fleets:** every pilot's in-game calendar, each event once with every pilot's answer.
- **EvE News:** the EVE launcher's news, patch notes, forums, or any RSS/Atom/JSON feed you add.
- **Time zones:** EVE time and your own list of cities.

### To-Do
Everything waiting on you, in one list: Omega to renew, structures to refuel, skill queues to fill, empty job slots per pilot, ongoing contracts, trips for a freight service, and what to buy for reactions, PI and builds.

### Map
3D/2D map with security and sovereignty colours, your structures, planets, capital ships, clones and incursions; **kills in the last hour** with a danger level you set; a **jump planner** that waits out fatigue in the best places; and the **Supply chain** (below).

#### Supply chain (on the Map)
Plans every jump freighter / Rorqual trip needed by your orders, reaction cycles and PI pickups, up to a horizon (3 days to 8 weeks):
- Each ship flies every leg: a trip starts where its last one ended (flying back empty if needed). A pilot flies one ship at a time and carries their fatigue; they change ships by shuttle or jump clone.
- The whole plan is optimised at once (lowest fuel, or fastest delivery), never one trip at a time, and shows how much it saves.
- Moves are marked done from your assets as goods arrive (with Undo); trips no ship can do go to a freight-service list on To-Do; gate legs through dangerous systems are flagged.

### Industry
- **PI Management:** P4 planner from CCP's planet schematics: profit per week, hauling, your real customs office taxes, shopping for N days of stock (with how long current stock lasts). Profit goes to the Forecast.
- **Reactions management:** composite and other reactions from CCP's formulas, balanced chains, rigs, hauling, shopping after your assets, a build-up / full-chain step-by-step view. Profit goes to the Forecast.
- **Build planning:** the full build tree for any item, each job in your cheapest structure (role bonus + rigs), invention for T2/T3 (decryptors, relics, chance to succeed), your stock used first, where to buy each material, hauling, a timeline over your pilots' slots, and whether buying on public contracts beats building. Optionally buys **ore instead of minerals** (cheapest ore mix over several reprocessing places, ore hauled compressed, left-overs reused, your own ore reprocessed where it's needed). Sends a build to Orders management.
- **Orders management:** builds you've committed to (planned / in progress / done), their materials and costs, the exact plan to reopen; their stock is reserved in later plans.
- **Jobs:** industry jobs per pilot and a 30-day calendar.

### Planets
Every pilot's colonies, ordered by when they stop, with the customs tax paid at your corporation's offices.

### Market
- **Prices:** import calculator and price comparison between markets.
- **Trading board:** market watch tables with 24 h / 7 day changes, sold per day and ISK per day (from ESI market history), and **Arbitrage** from citadel sell orders.
- **Suppliers:** a supplier's stock from a Google Sheet, a link or a paste, priced as listed or as a % of a pricing.
- **Contract management:** client orders, what's been sent and what's missing; in-game deliveries are found and can be recorded in one click; "Open in Janice".
- **Shortages:** doctrine fittings checked against a citadel's market: what's missing, what's low, what to seed.

### Stock
- **Assets:** personal and corporation hangars with filters and value in a chosen pricing. The search also finds items in your open contracts and outside the hangars (ship cargo, deliveries, containers…), shown but never counted as stock.
- **Stock management:** not built yet.

### Pilots
- **Characters:** implants and pilot cards (slots, ranges, reactions level, reprocessing, skill queue end…), roles.
- **Skills:** who can build or invent a blueprint, skill queues, key skills, skill matrix.
- **Omega:** Omega end dates.
- **Fittings:** EFT paste or in-game fittings; who can fly it now, and when the others will (from their queue or the training time left). Mark fits as doctrines.

### Tools
- **Misc:** Blueprint calculator (ME research and breakeven), jump freighters and Rorqual, jump fuel cost, mining fleet, ships and structures you can build, Quotation, Wallets.

### Settings
Pilots and backup, page visibility, **Pricings** (Jita buy / split / sell, a % of another pricing, or a citadel's own market), reprocessing yield, market taxes, jump drive skills, EvE News channels, time zones, citadel and structure imports.

### Notes
Free notes, kept with your data.

### Profit and loss
Real ISK in and out of every linked wallet (pilots and corporation divisions), sorted by activity (Manufacturing, Reactions, PI, Science, Trading, Hauling…, or your own). Nothing is counted twice, transfers between your own wallets are left out, contracts are split by what they held. You can move any item, client, kind of entry or single entry to another activity. History is kept beyond ESI's 30 days.

### LP store
Your loyalty points per corporation and pilot, and any NPC corporation's store ranked by ISK per LP in your pricings, with how fast each item sells.

### Corporation
Structure fuel (blocks per day from the online services, ISK per month, refuel warning on To-Do), moon extractions, and who mined what (moon drills and your own pilots) with its value.

### Intel
Your pilots' in-game notifications in plain lines (attacks, reinforcements, low fuel, moon chunks, wars…), grouped by kind, with a "needs attention" list counted on the tab.

Each page that computes numbers explains how in **How this page works**, folded at its bottom.

---

## Rules that apply everywhere
These are deliberate choices; they hold on every page.

- **Tables** sort by clicking a column title (again to reverse), A→Z by the first column until you click, except tables whose order means something (by date, by value, cheapest first…), which show an arrow on that column. Your sort is remembered.
- **Grouped tables** fold by group (▾/▸, "n hidden"); rows sort inside their group.
- **Panels** fold from their title; long pages have a **left navigation rail**.
- **Prices** come from your pricings (Settings → Pricings). A citadel pricing only uses that citadel's own orders.
- **Structure and rig bonuses**, **hauling** (jump freighters or a freight service) and **pricing** work the same way on every page.
- **Jump fatigue:** after a jump, fatigue = max(10, F) × (1 + ly), capped at 300 min; the activation timer = max(1 + ly, F / 10), capped at 30 min.

---

## Where the data comes from
CCP's own data first:
- **ESI** (`esi.evetech.net`): your characters and corporation, market orders and history, public contracts, kills, server status.
- **CCP's static data export** (developers.eveonline.com): items, blueprints, reactions, planet schematics, the map. It is indexed once per game build in your browser.
- **EVE Ref** (`ref-data.everef.net`): only when CCP's data can't be read.
- The EVE launcher's news and the feeds you add; images from `images.evetech.net`.

Pages the browser can't read directly (CCP's data zip, supplier sheets, news) go through the launcher's `/proxy`.

---

## Files in this folder

| File | What it is |
|---|---|
| `EVE Industry Management.html` | The whole app (HTML + CSS + JavaScript in one file, no dependencies). Don't rename it: the launchers serve it by name. |
| `Start EVE Industry Management.bat` | Windows launcher (PowerShell). |
| `start-eve-industry-management.sh` | macOS / Linux launcher (Python 3). |
| `CHANGELOG.md` | What changed, version by version. |
| `CLAUDE.md` | Working notes for development with Claude (start here when changing the code). |
| `docs/FEATURES.md` | Every page in detail, with the rules agreed for each. |
| `docs/ARCHITECTURE.md` | Code map, state and storage, shared helpers. |
| `docs/ROADMAP.md` | Known issues, limits and ideas not built yet. |
| `tests/` | End-to-end tests on fake EVE data (see `tests/README.md`). |
| `scripts/check.sh` | Quick syntax check (needs Node). |

---

## Develop it
- Read `CLAUDE.md` first, then `docs/`.
- Syntax check: `scripts/check.sh`
- End-to-end tests (Playwright, fake data, no EVE account needed): `python3 tests/e2e_smoke.py` (on Windows: `py -3.13 tests/e2e_smoke.py`). `--list` shows the scenarios; add words to run only some of them. See `tests/README.md`.
- Licence: GPL-3.0 (see `LICENSE`).

---

## Keeping this README up to date
This README describes what the tool does **now**; `CHANGELOG.md` records **how it got here**.

When features change:
1. Add the change to `CHANGELOG.md` under **Unreleased** (Added / Changed / Fixed / Removed), in plain words.
2. Update the matching section of this README, and the "README last updated" date at the top.
3. When the work is committed, the **Unreleased** entries move under a new dated version heading with its commit.

To refresh it, ask Claude: *"update the README"*. It compares the changelog's last entry with the git history and the docs, then updates both files.
