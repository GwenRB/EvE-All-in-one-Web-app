# Features and agreed rules

Tab bar: **Forecast · To-Do · Map · Industry ▾ (PI Management, Reactions management, Build planning, Orders management, Jobs) · Planets · Market ▾ (Prices, Trading board, Suppliers, Contract management, Shortages) · Stock ▾ (Assets, Stock management) · Pilots ▾ (Characters, Skills, Omega, Fittings) · Tools ▾ (Misc) · Settings · Notes**. Menus open on hover or click; the menu holding the open page shows its name. Pages can be hidden in Settings (Settings always stays).

## Overview
- **Forecast** — left nav; ISK and Omega lines split; clickable legend hides a line *and* removes it from totals; profit per month after Omega; activities (manual weekly incomes) plus linked ones: "Reactions plan" (`linked: "rx"`) and "PI plan" (`linked: "pi"`) kept up to date from those pages (deleting sets `rxGone`/`piGone`; the pages offer "Add to the Forecast" again). A linked plan with items that have no price doesn't update its line. Calendar of jobs (manufacturing, reactions, copying, invention, research; legend click hides a type, swatch click changes its colour; month starts drawn bold). EvE News panel (blank, wide-screen rail).
- **To-Do** — Omega to renew (7 days ahead), ongoing contracts, buy for reactions, buy for builds (orders).
- **Map** — 3D/2D map, security/sov colouring, structures with their real icons, PI icon, capital ships (freighters hidden, jump freighters shown) with overview bracket icons, clones, homes, incursions; jump planner (fatigue-optimised waits); **Supply chain** (below).

## Industry
- **Build planning** — full build tree, each job placed in the cheapest manufacturing structure (role bonus + best rig via `rigBonus`), reactions in the refinery, invention for T2/T3 (see below), stock use (assets, ore reprocessing, components owned, stock reserved by ongoing orders), "where to buy" (Jita, local citadel market, suppliers) with copy buttons per source, hauling (JF round trips or freight), timeline with pilots and slots (invention counted when no copies are held), left nav. Sends a build to Orders management (with its route data for the supply chain).
  - **Invention:** all sources read (T3: every relic with its own chance/runs/price; relic choice auto or forced); chance = base × (1 + science/30 + encryption/40) × decryptor; only the runs your copies don't cover are invented (mixed copies: the lower ME is counted); decryptors compared on invention cost + material effect (final job's materials where it would be built) + optional value of build time saved (ISK/hour setting); decryptors with no price aren't offered; attempts on average or enough to be 75/90/95 % sure (binomial); laboratory rigs (time and cost) on the science structure; copy and invention jobs spread over science slots in the timeline.
- **Reactions management** — static data formulas (composites, Molecular-Forged, Isotropic neofullerenes / Neurolink by name; intermediates are planned, not offered); kinds as collapsible groups; column-header sorting; balanced-chain instances (one feeding slot usually feeds 2 composite jobs); rigs like Build planning; selling by contract / immediate / sell order; import and export hauling separately, delivery ⇄ reactor runs priced like Build planning; shopping after assets (scope: every hangar or the build system); step 4 React has a **Build-up phase / Full chain** switch and click counters for jobs started; every job of a reaction runs the same number of runs, rounded up ("4 × 123"). Profit per week → Forecast.
- **PI Management (P4 planner)** — recipes from CCP's planet schematics (built-in table as fallback: P3 = 10 of each P2 → 3 per hour; P4 = 6 of each P3 (+ 40 P1) → 1 per hour); P4s grouped "P1 + two P3" / "three P3"; shared pricings; transport delivery ⇄ planets (JF or freight) and optional Jita import/export legs; shopping for N days of stock after assets; output and per-planet drop-off batches; Jita volume share warning; profit per week → Forecast.
- **Orders management** — orders with status planned / in progress (sets `startedAt`) / done; materials, components, ore, costs (missing prices flagged); reopen the exact plan; "Account for ongoing orders" in Build planning reserves their stock.
- **Jobs** — industry jobs per pilot, 30-day planning calendar.

## Planets
Colonies of every linked pilot, ordered by when they stop (extractor end or an input running out).

## Market
- **Prices** — import calculator (delivery vs buying station, hauling), price comparison (citadel vs another market, by item/group/category).
- **Trading board** — market watch tables (history columns fill as you refresh; past history isn't fetched) and **Arbitrage** (citadel sell orders → other market).
- **Suppliers** — supplier stock from a link or paste, priced as listed or a % of a pricing.
- **Contract management** — client orders, sends, what's missing; the client box remembers past clients.
- **Shortages** — **Doctrine shortages**: fittings marked Doctrine checked against a chosen citadel's sell orders; empty items (nobody sells), low items (under the fits to keep, set per doctrine), full fits on sale, items to seed with a multibuy copy.

## Stock
- **Assets** — personal and corporation hangars, filters, valuation in a chosen pricing (items with no price shown empty and listed), totals of the filtered items.
- **Stock management** — blank placeholder.

## Pilots
- **Characters** — implants, pilot cards (slots, ranges, manufacturing time, **Reactions level**, reprocessing, orders…), roles.
- **Skills** — skill check per blueprint (who can build/invent), key skills, skill matrix.
- **Omega** — Omega dates.
- **Fittings** — paste EFT or import in-game fittings (ESI); who can fly it; **Doctrine** tick box.

## Tools, Settings
- **Misc** — Blueprint calculator (ME research cost/time, savings in a chosen building place, breakeven), jump freighters and Rorqual, jump fuel cost, mining fleet, ships and structures you can build, Quotation, Wallets (last).
- **Settings** — Pilots and backup (Add pilot, Export/Import backup), page visibility, Pricings, ore reprocessing yield, market taxes (skills/standings), jump drive economizers, citadels/structures imports.

## Supply chain (Map page)
- **Carriers:** one per pilot who can fly a JF or Rorqual: ship flown now (ESI location + ship type scopes) or docked in assets, or set by hand (manual position wins until a newer ESI read); range with JDC, hold with skills/expanders, fatigue from ESI.
- **Moves:** orders (from `o.route`: materials D→structure, components between structures, product → D; ready/need offsets from the plan's timeline; planned orders have no deadlines, in-progress orders do, from `startedAt`; ESI job end times override readiness), reactions (inputs before the next cycle, products at cycle end, only if reactor ≠ delivery system), PI (inputs before planets stop, P4 pickup then). Done trips are tracked as fractions per move (`state.misc.sc.done`).
- **Planning:** same-lane moves ready within "hold goods at most N hours" and fitting the largest hold become one trip (oversized moves split); trips in ready order go to the carrier finishing first (reposition just in time, then load 10 min, gates 1.5 min, jumps 3 min + activation timers/fatigue via `simulateJumps`); cynos assumed everywhere (user's choice); lateness flagged against need times. Map shows each pilot's trips in its colour (dashed = repositioning).
- **User decisions recorded:** positions = ESI + manual override; batching = balance with a max wait; cynos = any of the user's systems; trips can start any time (no play-hour windows).
