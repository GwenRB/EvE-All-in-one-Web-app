<!-- tracks: Profit and loss, wallet, journal, activities, Not assigned, Left out, Actual profit -->

**Market → Profit and loss.** The ISK that really came in and went out of every linked wallet (pilots and corporation divisions), sorted by **what it was for**: Manufacturing, Reactions, Planets (PI), Science, Trading, Hauling, Structures, Personal, Other, or activities you add.

Needs the **Wallets** permission (and **Corporation wallets** with the Accountant role for the corporation's divisions). Read at each sync (at most every 30 minutes) and with **Refresh from ESI**.

## History beyond 30 days
ESI only gives the last 30 days. Every entry read is kept in your browser **and in backups**, so the history grows from your first read. A month without a refresh leaves a gap. Importing a backup **joins** its history with yours; it never replaces it.

## Nothing counted twice
- Purchases and sales are counted from market transactions (item, quantity, price), not from the journal's market lines. Buy order escrow is a deposit and isn't counted.
- Money between your own wallets (transfers, contracts, trades between your pilots and corporation) is left out.

## Teach it once, every entry follows
Each entry goes to the first activity that applies:
1. what you picked for **that entry** (Entries panel);
2. its **item's** activity (Items panel), for purchases, sales and sales tax;
3. the activity of **who you dealt with** (Who you dealt with panel), for contracts, transfers and donations;
4. its **kind of entry's** activity (Kinds of entry panel);
5. automatic: job fees by the job's activity, planet taxes to Planets, courier contracts to Hauling, PI to Planets, moon materials and reaction products to Reactions, minerals and components to Manufacturing, datacores and decryptors to Science, and so on.

Anything left is **Not assigned**: counted, and shown as a tile so you can sort it. **Left out** entries aren't counted anywhere.

### Contracts are split by what they held
A contract with no choice made is sorted item by item. When its items go to several activities, its price is shared between them by the items' value in the pricing chosen on the page (default Jita split). If an item has no price there, the contract stays whole and Not assigned, and the page names the item.

Broker fees only follow an item when ESI ties them to a transaction: otherwise give **Broker fees** an activity in Kinds of entry.

## Panels
- **Summary:** pick a period (this or last month, 7 / 30 / 90 days, this year, everything). Tiles: Income, Spending, Profit, Not assigned, Left out; by activity and kind.
- **By month:** each activity's profit, month by month (EVE time).
- **Items**, **Who you dealt with**, **Kinds of entry**, **Entries:** where you make your choices. Items and Entries also have [Filters](The-basics#filters) (date, wallet, kind, item, who, amount, quantity, activity…).

The [Overview's Forecast](Overview) shows your actual profit from here, next to the planned one.
