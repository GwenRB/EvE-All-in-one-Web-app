<!-- tracks: Map, jump planner, Gather items, kills, danger, Citadels, structures, sovereignty, incursions, markers, legend, hover -->

The **Map** tab holds the map of New Eden, the jump planner, Gather items, the [Supply chain](Supply-chain), and your list of citadels.

## The map
- **3D** (the real layout, seen from above) or **2D** (the game's schematic map): **Switch to 2D map**.
- Scroll to zoom, drag to move, **click a system** for its details. **Find a system** jumps to it; **Reset view** goes back.
- **Colour by** security or sovereignty. Add alliances under **Allies**: their space shows in dark blue.
- **Markers:** your pilots' last location (cyan ticks around the system's dot; needs the **Character location** permission, read at each sync; hover or click the system to see who is there, docked or in space, and when they were seen; the **Pilots** tick box hides them), your citadels (a gold diamond under the system's dot), friendly structures (a hollow pale diamond), stations with your hangar stock, planet systems, capital ships (the game's overview brackets; jump freighters shown, freighters hidden), jump clones, homes, incursions. The map, its legend, the selected system's panel and the hover box all use the same icons and colours. **Click a line of the legend** to hide those markers (it's struck out) and again to show them; the tick boxes above the map do the same.
- **Jump range:** pick a system in **Jump from** and a **Range** to see what's in reach. High-sec can't be jumped into, so it's never highlighted.

### Kills in the last hour
Read every 10 minutes while the Map is open. Each system with kills gets a ring that grows with ships and pods killed. It turns red from **Danger from N kills** (default 5). Click the system for ships, pods and NPCs killed.

## Jump planner
Plans a capital jump route that waits out jump fatigue in the best places.
1. **From** and **To**: two systems.
2. **Ship**, **Jump Drive Calibration** level, **Economizers**.
3. **Citadels:** don't care, prefer stops where the ship can dock, or only stop where it can dock.
4. **Trip:** one way or round trips.
5. **Current fatigue:** type it, or **Read now** from ESI (needs the Jump fatigue permission).
6. **Plan route.**

Fatigue follows the game's rules: after a jump, fatigue = max(10, F) × (1 + ly), up to 300 min; the jump timer = max(1 + ly, F ÷ 10), up to 30 min.

## Gather items
Plans a trip through the gates to collect items spread over several systems. It's under the Jump planner.
1. **Items:** type an item that's in your hangars (the list suggests them), then **Add**. **Stations:** pick a station or structure to empty from the dropdown (grouped by system, with how many items it holds): everything your hangars hold there is picked up. Use either or both, as many as you like; ✕ removes one.
2. **From:** the system you start in.
3. Tick **Back to the start** if you come home afterwards.
4. **Security:** tick the security levels you'll fly in (high-sec, low-sec, null-sec). Items in the others are listed and left out, and the route never passes through them. The start system always counts.
5. **Travel:** **Gates only**, or **Gates and jumps** with the ship chosen under **Range** above the map. With jumps, each leg takes gates or jumps, whichever is quicker (3 min a jump, 1.5 min a gate). You also get the jumps, light years and fuel (without economizers). Jump fatigue isn't counted, so plan a long leg in the Jump planner.
6. **Cargo:** **No limit**, **The ship under Range** (fitted with Expanded Cargoholds, with its pilot's skills), a ship from your hangars (its bare hold, without fittings or skills), or type the hold's m³. When the hold is full, the ship goes back to the start to unload, then carries on. Each row shows what's in the hold, and the unloads are rows of their own. With a hold, every trip ends at the start, and what's already there isn't moved.
7. **Plan route.**

You get the number of stops and gates, then one row per stop with what to pick up there (item, quantity, station, owner). The legs are drawn on the map, numbered by stop; **Clear** (or **Hide** in the legend) removes them. Systems with many kills in the last hour are marked **Dangerous**. Items in a structure whose system isn't known, or in a system with no gate route (wormholes), are listed and left out.

## Citadels
Every plan needs to know where you build, react and refine, and with which rigs. Structures come from:
- **ESI**: where your jobs run and your hangars are (needs **Structure names**), your corporation's own structures with their fuel (Station Manager role + **Corporation structures**). **Refresh from ESI** reads them again.
- **Search citadels by name** (3+ letters; needs **Find citadels by name**).
- **Import friendly structures from a list:** paste a copied table, then **Import**.
- **Import industry structures with their rigs:** from a Google Sheet link (**Read the sheet**) or a pasted table. **Remove all imported** clears them.

ESI has no list of every citadel you can dock in, so add the others by search or import.
