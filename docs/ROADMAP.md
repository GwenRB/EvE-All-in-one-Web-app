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
- Ideas: show the next trip on the To-Do page; play-hour windows per pilot; plan around jump bridges / Ansiblex.

## Build planning: ore instead of minerals
- The ore mix is chosen for the minerals the build needs; left-overs only count afterwards (at their buy price), so an ore whose by-products would be worth more isn't preferred for them.
- Hauling in the ore choice is an estimate per m³ (a freight rate, or a JF round trip ÷ its hold); the real hauling is priced afterwards with the whole build.
- Your own ore in hangars still uses the yield set in Settings (not the reprocessing places).

## Profit and loss
- History only exists from the first read (ESI keeps 30 days); a month without any sync leaves a gap.
- Broker fees aren't tied to an item by ESI (only to the order), so they follow their kind's activity, not the item's.
- Contract items are only readable while ESI still shows the contract (about 30 days): older contracts stay whole. A split needs every item priced in the chosen pricing.
- Ideas: cost of goods sold (profit per unit built using the build's material cost); actual profit per activity on the Forecast.

## Ideas from ESI (not built yet)
Suggested on 2026-10-20 (Profit and loss was the first one built). Each new ESI read needs its scope added to `ESI_SCOPE` / `SCOPE_USE` (new scopes start unticked), to the user's application on developers.eveonline.com, and a new login for every pilot.
- **Market orders** (`/characters/{id}/orders/`, `/orders/history/`, corporation orders; `esi-markets.read_character_orders.v1`, `esi-markets.read_corporation_orders.v1`): your orders against the Jita / citadel orders already read (undercut or not), order slots used vs the skill maximum, relist cost. Market menu.
- **Market history** (`/markets/{region}/history/`, already read for The Forge): fill the Trading board's 24 h / 7 days columns at once (13 months of daily volume and prices) instead of waiting for refreshes; sales-speed checks for the PI volume share warning.
- **Upcoming fleets** (`/characters/{id}/calendar/`, `/calendar/{event_id}/`; `esi-calendar.read_calendar_events.v1`): fill the blank panel on the Overview with in-game calendar events.
- **Skill queues** (`/characters/{id}/skillqueue/`; `esi-skills.read_skillqueue.v1`): queue end per pilot, an empty queue on To-Do, "when can this pilot build that blueprint" on Skills.
- **In-game notifications** (`/characters/{id}/notifications/`; `esi-characters.read_notifications.v1`): structure low fuel / attacked / reinforced, moon chunk ready, war declared, contracts, as To-Do alerts.
- **Moon mining** (`/corporation/{id}/mining/extractions/`, `/mining/observers/`, `/characters/{id}/mining/`; `esi-industry.read_corporation_mining.v1`, `esi-industry.read_character_mining.v1`): chunk times on the calendar, who mined what and its value, mined ore as stock for Reactions and Build planning.
- **Structure fuel and running costs** (`fuel_expires` is already read): fuel blocks per day from the service modules, ISK per month, a refuel warning on To-Do.
- **Contracts beyond Profit and loss** (`/contracts/{id}/items/` is now read): check client deliveries in Contract management; public contracts (`/contracts/public/{region}/`) to show when buying a blueprint copy or ship beats building it.
- **Customs office taxes** (`/corporations/{id}/customs_offices/`; `esi-planets.read_customs_offices.v1`): the real tax per planet in the PI planner's costs.
- **Research agents** (`/characters/{id}/agents_research/`; `esi-characters.read_agents_research.v1`): datacores accumulating per agent and their value, as invention inputs.
- **LP store calculator** (`/characters/{id}/loyalty/points/`, `/loyalty/stores/{corp}/offers/`; `esi-characters.read_loyalty.v1`): ISK per LP for each offer in your pricings.
- **Danger on the Map** (`/universe/system_kills/`, `/universe/system_jumps/`, public): ships and pods killed in the last hour per system; supply chain gate legs warn when they cross a dangerous system.
- **Buttons that act in game** (`/ui/autopilot/waypoint/`, `/ui/openwindow/marketdetails/`, `/ui/openwindow/contract/`; `esi-ui.write_waypoint.v1`, `esi-ui.open_window.v1`): "Set destination" on the next trip, "Open market" on shopping lists.
- **Server status** (`/status/`, public): online / players in the header; no refreshes during downtime.
- Smaller: container names on Assets (`/assets/names/`), lost doctrine ships to replace in Shortages (`/characters/{id}/killmails/recent/`; `esi-killmails.read_killmails.v1`), insurance payouts on ships you build (`/insurance/prices/`).
- From data already read:
  - **Stock management** (the blank page): a stock target per item against assets, open orders, stock reserved by orders and builds in progress → items to buy on To-Do, items to build to Build planning.
  - **Idle slots and job history** (jobs with `include_completed`, already read for Profit and loss): how busy each pilot's slots were, what was built in the last 30 days, idle manufacturing / reaction slots on To-Do.
  - **Blueprint library** (owned blueprints): ME/TE, runs left on copies, which originals are worth researching (Blueprint calculator).
  - **Clone and implant planner** (clones and implants): which jump clone has the industry implants and where it is compared with your build structures.

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
- `tests/e2e_smoke.py` runs independent scenarios with assertions; pages still without one: Assets filters, Orders management (reopen, status), Trading board, Prices' import calculator, Suppliers' page, Omega, Wallets, the Jobs calendar, Ships you can build, Roles.
- The layout audit (`AUDIT=1`) prints what doesn't fit but doesn't fail.
