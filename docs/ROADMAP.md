# Known issues, limits and ideas

## Bugs to look at
- **Build planning with 5 Redeemers showed an absurd time and ISK**, apparently linked to the reaction part of the chain. The user deferred it ("I will debug later"). Start here.
- Forecast: a linked plan (reactions/PI) with an unpriced item keeps the last value it sent instead of showing it's unknown.

## Supply chain (first version)
- Only the next reaction cycle and the next PI refill are planned; plan several cycles ahead.
- One ship per pilot; a pilot owning several JFs in different places can't be split.
- No gate-only freighter for high-sec runs; high-sec ends are reached by the JF through gates. Freight-service legs are only suggested, not planned.
- Fixed time constants (3 min/jump, 1.5 min/gate, 10 min load/unload); cyno alts' positions aren't modelled.
- Orders sent before route data existed must be re-sent from Build planning.
- `findJumpRoute` scans every system for each expansion: memoized per route and range, but slow with many lanes/ranges.
- Ideas: show the next trip on the To-Do page; play-hour windows per pilot; detect "done" from assets moving; plan around jump bridges / Ansiblex.

## Data and other limits
- Many lookups still use EVE Ref; the user prefers CCP's own data (move them to the static data export where possible).
- Fittings added before the Doctrine feature only kept hull/modules/drones (no cargo, no quantities): re-add them for a full check.
- Supplier links other than Google Sheets need the launcher's `/proxy`.
- Stock management page is a blank placeholder.

## Testing
- `tests/e2e_smoke.py` prints values but asserts almost nothing; split it into independent scenarios with assertions (fake data is at the top of the file).
