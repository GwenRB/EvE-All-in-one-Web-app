# Changelog

What changed in EVE Industry Management, newest first. The README describes the tool as it is now; this file is its history.

How entries are kept:
- New work goes under **Unreleased** as it's done, sorted into **Added**, **Changed**, **Fixed**, **Removed**, in plain words (what a user notices, not code names).
- When it's committed, Unreleased becomes a dated heading with the commit: `## 2026-10-21 · 67e84ed — short title`.
- Detailed rules for each page stay in `docs/FEATURES.md`; known limits in `docs/ROADMAP.md`.

---

## 2026-10-29 — Gather items on the Map, filter groups, industry jobs in Net worth

### Added
- Map: **Gather items**, under the Jump planner. Pick items from your hangars and a start system. You get the shortest trip through the gates that stops in every system holding some of them, optionally back to the start. Each stop says what to pick up and where, and the stops are numbered on the map.
- Gather items: **Security** tick boxes (high-sec, low-sec, null-sec). Stops in the others are left out, and the route doesn't fly through them.
- Gather items: **Travel by gates and jumps** with the ship chosen under Range. Each leg takes gates or jumps, whichever is quicker, and you see the jumps, light years and fuel.
- Gather items: **empty a station**. Pick a station or structure from the **Stations** dropdown (grouped by system, with how many items it holds), and everything your hangars hold there is picked up.
- Gather items: **Cargo**. Pick the ship under Range (fitted for hauling, with its pilot's skills), a ship from your hangars (its bare hold), or type the m³. When the hold is full, the trip goes back to the start to unload, then carries on, and each stop shows what's in the hold.
- Filters: **groups of conditions**, each with its own "all of them" / "any of them", inside each other. For example: (Item contains "ore" and Quantity more than 1m) or Location is Jita.
- Net worth: an **Industry jobs** part. It is what your running manufacturing and reaction jobs will deliver, priced like Assets. A product without a price is named and left out.

### Changed
- Net worth and the Forecast: a courier contract you are hauling now counts its collateral as well as its reward, since both come back when you deliver.

## 2026-10-29 · 3b15b21 — Trading board: a market browser, and a list of trade hubs

### Added
- **Trading board**: a market browser like the game's, over the whole width of the window and one screen tall (scroll past the header and it fills the screen; its notes open from **How this page works** in the item panel). Pick an item in the market groups or find it by name, and see every sell and buy order for it in every region and in your citadels, or only in one region, trade hub or citadel (the **Where** dropdown): price, quantity, location with its security, jumps from a pilot or a trade hub, range, expiry. PLEX is found too, in its global market. Tiles give the 5% sell and buy prices, the margin, units for sale and wanted. **Show history** (under the Market panel) charts a region's daily prices and units traded over 7 days to everything, with ISK on the left and volume on the right (PLEX: the global market's; point at a day to see its numbers), and **Show markets comparison** puts the trade hubs and your citadels that have orders side by side; both can open in a window of their own, to put on another screen. Sellers and buyers share the screen, with thin rows, and a clicked line stays highlighted. Filters: price, quantity, jumps, security, NPC stations or player structures, trade hubs only, your own orders, location. Your own orders are marked; click the item's name or a price to copy it.
- Settings: **Pricings** is now **Pricings and HUBs**, with a list of trade hubs. The five main hubs are built in; add any NPC station by its name or ID. Every menu that offers a trade hub (Trading board, Import calculator, Market watch, Arbitrage, public contracts, broker fees) uses this list.
- Item database: a **Trading board** button next to every item sold on the market (and **View on the Trading board** on an opened item).

### Changed
- The **Trading board** is now its own tab, between the Market and Stock menus. Its **Market watch** and **Arbitrage** panels moved to the **Prices** page.

## 2026-10-29 · 5786ba0 — Build planning: reactors, invention structures and refineries as lists, test copies, folding sections

### Changed
- Build planning: the **Refinery** is its own panel, set up like the other structures (known refinery, type, reprocessing rig, system, tax, pilot), and sits after the invention structures, followed by **Ore instead of minerals**.
- Build planning: the reaction structure is now the **Reactor**, and you can add several reactors and several invention structures, like manufacturing structures: each reaction, and the invention, goes where it comes out cheapest (a reaction can be moved to another reactor in the plan). "Set with imported structures" uses every refinery with reaction rigs and every engineering complex with laboratory rigs.
- Build planning: any structure can be removed, the last one too: manufacturing structures, reactors, invention structures and refineries.
- Build planning: with no manufacturing structure, the plan asks you to set one up first. A reaction (as the item planned) needs a reactor, and an item that needs invented copies an invention structure, or **Plan on a test copy instead** (ME 2 / TE 4, no invention counted).
- Build planning: when a structure the plan would use is missing, the plan says so (**Some structures are missing**): without a reactor the reactions are bought and marked **No reactor**; without a refinery, ore isn't bought instead of minerals.
- Build planning: **Set ME/TE** next to the blueprint plans the final job with the ME and TE you choose, whether you own the blueprint or not (a test copy for an invented item). **Use yours** / **Clear** goes back.
- Build planning: every section of the plan (Materials needed, Timeline, Who builds what, Per pilot…) folds from its title, and stays folded.
- Build planning: a timeline bar too short to hold its time shows it next to the bar.
- Build planning: **Ore to buy** only shows when the plan buys ore; when the minerals come out cheaper, it's left out.

## 2026-10-29 · 27b69a3 — Blueprint library, CONCORD LP conversion, boosters on Misc

### Added
- Tests: a **Blueprint library**: every original your pilots and corporations own with its ME and TE, in three groups: in research (the levels it will reach and when it's done), copying (how many copies, their runs, when it's done) and the others. Below it, every copy with its ME, TE and runs. Refresh from ESI once so copying jobs show the runs of each copy.
- LP store: picking **CONCORD** shows the stores CONCORD LP converts to (10 CONCORD LP give 8 LP of an empire faction's corporation, 4 of another faction's; militias, pirates and a few others can't be converted to), what your CONCORD LP gives in each and each store's best ISK per CONCORD LP. **Read every store** adds their offers to the list, their LP price turned into CONCORD LP, with the store each comes from. CCP's game data is read again once, to learn which faction each corporation belongs to.
- LP store: a list longer than 300 offers shows the best 300 first, with a "Show more" line.

### Changed
- The **Attribute boosters** panel moved from Tests to Misc.

## 2026-10-29 · 50cc4ec — Who makes what on Planets, owned economizers and formulas found, supplier prices

### Added
- Planets: a **Who makes what** panel: each pilot's highest tier output (P4, P3… or what they extract), summed over their colonies, grouped by tier.

### Changed
- Build planning → Materials needed: raw materials and components are each split into the items' groups (Mineral, Moon materials, Composite…), A→Z.

### Fixed
- Settings → Jump drive economizers: an economizer fitted on a ship (or in its cargo) now counts as one you own; only hangars were looked at.
- Reaction formulas (and other blueprints) bought from the market and never used sit in a stack, which ESI lists once: every one in the stack now counts. Refresh from ESI once to read them again.
- Item database: categories further down the list showed their count but no items (the first 100 items were shared by every category). Each category now shows its first 100 items with its own "Show more" row.
- Suppliers: a supplier priced at a % of a pricing showed "no price" in their stock list; it now shows their price for every item that has one in that pricing.

## 2026-10-29 · 06d308d — Tests page with attribute boosters, Reddit news channel, steadier background sync

### Added
- A **Tests** page at the end of the tab bar, with an **Attribute boosters** panel: every booster that adds to your attributes (cerebral accelerators), what it costs a month (30 days, injected back to back), the extra skill points it gives a month and what each costs, with its bonuses, how long it lasts (your Biology level counts) and the best one for each attribute. Buy at any of your pricings, a trade hub or a citadel market. Boosters with an expiry date are flagged, expired ones listed apart.
- EvE News: a **Reddit r/Eve: top today** channel, the day's 5 most upvoted posts on r/Eve, on by default (untick it in Settings → EvE News channels).

### Fixed
- Logins: the background sync could stay on "Syncing in the background" for hours for a pilot whose corporation has many contracts. ESI only lets the tool read so many contracts' items at a time; when it says to slow down, the sync now stops reading items and finishes, and the rest are read at the next syncs. The line also says what each pilot is reading (skills, contracts, hangars…), an ESI request that never answers gives up after a minute and is tried again, and a save the browser refuses no longer waits forever.

## 2026-10-27 · 1b658ed — Import calculator with suppliers, map legend toggles, materials needed

### Added
- Prices → Import calculator: a "Look at your suppliers too" tick box (their stock is bought when it's cheaper; picked up in Jita pays the hauling), a "Sync markets" button to read both markets again after you bought there, and item names copy on click.
- Map: click a line of the legend to hide or show those markers on the map (struck out while hidden); homes and incursions get their own tick boxes too.
- Build planning: a "Materials needed" summary near the top: every raw material the build uses (needed, from your stock, to buy) and the components built on the way, with a button to copy the raw materials.
- To-Do → Empty job slots: "Show" chips to list only some kinds of slot (manufacturing, science, reactions) and only some pilots; the To-Do tab's count follows them.
- PI Management → Shopping: "Round up to" rounds every quantity to buy up to a multiple you choose (To-Do's Buy for PI too), and an "Import calculator" button next to Copy multibuy opens the list there.

### Fixed
- Import calculator: an item without enough for sale no longer counts as if every unit was bought. Only what is for sale is counted (cheapest first, wherever it is); the missing units are shown per item and left out of the totals.

## 2026-10-27 — Unused code removed

### Removed
- Unused code and styles taken out of the page (old structure icon styles, a bar chart style, helpers nothing called). Nothing you use changes.

## 2026-10-27 — Background sync after logins, pilots on the map, safer launchers

### Added
- Overview → Forecast: a stock line from hangars can count only one location or one hangar (for example the corporation hangar you sell composites from, not the one kept for your own use), and can take everything there instead of one kind of item.
- Map: every pilot's last location (from the "Character location" permission, read at each sync), marked around the system's dot with the game's own-ship bracket; the hover box and the system panel say who is there, docked or in space, in which ship and when it was seen. A **Pilots** tick box hides them.

### Changed
- Linking or re-logging a character no longer makes you wait: it's linked as soon as you approve, and its skills, jobs, assets and the rest sync in the background (one pilot at a time, the others wait their turn), so you can log in the next character straight away. The login panel, the Characters page and the pilot cards show who is syncing and who is waiting.
- **To-Do**'s left navigation lists the panels only, without their sub-lists.
- Tab bar: **Intel** and the **Item database** moved to the Other menu (Intel's alert count shows on the menu), the **Contracts browser** to the Market menu.
- Map: your citadels are a gold diamond under the system's dot again (friendly ones a hollow pale diamond), instead of a structure icon hidden behind the dot.

### Fixed
- Launchers: other websites can no longer use the launcher's page reader, and what it reads always comes back as plain data, never as a page that could run as the tool (it could have read your logins). Restart the launcher to get this.
- When the browser's storage is full, the tool now says so once ("Use Export backup") instead of losing changes without a word.
- Pages respond faster: the Skills page and the Overview are only redrawn while open.
- Map: capital ship icons are the game's own overview brackets again, built into the page; they had turned into plain triangles because the website they came from stopped answering. The planet icon no longer depends on that website either.

## 2026-10-26 — Filters, net worth, Contracts browser and Item database

### Added
- **Filters** on every table that had filters (Assets, Profit and loss's Entries and Items, Intel, the skill matrix, Ships you can build) and on the two new pages: add conditions on any column (contains, is, more than, between, in the last N days…), show rows that match all of them or any, switch one off for a moment, and save a set under a name to load it again.
- **Net worth** on the Overview, like a tracker: day by day, your wallets, assets, sell orders, buy orders' escrow and contracts, for everyone or only the pilots and corporations you pick, with the change over the period and your highest day. Days you didn't open the tool are filled in from your wallet journals. A day is now also saved at each sync.
- **Market orders** read from ESI (new "Market orders" and "Corporation market orders" permissions): listed under Net worth, and counted in the Forecast's total value (sell orders at their price, buy orders' escrow).
- **Contracts browser** page (at the end of the tab bar): every contract of your pilots and corporations in one place, active or ended (kept 90 days), with what each one gives and asks for, your side (you sell, you buy, you haul…), who's in it, where, and what its items are worth against its price.
- **Item database** page (last tab): every item in the game from CCP's own data, by name or by category and group; open one to see what it is, its prices, how many you own, what makes it, what it's used in, what it reprocesses into, its bonuses and its attributes.

### Changed
- The browser tab shows the EVE Online logo as its icon.
- The Forecast's History is now the Net worth panel's **Day by day** table, with a column per part.
- Contracts: the items of every contract are read (also those offered to you, and what a contract asks for), not only your own; Assets still only lists what you put in contracts.

---

## 2026-10-25 — User guide wiki

### Added
- **User guide wiki** (`wiki/`, published as the repository's GitHub wiki): getting started, permissions, every page, step-by-step guides and troubleshooting. `scripts/wiki.sh` lists the changes the wiki doesn't explain yet and publishes it.

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
