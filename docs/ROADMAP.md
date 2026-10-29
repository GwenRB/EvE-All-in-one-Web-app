# Known issues, limits and ideas

## Supply chain
- No gate-only freighter for high-sec runs; high-sec ends are reached by the JF through gates. Freight-service legs are only suggested, not planned (user: leave high-sec out for now).
- Inputs of later reaction cycles and PI refills are ready "now" (you can buy them any time), so a long horizon may haul several cycles' inputs early when that saves fuel; there's no limit on stock held at the reactor or the planets.
- Changing ships: a pilot shuttles through the gates (1 min a gate, any security) or jump clones when that's an hour or more sooner; whether a jump clone is actually installed there, the clone's implants, and the risk of a shuttle through hostile space aren't modelled.
- Done from assets: goods a job used before the next assets read, or goods that arrived and left again, aren't seen; goods bought locally in the destination system look like arrivals (Undo puts them back). Reaction-cycle and PI move ids follow their dates, so a cycle that slips by an hour or more is a new move (its "Done" doesn't carry over).
- The whole-plan search (`scSolve`) is a heuristic with a budget (6,000 tries or 4 s): much better than trip by trip, not proven optimal. A ship never delays a pickup on purpose beyond "hold goods at most N hours".
- When several reaction cycles / PI refills are planned ahead, their products must wait for the inputs' trips (the way build products already do); today only the running cycle's products and the P4 already on the planets are moved, which don't depend on any planned trip.
- Fixed time constants (3 min/jump, 1.5 min/gate, 10 min load/unload); cyno alts' positions aren't modelled.
- Orders sent before route data existed must be re-sent from Build planning.
- `findJumpRoute` scans every system for each expansion: memoized per route and range, but slow with many lanes/ranges.
- Gather items (Map): the order is nearest first then 2-opt, short but not proven shortest; with jumps it compares legs by fixed minutes (no fatigue, no economizers), and every pair of stops runs a jump route search (slow with many stops). With a hold, trips are cut from one tour (route first, then trips), not planned trip by trip; goods only go to the start; a hangar ship's hold is its bare cargo hold; assembled ships count at their packaged volume; containers, ship cargo and blueprint copies aren't picked up.
- Ideas: show the next trip on the To-Do page; play-hour windows per pilot; plan around jump bridges / Ansiblex.

## Build planning: ore instead of minerals
- Hauling in the ore choice is an estimate per m³ of compressed ore (a freight rate, or a JF round trip ÷ its hold); the real hauling is priced afterwards with the whole build.
- Your own ore is used only when it sits in a system where its minerals are used or in the delivery system; ore anywhere else is pointed out, not hauled from there. Reprocessing your own ore pays no tax in the plan (the refinery's tax isn't known).
- An uncompressed ore counts at its compressed form's volume: the plan assumes you compress it before hauling (it doesn't check who can).

## Profit and loss
- Broker fees aren't tied to an item by ESI (only to the order), so they follow their kind's activity, not the item's.
- A contract split needs every item priced in the chosen pricing.
- Ideas: cost of goods sold (profit per unit built using the build's material cost); actual profit per activity on the Forecast.

## Trading board (market browser)
- Every region is read item by item: about 70 market requests per item (ESI has no "all regions" order list). They share `esiMarket`'s budget, so browsing many items fast can make other pages' price reads wait.
- A player structure's name is only read when one of your pilots may dock there (else "Structure in <system>"), at most 10 new ones per item; a refusal is remembered for good (`state.misc.mbLoc`).
- Jumps are stargate jumps only (no jump bridges, no wormholes) and need the map loaded once; security too.
- Orders aren't kept: each item is read again after 5 minutes. History is ESI's per region; there's no all-regions history. PLEX's history before it moved to the global market stays in the old regions (pick one under History).
- Ideas: favourites / recently viewed items; "Open market in game" (`esi-ui.open_window.v1`); undercut warnings on your own orders (see Market orders below); sold per day for each trade hub in By market (one history read per hub region).

## Corporation and Intel
- Fuel per service module comes from CCP's game data; a service ESI names in a way the page doesn't know isn't counted (the total shows ≥). Hyasyoda labs and other faction modules count as the standard module.
- Moon mining and notifications are kept 90 days in this browser only (not in backups); a structure's name in a notification is only known for structures the tool already knows.
- Ideas: chunk times on the Overview's calendar; notifications as To-Do alerts (only the Intel tab counts them now); fuel blocks to buy on To-Do.

## Ideas from ESI (not built yet)
Suggested on 2026-10-20 (built since: Profit and loss; skill queues on Skills, To-Do and Fittings; Upcoming events; LP store; danger on the Map; server status; empty job slots on To-Do; market history on the Trading board and LP store; client deliveries; public contracts vs building; fleets on the calendar; moon mining, structure fuel and running costs (Corporation page); in-game notifications (Intel page); customs office taxes (PI Management and Planets)). Each new ESI read needs its scope added to `ESI_SCOPE` / `SCOPE_USE` (new scopes start unticked), to the user's application on developers.eveonline.com, and a new login for every pilot.
- **Market orders, what's left** (orders are read since Net worth: `c.orders`, `state.misc.corpOrders`): your orders against the Jita / citadel orders already read (undercut or not), order slots used vs the skill maximum, relist cost, order history (`/orders/history/`). Market menu.
- **Skill queues, what's left**: "when can this pilot build that blueprint" on the Skill check (`readyFor` does it for fittings); the same on Roles and the jump freighter table.
- **Public contracts, what's left**: a blueprint copy is only found by its title (every copy has the same volume); buy orders and a client's courier contracts aren't checked; contracts can't be opened in game from the page (needs `esi-ui.open_window.v1`).
- **Customs office taxes, what's left**: offices are only known per system (ESI gives no planet); offices of other corporations and standings-based rates aren't read (their tax stays unknown); a list of your offices with their reinforcement times (Corporation page).
- **Research agents** (`/characters/{id}/agents_research/`; `esi-characters.read_agents_research.v1`): datacores accumulating per agent and their value, as invention inputs.
- **LP store, what's left**: value blueprint copies as what they build (Build planning's cost), broker fees.
- **Danger on the Map, what's left**: jumps per system (`/universe/system_jumps/`, traffic); routes that avoid dangerous systems instead of only warning; the same warning on Build planning's hauling.
- **Buttons that act in game** (`/ui/autopilot/waypoint/`, `/ui/openwindow/marketdetails/`, `/ui/openwindow/contract/`; `esi-ui.write_waypoint.v1`, `esi-ui.open_window.v1`): "Set destination" on the next trip, "Open market" on shopping lists.
- Smaller: container names on Assets (see jEveAssets below), lost doctrine ships to replace in Shortages (`/characters/{id}/killmails/recent/`; `esi-killmails.read_killmails.v1`), insurance payouts on ships you build (`/insurance/prices/`).
- From data already read:
  - **Stock management** (the blank page): see Stockpiles (jEveAssets) below.
  - **Job history** (jobs with `include_completed`, already read for Profit and loss): how busy each pilot's slots were over the last 30 days and what was built (empty slots right now are on To-Do).
  - **Blueprint library** (owned blueprints): ME/TE, runs left on copies, which originals are worth researching (Blueprint calculator).
  - **Clone and implant planner** (clones and implants): which jump clone has the industry implants and where it is compared with your build structures.

