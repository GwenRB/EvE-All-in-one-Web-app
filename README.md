# EVE Industry Management

A personal web tool for running EVE Online industry across several characters, in one place: skills, jobs, assets, prices, build planning, reactions, planetary industry (PI), client orders, jump freighter logistics, wallets and forecasts.

It is a single HTML page that runs in your browser. A small launcher serves it on your own computer; nothing is hosted anywhere and your data never leaves your browser.

> **README last updated:** 2026-10-29 · what changed and when: [CHANGELOG.md](CHANGELOG.md) · how to use each page, step by step: [the wiki](https://github.com/GwenRB/EvE-All-in-one-Web-app/wiki)

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
3. Click **Log in with EVE Online** and pick a character. It's linked at once and syncs in the background: log in the next character straight away.

Every feature only needs the permissions it reads. New permissions start unticked; when you add one, add it to your EVE application too and log each pilot in again.

### Back up and move your data
Everything is stored in your browser (localStorage and IndexedDB). **Settings → Export backup** saves it to a file; **Import backup** loads it in another browser or computer. Login tokens are never put in backups (log in again after a move). Importing a backup *joins* its wallet history with what's already there.

---

## How it works

- **One page, many tabs.** The tab bar groups pages into menus (Industry, Market, Stock, Pilots, Other). Any page except Settings can be hidden in Settings. Each page has its own web address (e.g. `#overview`, `#profit-and-loss`), so bookmarks and the back button work.
- **Sync.** Linked pilots are read from ESI (CCP's official API) when you sync: skills, queues, jobs, assets, planets, wallets, contracts, calendar, notifications… Prices and market history are read on demand, through one shared queue that stays under ESI's rate limit.
- **Downtime aware.** The header shows the server status. During the daily downtime (from 11:00 EVE time) syncs and market reads wait; prices keep what they had.
- **Pages read each other, but don't write into each other.** A new tool can use another page's data; it only changes it when you asked for that link (for example Reactions and PI feed the Forecast).
- **Prices are never invented.** An item without a price shows as "no price", never 0 and never another market's price. Totals leave it out and say so, and anything that depends on it (margins, profits) shows as unknown.

---

## Pages

Tab bar: **Overview · To-Do · Map · Industry ▾ · Planets · Market ▾ · Stock ▾ · Pilots ▾ · Other ▾ · Settings · Notes · Tests**

What each page is for, and how to use it step by step, is in [the wiki](https://github.com/GwenRB/EvE-All-in-one-Web-app/wiki) (its home page lists every page of the tool). Each page that computes numbers also explains how in **How this page works**, folded at its bottom.

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

Pages the browser can't read directly (CCP's data zip, supplier sheets, news) go through the launcher's `/proxy`, which only the tool itself can use and which always answers as plain data.

---

## Files in this folder

| File | What it is |
|---|---|
| `EVE Industry Management.html` | The whole app (HTML + CSS + JavaScript in one file, no dependencies). Don't rename it: the launchers serve it by name. |
| `Start EVE Industry Management.bat` | Windows launcher (PowerShell). |
| `start-eve-industry-management.sh` | macOS / Linux launcher (Python 3). |
| `CHANGELOG.md` | What changed, version by version. |
| `wiki/` | The user guide, published as the repository's GitHub wiki (`scripts/wiki.sh`). |
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
3. Update the wiki page that explains it (`wiki/`). `sh scripts/wiki.sh` lists every changelog line the wiki doesn't cover yet, with the pages to update; `sh scripts/wiki.sh mark` records them as done, and `sh scripts/wiki.sh publish` pushes the pages to the GitHub wiki.
4. When the work is committed, the **Unreleased** entries move under a new dated version heading with its commit.

To refresh it, ask Claude: *"update the README"*. It compares the changelog's last entry with the git history and the docs, then updates both files. Likewise *"update the wiki"*.
