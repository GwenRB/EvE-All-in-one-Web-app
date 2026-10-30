<!-- tracks: Corporation, Structure fuel, Moon extractions, Who mined what, mining ledger, refuel -->

**Other → Corporation.**

## Structure fuel
Your corporation's structures (needs a pilot with the **Station Manager** role and the **Corporation structures** permission), the one running out first on top.
- **Fuel blocks per day:** each online service's module counted once, at its fuel use from CCP's game data, less the structure's role bonus. A service the tool doesn't know isn't counted: the total shows ≥ and names it.
- **Fuel runs out**, time left, **blocks to reach 30 days**.
- **Fuel per month** in ISK: pick the fuel block (or the cheapest of the four) and a [pricing](Pricings).

### Refuel warning
Set how many days ahead to warn (1–30, default 7). Structures running out within that go on [To-Do](To-Do) under **Structures to refuel**.

## Moon extractions
Needs the **Corporation moon mining** permission and Station Manager. For each moon: structure, started, when the chunk arrives, when it fractures by itself, and its state now (extracting / ready / fractured).

## Who mined what
What each miner took from your moon drills (Accountant role). Your pilots' own mining is on the [Misc](Misc#your-pilots-mining) page, with the same period and valuation.

Grouped by miner, over 7, 30 or 90 days, with units, m³ and value. Value = its minerals at the best possible yield, or the ore's own price, in a pricing you pick. An ore with no price is left out and named.

Moon mining is kept 90 days in your browser (not in backups).
