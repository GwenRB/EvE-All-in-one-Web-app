<!-- tracks: troubleshooting, login, proxy, downtime, rate limit, no price -->

### The login comes back to a page that doesn't load
You opened the HTML file directly instead of through the launcher. Either start the launcher and use http://localhost:8642/, or copy the whole address from that tab and paste it in the box under **Link EVE characters**.

### EVE says the callback URL doesn't match
Your application's callback must be exactly `http://localhost:8642/` (with the final `/`), and you must open the tool at that address.

### A page says a permission is missing
Tick it in **Link EVE characters**, add it to your application on developers.eveonline.com, and log in again with each pilot ([ESI permissions](ESI-permissions)).

### Corporation data is empty
It needs a linked pilot with the right in-game role: Director (hangars, customs offices), Accountant (wallets, mining ledgers), Station Manager (structures, extractions), Factory Manager (jobs). See [ESI permissions](ESI-permissions).

### An item shows "no price"
Its pricing has no order for it, for example a citadel nobody sells it in. This is on purpose: the tool never puts 0 or another market's price instead. Pick another pricing for that list. See [Pricings](Pricings).

### Prices are slow to fill in
Every page's market reads share one queue that stays under ESI's limit; big builds wait their turn. A status at the bottom left shows when reads are held back. During the daily downtime (from 11:00 EVE) market reads wait until the server is back.

### Supplier sheets, news or CCP's data can't be read
These go through the launcher. Start the tool with the launcher, not by opening the file. Only the tool can use the launcher's page reader: other websites are refused. After updating the tool, close the launcher's window and start it again so it runs the new version.

### A new pilot's contracts show without their items
ESI only lets the tool read a few contracts' items at a time. For a corporation with many contracts, the first sync reads what ESI allows and finishes; the rest fill in at the next syncs (**Sync all**, or **Sync now** on the Characters page).

### My data is gone
Data lives in the browser you used, on that computer. Another browser, a private window, or clearing site data starts empty. Import your last backup (**Settings → Import backup**). Export one regularly.

### Moving to another computer
**Export backup**, copy the file, **Import backup** there, log in again ([Settings and backups](Settings-and-backups#backups)).

### The supply chain plans a trip I can't do
Check the ship's position (set it by hand if ESI is behind), the pilot's skills, and the danger level. Trips no ship can do go to **Trips for a freight service** ([Supply chain](Supply-chain)).

### Something else
Use the **Notes** tab to keep track, and open an issue on the [repository](https://github.com/GwenRB/EvE-All-in-one-Web-app/issues).
