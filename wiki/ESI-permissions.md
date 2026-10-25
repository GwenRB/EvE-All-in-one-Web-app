<!-- tracks: permission, scope, ESI_SCOPE, roles -->

Every page only needs the permissions it reads. Tick only what you use; you can add more later (tick it in **Link EVE characters**, add it to your EVE application, and log each pilot in again).

Some corporation data also needs an **in-game role** on at least one linked pilot. When nobody has it, that part of the page stays empty.

| Permission (scope) | What it's for | Role needed |
|---|---|---|
| `esi-skills.read_skills.v1` | Skills (always on) | |
| `esi-skills.read_skillqueue.v1` | Skill queues: when training ends, time to fly a fitting, "skill queues to fill" on To-Do | |
| `esi-clones.read_implants.v1` | Implants (exact training times) | |
| `esi-clones.read_clones.v1` | Jump clones (on the map, and for changing ships in the supply chain) | |
| `esi-industry.read_character_jobs.v1` | Industry jobs | |
| `esi-industry.read_corporation_jobs.v1` | Corporation jobs | Factory Manager |
| `esi-characters.read_blueprints.v1` | Blueprints owned | |
| `esi-corporations.read_blueprints.v1` | Corporation blueprints | Director |
| `esi-planets.manage_planets.v1` | Planets (your colonies) | |
| `esi-planets.read_customs_offices.v1` | Your corporation's customs offices and their tax | Director |
| `esi-assets.read_assets.v1` | Personal hangars | |
| `esi-assets.read_corporation_assets.v1` | Corporation hangars | Director |
| `esi-corporations.read_divisions.v1` | Hangar and wallet division names | Director |
| `esi-wallet.read_character_wallet.v1` | Wallets, Profit and loss | |
| `esi-wallet.read_corporation_wallets.v1` | Corporation wallets, Profit and loss | Accountant |
| `esi-contracts.read_character_contracts.v1` | Contracts (ongoing contracts, in-game deliveries, Profit and loss, Assets search) | |
| `esi-contracts.read_corporation_contracts.v1` | Corporation contracts | |
| `esi-universe.read_structures.v1` | Structure names | |
| `esi-search.search_structures.v1` | Find citadels by name | |
| `esi-corporations.read_structures.v1` | Corporation structures and fuel | Station Manager |
| `esi-markets.structure_markets.v1` | Citadel markets (prices) | |
| `esi-characters.read_standings.v1` | Standings (broker fees) | |
| `esi-fittings.read_fittings.v1` | Fittings saved in game | |
| `esi-characters.read_fatigue.v1` | Jump fatigue | |
| `esi-location.read_location.v1` | Character location (supply chain: where ships are) | |
| `esi-location.read_ship_type.v1` | Current ship (supply chain) | |
| `esi-calendar.read_calendar_events.v1` | Calendar (upcoming events on the Overview) | |
| `esi-characters.read_loyalty.v1` | Loyalty points (LP store) | |
| `esi-industry.read_corporation_mining.v1` | Corporation moon mining | Station Manager (extractions), Accountant (who mined what) |
| `esi-industry.read_character_mining.v1` | Your pilots' mining ledger | |
| `esi-characters.read_notifications.v1` | In-game notifications (Intel) | |

The same list, with a short note per line, is in the tool under **Link EVE characters**. That list is always the up-to-date one.

## Safety
- The login uses EVE's official sign-in. Your login tokens stay in your browser and are **never** put in backups.
- The tool only reads. None of these permissions lets it change anything in game.
- Never paste your application's secret key anywhere: the tool only needs the Client ID.
