<!-- tracks: Trading board, market browser, By market, 5% sell, orders in every region, PLEX, global market -->

**Trading board**, its own tab between **Market** and **Stock**. A market browser like the game's, using the whole width of the window. Scroll past the header and the board fills the screen: the market groups and the order lists scroll inside it. No permission needed for public orders; your citadels' orders need a pilot with **Citadel markets**.

[Market watch and Arbitrage](Prices#market-watch) moved to the **Prices** page.

## Find an item
- **Market groups** on the left, like the game's market: click a group to open it (▸ / ▾), then an item.
- Or type part of its name in **Find an item**.
- From the [Item database](Item-database): click the small chart button next to an item (or **View on the Trading board** on an opened item).

The tool reopens the last item you looked at.

## What you see
The item's panel at the top:
- Its market group path (click a part to open it in the tree) and its name (**click it to copy it**).
- **Where**: every region, a trade hub (your list in [Settings → Pricings and HUBs](Pricings)), one of your citadels, or a region. Only the orders there are read and shown; picking a region or a hub also moves the history there.
- **Item database**, **Refresh** (reads the orders again; they're kept 5 minutes, like ESI's own), and **How this page works** (how the numbers are worked out).
- **Tiles**, over the orders your filters keep:
  - **Sell (5%)**: the average price of the cheapest 5% of the units for sale, with the lowest sell order and where.
  - **Buy (5%)**: the same for the highest buy orders.
  - **Margin**: Sell (5%) − Buy (5%).
  - **For sale** and **Wanted**: units and orders.
Under it:
- **Sellers** and **Buyers**: every order, cheapest sells and highest buys first. Region, quantity, price, location (with its security), jumps, range and minimum volume (buyers), expires in, changed. Click a column title to sort. Your own orders say **yours** with their owner. **Click a price to copy it**, to list at the same price. **Click a line to keep it highlighted** (click it again to let go). The two lists share the screen and scroll inside; when one is short, the other gets the room.
- On the left, under the Market panel, **Show history** and **Show markets comparison** show that panel in place of sellers and buyers (the same button brings them back). Each panel has **Open in a window**: it opens in a browser window of its own, which you can put on another screen, and the board goes back to sellers and buyers. The window follows the item you open on the board. (If nothing opens, allow pop-ups for the page in your browser.)
  - **History**: a region's daily prices, from 7 days to everything ESI keeps (about 13 months). The line is the day's average, the band the lowest to highest trade, the bars the units traded; ISK is on the left, volume on the right. Pick the region and the span; **point at the chart** to see a day's average, highest, lowest, volume and orders. Below: sold per day and ISK traded per day over the last 7 days, and how the average moved.
  - **Markets comparison**: the trade hubs and your citadels that have orders for the item, side by side (lowest sell, for sale, highest buy, wanted, spread). Not filtered. A citadel whose market can't be read (most have no market module) is left out.

## PLEX
PLEX trades in one market for the whole game. ESI keeps it as its own region, shown here as **Global PLEX market**: its orders sit at stations everywhere, and its history is that market's. Picking a region or a trade hub under **Where** keeps the PLEX orders placed there.

## Filters
Open **Filters** under the search (it shows how many are on):
1. **Jumps from**: one of your pilots (where they are now) or a trade hub. Adds a **Jumps** column.
2. **Price**, **Quantity** (from–to) and **Jumps** (up to). Amounts can be typed like 1.5m.
3. **Leave out** high-sec, low-sec, null-sec, NPC stations or player structures.
4. **Only trade hubs and your citadels**, **Only your orders**.
5. **Location contains**: a station, system or region name.
6. **Clear filters**.

## Good to know
- Reading an item across every region takes about 70 market requests (one region, a hub or a citadel: one or two). They share the tool's market budget with every other page, so they may wait a little when another page is reading prices.
- Security and jumps need the map: open the [Map](Map-and-jump-planner) page once.
- A player structure's name is read once with a pilot who can dock there (**Structure names** permission); otherwise it shows as "Structure in" its system.
