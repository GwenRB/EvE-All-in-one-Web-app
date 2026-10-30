<!-- tracks: tab bar, tables, sort, fold, panels, navigation rail, How this page works, sync, downtime, server status, market reads, Filters -->

## Tabs and menus
The tab bar groups pages into menus: **Industry**, **Market**, **Stock**, **Pilots** and **Other** open when you hover or click them; the menu holding the open page shows that page's name. The bar wraps onto a second line when the window is too narrow for every tab.

Each page has its own web address (for example `http://localhost:8642/#build-planning`), so bookmarks and the browser's back button work.

Pages you don't use can be hidden in **Settings → Pages** (Settings itself always stays).

Some tabs show a **red number**: To-Do counts what waits on you, Intel (and its Other menu) counts notifications that need attention.

## The header
- **Link EVE characters:** add or re-log characters, choose permissions. See [Getting started](Getting-started#4-link-your-characters).
- **Server status:** online with the number of players, VIP mode, or not answering. After the daily downtime it shows **"Online since HH:MM EVE"** for a day, the minute the server came back up (system indices, bounty payouts and so on follow it). Hover it for your local time too.

## Syncing
Linked pilots are read from ESI when you sync them, and most pages also have a **Refresh from ESI** button. A sync reads skills, queues, jobs, assets, planets, wallets, contracts, calendar, notifications… depending on the [permissions](ESI-permissions) you gave.

A page's **Refresh from ESI** reads only what that page shows (Planets: the planets; Jobs: jobs and structures; Wallets: the wallets; Stock: hangars and contracts; Contracts browser: contracts), so it takes seconds. **Sync now** and **Sync all** read everything. While it runs, the button and the Characters panel in Settings say which pilot is read and which part (for example *Syncing: wallet history…*, or *contracts: items 40 of 300*). Contract items are read once each; when ESI asks to slow down, the rest wait for the next sync instead of holding this one. After a full sync, the **Last synced** column says how long it took and which part took most of it (hover for every part): if a sync is slow, that's where to look.

Prices and market history are read when a page needs them. Every page's market reads share **one queue** that stays under ESI's rate limit, and the page you're looking at goes first. When reads are held back, a small status shows at the bottom left. A big build may take a little while to price: that's the queue waiting, not an error.

### Daily downtime
From **11:00 EVE time** until the server is back, the header says so, and syncs, market reads, sovereignty, incursions and kills wait. Prices keep what they had.

## Tables
- **Click a column title to sort**, click again to reverse. Your sort is remembered (and saved in backups).
- Before you click, a table is A→Z by its first column, **except** tables whose order means something (by date, by value, cheapest first…). Those show an arrow on the column they're sorted by.
- **Grouped tables** fold by group: click a group's title (▾ / ▸) to hide its rows; it shows "· n hidden". Rows sort inside their group, and totals stay last.

## Filters
Tables with filters (Assets, Profit and loss, Intel, the skill matrix, Ships you can build, the Contracts browser, the Item database) have a **Filters** button under their search box:
1. Click **Filters**: a first condition appears. Pick a **column**, what it should be (*contains*, *is*, *more than*, *between*, *in the last … days*, *is empty*…) and a **value**. Amounts take `1.5b`, `200m` or `12k`; text boxes suggest values from the table.
2. **Add a condition** for more. With two or more, choose **Show rows that match all of them** or **any of them**.
3. **Add a group** for conditions that go together, like *(Item contains "ore" and Quantity more than 1m) or Location is Jita*. A group has its own **all of them** / **any of them**, its own **Add a condition** and **Add a group** (groups can sit inside groups), and starts as the opposite of the one holding it. So for *(A and B) or C*, set the top to **any of them**, add a group (it starts as **all of them**) with A and B inside, then add C beside it.
4. Untick a condition or a group to switch it off for a moment; ✕ removes it. The conditions in use show as chips next to the button, with brackets around groups and how many rows pass.
5. Type a **Name** and **Save filter** to keep the set; load it again from **Saved filters…** (saved per table, in backups). **Clear** removes every condition.

A value that isn't known (an item with no price, a missing date) never passes a comparison: use **is empty** to find those.

## Panels and navigation
- Every **panel folds from its title** (▾ / ▸), and stays folded.
- Long pages have a **left navigation rail** listing their panels. Clicking a folded panel there opens it.
- Pages that compute numbers explain how at the bottom, under **How this page works** (folded).

## Rules that hold on every page
These are deliberate:
- **Prices are never invented.** An item without a price shows "no price": never 0 and never another market's price. Totals leave it out and say so, and anything that depends on it (margins, profits, breakeven) shows as unknown. See [Pricings](Pricings).
- **Pages read each other, but don't write into each other.** For example Build planning uses your Assets, but never changes them. The few links that do write were asked for on purpose: Reactions and PI send their profit to the Forecast, Build planning sends builds to Orders management.
- **Structure and rig bonuses, hauling and pricing work the same way everywhere.** A citadel you set up once is used by every plan.
- **Jump fatigue:** after a jump, fatigue = max(10, current fatigue) × (1 + light years), at most 300 minutes; the jump timer = max(1 + light years, fatigue ÷ 10), at most 30 minutes. Fatigue under 10 minutes counts as 10, so waiting it lower never helps.

## Where your data lives
In your browser (localStorage and IndexedDB), on your computer. The tool doesn't send your data anywhere: it only reads from CCP's servers, from EVE Ref when CCP's data can't be read, and from the sites you add (supplier sheets, news feeds). To move to another browser or computer, use **Settings → Export backup / Import backup**. See [Settings and backups](Settings-and-backups#backups).

## Where the game data comes from
CCP's own data first:
- **ESI:** your characters and corporation, market orders and history, public contracts, kills, server status.
- **CCP's static data export:** items, blueprints, reactions, planet schematics, the map. Indexed once per game build in your browser.
- **EVE Ref:** only when CCP's data can't be read.