## From jEveAssets (not built yet)
Features of jEveAssets (the Java asset manager) the tool doesn't have, or only partly. Compared on 2026-10-25; built since: Filters (custom filters), Net worth (tracker, with industry jobs and courier collateral), Contracts browser (all contracts across characters), Item database, market orders, Routing (Gather items on the Map).
- **Stockpiles** (jEveAssets: Stockpiles), on the blank Stock management page: a stock target per item (or a group of items) with a low-stock threshold, counted from assets, open market orders (buy orders still to fill), industry jobs (their products), stock reserved by Orders management and builds in progress → an alert and items to buy on To-Do, items to build to Build planning.
- **Container names** (jEveAssets: rename containers): your containers' and ships' names from ESI (`/characters/{id}/assets/names/`, `/corporations/{id}/assets/names/`), shown in Assets' "Hangar or place"; and a name of your own for any container, kept in this browser.
- **Exports** (jEveAssets: HTML, SQL and column-based exports): any table as CSV (the rows a table shows, after its filters and sort), copied or downloaded; maybe a printable HTML page.
- **Reprocessed values** (jEveAssets: Reprocessed tool): what any item (modules, ships, scrap) gives when reprocessed, at your best yield (the Item database already shows what an item reprocesses into, before yield), and its worth against the item's own price (reprocess or sell?) on Assets and the Item database.
- **Structures with unknown locations** (jEveAssets: structure hunt, edit locations by hand): set the system of a structure ESI won't name (no docking access), so its assets and contracts show where they are and count for hauling.
- **Filters, what's left** (jEveAssets: filters): a condition that compares two columns; a filter shared between tables.
- **Net worth, what's left** (jEveAssets: Tracker): per-owner days only from when owners were kept; days you never synced only have the wallets (from the journals); days are as good as what was read that day (hangars and orders at the last sync).
- **Contracts browser, what's left** (jEveAssets: Contracts): auction bids (`/contracts/{id}/bids/`); contracts older than ESI's 30 days only exist here if a sync saw them; open a contract in game (`esi-ui.open_window.v1`).
- **Market orders tool** (jEveAssets: Market Orders): see "Market orders, what's left" above (undercut, order slots, relist cost, history).
- **Item database, what's left** (jEveAssets: Items): names in English only; several items side by side.

## Data and other limits
- EVE Ref is now only a fallback (game data lookups, map, reaction formulas). Prices come from ESI; `esiNames` too. `resolveIds` (name → type ID) answers from CCP's static data (`ccpNames`) and only asks ESI about leftovers (max 100 characters a name, else ESI refuses the whole request).
- Jita prices: every market read now shares one budget (`esiMarket`), so several big builds in a row wait instead of being refused; one still refused keeps its last price and is read again ~2 minutes later. The budget is per tab (ESI's rate-limit headers, when its CORS lets the page read them, bring in other tabs' use).
- Fittings added before the Doctrine feature only kept hull/modules/drones (no cargo, no quantities): re-add them for a full check.
- Supplier links other than Google Sheets need the launcher's `/proxy`.
- Stock management page is a blank placeholder.
- EvE News channels: the launcher feed is English only.

## Layout
- Tables with one column per pilot (Skill matrix, Key skills, Jump freighters) scroll sideways inside their box (first column stays put). Build planning's "Who builds what" (9 columns, two dropdowns) does too below about 1366 px wide.
- Table headers wrap onto two lines when a table runs short of room (e.g. "Unit / price" on Assets).

## Testing
- `tests/e2e_smoke.py` runs independent scenarios with assertions; pages still without one: Assets filters, Orders management (reopen, status), Market watch (only its history columns), Prices' import calculator, Suppliers' page, Omega, Wallets, the Jobs calendar, Ships you can build, Roles.
- The layout audit (`AUDIT=1`) prints what doesn't fit but doesn't fail.
