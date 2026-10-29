<!-- tracks: Misc, Blueprint library, blueprint copies, Location filter, Blueprint calculator, Jump freighters and Rorqual, Jump fuel cost, Mining fleet, Ships and structures you can build, Quotation, Wallets, attribute boosters, cerebral accelerators, Biology -->

**Other → Misc.** Calculators and lists. Use the left navigation to jump between them.

## Blueprint calculator
What researching a blueprint's material efficiency (ME) further saves, what the research costs, and how many runs pay it back.
1. Search a blueprint, set **Current ME** and **Target ME**.
2. **Research in** (system, **Facility tax %**), **Materials at** (a pricing), **Built in** (where you'd build).
3. **Calculate.**

## Jump freighters and Rorqual
Who can fly each jump freighter and the Rorqual. Each cell is the training time, prerequisites included (~ means default attributes until the next sync). Hover a cell for the skills.

## Jump fuel cost
ISK per light year for each pilot who can fly a jump freighter or the Rorqual, cheapest first, with their Jump Fuel Conservation and Jump Drive Calibration. Isotopes are priced in a pricing you choose, or a price you type (which then wins everywhere, the map and supply chain included). Also ISK per m³ carried.

## Mining fleet
Pick a barge or exhumer, strip miners and crystal: who can fly it and roughly how much ore (or ice) each mines per hour. Boosts, implants and critical yields aren't counted.

## Ships and structures you can build
Every ship and Upwell structure with a manufacturing blueprint, checked against your whole roster: **Fully buildable**, **Can do last build**, **Missing skills**; filter by name and tech level, or with [Filters](The-basics#filters) (class, race, build steps not covered, who can do it all…).
- **Scan ships and structures** the first time (a few thousand requests, sent slowly). It's kept in your browser and in backups; use **Rescan** after a game patch.

## Quotation
What it costs to build something and what to ask for it.
1. Search a blueprint, set the **Quantity**.
2. **Margin %**: of the selling price, or on top of the cost (markup).
3. **Get the cost.**

Structures and hauling are the ones set in [Build planning](Build-planning#structures-and-settings).

## Wallets
All the ISK your pilots and corporation hold, and who holds it. Corporation divisions need one pilot with the Accountant role.

## Attribute boosters
Every booster that adds to your attributes (cerebral accelerators), from CCP's own game data, and what each costs for the training it gives. (It used to be on the Tests page.)
1. Pick **Buy at**: one of your [pricings](Pricings), or a trade hub or citadel market (the cheapest sell order there).
2. Pick **Biology**: each level makes boosters last 20% longer. By default, your best pilot's level; the list shows who has each level.
3. **Refresh prices** reads the prices again.

The tiles show the **best for each attribute**: the booster with the least ISK a month for each point it adds to that attribute.

Per booster:
- **Attributes:** what it adds (+N to all, or per attribute).
- **Lasts:** its duration with your Biology level.
- **ISK a month:** what keeping one running for 30 days costs (a new one injected each time one runs out).
- **Extra SP a month:** what a skill gains over those 30 days when its two attributes are the ones the booster adds most to.
- **ISK per SP:** what each extra skill point costs. The cheapest come first.

A **⚠ Expires** tag means it can't be injected after that date. Expired boosters are listed apart, without a price. Boosters with no market group can only be traded by contract, so they have no price. A booster with no price shows no figures (never 0).

## Blueprint library
Every blueprint your pilots and corporations own, with its research levels (it used to be on the Tests page). It needs the **Blueprints** permission (and **Corporation blueprints**, with the Director role, for your corporation's): see [ESI permissions](ESI-permissions). It follows each ESI sync.

The tiles count your originals, those in research, those copying (and when the next one is done) and your copies (and their runs).

The table has four groups (click a group's title to fold it):
- **In research:** the ME or TE research job, the level it will reach (ME 5 → 8) and when it ends. **Ready** means the job is done and waits to be delivered.
- **Copying:** how many copies and their runs (4 copies × 10 runs), and when it ends.
- **Not in a job:** the other originals, A→Z.
- **Copies:** every copy, one line per blueprint, ME, TE, runs and owner, with how many (× 2). Copies show the copy icon (the lighter one).

When the pilot running a job isn't the owner (a corporation blueprint), their name shows after the job. A job whose blueprint isn't in the list still shows, without its levels. Copying jobs show the runs of each copy after the next sync.

Type in **Find a blueprint** to filter the table. **Location** shows only the blueprints kept in one station or structure (with how many in each); the tiles follow it. A blueprint in a container, a ship or a corporation office counts where that container is (read from your hangars, so allow **Assets** too). Until the next ESI refresh, blueprints read before show as **Unknown: refresh from ESI**.
