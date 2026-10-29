<!-- tracks: Build planning, Materials needed, invention, decryptor, relic, ore instead of minerals, reprocessing, refinery, left-over, Public contracts, Timeline, Who builds what, Structures and settings, Quotation -->

**Industry → Build planning.** Pick a blueprint and a quantity; the page works out the whole build: every component and reaction, what to buy and where, who runs each job, the hauling, and a timeline.

## Plan a build
1. Type a blueprint in the search box (for example *Sleipnir Blueprint*) and a **Quantity**.
2. Click **Plan the build**.
3. Read the result top to bottom, using the left navigation:
   - **Materials needed**: the summary of everything the build uses: each raw material (needed, from your stock, still to buy) and the components built on the way, each split into the items' groups (Mineral, Moon materials, Composite…). **Copy raw materials** copies the full list.
   - **Final build** and **Components to manufacture**: the build tree. Switch any component between **build** and **buy**.
   - **Materials you already own**, **Components you already own**: your stock is used first (from [Assets](Assets)).
   - **Materials to buy**: with where to buy each (Jita, a local citadel market, your [suppliers](Suppliers)) and a copy button per source, ready to paste in game.
   - **Invention** (T2/T3): see below.
   - **Hauling trips** or **Hauling by freight service**.
   - **Timeline**, **Who builds what**, **Per pilot**: jobs spread over your pilots' free slots, given their skills and speed. Change the pilot of a job in the table.
   - **Public contracts** and **Build or buy**: see below.
4. Happy with it? **Send to Orders management** to commit to it (see [Orders management](Orders-management-and-Jobs)).

## Structures and settings
The panel at the bottom: where you build, the rigs fitted, how materials are moved, how blueprints and prices are counted. It's shared with the **Quotation** on the [Misc](Misc) page. **Reset structures and settings** goes back to the defaults.

- Each job goes to your **cheapest structure** for it: the structure's role bonus plus its best rig. Reactions go to the refinery.
- Structures come from the **Citadels** panel on the Map (see [Map and jump planner](Map-and-jump-planner#citadels)): add yours there with their rigs.
- **Hauling:** jump freighter round trips or a freight service rate.
- **Keep what ongoing orders need:** stock already reserved by your ongoing orders isn't offered to this build (the plan says how many items it kept back).

## Invention (T2 and T3)
- Every source is read; for T3, every relic with its own chance, runs and price (pick one, or let the page choose).
- **Chance** = base × (1 + science levels ÷ 30 + encryption level ÷ 40) × decryptor.
- Only the runs your copies don't cover are invented.
- **Decryptors** are compared on invention cost + the material effect + (optionally) the build time saved, at an ISK per hour you set. Decryptors without a price aren't offered.
- **Attempts:** on average, or enough to be 75 / 90 / 95 % sure of getting the copies.
- Laboratory rigs count on the science structure; copy and invention jobs go in the timeline.

## Ore instead of minerals (optional, off by default)
Buys ore and reprocesses it when that's cheaper than buying the minerals.
1. Turn on **Ore instead of minerals**.
2. Add your **reprocessing places**: a known refinery, or a type (Tatara, Athanor, NPC station, other structure), its **Reprocessing rig**, **System** (for the security bonus) and **Tax %**.
3. Pick the **Pilot**: the best one for each ore, or one pilot.

The page then finds the cheapest mix of ore and minerals for what the build still needs, using every place at once (each ore goes where it comes out cheapest). Good to know:
- Compressed ore only, by default. All ore is **hauled compressed**.
- Ore is rounded up to whole batches, and only kept when it costs less than the minerals it replaces.
- **Left-over minerals** count at what buying them would cost and come off the build cost. Ore is never bought just for its left-overs.
- **Your own ore** is reprocessed in the system where its minerals are used, at your best refinery there, by your best pilot. If no refinery is known in that system, the plan warns **"No refinery detected"** and doesn't use that ore.
- The **Ore to buy** section shows the places, the mix, yields, left-overs and what you save in ISK and m³.

## Public contracts: build or buy?
**Public contracts** reads the item exchanges in a trade hub's region (on demand, kept 30 minutes). Only contracts holding that item alone, and asking nothing in return, count. The page tells you whether **buying on contracts beats building** (per unit, everything the plan counts), and for invention, **blueprint copies vs inventing**. Unknown when the build has items without a price.
