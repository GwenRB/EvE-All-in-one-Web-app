<!-- tracks: Supply chain, jump freighter, Rorqual, hauling, trips, horizon, Plan ahead, Plan for, freight service, Done from assets -->

On the **Map** page. It plans every **jump freighter and Rorqual trip** your plans need, and shows the routes on the map.

## What it moves
- **Builds** in [Orders management](Orders-management-and-Jobs): materials to each structure, components between structures, the product back to your delivery system. Orders sent before route data existed have to be sent again from Build planning.
- **Reactions** ([Reactions management](Reactions-management)), when the reactor isn't in the delivery system: each cycle's inputs there and products back.
- **PI** ([PI Management](PI-Management)): the P4 you pick up at your planets' harvest times (from the Planets page) back to the delivery system, and the inputs out. The hauler never takes from the planets itself: you pick up.

## Ships
Every jump freighter or Rorqual a pilot can fly is its own row: the one they're in now (needs **Character location** and **Current ship**), each one docked in their assets, and any you add with **Another ship**. A pilot with none gets one of the type you pick.
- Set a ship's position by hand if ESI is out of date; your setting wins until a newer read.
- **A pilot flies one ship at a time and carries their fatigue.** To take another ship, they fly a shuttle through the gates, or use a jump clone when that's at least an hour sooner. The trip says which.

## Settings
- **Plan for:** *Lowest fuel cost* (least fuel, then soonest), or *Fastest delivery* (soonest, then least fuel). Being late always weighs most.
- **Plan ahead:** 3 days, 1, 2 (default), 4 or 8 weeks. Every reaction cycle and PI refill starting before then is planned.
- **Hold goods at most N hours:** how long a ship may wait at a pickup for more goods.

## How it plans
- **A ship flies every leg.** A trip always starts where that ship's last trip ended. When the next pickup is elsewhere, it flies there empty first (fuel and time counted), shown as its own row and a dashed line.
- **The whole plan is optimised at once**, never one trip at a time, and the panel shows what that saves compared with planning trip by trip. The same inputs always give the same plan.
- Most urgent goods load first. Ore goes in a Rorqual's ore hold, then the cargo only when nothing else needs the room.
- Timing: 10 min to load, 1.5 min per gate, 3 min per jump, plus jump timers and fatigue. Cynos are assumed available everywhere.

## Danger
A leg that goes by gate through a dangerous system, or jumps into one (its cyno can be caught), shows ⚠ with the systems and kills. Routes aren't changed: it's a warning. Set the level with **Danger from N kills** on the map.

## Following the plan
- **Done from assets:** when your hangars show more of an item in a move's destination than when the move was planned, that much is marked done. The plan lists what it marked, with **Undo**.
- **Trips no ship can do** (too big, or no route) go to **Trips for a freight service**, here and on [To-Do](To-Do), with a count on the To-Do tab. Mark them **Sent by freight** once contracted.

## Limits
High-sec runs by gate-only freighter aren't planned. Jump bridges / Ansiblex aren't used. See the roadmap for the full list.
