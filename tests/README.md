# Tests

`e2e_smoke.py` is a Playwright walk-through of the whole app with **fake data**: every request to ESI, EVE Ref, CCP's static data and the image servers is intercepted and answered from the tables at the top of the file (7 fake systems Alpha…Golf, a fake Venture build chain, reaction formulas, PI items, a Rhea, decryptors, a test citadel market…). No EVE account or internet access is needed.

```sh
pip install playwright && playwright install chromium   # once
python3 tests/e2e_smoke.py                               # or CHROMIUM_PATH=/path/to/chrome python3 tests/e2e_smoke.py
```

- It starts the launcher's server on http://localhost:8642 if nothing is running there (and stops it at the end).
- It prints, page by page, what the app shows (`label: value` lines). It does **not** assert most values yet: compare the output before/after a change. It exits with status 1 when the page throws a JavaScript error (`errors [...]` at the end).
- Screenshots go to `tests/out/` (git-ignored).
- `fixtures/sde.zip` is a tiny fake of CCP's static data zip (`blueprints.jsonl`, `types.jsonl`, `planetSchematics.jsonl`), served for `eve-online-static-data-latest-jsonl.zip`.
- The script grew feature by feature: later sections reuse state set by earlier ones (characters, assets, build settings…), so run it whole. Good first task: split it into independent scenarios with real assertions.

Quick syntax check without a browser: `scripts/check.sh` (needs Node).
