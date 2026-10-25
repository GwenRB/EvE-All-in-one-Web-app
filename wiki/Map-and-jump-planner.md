<!-- tracks: Map, jump planner, kills, danger, Citadels, structures, sovereignty, incursions, markers, legend, hover -->

The **Map** tab holds the map of New Eden, the jump planner, the [Supply chain](Supply-chain), and your list of citadels.

## The map
- **3D** (the real layout, seen from above) or **2D** (the game's schematic map): **Switch to 2D map**.
- Scroll to zoom, drag to move, **click a system** for its details. **Find a system** jumps to it; **Reset view** goes back.
- **Colour by** security or sovereignty. Add alliances under **Allies**: their space shows in dark blue.
- **Markers:** your citadels (the biggest one's type icon), friendly structures, stations with your hangar stock, planet systems, capital ships (jump freighters shown, freighters hidden), jump clones, homes, incursions. The map, its legend, the selected system's panel and the hover box all use the same icons and colours.
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

## Citadels
Every plan needs to know where you build, react and refine, and with which rigs. Structures come from:
- **ESI**: where your jobs run and your hangars are (needs **Structure names**), your corporation's own structures with their fuel (Station Manager role + **Corporation structures**). **Refresh from ESI** reads them again.
- **Search citadels by name** (3+ letters; needs **Find citadels by name**).
- **Import friendly structures from a list:** paste a copied table, then **Import**.
- **Import industry structures with their rigs:** from a Google Sheet link (**Read the sheet**) or a pasted table. **Remove all imported** clears them.

ESI has no list of every citadel you can dock in, so add the others by search or import.
