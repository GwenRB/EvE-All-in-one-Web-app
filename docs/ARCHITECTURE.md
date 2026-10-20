# Architecture

Everything is in `EVE Industry Management.html`: `<style>` (theme tokens on `:root`, light/dark), the page markup (one `<div id="page-…" class="page">` per page), then one `<script>`.

## Code map
Line numbers drift; grep the section markers (`/* ---------- … */` or `// ---------- …`). In file order:

| Marker | What |
|---|---|
| `helpers` | `$`, `esc`, `toast`, small utilities |
| `storage` | `saveLocal`, the `store` API for characters, `exportBackup` / `importBackup` |
| `derived industry numbers` / `render` / `events` | pilot cards (Characters page), slot counts, skill matrix |
| `blueprints` | Skill check: who can build/invent a blueprint (`REF` = EVE Ref base URL) |
| `key skills page` | Skills page panels |
| `pages` | `PAGES` (tab key → URL hash), `showPage(tab)` hooks, tab menus (`tabGroupsSync`, `tabMenusClose`), `hiddenTabs` |
| `Import calculator (Prices page)` | import calculator, price comparison, arbitrage (arbitrage panel now sits on the Trading board page) |
| `Contract management` | client orders, sends, remembered clients (`cmRemember`) |
| `Suppliers` | supplier stock lists (Google Sheets, links via `/proxy`, paste) and `supplierPrice` |
| `Orders management` | builds sent from Build planning: `sendToOrders`, `orderRoute` (moves + timing for the supply chain), snapshots in IndexedDB (`orderSnap`, `viewOrder`) |
| `Trading board` | market watch tables (`boardPrices`) |
| `Reactions management` | CCP static data loader (`sdeFetch`, `sdeZip`, `zipEntries`, `zipLines`, `rxFromSde`, EVE Ref fallback), `rxCfg` (v4), `rxEnv`, `rxInstShape`, `rxPlan`, `rxHaulEnsure/Cost`, renderers `renderRx*` |
| `PI Management` | P4 planner: `PI_*` tables, recipes from the static data (`piRecipesLoad`, `piSchemParse`, `piRecipesApply`), `piCfg` (v2), `piPlanet`, `piPortfolio`, `piNeeds`, `piWeekly` |
| `ESI link` | EVE SSO with PKCE (no secret), tokens in localStorage, `ESI_SCOPE` / `SCOPE_USE` (new scopes start unticked; the user must add them to their ESI application), per-character sync |
| `characters page`, `ships page`, `jobs page`, `planets page`, `wallets page` | as named; `planetFinish` = when a colony stops |
| `fittings page` | EFT parse (`parseEft`), `addFit` (skills + `contents` with quantities), ESI fittings import, Doctrine flag |
| `Shortages` | doctrine shortages against a citadel market (`renderDoctrines`, `docRefresh`) |
| `omega page`, `forecast page`, `combined calendar` | Omega dates, Forecast (activities, chart, linked activities `syncRxActivity` / `syncPiActivity`), jobs calendar |
| `contracts` | contract valuation for the Forecast |
| `stock (hangars)` | Assets page, `stockByType`, stock valuation `stockPrice`, ore reprocessing value |
| `training time` | skill training estimates |
| `misc: jump freighters and mining fleet` | ship type data (`miscTypes`, `state.misc.types`), `JFS`, `haulCapacity`, `jumpFuel`, `isoPrice`, mining fleet |
| `citadels` | known structures (`state.misc.structs`, friendly/indy imports), citadel markets |
| `map` | map data (`loadMapData`, `mapIndex`, `lyBetween`), drawing (`drawMap`, `mapUI`), info panel; `mapUI.haul` = routes to draw (arrays of system ids, or `{ids, color, dash, label}`) |
| `jump planner` | `jumpable`, `findJumpRoute`, `jumpAnchor`, `fatigueNow`, `simulateJumps`, `optimizeWaits`, `planJumps` |
| `owned blueprints` | `ownedBps()` (BPO/BPC, ME/TE, runs) |
| `production engine` | Build planning + Quotation: `STRUCTS`/`RSTRUCTS`, rigs (`parseRig`, `rigInfo`, `rigsFor`, `rigBonus`, `loadRigData`, laboratory rigs `parseSciRig`/`sciBonus`), `buildCfg`, invention (`inventionPlan`, `invAttempts`, `DECRYPTORS`), `computeBuild`, pricing (`priceIn`, `pricesIn`, `ensurePrices`, `buyPrices`, `noPriceNote`, `structOrders`), `computeHaul`, `haulItinerary`, `moveRoute`, `gatePath`, job assignment and timeline (`assignJobs`, `scheduleParts`, `sciParts`, `timelineSvg`), `renderBuild`, Blueprint calculator (`renderBpCalc`, `runBpCalc`) |
| `Supply chain` | logistics planner on the Map page (`scCarriers`, `scMoves`, `scRoute`, `scLeg`, `scPlan`, `renderSupply`, `scShowOnMap`) |
| `roles` | roles (ships/fittings/skills) and who can fill them |
| `boot` | first render, tab visibility, initial page from the URL hash |

