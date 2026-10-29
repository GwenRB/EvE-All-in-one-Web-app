<!-- tracks: Overview, Forecast, Calendar, Upcoming events, EvE News, Time zones, Planned orders, Actual profit, Omega costs, Objectives, Net worth, Market orders, History, Day by day -->

The first tab: where your ISK is heading, what you're worth, and what's coming up.

## Forecast
Today's value is the ISK in your wallets plus your stock value and your open **market orders** (sell orders at their price, buy orders' escrow). The forecast starts there and adds what's planned:

- **Planned activities:** weekly incomes you enter by hand (for example "ratting, 300 M a week").
- **Reactions plan** and **PI plan:** the profit of your [Reactions management](Reactions-management) and [PI Management](PI-Management) plans. Add them with **Add to the Forecast** on those pages; they stay up to date when you change the plans. Deleting one here is fine: the page offers to add it again.
- **Planned orders:** each build in [Orders management](Orders-management-and-Jobs) not yet Done counts (what it's worth less its build cost) on the day it should be finished:
  - *In progress:* from when you set it In progress, plus the plan's timeline (or later, if a running job making it ends later).
  - *Planned:* today plus the timeline.
- **Active contracts** count what they'll pay you (+) or cost you (−). Contracts between your own pilots are ignored.
- **Omega costs** are taken off.
- **Stock value:** enter a value by hand, or add a line **from hangars**: pick where (every hangar ticked on [Assets](Assets), one location, or one hangar) and what (one category or group, or everything there), then **Add from hangars**. It stays live with your hangars. For example, if a station holds a corporation hangar of composites to sell and another for your own use, pick the selling hangar and *Composite*: only that one counts.
- **Actual profit** (from [Profit and loss](Profit-and-loss)) is drawn for comparison over the past, with a tile for your profit per week over the last 30 days. It isn't added to the total: that ISK is already in your wallets.

**Tips**
- Click a line in the legend to hide it **and** take it out of the totals.
- A plan with items that have no price shows as "unknown" and is left out of the totals; the tiles say which.
- **Objectives** let you set ISK goals; the calendar shows when each becomes affordable.
- One point is recorded per day, building your **Net worth** history (below).

## Net worth
What you own, day by day, like a tracker. Each day keeps:
- **Wallets:** every linked pilot and your corporation's divisions.
- **Assets:** the hangars ticked on [Assets](Assets), plus stock you entered by hand on the Forecast.
- **Sell orders** (price × what's left, before sales tax) and **Buy order escrow** (the ISK your buy orders already hold). Needs the **Market orders** permission (and **Corporation market orders** with the Accountant or Trader role for your corporation's).
- **Contracts:** what active contracts will pay you or cost you.

How to use it:
1. Pick the span with **Show** (30 days, 90 days, a year, everything).
2. Click **Owners** to see only some pilots or corporations (click **Everyone** to go back). Contracts and stock entered by hand have no owner, so they're left out then.
3. Click a line in the legend to hide it. Hover the chart for a day's values.

A day is saved at each sync and when the Overview opens. **Days you didn't open the tool** show your wallets from the wallet journals (hollow dots), as long as every wallet's journal is read (the **Wallets** permission, see [Profit and loss](Profit-and-loss)).

The tiles give today's net worth, the change over the span, your highest day and your market orders. **Market orders** lists every open order. **Day by day** lists the recorded days with each part; ✕ deletes a day, **Record today's values now** saves one, **Delete all history** (two clicks) starts over.

## Calendar
Everything with a date: industry jobs finishing (manufacturing, reactions, copying, invention, research), planets stopping, Omega ending, structure fuel running out, contracts expiring, objectives, and in-game events (with their own **Fleets** tick box).
- Click a job type in the legend to hide it; click its colour swatch to change the colour.
- Hover an entry for its details.

## Upcoming events
Every pilot's in-game calendar (needs the **Calendar** permission), each event once, with every pilot's answer (✓ accepted, ? maybe, ✗ declined, · no answer), in local and EVE time. Events stay until they end.

## EvE News
The EVE launcher's news, and any other channel you turn on in **Settings → EvE News channels**: patch notes, EVE forums' latest topics, **Reddit r/Eve: top today** (the day's 5 most upvoted posts, on by default), or any RSS / Atom / JSON feed you add by its link. All channels in one list, newest first. **Refresh** reads them again (otherwise each is kept an hour). Needs the launcher.

## Time zones
EVE time first, then your cities. Change the list in **Settings → Time zones**. When a city's day isn't EVE's day, the weekday shows; hover for the date and UTC offset.

On wide screens, Upcoming events, News and Time zones sit beside the page; on narrower ones they move to the bottom and appear in the left navigation.
