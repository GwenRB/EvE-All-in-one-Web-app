<!-- tracks: Orders management, orders, Jobs, industry jobs, Buy for builds, planned, in progress -->

## Orders management
**Industry → Orders management.** The builds you've committed to, sent from [Build planning](Build-planning) with **Send to Orders management**. Listed oldest first.

For each order:
- **Status:** *Planned*, *In progress* (set it when you start the jobs: the Forecast and the supply chain date it from then), *Done*.
- Its **materials**, components, ore and costs. Missing prices are flagged.
- **Reopen the exact plan** in Build planning.

What orders feed:
- Materials still to buy go to [To-Do](To-Do) as **Buy for builds**.
- Their stock is **reserved**: later plans don't offer it again (when "Keep what ongoing orders need" is on in Build planning).
- The [Forecast](Overview) counts each one not Done on the day it should be finished.
- The [Supply chain](Supply-chain) plans their hauling.

## Jobs
**Industry → Jobs.** Your industry jobs per pilot, and a calendar of the next 30 days.
- Slots across your whole roster, how many are busy, when each job finishes.
- Job slots in use include jobs that are finished but not delivered yet.
- Corporation jobs need one linked pilot with the **Factory Manager** role; they count against the slots of whoever installed them.
- Job data comes from ESI: **Refresh** to see jobs started since the last sync.