## State and storage
- `state` (global): `chars` (skills, ESI data per character: jobs, planets, wallet, clones, fatigue, `loc`, `ship`…), `misc` (most feature settings), `forecast`, `fits`, `assets`, `contracts`, `typeNames` / `typeMeta` / `locNames` caches, `roles`…
- localStorage keys (all `eve-industry-*`): `roster` (characters), `misc`, `forecast`, `fits`, `assets`, `contracts`, `jita` (Jita price cache), `esi-tokens`, `esi-client`, `scopes-on/-off/-seen`, `notes`, `roles`, `ships`, `bp-*`, `cal-colors`, `corp-*`…
- IndexedDB (`idb.get/set`): the map data, Build planning snapshots of orders (`order:<id>`).
- `state.misc` namespaces worth knowing: `build` (Build planning settings, via `buildCfg()`), `rxn` (+ `rxnData` formulas from the static data), `pi` (+ `piSchem` recipes, `piHist`, `piVol`), `pricings` (custom pricings), `orders`, `sc` (supply chain: max wait, done moves, per-pilot ship/position), `doctrine`, `structs` / `indy` / `friendly` (structures), `rigData` (v2: manufacturing/reaction rigs in `list`, laboratory rigs in `sci`), `types` (ship data), `map`, `hiddenTabs`.

## Shared systems (reuse them)
- **Pricing** (Settings → Pricings): base modes `jbv`, `split`, `jsv` (Jita 4-4 from ESI orders, `jitaFetch` → `jitaCache[t] = {p: sell, b: buy}`) plus custom pricings `p:<id>`: a % of another pricing, or a citadel's market (`kind: "cit"`, `sid`, `side`). Use `priceIn(id, t)` (sync, null when unknown), `pricesIn(ids, id)` / `ensurePrices` (async), `pricingOptions(cur, attrs)` for selects, `validPricing`, `pricingName`. A citadel that can't be read is recorded in `citErr`. Show missing prices with `noPriceNote(pricingId, items, what)`.
- **Structures and rigs:** `STRUCTS` (role bonuses), `rigBonus(st, "me"|"te", recipe, isReaction, sec)` with real rig data from EVE Ref (security multipliers hi/lo/null), `sciBonus(st, "inv"|"copy", sec)` for laboratory rigs.
- **Systems:** `industrySystem(name)` → `{id, name, sec, idx}` (cost indices from ESI), `mapIndex()` → `{byId, byName}` of map systems (`s.n` name, `s.s` security, `x/y/z`).
- **Hauling:** jump freighters / Rorquals (`JFS`, `haulCapacity`, `jumpFuel`, `isoPrice`) or a freight service (ISK/m³ + collateral). `computeHaul(resStub)` prices round trips from a delivery system (used by Reactions, PI and Build planning). Routes: `jumpAnchor` + `gatePath` for high-sec ends, `findJumpRoute(from, to, range, jumpable)` (note: O(systems²), memoize).
- **Static data:** `sdeBuild()` reads the current build number; `sdeZip(build)` downloads the static data zip once per session (shared by Reactions and PI); `zipLines(entry, onLine)` streams a `.jsonl` file out of it.
- **Formatting:** `isk`, `iskFull`, `fmtDur(seconds)`, `fmtDate(ms)`, `ago(ms)`, `icon(typeId)`, `iconBp`.
- **Copy buttons:** any element with `data-copy="text"` (+ `data-copy-msg`) copies on click; classes `cargo` / `copyname` style them.

## External services
- ESI `https://esi.evetech.net` (public + authenticated, `esiGet`, `esiAuthGet`, `fetchRetry`), SSO `login.eveonline.com`.
- CCP static data `https://developers.eveonline.com/static-data/…` (via `/proxy` when CORS blocks).
- EVE Ref `https://ref-data.everef.net` (types, blueprints, dogma, market groups).
- Images `images.evetech.net`; overview bracket icons from the EVE University wiki.
