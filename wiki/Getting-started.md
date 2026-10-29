<!-- tracks: launcher, Link EVE characters, login, Client ID, first sync -->

## What you need
- A recent browser: Chrome, Edge or Firefox.
- **Windows:** nothing else. The launcher uses PowerShell, which comes with Windows.
- **macOS / Linux:** Python 3.
- An EVE Online account, to link your characters (optional: you can also add pilots by hand, see [Characters](Characters)).

## 1. Download the tool
Download these files from the repository and keep them **in the same folder**:
- `EVE Industry Management.html` (the whole tool; don't rename it, the launchers open it by name)
- `Start EVE Industry Management.bat` (Windows) or `start-eve-industry-management.sh` (macOS / Linux)

## 2. Start it
- **Windows:** double-click `Start EVE Industry Management.bat`. A window opens: keep it open while you use the tool, close it to stop.
- **macOS / Linux:** in a terminal, in that folder, run `./start-eve-industry-management.sh`. Press Ctrl+C to stop.

The launcher opens **http://localhost:8642/** in your browser.

> **Use that exact address.** It is where EVE's login sends you back after you sign in. You can open the HTML file directly, but then each login needs an extra copy-paste step, and a few things can't be read (CCP's static data, supplier sheets, news feeds), because they go through the launcher.

The first start reads CCP's static data (items, blueprints, the map…) and indexes it in your browser. This takes a moment once per game build.

## 3. Create your EVE application (one time)
The tool reads your characters through **ESI**, CCP's official API. For that you need your own "application" on CCP's developer site:

1. Go to [developers.eveonline.com/applications](https://developers.eveonline.com/applications) and sign in.
2. Create a new application, type **Authentication & API Access**.
3. Callback URL: `http://localhost:8642/`
4. Add the permissions (scopes) you want to use. The tool can copy the list for you (step 4 below). [ESI permissions](ESI-permissions) says what each one is for.
5. Save, and keep the page open: you need its **Client ID**.

## 4. Link your characters
1. In the tool, click **Link EVE characters** at the top of the page.
2. Tick the permissions you want (the same ones as in your application). **Copy** puts the list on your clipboard, ready to paste into the application.
3. Paste the application's **Client ID**. Only the Client ID: **never paste the secret key**, the tool doesn't need it.
4. Click **Log in with EVE Online**, sign in and pick a character.
5. You come back to the tool and the character is linked right away. Its skills, jobs, assets and the rest sync in the background (one pilot at a time), so log in the next character straight away. The login box, the **Characters** page and the pilot cards show who is still syncing or waiting; the login box also says what the pilot is reading (skills, contracts, hangars…). A first sync with a big corporation can take several minutes. If you close the page before they finish, use **Sync all** later.

If you opened the HTML file without the launcher, EVE sends you to an address that doesn't load: copy that whole address from the address bar and paste it in the box the tool shows.

### Adding a permission later
New permissions start unticked. When you want a new one:
1. Tick it in **Link EVE characters**.
2. Add it to your application on developers.eveonline.com.
3. Log in again with **each** pilot, so their login includes it.

## 5. First things to set up
- **Settings → Pricings:** the default Jita prices are there already; add a citadel's market or a buyback % if you use them. See [Pricings](Pricings).
- **Settings → Market taxes:** check your sales tax and broker fee.
- **Map → Citadels:** add the structures you build or react in, with their rigs, so plans place jobs in the right place. See [Map and jump planner](Map-and-jump-planner#citadels).
- **Omega:** enter when each account's Omega ends (ESI doesn't share it). See [Omega](Omega).
- **Settings → Export backup** once you're set up. See [Settings and backups](Settings-and-backups#backups).

Next: [The basics](The-basics).
