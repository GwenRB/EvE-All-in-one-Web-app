<!-- tracks: Prices, Import calculator, Price comparison, Sync markets, Market watch, Arbitrage, market history, Sold per day, ISK per day -->

**Market → Prices.** The import calculator, price comparison, market watch tables and arbitrage. To browse a market item by item, use the [Trading board](Trading-board).

## Import calculator
Is it cheaper to buy locally, or buy elsewhere and haul it in?
1. Paste a list of items: a copy from your inventory or a contract, a multibuy list, an EFT fit, a cargo scan… one item per line (`Tritanium 10000`, `10000 Tritanium` or `Tritanium x10000` all work).
2. Pick the **Delivery station** (where you need them), the **Buying station** (where you could buy them) and how you buy there: sell orders (instant), split, or buy orders (wait).
3. Set the hauling price. Tick **Look at your suppliers too** to also buy from your [suppliers](Suppliers) when they're cheaper.
4. **Compare.**

For each item, every unit comes from the cheapest offer: local sell orders, imported ones (hauling included) or a supplier ("picked up in Jita" suppliers pay the hauling). With sell orders, only what is for sale is counted: when there isn't enough anywhere, the item says how many are missing and the totals leave them out.

- **Sync markets:** after buying, click it to read both markets again (ESI updates market orders every 5 minutes).
- Click an item's name to copy it; **Copy list** copies what to buy at each place (multibuy format).
- [PI Management](PI-Management)'s Shopping can open its list here with its **Import calculator** button.

## Price comparison
What a **citadel** sells, against another market, for the items you pick.
1. Pick the **Citadel** and what it's **Compared with**: highest buy order (JBV), split, lowest sell order (JSV), or one of your [pricings](Pricings).
2. Add whole **categories**, **groups**, or single **items**. Remove anything with its ✕.
3. **Compare.** Results group by category › group, and fold.

## Market watch
Tables that follow prices in one market for the categories, groups and items you pick.
1. Name a table (for example *Jita PI*) and click **New table**.
2. Add what to follow. Make one table per market, or several for one market.
3. Put tables in your own order with the **↑ / ↓** buttons on each.

Columns:
- **24 h** and **7 days** change. Until your own refreshes are that old, they come from the region's daily average prices in ESI's market history (marked ~, hover for details).
- **Sold per day** and **ISK per day:** the region's trades over the last 7 days (days without trades count as 0).

Each refresh is kept, so the history grows as you use it.

## Arbitrage
Items you could buy from a citadel's sell orders, ship with a freight service, and sell instantly to another market's buy orders at a profit.
1. **From citadel**, **To** (the market you sell in).
2. **Sell:** instantly to buy orders, or with sell orders (broker fee). **Sales tax %**.
3. Hauling: ISK per m³ plus collateral on what you paid.
4. Optional filters: **Item volume up to**, **Profit at least**.
5. **Find.**

It walks both order books, so the units and profit are what the orders can take right now. Results are sorted by profit.
