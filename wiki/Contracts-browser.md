<!-- tracks: Contracts browser, contracts of your pilots, contract items -->

**Contracts browser** tab (near the end of the bar). Every contract of your linked pilots and corporations in one place: what each one gives and asks for, who's in it, where, and what its items are worth. Needs the **Contracts** permission (and **Corporation contracts** for your corporation's). For orders you deliver to clients, see [Contract management](Contract-management).

## What you see
- **Tiles:** active contracts (waiting, in progress), what you sell and buy on them, courier contracts you ship or haul (with their rewards and collateral), and how many still waiting expire within a day.
- **The list**, grouped by status: Waiting, In progress, Expired (still waiting after its expiry date), Finished, Rejected, Cancelled, Deleted… Each contract once, even when several of your pilots see it.
- For each contract:
  - **Contract:** its type, title and a few of its items (*asks …* for what it wants in return). Click **n items** to open its details: every item with its value, **Copy the list**, its ID, availability and dates.
  - **Your side:** *You sell* (you put items up for a price), *You buy* (you pay for someone's items), *You give* / *You receive* (no ISK), *You ship* (your courier contract), *You haul* (a courier you accepted), *Between your pilots*.
  - **Between:** who issued it → who it's for or who accepted it (yours in bold).
  - **Price or reward**, with the collateral of a courier and the buyout of an auction.
  - **Items worth:** what it gives less what it asks for, in the pricing picked at the top (**Value items at**). Blueprint copies count as zero. An item without a price there makes it "no price" and is named above the list: never 0.
  - **Against worth:** how much better than that worth the price is for you (selling: price − worth; buying: worth − price). Green is in your favour.
  - **Where** (a courier's start → end, and its volume), **Issued**, **Expires or ended**, and **Read from** (which pilot or corporation it came from).

## How to use it
1. Pick **Active**, **Ended** or **Everything**.
2. Type in the search box to find a title, an item, a name or a place.
3. Use [Filters](The-basics#filters) for anything else: for example *Your side is You sell* and *Against worth less than 0* to find sales below what the items are worth, or *Expires in the next 1 days*.
4. **Refresh from ESI** syncs your pilots.

## Good to know
- ESI gives a pilot's active contracts and those of the last 30 days. Ended ones are kept here for **90 days**.
- What a contract holds is read once, at the next sync after it appears. One that can't be read any more says so.
