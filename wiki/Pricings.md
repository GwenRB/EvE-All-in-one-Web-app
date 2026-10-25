<!-- tracks: Pricings, pricing, no price, Jita, citadel market, buyback -->

Every price in the tool comes from a **pricing**: a named way of valuing items. Every page that shows prices lets you pick one from the same list.

## The built-in ones
Always there, from Jita 4-4's orders (read from ESI):
- **Jita buy (JBV):** the highest buy order.
- **Jita sell (JSV):** the lowest sell order.
- **Jita split:** halfway between.

## Add your own
In **Settings → Pricings**, give it a name, then pick:
- **A percentage of another pricing**, for example "Buyback 90%" = 90% of Jita buy.
- **A citadel's market**: its lowest sell order, its highest buy order, or halfway between. Reading a citadel's orders needs the **Citadel markets** permission on a pilot who can dock there.

Then click **Add pricing**. It appears in every price list of the tool.

## "No price"
A citadel pricing only uses **that citadel's own orders**. When nobody sells (or buys) an item there, the item has **no price** in that pricing:
- It shows empty, marked "no price", never 0, and never Jita's price instead.
- Totals leave it out and say which items they left out.
- Results that depend on it (margin, profit, ISK per LP, breakeven…) show as **unknown**.

This is on purpose: a number that looks real but isn't would be worse than a gap. When you see "no price", pick another pricing for that list, or check that the market was read (the daily downtime pauses market reads).

## Where pricings are used
Just a few examples: [Assets](Assets) values, [Build planning](Build-planning) "where to buy", [Reactions](Reactions-management) and [PI](PI-Management) inputs and outputs, [Profit and loss](Profit-and-loss) contract splits, [LP store](LP-store), [Corporation](Corporation) fuel costs, [Prices](Prices) comparisons.

The Import calculator and Arbitrage (Market pages) keep their own freight fields.
