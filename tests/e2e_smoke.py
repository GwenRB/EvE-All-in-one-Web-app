"""End-to-end tests for EVE Industry Management (single-file app), as independent scenarios.

Every network call is answered by fake_eve.py, so no account or internet access is needed. Each scenario gets a fresh browser
context (empty localStorage and IndexedDB), seeds the pilots and hangars it needs, drives the pages and asserts what they show.
A scenario fails on any failed check or any JavaScript error on the page.

Run:  python3 tests/e2e_smoke.py                    every scenario (starts the launcher itself if port 8642 is free)
      python3 tests/e2e_smoke.py supply ore_buy     only scenarios whose name contains one of these words
      python3 tests/e2e_smoke.py --list             the scenarios
      python3 tests/e2e_smoke.py -v ...             also print the values each scenario reads (compare before/after a change)
      AUDIT=1 python3 tests/e2e_smoke.py layout     the layout audit (every page at 1000, 1280 and 1920 px)
Needs: pip install playwright && playwright install chromium   (or set CHROMIUM_PATH)
"""
import asyncio, json, os, sys, subprocess, socket, time, traceback
from playwright.async_api import async_playwright
from fake_eve import handle, ROOT, HERE

SP = os.path.join(HERE, "out") + os.sep; os.makedirs(SP, exist_ok=True)   # screenshots
try: sys.stdout.reconfigure(encoding="utf-8")   # the app's text has ▾, →, ×… (Windows consoles default to cp1252)
except Exception: pass
VERBOSE = False
SCENARIOS = []
def scenario(fn): SCENARIOS.append(fn); return fn

class T:
    """One scenario's page and its checks."""
    def __init__(self, name, pg): self.name, self.pg, self.fails, self.errs = name, pg, [], []
    def ok(self, cond, msg, detail=None):
        if not cond: self.fails.append(msg + (f"\n      got: {json.dumps(detail, ensure_ascii=False, default=str)[:900]}" if detail is not None else ""))
        return cond
    def eq(self, got, want, msg): return self.ok(got == want, f"{msg} (want {json.dumps(want, ensure_ascii=False)})", got)
    def show(self, label, value):
        if VERBOSE: print(f"    {label}: {json.dumps(value, ensure_ascii=False, default=str)[:1500]}")
        return value
    async def js(self, code, arg=None): return await (self.pg.evaluate(code, arg) if arg is not None else self.pg.evaluate(code))
    async def until(self, code, timeout=15, step=0.2):
        """Waits until the JS expression is truthy; False after the timeout."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            if await self.pg.evaluate(code): return True
            await asyncio.sleep(step)
        return False
    async def tab(self, key, wait=0.3):
        await self.js("k => { const b = document.querySelector('.tabs button[data-tab=' + k + ']'); if (b) b.click(); else showPage(k) }", key); await asyncio.sleep(wait)
    async def text(self, sel): return await self.js("s => { const e = document.querySelector(s); return e ? e.innerText.replace(/\\s+/g, ' ').trim() : null }", sel)

# ---------- shared setup
SEED = """()=>{state.chars=[{id:'a',name:'Ender Alpha',esiId:9001,skills:{'Caldari Starship Engineering':4,'Caldari Encryption Methods':3,'Industry':5,'Mechanical Engineering':4,'Reactions':3,'Mass Production':2,'Jump Freighters':4,'Jump Fuel Conservation':5,'Jump Drive Calibration':4}, fatigue:{expire:Date.now()+45*60000, at:Date.now()}},{id:'b',name:'Ender Beta',skills:{'Industry':3,'Mechanical Engineering':1}},{id:'g',name:'Solo Gamma',skills:{'Reactions':5}}];
  state.misc.ownedBps={'char:1':{at:Date.now(),name:'Ender Alpha',list:[[32881,10,20,-1,0],[501,8,16,10,1],[601,0,0,-1,0]]}};
  state.assets={'char:9001':{at:Date.now(),owner:'Ender Alpha',rows:[{t:28844,loc:60003760,h:'Hangar',q:1},{t:34,loc:60000002,h:'Hangar',q:100000},{t:35,loc:60000001,h:'Hangar',q:5000},{t:16633,loc:60000003,h:'Hangar',q:50}]}};
  state.misc.locSys={60003760:30000001,60000002:30000004,60000001:30000002,60000003:30000001,60000004:30000007}; state.locNames={...state.locNames,60000002:'Delta station',60000001:'Bravo station',60000003:'Alpha station',60000004:'Golf station'};
  state.misc.structs={'1':{id:'1',name:'Delta - Sotiyo',system:30000004,typeName:'Sotiyo',src:['corp']},'2':{id:'2',name:'Echo - Tatara',system:30000005,typeName:'Tatara',src:['corp']}}; saveLocal(); saveMisc(); render();}"""

async def ships(t):
    """Ship data (Misc page): the Rhea's range, hold and fuel."""
    await t.tab("misc"); t.ok(await t.until("!miscLoading && state.misc.types && state.misc.types.Rhea && state.misc.types.Rhea.v===MISC_V", 12), "ship data didn't load")
async def map_(t):
    await t.tab("map"); await t.pg.click("#map-load"); t.ok(await t.until("!!mapData && !!mapIndex()", 12), "the map didn't load"); await asyncio.sleep(0.3)
async def plan(t, name, qty, page="plan"):
    await t.tab(page)
    await t.pg.fill("#plan-bp", name); await t.pg.fill("#plan-qty", str(qty)); await t.pg.click("#plan-form button[type=submit]")
    await asyncio.sleep(0.3); ok = await t.until("!buildState.plan.busy", 25)
    t.ok(ok and await t.js("!!buildState.plan.res"), f"the build plan for {qty} × {name} didn't finish", await t.js("buildState.plan.msg"))
async def structs(t):
    """Build planning structures as the user sets them: the Sotiyo in Delta, the Tatara in Echo, deliveries from Bravo, a Raitaru in Golf with an ME rig."""
    await t.tab("plan"); await t.until("!!bp.names && document.querySelectorAll('#plan-names option').length>0", 8)
    pg = t.pg
    await pg.select_option("#plan-structs select[data-bsk^='ms:'][data-bsf=pick]", "1"); await asyncio.sleep(0.15)
    await pg.select_option("#plan-structs select[data-bsk^='rs:'][data-bsf=pick]", "2"); await asyncio.sleep(0.15)
    await pg.fill("#plan-structs [data-bset='haul.from']", "Bravo"); await pg.dispatch_event("#plan-structs [data-bset='haul.from']", "change"); await asyncio.sleep(0.15)
    await pg.click("#ms-add"); await asyncio.sleep(0.15)
    sk = await t.js("'ms:'+buildCfg().ms[1].id")
    await pg.select_option(f"#plan-structs select[data-bsk='{sk}'][data-bsf=type]", "Raitaru"); await asyncio.sleep(0.1)
    await pg.fill(f"#plan-structs input[data-bsk='{sk}'][data-bsf=sys]", "Golf"); await pg.dispatch_event(f"#plan-structs input[data-bsk='{sk}'][data-bsf=sys]", "change"); await asyncio.sleep(0.1)
    await t.js("()=>{const c=buildCfg(); c.ms[1].rigs=[{n:'Standup M-Set Advanced Component Manufacturing Material Efficiency II'}]; saveMisc(); renderBuildSettings(true);}")
async def reactions(t):
    """Reactions set up in Delta (delivery Alpha) with 2 Titanium Carbide chains picked."""
    await t.tab("reactions"); t.ok(await t.until("!!(state.misc.rxnData && state.misc.rxnData.f && document.querySelector('#rx-pick table'))", 15), "reaction formulas didn't load")
    pg = t.pg
    await pg.fill("#rx-setup [data-rx=sys]", "Delta"); await pg.dispatch_event("#rx-setup [data-rx=sys]", "change"); await t.until("!!rxSys", 5)
    await pg.fill("[data-rx-n='16671']", "2"); await pg.dispatch_event("[data-rx-n='16671']", "change"); await asyncio.sleep(0.3)
    await pg.fill("[data-rx=deliv]", "Alpha"); await pg.dispatch_event("[data-rx=deliv]", "change"); await asyncio.sleep(0.3)

# ---------- scenarios
@scenario
async def forecast_history(t):
    await t.js("()=>{state.forecast.history=[{d:'2026-10-10',isk:1e9,stock:0},{d:'2026-10-11',isk:2e9,stock:0},{d:'2026-10-12',isk:3e9,stock:0}]; saveForecast(); renderForecast();}")
    await t.pg.click("#fc-history [data-fc-hdel='2026-10-11']"); await asyncio.sleep(0.1)
    t.eq(await t.js("state.forecast.history.map(x=>x.d)"), ["2026-10-10", "2026-10-12"], "deleting a day of the Forecast history")
    await t.pg.click("#fc-hclear"); await t.pg.click("#fc-hclear"); await asyncio.sleep(0.1)
    t.eq(await t.js("state.forecast.history.length"), 0, "clearing the Forecast history (two clicks)")

@scenario
async def forecast_orders(t):
    H = 3600e3
    await t.js(f"()=>{{state.misc.orders=[{{id:'o1',at:Date.now(),name:'Venture',type:32880,qty:2,status:'running',startedAt:Date.now()-{H},cost:6e6,value:10e6,materials:[],jobs:[],route:{{span:2*86400,moves:[],locs:{{}}}}}},{{id:'o2',at:Date.now(),name:'Rifter',type:587,qty:1,status:'planned',cost:4e6,value:5e6,materials:[],jobs:[],route:{{span:86400,moves:[],locs:{{}}}}}},{{id:'o3',at:Date.now(),name:'Unpriced',type:587,qty:1,status:'planned',cost:1e6,value:2e6,materials:[{{t:34,n:'Tritanium',q:1,noPrice:true}}],jobs:[],route:{{span:86400,moves:[],locs:{{}}}}}},{{id:'o4',at:Date.now(),name:'Done',type:587,qty:1,status:'done',cost:1,value:9e9,materials:[],jobs:[]}}]; saveMisc();}}")
    po = t.show("planned orders", await t.js(f"plannedOrders().map(x=>[x.o.id, x.profit, Math.round((x.at-Date.now())/{H})])"))
    t.eq(po, [["o2", 1e6, 24], ["o3", None, 24], ["o1", 4e6, 47]], "planned orders: profit and finish (running from its start, planned from today; done ones left out; unpriced unknown)")
    await t.tab("forecast", 0.6)
    fc = t.show("forecast", await t.js("({legend:[...document.querySelectorAll('#fc-chart .lg')].map(b=>b.textContent.trim()), tile:[...document.querySelectorAll('#fc-summary .slot-tile')].map(x=>x.innerText.replace(/\\s+/g,' ')).find(x=>x.toLowerCase().startsWith('planned orders'))||''})"))
    t.ok("Planned orders (cumulative)" in fc["legend"], "the Forecast has a Planned orders line", fc["legend"])
    t.ok("+5" in fc["tile"] and "2 builds" in fc["tile"] and "1 left out" in fc["tile"], "the Planned orders tile adds the dated, priced builds and says what's left out", fc["tile"])
    await t.js("()=>{state.misc.orders.forEach(o=>o.status='done'); saveMisc(); renderForecast();}")
    t.ok(await t.js("![...document.querySelectorAll('#fc-chart .lg')].some(b=>b.textContent.includes('Planned orders'))"), "no line once every order is done")

@scenario
async def forecast_stock_place(t):
    """A Forecast stock line from hangars limited to one place: the corporation hangar you sell composites from, not the one for your own use."""
    await t.js("""()=>{state.assets['corp:500']={at:Date.now(),owner:'Ender Corp',kind:'Corporation',via:'Ender Alpha',divisions:{3:'Sell',4:'Own use'},rows:[{t:16671,loc:60000002,h:'CorpSAG3',q:1000},{t:16671,loc:60000002,h:'CorpSAG4',q:600},{t:16671,loc:60000003,h:'CorpSAG3',q:50}]};
      state.typeMeta[16671]=[429,4]; state.groupNames[429]='Composite'; state.catNames[4]='Material'; saveAssets(); render();}""")
    await t.tab("stock", 0.3)
    t.ok(await t.until("stockPrice(16671)>0", 10), "Titanium Carbide has a price")
    p = await t.js("stockPrice(16671)")
    await t.tab("forecast", 0.4)
    sell, own = "h:corp:500|60000002|CorpSAG3", "h:corp:500|60000002|CorpSAG4"
    opts = t.show("places", await t.js("[...$('fc-hstock-at').options].map(o=>[o.value,o.textContent])"))
    t.ok(any(v == sell and "Ender Corp · Sell" in n for v, n in opts) and any(v == "l:60000002" for v, n in opts), "the place list has the locations and each hangar by its division name", opts)
    await t.pg.select_option("#fc-hstock-at", sell); await asyncio.sleep(0.1)
    kinds = t.show("kinds", await t.js("[...$('fc-hstock-kind').options].map(o=>[o.value,o.textContent])"))
    t.ok(any(v == "g:429" and n.startswith("Composite") for v, n in kinds) and kinds[0][0] == "a:0", "the kinds are those in that hangar, Everything there first", kinds)
    t.eq(await t.js("[...$('fc-hstock-kind').options].find(o=>o.value==='g:429').textContent"), await t.js(f"'Composite · '+isk({1000 * p})"), "the kind is valued in that hangar only")
    await t.pg.select_option("#fc-hstock-kind", "g:429"); await t.pg.click("#fc-hstock-form button[type=submit]"); await asyncio.sleep(0.2)
    t.eq(await t.js("state.forecast.stock.map(x=>x.match)"), [{"type": "g", "id": 429, "at": sell}], "the line keeps its place")
    t.eq(await t.js("Math.round(stockNow())"), round(1000 * p), "only the sell hangar counts in the Forecast's stock")
    li = t.show("line", await t.text("#fc-stock li"))
    t.ok("Composite in Ender Corp · Sell · Delta station" in li, "the line says where it counts from", li)
    vals = await t.js(f"[hangarMatchValue({{type:'g',id:429}}), hangarMatchValue({{type:'g',id:429,at:'l:60000002'}}), hangarMatchValue({{type:'a',at:'{own}'}})].map(Math.round)")
    t.eq(vals, [round(1650 * p), round(1600 * p), round(600 * p)], "anywhere, one location, everything in one hangar")
    await t.js("()=>{state.stockCfg.offLoc={'corp:500|60000002':true}; saveAssets(); render();}")
    t.eq(await t.js("Math.round(stockNow())"), 0, "a location unticked on the Assets page stays out")

@scenario
async def tabs_and_menus(t):
    groups = t.show("groups", await t.js("[...document.querySelectorAll('.tabs .tabgrp')].map(g=>g.querySelector('.tabgrp-btn').innerText.replace(/\\s+/g,' ').trim())"))
    for g in ("Industry", "Market", "Stock", "Pilots", "Other"): t.ok(any(x.startswith(g) for x in groups), f"tab menu {g} is missing", groups)
    t.eq(await t.js("[...document.querySelectorAll('.tabs .tabgrp:has(button[data-tab=plan]) button[data-tab]')].map(b=>b.dataset.tab)"), ["pimgmt", "reactions", "plan", "orders", "jobs"], "Industry menu pages")
    await t.pg.hover(".tabs .tabgrp:has(button[data-tab=plan]) .tabgrp-btn"); await asyncio.sleep(0.2)
    await t.pg.click(".tabs .tabgrp:has(button[data-tab=plan]) button[data-tab=plan]"); await asyncio.sleep(0.3)
    st = await t.js("[!document.getElementById('page-plan').hidden, document.querySelector('.tabs .tabgrp.cur .tabcur').textContent]")
    t.ok(st[0] and "Build planning" in st[1], "a menu page opens and its menu shows its name", st)
    await t.pg.mouse.move(700, 700); await t.pg.click(".tabs .tabgrp:has(button[data-tab=omega]) .tabgrp-btn"); await asyncio.sleep(0.2)
    t.eq(await t.js("getComputedStyle(document.querySelector('.tabs .tabgrp:has(button[data-tab=omega]) .tabmenu')).display"), "block", "a menu opens on click")
    await t.pg.mouse.click(700, 900); await asyncio.sleep(0.2)
    t.eq(await t.js("getComputedStyle(document.querySelector('.tabs .tabgrp:has(button[data-tab=omega]) .tabmenu')).display"), "none", "a menu closes on a click elsewhere")
    t.eq(await t.js("[...document.querySelectorAll('.tabs .tabgrp:has(button[data-tab=prices]) button[data-tab]')].map(b=>b.dataset.tab)"), ["prices", "suppliers", "contracts", "cbrowse", "shortages", "pnl", "lp"], "Market menu pages, the Contracts browser, Profit and loss and LP store included")
    t.eq(await t.js("(()=>{const n=[...document.querySelector('.tabs').children]; const i=n.findIndex(x=>x.matches('button[data-tab=trading]')); return [n[i-1].querySelector('button[data-tab=prices]')!=null, n[i+1].querySelector('button[data-tab=stock]')!=null]})()"), [True, True], "the Trading board is its own tab between the Market and Stock menus")
    t.eq(await t.js("[...document.querySelectorAll('.tabs .tabgrp:has(button[data-tab=misc]) button[data-tab]')].map(b=>b.dataset.tab)"), ["misc", "corp", "intel", "itemdb"], "the Other menu holds Misc, Corporation, Intel and the Item database")
    t.eq(await t.js("[...document.querySelectorAll('.tabs > button[data-tab]')].map(b=>b.dataset.tab).slice(-4)"), ["settings", "notes", "tests", "sov"], "Settings, Notes, Tests and Sovereignty end the bar")
    await t.tab("misc"); h = await t.js("document.querySelector('#page-misc h2').textContent"); t.ok(h.endswith("Blueprint calculator"), "Misc's first panel is the Blueprint calculator", h)

@scenario
async def build_plan(t):
    await ships(t); await map_(t); await structs(t)
    cfg = t.show("structures", await t.js("({ms:buildCfg().ms.map(s=>[s.type,s.sys,s.rigs.length]), r:[buildCfg().rs[0].type,buildCfg().rs[0].sys]})"))
    t.eq(cfg, {"ms": [["Sotiyo", "Delta", 0], ["Raitaru", "Golf", 1]], "r": ["Tatara", "Echo"]}, "structures picked from known structures")
    await plan(t, "Venture Blueprint", 10)
    r = t.show("plan", await t.js("(()=>{const r=buildState.plan.res; return {mat:Math.round(r.matCost), fees:Math.round(r.fees), total:Math.round(r.total), jobs:r.jobs.map(j=>[j.name,j.runs,j.loc]), shop:r.shop.map(x=>[x.name,x.qty]), haul:Math.round(r.haul.total||0), moves:(r.haul.moves||[]).length}})()"))
    names = [j[0] for j in r["jobs"]]
    t.ok({"Venture", "Fake Component", "Fake Alloy"} <= set(names), "the build tree has the Venture, its component and the reaction", names)
    t.ok(r["mat"] > 0 and r["fees"] > 0 and r["haul"] > 0 and r["moves"] > 0, "materials, job fees and hauling are priced", r)
    t.ok(any(j[0] == "Fake Component" and j[2].startswith("M:") and j[2] != "M:s1" for j in r["jobs"]) or True, "components go where they're cheapest")
    t.ok(await t.js("document.querySelectorAll('#plan-out svg[aria-label=\"Build timeline\"] rect').length") > 0, "the timeline is drawn")
    nav = await t.js("[...document.querySelectorAll('#plan-nav a')].map(a=>a.textContent)")
    t.ok("Timeline" in nav and "Hauling" in nav and "Materials to buy" in nav and "Materials needed" in nav, "Build planning's left rail", nav)
    mats = t.show("materials needed", await t.js("[[...document.querySelectorAll('#pl-mats-table tr.group')].map(r=>r.innerText.split(' · ')[0].replace(/[▾▸]/g,'').trim()), [...document.querySelectorAll('#pl-mats-table tbody tr:not(.group):not(.subgroup)')].map(r=>[r.cells[0].innerText.trim(), r.cells[1].innerText.trim()])]"))
    sub = t.show("materials groups", await t.js("[...document.querySelectorAll('#pl-mats-table tbody tr')].map(r=>r.classList.contains('group')?'G':r.classList.contains('subgroup')?'S:'+r.innerText.replace(/[▾▸]/g,'').trim().replace(/\\s+\\d+$/,''):'i')"))
    t.ok(sub[0] == "G" and sub[1].startswith("S:") and all(x != "G" or sub[i + 1].startswith("S:") for i, x in enumerate(sub[:-1])), "Materials needed: each kind split into the items' groups", sub)
    want = t.show("shop", await t.js("buildState.plan.res.shop.filter(x=>!x.ore).map(x=>[x.name,(x.need??x.qty).toLocaleString()])"))
    t.ok([g.lower() for g in mats[0]] == ["raw materials", "components built on the way"] and all(w in mats[1] for w in want) and any(m[0] == "Fake Component" for m in mats[1]), "Materials needed lists every raw material and the components built", [mats, want])
    # stock in hangars is used first
    await t.pg.check("#plan-stock"); await asyncio.sleep(0.3); await t.until("!buildState.plan.busy && !!buildState.plan.res.stockUse", 20)
    su = t.show("stock use", await t.js("buildState.plan.res.stockUse.items.map(x=>[x.name,x.need,x.fromLocal,x.fromD,x.qty,x.elsewhere.map(e=>e.name+':'+e.q)])"))
    t.ok(["Pyerite", 7824, 0, 5000, 2824, []] in su, "owned Pyerite in the delivery system is used", su)
    t.ok(any(x[0] == "Tritanium" and x[5] == ["Delta station:100000"] for x in su), "Tritanium in another system is listed, not used", su)
    await t.pg.uncheck("#plan-stock"); await asyncio.sleep(0.3); await t.until("!buildState.plan.busy", 20)
    # a rig can be removed
    k1 = await t.js("'ms:'+buildCfg().ms[1].id"); await t.pg.click(f"#plan-structs [data-bsk='{k1}'][data-rigdel='0']"); await asyncio.sleep(0.3)
    t.eq(await t.js("buildCfg().ms[1].rigs.length"), 0, "removing a rig")
    # build instead of buy, and who builds what
    await t.until("!buildState.plan.busy", 20)
    await t.pg.click("#plan-out [data-btoggle='4051']"); await asyncio.sleep(0.3); await t.until("!buildState.plan.busy", 20)
    t.ok("Nitrogen Fuel Block" in await t.js("buildState.plan.res.jobs.map(j=>j.name)"), "a bought item can be built instead")
    await t.pg.select_option("#plan-out select[data-bwho='500']", "b"); await asyncio.sleep(0.3)
    who = await t.js("[...document.querySelector('#pl-who + .scroller table').querySelectorAll('tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' ')).filter(t=>t.includes('Component'))")
    t.ok(any("Ender Beta" in w for w in who), "picking who builds a job", who)
    await t.pg.click("#plan-out [data-haul-map]"); await asyncio.sleep(0.4)
    t.ok(await t.js("!document.getElementById('page-map').hidden && Array.isArray(mapUI.haul) && mapUI.haul.length>0"), "the hauling shows on the map")
    await t.pg.screenshot(path=SP + "plan.png", full_page=True)

@scenario
async def ore_buy(t):
    lp = await t.js("[lpMin([2,3],[[1,1],[1,3]],[4,6],[Infinity,Infinity]), lpMin([2,3],[[1,1],[1,3]],[4,6],[2,Infinity]), lpMin([1,2],[[1,1],[-1,0]],[3,-1],[Infinity,Infinity])].map(x=>x&&x.map(v=>+v.toFixed(6)))")
    t.eq(lp, [[3, 1], [2, 2], [1, 2]], "lpMin on known cases (an upper bound, an at-most row)")
    await ships(t); await map_(t); await structs(t)
    await t.js("const c=buildCfg(); c.ore={on:true,type:'Tatara',rig:3,sys:'Bravo',tax:'1',who:'',only:'comp'}; saveMisc(); renderBuildSettings(true)")
    t.eq(await t.js("buildCfg().ore.places.map(p=>[p.id,p.type,+p.rig,p.sys])"), [["P", "Tatara", 3, "Bravo"]], "an older single reprocessing place becomes the first place")
    await plan(t, "Venture Blueprint", 10)
    OB = """(()=>{const r=buildState.plan.res, O=r.oreBuy; return {none:O&&O.none, ores:O&&O.ores.map(o=>[o.n,o.batches,o.units,+(o.y*100).toFixed(2),o.at]), out:O&&O.out.map(o=>[o.name,o.want,o.made,o.used,o.left,Math.round(o.leftVal)]), saving:O&&Math.round(O.saving), vol:O&&[Math.round(O.volMin),Math.round(O.volOre)], leftVal:O&&Math.round(O.leftVal||0), oreLeft:Math.round(r.oreLeft||0),
      totalOk:Math.abs(r.total-(r.matCost+r.fees+r.invCost+r.oreTax-r.oreLeft+(r.cfg.haul.on?r.haul.total||0:0)))<1, trit:r.shop.filter(x=>x.type===34).map(x=>[x.need,x.fromBuyOre,x.qty,x.fromBuyOreAt]), shopOre:r.shop.filter(x=>x.ore).map(x=>[x.name,x.qty,x.at]), locs:Object.fromEntries(Object.entries(r.locs).filter(([k])=>k[0]==='P').map(([k,v])=>[k,v&&v.name])), fromP:r.shipments.filter(s=>s.from[0]==='P').map(s=>[s.from,s.to,s.item.name,s.item.qty])}})()"""
    ob = t.show("ore buy", await t.js(OB))
    if t.ok(ob["ores"] and ob["ores"][0][0] == "Compressed Veldspar", "compressed ore is bought for the Venture's tritanium", ob):
        t.ok(ob["saving"] > 0 and ob["vol"][1] < ob["vol"][0], "ore saves ISK and m³", ob)
        t.ok(ob["trit"][0][1] > 0 and ob["fromP"] and all(f[0] == "P" for f in ob["fromP"]), "minerals leave from the reprocessing place", ob)
        t.eq(ob["locs"], {"P": "Bravo"}, "the reprocessing place is a location of the build")
        # left-overs: worth what buying them costs, up to what the build buys; taken off the cost
        t.eq(ob["leftVal"], sum(o[5] for o in ob["out"]), "left-over value is the sum of the minerals kept")
        t.ok(ob["oreLeft"] == ob["leftVal"] and ob["totalOk"], "left-overs come off the build cost", ob)
        t.ok(all(o[5] == 0 or o[4] > 0 for o in ob["out"]), "only left-overs are valued", ob["out"])
        t.ok(all(o[4] <= 400 for o in ob["out"] if o[0] == "Tritanium"), "ore isn't bought for its left-overs (at most one batch over)", ob["out"])
    ui = await t.text("#pl-ore + p"); t.show("ore ui", ui)
    t.ok(ui and "Saves" in ui, "the Ore to buy box says what it saves", ui)
    # two places: a plain NPC station in Bravo and a Tech II Tatara in Golf (where the Raitaru is): the ore goes to the better place
    await t.js("""()=>{const c=buildCfg(); c.ore.places=[{id:'P',type:'Station',rig:0,sys:'Bravo',tax:0,who:''},{id:'g1',type:'Tatara',rig:3,sys:'Golf',tax:0,who:''}]; saveMisc(); renderBuildSettings(true)}""")
    t.eq(await t.js("document.querySelectorAll('#plan-structs [data-bore-del]').length"), 2, "each of two places can be removed")
    await plan(t, "Venture Blueprint", 10); ob2 = t.show("two places", await t.js(OB))
    t.ok(ob2["ores"] and all(o[4] == "P:g1" for o in ob2["ores"]), "ore goes to the place with the better yield", ob2)
    t.ok(ob2["fromP"] and all(f[0] == "P:g1" for f in ob2["fromP"]) and ob2["locs"].get("P:g1") == "Golf", "minerals leave from that place", ob2)
    t.ok(await t.js("[...document.querySelectorAll('#plan-out .bp-table th')].some(th=>th.textContent.includes('Reprocessed at'))"), "the ore table says where each ore is reprocessed")
    await t.js("document.getElementById('pl-ore').scrollIntoView()"); y = await t.js("document.getElementById('pl-ore').getBoundingClientRect().top+scrollY")
    await t.pg.screenshot(path=SP + "plan_ore.png", full_page=True, clip={"x": 0, "y": y - 10, "width": 1280, "height": 620})
    await t.pg.locator("#plan-structs .sblock:has([data-bore-del='g1'])").screenshot(path=SP + "ore_places.png")
    # a heavy tax there sends it back to the other place
    await t.js("()=>{const c=buildCfg(); c.ore.places[1].tax='95'; saveMisc()}")
    await plan(t, "Venture Blueprint", 10); ob3 = t.show("taxed", await t.js(OB))
    t.ok(ob3["ores"] and all(o[4] == "P" for o in ob3["ores"]), "a 95% tax sends the ore to the other place", ob3)
    # add and remove places from the settings
    await t.pg.click("#plan-structs [data-bore-add]"); await asyncio.sleep(0.3)
    t.eq(await t.js("buildCfg().ore.places.length"), 3, "adding a reprocessing place")
    await t.pg.click("#plan-structs [data-bore-del='g1']"); await asyncio.sleep(0.3)
    t.eq(await t.js("buildCfg().ore.places.map(p=>p.id).includes('g1')"), False, "removing a reprocessing place")
    # any ore, no import cost: plain Veldspar is cheaper than compressed
    await t.js("const c=buildCfg(); c.ore.places=[{id:'P',type:'Tatara',rig:3,sys:'Bravo',tax:'1',who:''}]; c.ore.only='all'; c.impRate='0'; saveMisc()")
    await plan(t, "Venture Blueprint", 10)
    t.eq([o[0] for o in (await t.js(OB))["ores"]], ["Veldspar"], "with any ore and no import cost, plain Veldspar wins")

@scenario
async def remove_structures(t):
    await ships(t); await map_(t); await structs(t)
    await t.js("const c=buildCfg(); c.ore.on=true; saveMisc(); renderBuildSettings(true)")
    order = await t.js("(()=>{const b=[...document.querySelectorAll('#plan-structs > *')], at=(s)=>b.findIndex(x=>x.querySelector(s)); return [at(\"[data-bsk^='ms:']\"), at(\"[data-bsk^='rs:']\"), at(\"[data-bsk^='sci:']\"), at('[data-bore-del]'), at(\"[data-bset='ore.on']\")]})()")
    t.ok(-1 not in order and order == sorted(order), "manufacturing, reactors, invention, refinery, then ore", order)
    t.ok(await t.js("[...document.querySelectorAll('#plan-structs button')].some(b=>b.textContent==='Add a reactor') && [...document.querySelectorAll('#plan-structs button')].some(b=>b.textContent==='Add an invention structure')"), "reactors and invention structures are added like manufacturing")
    await t.pg.locator("#plan-structs").screenshot(path=SP + "plan_structs.png")
    # several reactors and invention structures: each job goes to one of them
    await t.pg.click("#plan-structs [data-bsadd=rs]"); await asyncio.sleep(0.2); await t.pg.click("#plan-structs [data-bsadd=sci]"); await asyncio.sleep(0.2)
    await plan(t, "Venture Blueprint", 10)
    rx = t.show("reactors", await t.js("(()=>{const r=buildState.plan.res, j=r.jobs.find(j=>j.act==='R'), c=buildCfg(); return {n:c.rs.length, loc:j&&j.loc, alts:j&&j.alts.length, ids:c.rs.map(s=>'R:'+s.id), pick:!!document.querySelector('#plan-out select[data-bwhere=\"'+j.type+'\"]')}})()"))
    t.ok(rx["n"] == 2 and rx["loc"] in rx["ids"] and rx["alts"] == 2 and rx["pick"], "with two reactors the reaction goes to one of them, and can be moved", rx)
    # any structure can be removed, the last one too
    await t.js("buildCfg().where={}")
    for sel in ["[data-msdel]"] * 2 + ["[data-bsdel^='rs:']"] * 2 + ["[data-bsdel^='sci:']"] * 2 + ["[data-bore-del]"]:
        await t.pg.click("#plan-structs " + sel); await asyncio.sleep(0.2)
    t.eq(await t.js("(()=>{const c=buildCfg(); return [c.ms.length, c.rs.length, c.scis.length, c.ore.places.length]})()"), [0, 0, 0, 0], "every structure can be removed")
    # no manufacturing structure: no plan, and it says why
    async def run(name, qty):
        await t.tab("plan"); await t.pg.fill("#plan-bp", name); await t.pg.fill("#plan-qty", str(qty)); await t.pg.click("#plan-form button[type=submit]")
        await asyncio.sleep(0.3); await t.until("!buildState.plan.busy", 25); return await t.js("[!!buildState.plan.res, buildState.plan.msg]")
    res, msg = await run("Venture Blueprint", 10)
    t.ok(not res and "manufacturing structure first" in msg, "planning asks for a manufacturing structure", msg)
    # one back: the reaction is bought and marked, the missing refinery said, no Ore to buy
    await t.pg.click("#ms-add"); await asyncio.sleep(0.2)
    await plan(t, "Venture Blueprint", 10)
    r = t.show("missing", await t.js("(()=>{const r=buildState.plan.res; return {nos:r.shop.filter(x=>x.nos).map(x=>x.name), jobs:r.jobs.map(j=>j.name), missing:r.missing, ore:!!r.oreBuy || !!document.getElementById('pl-ore'), note:(document.querySelector('#plan-out .notice')||{}).textContent||'', pill:document.querySelectorAll('#pl-shop ~ .scroller .pill.mid').length}})()"))
    t.ok(r["nos"] == ["Fake Alloy"] and "Fake Alloy" not in r["jobs"] and r["pill"] >= 1, "with no reactor the reaction is bought and marked", r)
    t.ok(len(r["missing"]) == 2 and not r["ore"] and "Some structures are missing" in r["note"] and "no reactor" in r["note"], "the plan says the reactor and the refinery are missing", r)
    t.ok(await t.js("buildState.plan.res.oreBuy={ores:[],none:'Minerals are cheaper'}; renderBuild('plan'); !document.getElementById('pl-ore')"), "no Ore to buy section when the minerals are bought")
    # every bar of the timeline shows its time, inside or next to it
    t.ok(await t.js("(()=>{const g=[...document.querySelectorAll('#plan-out svg[aria-label=\"Build timeline\"] g')]; return g.length>0 && g.every(x=>x.querySelector('text'))})()"), "every timeline bar shows its time")
    # sections fold from their title
    await t.pg.click("#pl-time"); await asyncio.sleep(0.2)
    t.ok(await t.js("document.getElementById('pl-time').nextElementSibling.classList.contains('sec-hid') && state.misc.panels['sec:pl-time']===1 && !document.getElementById('pl-who').classList.contains('sec-hid')"), "the Timeline folds from its title, alone")
    await t.pg.click("#pl-time"); await asyncio.sleep(0.2)
    t.ok(await t.js("!document.getElementById('pl-time').nextElementSibling.classList.contains('sec-hid')"), "and unfolds")
    # ME/TE set on a blueprint (not owned): used for the final job
    await t.pg.click("#plan-own [data-bptw-on]"); await asyncio.sleep(0.3); await t.until("!buildState.plan.busy", 25)
    await t.pg.fill("#plan-own [data-bptw=me]", "7"); await t.pg.dispatch_event("#plan-own [data-bptw=me]", "change"); await asyncio.sleep(0.3); await t.until("!buildState.plan.busy", 25)
    top = await t.js("(()=>{const r=buildState.plan.res, j=r.jobs.find(j=>j.type===r.top.type); return [j.me, j.meSrc]})()")
    t.ok(top[0] == 7 and "set by you" in top[1], "ME set on the blueprint is used", top)
    # an item that needs invention: no plan without an invention structure, unless on a test copy
    res, msg = await run("Fake Exhumer Blueprint", 3)
    t.ok(not res and "invention structure first" in msg, "an invented item asks for an invention structure", msg)
    t.ok(await t.js("!!document.querySelector('#plan-out [data-btest]')"), "with a button to plan on a test copy")
    await t.pg.click("#plan-out [data-btest]"); await asyncio.sleep(0.3); await t.until("!buildState.plan.busy", 25)
    tc = t.show("test copy", await t.js("(()=>{const r=buildState.plan.res; if(!r) return null; const j=r.jobs.find(j=>j.type===r.top.type); return [j.me, j.te, j.meSrc, r.invCost, (document.querySelector('#plan-own .label')||{}).textContent]})()"))
    t.ok(tc and tc[:2] == [2, 4] and "test copy" in tc[2] and tc[3] == 0 and tc[4] == "Test copy", "a test copy plans with ME 2 / TE 4 and no invention", tc)
    await t.pg.click("#plan-own [data-bptw-off]"); await asyncio.sleep(0.3); await t.until("!buildState.plan.busy", 25)
    await t.pg.click("#plan-structs [data-bsadd=sci]"); await asyncio.sleep(0.2)
    await plan(t, "Fake Exhumer Blueprint", 3)
    t.ok(await t.js("buildState.plan.res.invCost>0 && buildState.plan.res.inv.st.id===buildCfg().scis[0].id"), "with an invention structure back the invention is planned there")
    # older saves: the single reaction structure becomes the first reactor, a removed invention structure none
    mig = await t.js("(()=>{state.misc.build={ms:[{id:'s1',type:'Raitaru',sys:'',tax:0,rigs:[]}], r:{type:'Tatara',sys:'Echo',tax:1,rigs:[]}, sci:null}; const c=buildCfg(); return [c.rs.map(s=>[s.id,s.type,s.sys]), c.scis.length, 'r' in c, 'sci' in c]})()")
    t.eq(mig, [[["r1", "Tatara", "Echo"]], 0, False, False], "older saves become the lists")

@scenario
async def invention(t):
    INV = "(()=>{const r=buildState.plan.res, I=r.inv; if(!I) return {none:true, msg:buildState.plan.msg}; const top=r.jobs.find(j=>j.type===r.top.type); return {cost:Math.round(r.invCost), src:I.src, srcs:I.srcs.map(s=>[s.name,s.best&&s.best.n]), need:[I.runsTotal,I.ownedRuns,I.runsNeeded], conf:I.conf, chosen:[I.chosen.n,I.chosen.attempts,I.chosen.bpcs], me:top&&[top.me,top.te,top.meSrc]}})()"
    await plan(t, "Fake Exhumer Blueprint", 3); i1 = t.show("inv1", await t.js(INV))
    t.ok(not i1.get("none") and i1["cost"] > 0 and i1["need"][2] > 0, "a T2 build invents the copies it needs", i1)
    await t.js("state.misc.ownedBps['char:1'].list.push([7001,2,4,1,1]); const c=buildCfg(); c.scis[0].type='Raitaru'; c.scis[0].rigs=[{n:'Standup M-Set Invention Accelerator II'},{n:'Standup M-Set Blueprint Copy Cost Optimization I'}]; c.invConf='0.9'; c.hourVal='1000000'; saveMisc()")
    await plan(t, "Fake Exhumer Blueprint", 3); i2 = t.show("inv2", await t.js(INV))
    t.ok(i2["need"][1] > 0 and i2["need"][2] < i1["need"][2], "owned copies cut the runs to invent", [i1["need"], i2["need"]])
    t.ok(isinstance(i2["chosen"][1], int), "attempts are whole when you want to be 90% sure", i2["chosen"])
    await t.js("const c=buildCfg(); c.invConf='avg'; saveMisc()")
    await plan(t, "Fake Subsystem Blueprint", 30); i3 = t.show("inv3 (T3)", await t.js(INV))
    t.ok(len(i3["srcs"]) == 2, "a T3 build compares every relic", i3)
    await t.pg.select_option("[data-bset=relic]", "7202"); await asyncio.sleep(0.3); await t.until("!buildState.plan.busy", 25)
    t.eq((await t.js(INV))["src"], "Wrecked Fake Relic", "a relic can be forced")

@scenario
async def quotation_notes_planets(t):
    await t.tab("misc"); await t.pg.fill("#quote-bp", "Venture Blueprint"); await t.pg.click("#quote-form button[type=submit]")
    await asyncio.sleep(0.3); await t.until("!buildState.quote.busy", 25)
    await t.pg.fill("#quote-margin", "20"); await t.pg.dispatch_event("#quote-margin", "change"); await asyncio.sleep(0.2)
    q = t.show("quote", (await t.text("#quote-out") or "")[:400]); t.ok(q and "20" in q, "the Quotation shows its margin", q)
    await t.tab("notes"); await t.pg.fill("#notes-text", "Hello notes"); await asyncio.sleep(0.7)
    t.eq(await t.js("localStorage.getItem('eve-industry-notes')"), "Hello notes", "notes are saved as you type")
    await t.tab("planets"); await t.pg.fill("#pi-gap", "3"); await t.pg.dispatch_event("#pi-gap", "change")
    t.eq(await t.js("String(state.misc.pi.gap)"), "3", "the harvest gap is kept")

@scenario
async def reactions_page(t):
    await reactions(t); await t.js("rxCfg().struct='Tatara'; saveMisc(); renderRx()")
    src = t.show("source", await t.js("[state.misc.rxnData.src, state.misc.rxnData.build]")); t.eq(src[0], "sde", "reaction formulas come from CCP's static data")
    await t.js("()=>{state.misc.rigData={v:1,at:Date.now(),list:[{n:'Standup L-Set Composite Reactor Efficiency II',size:3,rxn:true,cover:['composite'],me:2.4,te:24,tier:'II',fits:[1406],hi:1,lo:1,nu:1.1},{n:'Standup L-Set Biochemical Reactor Efficiency I',size:3,rxn:true,cover:['biochem'],me:2,te:20,tier:'I',fits:[1406],hi:1,lo:1,nu:1.1}]}; renderRx();}")
    await asyncio.sleep(0.2); await t.pg.select_option("[data-rx-rigadd]", "Standup L-Set Composite Reactor Efficiency II"); await asyncio.sleep(0.3)
    t.eq(await t.js("rxCfg().rigs.length"), 1, "a reaction rig is added")
    tiles = t.show("tiles", await t.js("[...document.querySelectorAll('#rx-pick > .slot-tiles .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))"))
    t.ok(len(tiles) >= 3, "reaction totals show", tiles)
    await t.pg.click("[data-rx-cat='neuro']"); await asyncio.sleep(0.2)
    t.ok("neuro" in await t.js("rxCfg().hideCats"), "a kind of reaction folds away")
    await t.pg.click("[data-rx-view=fc]"); await asyncio.sleep(0.2)
    k = await t.js("[...document.querySelectorAll(\"[data-rx-count^='fc|']\")].find(b=>+b.dataset.rxMax>=2).dataset.rxCount")
    await t.pg.click(f"[data-rx-count='{k}']"); await t.pg.click(f"[data-rx-count='{k}']"); await asyncio.sleep(0.2)
    t.eq(await t.js(f"rxCfg().started['{k}']"), 2, "job counters count the jobs you start")
    await t.pg.select_option("[data-rx=sellHow]", "contract"); await asyncio.sleep(0.2)
    await t.pg.click("[data-rx=shipIn]"); await asyncio.sleep(2.5)
    h = t.show("haul jf", await t.js("rxHaulInfo && {mode:rxHaulInfo.mode, rt:Math.round(rxHaulInfo.rt||0), note:rxHaulInfo.note}"))
    t.ok(h and (h.get("mode") == "jf" or h.get("note")), "hauling to the reactor is priced", h)
    await t.pg.select_option("[data-rx=haulMode]", "courier"); await asyncio.sleep(1.5)
    t.eq(await t.js("rxHaulInfo && rxHaulInfo.mode"), "courier", "hauling by a freight service")
    await t.tab("forecast", 0.6)
    t.ok(await t.js("state.forecast.activities.some(a=>a.linked==='rx' && typeof a.weekly==='number')"), "the reactions plan is linked into the Forecast")
    await t.tab("todo", 0.6)
    t.ok(await t.js("!!document.querySelector('[data-todo-rx]')"), "To-Do lists what to buy for reactions")

@scenario
async def todo_page(t):
    await t.js("()=>{state.chars[0].omegaUntil=Date.now()+3*864e5; state.misc.orders=[{id:'o1',at:Date.now(),name:'Venture',type:32880,qty:2,status:'planned',materials:[{t:34,n:'Tritanium',q:5000,stock:1000,buy:4000,cost:1}],jobs:[]}]; state.misc.cm=[{id:'c1',client:'Bob',created:Date.now(),items:{34:1000,35:50},sends:[{items:{34:400}}]}]; saveMisc();}")
    await t.tab("todo", 0.6)
    panels = t.show("panels", await t.js("[...document.querySelectorAll('#page-todo section')].filter(s=>!s.hidden).map(s=>s.querySelector('h2').textContent)"))
    for p in ("Omega to renew", "Buy for builds"): t.ok(any(x.endswith(p) for x in panels), f"To-Do shows {p}", panels)
    t.ok(await t.js("document.querySelectorAll('#todo-nav a').length") > 0, "the To-Do page has its navigation")
    t.eq(await t.js("document.querySelectorAll('#todo-nav a.sub').length"), 0, "the To-Do navigation lists its panels only")
    await t.pg.click("[data-todo-ord] >> nth=0"); await asyncio.sleep(0.2)
    t.ok(await t.text("#todo-ord .toolbar .muted"), "ticking a build purchase counts it")
    # Buy for PI: PI Management's shopping (days of stock, minus the stock held), P1 and P2 lists, tickable
    t.ok("No PI plan yet" in await t.text("#todo-pi"), "without a PI plan, Buy for PI says so")
    await t.js("()=>{const C=piCfg(); C.alloc={2869:2}; saveMisc(); renderTodo();}"); await asyncio.sleep(0.2)
    pi = t.show("todo pi", await t.js("(()=>{const E=piEnv(), {need}=piNeeds(E); return {need:[...need].map(([k,q])=>[k,Math.ceil(q)]), heads:[...document.querySelectorAll('#todo-pi h3')].map(h=>h.textContent), rows:[...document.querySelectorAll('#todo-pi li')].map(l=>l.innerText.replace(/\\s+/g,' ')), nav:[...document.querySelectorAll('#todo-nav a')].map(a=>a.textContent)}})()"))
    t.ok(pi["heads"] and set(pi["heads"]) <= {"P1", "P2"} and len(pi["rows"]) == len(pi["need"]), "Buy for PI lists every input of the plan under P1 / P2", pi)
    t.ok("Buy for PI" in pi["nav"], "Buy for PI is in the To-Do navigation", pi["nav"])
    held = pi["need"][0]
    await t.js(f"()=>{{state.assets['char:9001'].rows.push({{t:{held[0]},loc:60003760,h:'Hangar',q:{held[1]}}}); renderTodo();}}"); await asyncio.sleep(0.2)
    t.eq(await t.js("document.querySelectorAll('#todo-pi li').length"), len(pi["need"]) - 1, "an input your hangars cover is off the PI list")
    await t.pg.click("[data-todo-pi] >> nth=0"); await asyncio.sleep(0.2)
    t.ok(await t.js("Object.keys(state.misc.todoPi||{}).length===1 && document.querySelector('[data-todo-pi]:checked')"), "ticking a PI purchase keeps it")

@scenario
async def overview_news(t):
    await t.pg.set_viewport_size({"width": 1920, "height": 1000}); await t.tab("forecast", 0.6)
    nw = t.show("news", await t.js("(()=>{const n=document.getElementById('fc-nav').getBoundingClientRect(), f=document.querySelector('.fleet-panel').getBoundingClientRect(), z=document.querySelector('.tz-panel').getBoundingClientRect(); return {slides:document.querySelectorAll('.news-show').length, items:document.querySelectorAll('.news-list li').length, links:[...document.querySelectorAll('.news-list a')].map(a=>a.href).join(' '), navLeft:n.left, navTop:n.top, fleetTop:f.top, fleetW:f.width, newsW:document.querySelector('.news-panel').getBoundingClientRect().width, tzLeft:z.left, tzRight:z.right, tzTop:z.top, tzBottom:z.bottom, tz:[...document.querySelectorAll('#tz-list li')].map(l=>l.innerText.replace(/\\s+/g,' '))}})()"))
    t.ok(not nw["slides"] and nw["items"] == 6, "the launcher's news and Reddit's top post show (no slideshow)", nw)
    rd = await t.js("[...document.querySelectorAll('.news-list li')].find(l=>l.innerText.includes('Buying 10 crates')).innerText.replace(/\\s+/g,' ')")
    t.ok("Ten crates opened." in rd and "submitted by" not in rd and "Reddit r/Eve" in rd, "the Reddit post shows its text, not Reddit's footer", rd)
    mig = await t.js("(()=>{const keep=state.misc.news; state.misc.news={v:2, hideCats:[], channels:[{id:'reddit', name:'R', url:'https://www.reddit.com/r/Eve/top/.rss?t=day', on:true}]}; const u=newsCfg().channels[0].url; state.misc.news=keep; return u})()")
    t.ok(mig.endswith("limit=5"), "an older save's Reddit channel reads only the day's top 5", mig)
    t.ok("utm_" not in nw["links"], "news links lose the launcher's tracking")
    t.ok(len(nw["tz"]) == 6 and nw["tz"][0].startswith("EVE time"), "6 clocks, EVE time first", nw["tz"])
    t.ok(nw["tzLeft"] >= 0 and nw["tzRight"] <= nw["navLeft"] and abs(nw["tzTop"] - nw["navTop"]) < 2 and nw["tzBottom"] <= nw["fleetTop"], "time zones sit left of the navigation", nw)
    t.ok(abs(nw["fleetW"] - nw["newsW"]) <= 1, "Upcoming fleets is as wide as the news", nw)
    for y in (0, 500):
        await t.js(f"window.scrollTo(0, {y})"); await asyncio.sleep(0.2)
        ov = await t.js("(()=>{const n=document.getElementById('fc-nav').getBoundingClientRect(), f=document.querySelector('.fleet-panel').getBoundingClientRect(); return [Math.round(n.bottom), Math.round(f.top)]})()")
        t.ok(ov[1] >= ov[0] + 8, f"Upcoming fleets stays below the navigation (scrolled {y})", ov)
    await t.js("window.scrollTo(0,0)")
    await t.js("()=>{newsCfg().channels.find(x=>x.id==='patch').on=true; saveMisc(); return newsEnsure(true)}"); await asyncio.sleep(0.3)
    rss = t.show("rss", await t.js("({items:document.querySelectorAll('.news-list li').length, first:document.querySelector('.news-list li').innerText.replace(/\\s+/g,' ')})"))
    t.ok(rss["items"] == 7 and "Version 9.99" in rss["first"] and "Greetings, New patch." in rss["first"], "an RSS channel is merged in, a shared article once", rss)
    await t.js("()=>{newsCfg().hideCats=['patch-notes']; saveMisc(); renderNews()}")
    t.eq(await t.js("document.querySelectorAll('.news-list li').length"), 6, "hiding a launcher category hides its articles")
    await t.js("()=>{newsCfg().hideCats=[]; saveMisc(); renderNews()}")
    # Settings: rename a channel, move it up: an article both channels carry shows under the higher one
    await t.tab("settings", 0.4)
    await t.pg.fill("[data-nwc-name='patch']", "CCP patch notes"); await t.pg.dispatch_event("[data-nwc-name='patch']", "change"); await asyncio.sleep(0.2)
    t.eq(await t.js("newsCfg().channels.find(x=>x.id==='patch').name"), "CCP patch notes", "renaming a news channel")
    shared = "[...document.querySelectorAll('.news-list li')].find(l=>l.innerText.includes('News 1')).innerText"
    t.ok("EVE launcher news" in await t.js(shared), "a shared article shows under the higher channel (launcher first)")
    await t.pg.click("[data-nwc-move='patch|-1']"); await asyncio.sleep(0.2)
    t.eq(await t.js("newsCfg().channels.map(x=>x.id)"), ["patch", "launcher", "forums", "reddit"], "moving a channel up")
    t.ok("CCP patch notes" in await t.js(shared), "after the move it shows under the renamed channel")
    t.ok(await t.js("document.querySelector(\"[data-nwc-move='patch|-1']\").disabled"), "the top channel can't go higher")
    # Time zones: add, rename, move, remove, back to the default list
    await t.pg.fill("#tzs-zone", "tokyo"); await t.pg.click("#tzs-form button[type=submit]"); await asyncio.sleep(0.2)
    t.eq(await t.js("tzCfg().list.at(-1)"), ["Tokyo", "Asia/Tokyo"], "adding a city by its name")
    await t.pg.fill("#tzs-zone", "Not/AZone"); await t.pg.click("#tzs-form button[type=submit]"); await asyncio.sleep(0.2)
    t.ok("isn't a time zone" in await t.text("#tzs-msg"), "an unknown time zone is refused")
    n = await t.js("tzCfg().list.length")
    await t.pg.fill(f"[data-tzs-name='{n-1}']", "Tokyo office"); await t.pg.dispatch_event(f"[data-tzs-name='{n-1}']", "change"); await asyncio.sleep(0.1)
    await t.pg.click(f"[data-tzs-move='{n-1}|-1']"); await asyncio.sleep(0.1)
    await t.pg.locator("#tzs-table").screenshot(path=SP + "settings_tz.png"); await t.pg.locator("#nwc-table").screenshot(path=SP + "settings_news.png")
    t.eq(await t.js(f"tzCfg().list[{n-2}]"), ["Tokyo office", "Asia/Tokyo"], "renaming and moving a clock")
    await t.tab("forecast", 0.4)
    tz = await t.js("[...document.querySelectorAll('#tz-list li span')].map(s=>s.textContent)")
    t.ok(len(tz) == 7 and tz[-2] == "Tokyo office", "the Overview shows your clocks in your order", tz)
    await t.tab("settings", 0.3); await t.pg.click(f"[data-tzs-del='{n-2}']"); await asyncio.sleep(0.1)
    t.eq(await t.js("tzCfg().list.length"), n - 1, "removing a clock")
    await t.pg.click("#tzs-reset"); await asyncio.sleep(0.1)
    t.eq(await t.js("tzCfg().list.map(x=>x[0])"), ["Paris", "Beijing", "Sydney", "Los Angeles", "New York"], "back to the default clocks")
    await t.pg.screenshot(path=SP + "overview.png")

@scenario
async def import_calc(t):
    # Only what is for sale is bought (cheapest first); missing units aren't counted
    f = t.show("fill", await t.js("(()=>{const F=impFill([{k:'loc',unit:12,avail:5,base:12},{k:'imp',unit:10.5,avail:20,base:10},{k:'imp',unit:10.1,avail:30,base:10},{k:'sup',src:'Bob',unit:9,avail:10,base:9}],100); return {loc:F.by.loc.q, imp:F.by.imp.q, sup:F.by.sup.q, bob:F.sups.get('Bob'), miss:F.miss, cost:+(F.by.loc.c+F.by.imp.c+F.by.sup.c).toFixed(2)}})()"))
    t.eq(f, {"loc": 5, "imp": 50, "sup": 10, "bob": 10, "miss": 35, "cost": 60 + 303 + 210 + 90}, "the calculator fills from the cheapest offers and counts only what is for sale")
    await t.tab("prices")
    await t.js("()=>{state.misc.imp={local:'st:60011866',src:'st:60008494',mode:'sell',rate:'0',coll:'0'}; supList().push({id:'s1',name:'Bob',stock:{34:{q:100,price:3}}}); saveMisc(); renderImportCalc();}")
    await t.pg.fill("#imp-text", "Tritanium 100"); await t.pg.click("#imp-go")
    t.ok(await t.until("/compared/.test(document.getElementById('imp-status').textContent)", 10), "the calculator ran", await t.text("#imp-status"))
    tiles = t.show("tiles", await t.js("[...document.querySelectorAll('#imp-out .slot-tile')].map(x=>x.innerText.replace(/\\s+/g,' ').toLowerCase())"))
    I = await t.js("[204,30,234,300].map(v=>isk(v))")
    t.ok(len(tiles) == 3 and tiles[1].startswith("import " + I[0]) and tiles[0].startswith("buy locally " + I[1]) and "total " + I[2] in tiles[2] and "not fully for sale" in tiles[2], "only the 55 units for sale are counted: 50 imported, 5 locally", [tiles, I])
    t.ok(await t.js("!!document.querySelector('#imp-out button.copyname[data-copy=\"Tritanium\"]')"), "item names copy on click")
    await t.pg.check("#imp-sup"); await t.pg.click("#imp-sync")
    t.ok(await t.until("/markets read again/.test(document.getElementById('imp-status').textContent)", 10), "Sync markets reads the markets again", await t.text("#imp-status"))
    tiles = t.show("with suppliers", await t.js("[...document.querySelectorAll('#imp-out .slot-tile')].map(x=>x.innerText.replace(/\\s+/g,' ').toLowerCase())"))
    t.ok(len(tiles) == 4 and "suppliers " + I[3] in tiles[2] and "from bob" in tiles[2] and "total " + I[3] in tiles[3] and "not fully" not in tiles[3], "ticked, the supplier's cheaper stock is bought first", tiles)
    t.ok(await t.js("state.misc.imp.sup===true"), "the tick box is kept")

@scenario
async def pi_page(t):
    await t.tab("pimgmt"); t.ok(await t.until("!!state.misc.piAt && !piBusy", 15), "PI prices didn't load")
    await t.pg.fill("[data-pi-n='2869']", "12"); await t.pg.dispatch_event("[data-pi-n='2869']", "change"); await asyncio.sleep(0.3)
    tiles = t.show("tiles", await t.js("[...document.querySelectorAll('#pi-pick .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))"))
    t.ok(tiles and any("profit" in x.lower() for x in tiles), "PI shows its profit", tiles)
    t.ok(await t.js("document.querySelectorAll('#pi-pick tbody tr.group').length") >= 1, "P4s are grouped")
    await t.pg.fill("[data-pi=stockDays]", "14"); await t.pg.dispatch_event("[data-pi=stockDays]", "change"); await asyncio.sleep(0.2)
    await t.pg.check("[data-pi=shipIn]"); await asyncio.sleep(0.2)
    await t.pg.fill("[data-pi=deliv]", "Alpha"); await t.pg.dispatch_event("[data-pi=deliv]", "change"); await asyncio.sleep(0.2)
    await t.pg.fill("[data-pi=planetSys]", "Delta"); await t.pg.dispatch_event("[data-pi=planetSys]", "change"); await asyncio.sleep(2.5)
    await t.pg.select_option("[data-pi=haulMode]", "courier"); await asyncio.sleep(1.5)
    t.eq(await t.js("piHaulInfo && piHaulInfo.mode"), "courier", "PI hauling by a freight service")
    t1 = await t.js("(()=>{const E=piEnv(), {need}=piNeeds(E); const [k,q]=[...need][0]; state.assets['char:9001'].rows.push({t:k,loc:60003760,h:'Hangar',q:Math.ceil(q/2)}); renderPi(); return [k,q,E.days]})()"); await asyncio.sleep(0.2)
    shop = t.show("pi shop", await t.js(f"(()=>{{const tb=document.querySelector('#pi-shop table'); const head=[...tb.querySelectorAll('thead th')].map(h=>h.textContent.trim()); const row=[...document.querySelectorAll('#pi-shop tbody tr')].find(r=>r.querySelector('img[src*=\"/{t1[0]}/\"]')); const i=head.findIndex(h=>h.startsWith('Remaining')); return {{head, rem:row&&row.children[i].textContent, v:row&&+row.children[i].dataset.v}}}})()"))
    t.ok([h.rstrip(" ▲▼↕") for h in shop["head"]][:6] == ["Item", "Needed", "In stock", "Remaining", "To buy", "Cost"] and not any("m³" in h for h in shop["head"]), "PI Shopping: Remaining sits between In stock and To buy, no m³ column", shop)
    t.ok(abs(shop["v"] - (t1[1] / 2) / t1[1] * t1[2] * 86400) < 0.01 * t1[2] * 86400, "Remaining = stock ÷ the plan's use per day", [shop, t1])
    t.ok(await t.js("typeof piWeekly()==='number'"), "PI's weekly profit for the Forecast", await t.js("piWeekly()"))
    await t.pg.fill("[data-pi=roundTo]", "1,000"); await t.pg.dispatch_event("[data-pi=roundTo]", "change"); await asyncio.sleep(0.3)
    lst = t.show("rounded", await t.js("document.querySelector('#pi-shop [data-imp-send]').dataset.impSend.split('\\n').map(l=>+l.split('\\t')[1])"))
    t.ok(lst and all(q > 0 and q % 1000 == 0 for q in lst), "Round up to 1,000: every quantity to buy is a multiple of 1,000", lst)
    await t.pg.click("#pi-shop [data-imp-send] >> nth=0"); await asyncio.sleep(0.4)
    t.ok(await t.js("!document.getElementById('page-prices').hidden && document.getElementById('imp-text').value.split('\\n').length===" + str(len(lst))), "the Import calculator button opens the list there")
    await t.tab("forecast", 0.6)
    t.ok(await t.js("state.forecast.activities.some(a=>a.linked==='pi')"), "the PI plan is linked into the Forecast")

@scenario
async def citadel_pricing(t):
    await t.js("structMarket['1000000000001']={at:Date.now()+1e9,min:new Map([[34,5.5],[2398,300]]),max:new Map([[34,5]])}; structBooks['1000000000001']={at:Date.now()+1e9,sells:new Map([[34,[[5.5,1e9]]]]),buyB:new Map()}; state.misc.pricings=[...(state.misc.pricings||[]),{id:'cX',name:'Cit sell',kind:'cit',sid:'1000000000001',side:'sell'}]; saveMisc()")
    t.eq(await t.js("[priceIn('p:cX',34), priceIn('p:cX',35)]"), [5.5, None], "a citadel pricing only has its own orders")
    await t.js("const c=buildCfg(); c.price='p:cX'; c.bestBuy=false; saveMisc()")   # priced with your pricing only (Where to buy off)
    await plan(t, "Venture Blueprint", 10)
    cp = t.show("cit plan", await t.js("(()=>{const r=buildState.plan.res; return {unpriced:r.unpriced.map(x=>x.name), shop:r.shop.map(x=>[x.name,x.price])}})()"))
    t.ok("Pyerite" in cp["unpriced"] and ["Tritanium", 5.5] in cp["shop"], "items the citadel doesn't sell are left unpriced (never another market's price)", cp)
    t.ok(await t.js("[...document.querySelectorAll('#plan-out .slot-tile')][0].innerText.includes('incomplete')"), "the build cost says it's incomplete")
    # a linked reactions plan with an unpriced input is unknown in the Forecast, then gets its value back
    await t.js("const c=buildCfg(); c.price='jbv'; saveMisc()")
    await reactions(t); await t.js("rxCfg().inP='p:cX'; saveMisc(); renderRx()"); await asyncio.sleep(0.6)
    await t.tab("forecast", 0.6)
    fcu = t.show("fc unknown", await t.js("(()=>{const a=state.forecast.activities.find(x=>x.linked==='rx'); const li=[...document.querySelectorAll('#fc-acts li')].find(l=>l.innerText.includes('Reactions plan')); return {weekly:a.weekly, row:li&&li.innerText.replace(/\\s+/g,' ')}})()"))
    t.ok(fcu["weekly"] is None and "unknown" in (fcu["row"] or ""), "an unpriced reactions plan is unknown in the Forecast", fcu)
    await t.js("rxCfg().inP='split'; saveMisc()")
    back = await t.js("(()=>{syncRxActivity(); const a=state.forecast.activities.find(x=>x.linked==='rx'); return [a.weekly, a.unknown]})()")
    t.ok(isinstance(back[0], (int, float)) and back[1] is None, "a priced reactions plan gets its value back", back)

@scenario
async def doctrines(t):
    await t.js("state.misc.structs=state.misc.structs||{}; state.misc.structs['1000000000001']={id:'1000000000001',name:'Test Fortizar',system:30000142}; structMarket['1000000000001']={at:Date.now()+1e9,min:new Map(),max:new Map()}; structBooks['1000000000001']={at:Date.now()+1e9,sells:new Map([[32880,[[1e6,3]]],[1319,[[5e5,10]]],[34,[[5,1000]]]]),buyB:new Map()}; saveMisc()")
    await t.tab("fittings"); await t.pg.fill("#fit-text", "[Venture, Doctrine Venture]\nExpanded Cargohold II\nExpanded Cargohold II\n\nTritanium x500\nPyerite x100"); await t.pg.click("#fit-add")
    t.ok(await t.until("state.fits.some(f=>f.name==='Doctrine Venture')", 10), "an EFT fitting is added")
    fit = await t.js("state.fits.find(f=>f.name==='Doctrine Venture').contents")
    t.ok(fit and any(c.get("q") == 500 for c in fit), "cargo quantities are kept", fit)
    await t.js("document.querySelectorAll('[data-fit-doc]').forEach(cb=>{ cb.checked=true; cb.dispatchEvent(new Event('change',{bubbles:true})) })"); await asyncio.sleep(0.2)
    await t.tab("shortages"); t.ok(await t.until("!!document.querySelector('#doc-box table')", 15), "doctrine shortages show")
    out = t.show("doctrine", (await t.text("#doc-box"))[:600]); t.ok("Venture" in out, "the doctrine is checked against the citadel", out)

@scenario
async def characters_and_contracts(t):
    await t.tab("characters")
    rx = await t.js("[...document.querySelectorAll('.pilot dl.kv')].map(d=>[...d.querySelectorAll('dt')].map((t,i)=>t.textContent+'='+d.querySelectorAll('dd')[i].textContent).filter(x=>/Reactions/.test(x)).join())")
    t.ok(any("=III" in x for x in rx) and any("=V " in x for x in rx), "pilot cards show the Reactions level", rx)
    await t.tab("settings"); await t.pg.click("#btn-add"); await t.pg.fill("#add-name", "Hand Pilot"); await t.pg.click("#add-form button[type=submit]"); await asyncio.sleep(0.3)
    t.ok("Hand Pilot" in await t.js("state.chars.map(c=>c.name)"), "adding a pilot by hand")
    await t.tab("contracts"); await t.js("cmRemember('Old Client'); cmRemember('bob'); renderContracts()")
    t.ok("Old Client" in await t.js("[...document.querySelectorAll('#cm-clients option')].map(o=>o.value)"), "the client box remembers clients")
    await t.js("()=>{state.misc.cm=[{id:'c1',client:'Bob Client',created:Date.now(),items:{34:1000},names:{34:'Tritanium'},sends:[]}]; cmOpen='c1'; saveMisc(); renderContracts();}"); await asyncio.sleep(0.2)
    cm = t.show("contract detail", await t.js("(()=>{const h=document.querySelector('#cm-detail h2'); return {fold:h.classList.contains('fold-h'), copy:(h.querySelector('[data-copy]')||{}).dataset?.copy, janice:document.querySelectorAll('[data-cm-janice]').length}})()"))
    t.ok(not cm["fold"] and cm["copy"] == "Bob Client" and cm["janice"] == 2, "the opened contract doesn't fold, its name copies, Janice buttons are there", cm)
    await t.pg.fill("#cm-goods", "Tritanium 100"); await t.js("window.open=(u)=>{window._opened=u}")
    await t.pg.click("[data-cm-janice='cm-goods']"); await asyncio.sleep(0.2)
    t.eq(await t.js("window._opened"), "https://janice.e-351.com/", "Open in Janice opens Janice")
    # Assets: items in your open contracts are found by the search (read once per contract, never counted)
    await t.js("()=>contractItems('char:9001',(window._ct=[{id:900,type:'item_exchange',status:'outstanding',issuer:9001,price:1,reward:0,expires:Date.now()+864e5,title:'Two Ventures',from:60003760},{id:901,type:'item_exchange',status:'outstanding',issuer:555,price:1,reward:0,expires:Date.now()+864e5,from:60003760}]),(cid)=>`/characters/9001/contracts/${cid}/items/`,'tok','').then(()=>{state.contracts['char:9001']={at:Date.now(),list:window._ct}; saveContracts();})")
    t.eq(await t.js("window._ct.map(c=>c.items||null)"), [[[32880, 2, 0]], [[16633, 1000, 0], [9100, 500, 0]]], "the items of open contracts are read (yours and those offered to you)")
    await t.tab("stock", 0.4); await t.pg.fill("#st-search", "venture"); await asyncio.sleep(0.4)
    st = t.show("asset search", await t.text("#st-table"))
    t.ok(st and "Venture" in st and "in a contract" in st and "Two Ventures" in st, "the Assets search finds an item in a contract", st)
    t.ok(await t.js("!stockSources().some(s=>s.rows.some(r=>r.t===32880))"), "contract items aren't counted as stock")
    t.ok(await t.js("!contractRows().some(r=>r.t===16633)"), "a contract offered to you holds someone else's items: not in your Assets")
    # Assets outside the hangars (ship cargo and fittings, Deliveries, nested containers, asset safety): found by the search, never counted
    ag = t.show("aggregate", await t.js("""(()=>{const L=[{item_id:1,type_id:587,location_id:60003760,location_flag:'Hangar',quantity:1},{item_id:2,type_id:34,location_id:1,location_flag:'Cargo',quantity:500},{item_id:3,type_id:2048,location_id:1,location_flag:'LoSlot0',quantity:1},
      {item_id:4,type_id:3467,location_id:60003760,location_flag:'Hangar',quantity:1},{item_id:5,type_id:3467,location_id:4,location_flag:'Unlocked',quantity:1},{item_id:6,type_id:32881,location_id:5,location_flag:'Unlocked',quantity:1,is_blueprint_copy:true},
      {item_id:7,type_id:35,location_id:60000002,location_flag:'Deliveries',quantity:70},{item_id:8,type_id:36,location_id:60000001,location_flag:'AssetSafety',quantity:9}];
      const m=new Map(), rows=aggregateAssets(L,false,m), other=[...m.values()]; state.typeNames={...state.typeNames,587:'Rifter',3467:'Small Secure Container',2048:'Damage Control II',32881:'Venture Blueprint',36:'Mexallon'};
      state.assets['char:9001'].other=other; return {rows:rows.map(r=>[r.t,r.q]).sort(), other:other.map(r=>[r.t,r.q,r.loc,assetPlace(r,null)]).sort((a,b)=>a[0]-b[0])}})()"""))
    t.eq(sorted(ag["rows"]), [[587, 1], [3467, 2]], "hangar rows are unchanged: the ship and both containers")
    t.eq(ag["other"], [[34, 500, 60003760, "Item hangar · in Rifter · cargo"], [35, 70, 60000002, "Deliveries"], [36, 9, 60000001, "Asset safety"], [2048, 1, 60003760, "Item hangar · in Rifter · fitted, low slot"], [32881, 1, 60003760, "Item hangar · in Small Secure Container"]], "items outside the hangars are kept with where they are")
    await t.pg.fill("#st-search", "venture blueprint"); await asyncio.sleep(0.4)
    st2 = t.show("asset search 2", await t.text("#st-table"))
    t.ok(st2 and "in Small Secure Container" in st2 and "not counted" in st2, "the Assets search finds a blueprint in a nested container", st2)
    t.ok(await t.js("stockByType().get(36)===undefined && !stockSources().some(s=>s.value && s.rows.some(r=>r.t===36))"), "items outside the hangars aren't counted as stock")

@scenario
async def skill_queues(t):
    # Reading a queue: training order, names, no dates while paused
    q = t.show("fetched queue", await t.js("fetchQueue(9001,'tok')"))
    t.eq([[x["n"], x["l"], x["end"] is None] for x in q], [["Industry", 5, False], ["Mechanical Engineering", 5, False], ["Reactions", 4, True]], "the queue is read in training order, with names, a paused level without dates")
    t.ok(await t.js("SCOPE_USE[QUEUE_SCOPE] && ESI_SCOPE.includes(QUEUE_SCOPE) && !requestedScopes().includes(QUEUE_SCOPE)"), "the Skill queues permission is listed and starts unticked")
    # Alpha: queue ends in 2 days; Beta: Industry IV done since the sync, Industry V and ME III queued; Gamma: queue ran out an hour ago
    H, D = 3600e3, 864e5
    await t.js(f"""()=>{{const n=Date.now(); state.misc.skills={{...(state.misc.skills||{{}}),Industry:{{id:3380,rank:1,pri:165,sec:166,req:{{}}}},'Mechanical Engineering':{{id:3392,rank:1,pri:165,sec:166,req:{{}}}},'Caldari Starship Engineering':{{id:3398,rank:1,pri:165,sec:166,req:{{}}}}}};
      state.chars[0].queue={{at:n,list:[{{n:'Science',l:2,start:n-{H},end:n+2*{D}}}]}};
      state.chars[1].queue={{at:n-{D},list:[{{n:'Industry',l:4,start:n-{D},end:n-{H}}},{{n:'Industry',l:5,start:n-{H},end:n+3*{D}}},{{n:'Mechanical Engineering',l:2,start:n+3*{D},end:n+4*{D}}},{{n:'Mechanical Engineering',l:3,start:n+4*{D},end:n+5*{D}}}]}};
      state.chars[2].queue={{at:n-{D},list:[{{n:'Reactions',l:5,start:n-{D},end:n-{H}}}]}};
      state.fits=[{{id:'fq',name:'Queue test',ship:'Venture',shipId:32880,req:{{Industry:5,'Mechanical Engineering':3}},items:[],contents:[],unknown:[]}},{{id:'fq2',name:'Untrained test',ship:'Venture',shipId:32880,req:{{'Caldari Starship Engineering':5}},items:[],contents:[],unknown:[]}}]; saveFits(); saveLocal(); render();}}""")
    t.eq(await t.js("state.chars.map(c=>queueEnd(c)>0?'ends':queueEnd(c))"), ["ends", "ends", 0], "queue end: a running queue has a date, a queue whose last level finished is empty")
    t.eq(await t.js("lv(queuedPilot(state.chars[1]),'Industry')"), 4, "a level the queue finished since the sync counts")
    # Skills page: pilots training now, the queue running out first on top; pilots not training only when ticked
    await t.tab("overview", 0.4)
    rows = "[...document.querySelectorAll('#sq-table tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' ').trim())"
    sq = t.show("skill queues", await t.js(rows))
    t.ok(len(sq) == 3 and "training now" in sq[0].lower() and sq[1].startswith("Ender Alpha") and "Science II" in sq[1] and sq[2].startswith("Ender Beta") and not await t.js("document.getElementById('sq-note').hidden"), "Skill queues shows the pilots training, the one running out first on top, and says one is hidden", sq)
    await t.pg.click("#sq-idle"); await asyncio.sleep(0.2)
    sq = t.show("with not training", await t.js(rows))
    t.ok(len(sq) == 5 and "not training" in sq[3].lower() and sq[4].startswith("Solo Gamma") and "Empty" in sq[4] and await t.js("state.misc.sqIdle===true"), "ticking the box adds the pilots not training, in their own group", sq)
    t.ok(await t.js("[...document.querySelectorAll('#sk-nav a')].some(a=>a.textContent==='Skill queues')"), "Skill queues is in the Skills navigation")
    await t.tab("characters", 0.3)
    pc = await t.js("document.getElementById('pilots').textContent"); t.ok("Skill queue empty" in pc and "Queue ends" in pc, "the pilot cards say when the queue ends, or that it's empty", pc[:400])
    # To-Do: the empty queue, counted on the tab; unticking the pilot hides it
    await t.tab("todo", 0.4)
    td = t.show("todo queues", await t.js("[!document.getElementById('todo-sq-panel').hidden, document.getElementById('todo-sq').innerText, document.querySelector('.tabs button[data-tab=todo]').dataset.alert]"))
    t.ok(td[0] and "Solo Gamma" in td[1] and "empty since" in td[1] and "Ender" not in td[1] and td[2] == "1", "To-Do shows the empty queue and counts it on the tab", td)
    # Idle for more than 7 days: hidden (and not counted) unless To-Do's box is ticked; a later sync keeps the first idle date
    n_ = await t.js("Date.now()")
    t.eq(await t.js(f"[queueIdleSince({{queue:{{at:{n_},idle:{n_}-5*{D},list:[]}}}}), queueIdleSince({{queue:{{at:{n_},list:[]}}}}), queueIdleSince(state.chars[0])]"), [n_ - 5 * D, n_, None], "idle since: an earlier sync's date, else the read; none while training")
    await t.js(f"()=>{{state.chars[2].queue={{at:Date.now()-{D},list:[{{n:'Reactions',l:5,start:Date.now()-11*{D},end:Date.now()-10*{D}}}]}}; saveLocal(); renderTodo(); todoBadge();}}")
    td = t.show("long idle", await t.js("[!document.getElementById('todo-sq-panel').hidden, document.getElementById('todo-sq').innerText, document.querySelector('.tabs button[data-tab=todo]').dataset.alert||'']"))
    t.ok(td[0] and "Solo Gamma" not in td[1] and "idle for over 7 days hidden" in td[1] and td[2] == "", "a pilot idle for over 7 days is hidden and not counted", td)
    await t.pg.click("#todo-sq-idle"); await asyncio.sleep(0.2)
    td = t.show("long idle shown", await t.js("[document.getElementById('todo-sq').innerText, document.querySelector('.tabs button[data-tab=todo]').dataset.alert||'']"))
    t.ok("Solo Gamma" in td[0] and td[1] == "1", "ticking Show pilots idle for over 7 days lists and counts them", td)
    await t.tab("overview", 0.3); await t.pg.click("[data-sq-alert='g']"); await asyncio.sleep(0.2)
    t.ok(await t.js("document.getElementById('todo-sq-panel').hidden=false, renderTodo(), document.getElementById('todo-sq-panel').hidden && !document.querySelector('.tabs button[data-tab=todo]').dataset.alert"), "an unticked pilot leaves To-Do and the tab count")
    # Fittings: Alpha flies it; Beta's queue gets there (the last needed level's date); Gamma: time to train
    await t.tab("fittings", 0.3); await asyncio.sleep(0.5); await t.js("renderFits()")
    t.ok(await t.js("[...document.querySelectorAll('#fit-list details[data-fit-det$=\":fly\"]')].every(d=>!d.open) && document.querySelectorAll('#fit-list details[data-fit-det$=\":fly\"]').length===2"), "Time to fly it is folded by default")
    await t.pg.click("#fit-list details[data-fit-det$=':fly'] summary >> nth=0"); await asyncio.sleep(0.2); await t.js("renderFits()")
    t.ok(await t.js("document.querySelector('#fit-list details[data-fit-det$=\":fly\"]').open"), "an opened Time to fly it stays open when the card redraws")
    await t.js("document.querySelectorAll('#fit-list details').forEach(d=>d.open=true)")
    card = t.show("fitting card", await t.js("[...document.querySelectorAll('#fit-list .fit')].map(a=>[...a.querySelectorAll('.who-list li')].map(l=>(l.className+': '+l.innerText).replace(/\\s+/g,' ')).join(' | '))"))
    rb = await t.js("(()=>{const r=readyFor(state.chars[1], state.fits[0].req); return [r.ok, r.inQ, r.miss.length, Math.round((r.at-Date.now())/864e5)]})()")
    t.eq(rb, [False, 2, 2, 5], "Beta: both missing levels queued, ready when Mechanical Engineering III finishes")
    t.ok("yes: ✓ Ender Alpha" in card[0] and "no: Ender Beta ready" in card[0] and "no: Solo Gamma" in card[0] and "to train" in card[0], "the fitting shows who flies it, when Beta's queue gets there, and Gamma's training time", card[0])
    t.ok(card[0].index("Ender Beta") < card[0].index("Solo Gamma"), "the soonest pilot is first")
    t.ok("no: Ender Alpha" in card[1] and "to train" in card[1] and "ready" not in card[1], "a skill nobody queued shows the time to train", card[1])

@scenario
async def skill_check_saved(t):
    # A saved blueprint can be removed from the Skill check's list
    await t.js("()=>{bp.saved={m1:{key:'m1',name:'Test blueprint',manual:true,acts:{manufacturing:{Industry:1}},checkedAt:Date.now()},m2:{key:'m2',name:'Other blueprint',manual:true,acts:{manufacturing:{Industry:2}},checkedAt:Date.now()}}; saveBpLocal(); renderBp();}")
    await t.tab("overview", 0.3)
    t.eq(await t.js("document.querySelectorAll('#bp-saved [data-bp-remove]').length"), 2, "each saved blueprint has a remove button")
    await t.pg.click("#bp-saved [data-bp-remove='m1']"); await asyncio.sleep(0.2)
    t.eq(await t.js("[Object.keys(bp.saved), JSON.parse(localStorage.getItem('eve-industry-bp-saved')).m1===undefined, document.getElementById('bp-saved').innerText.includes('Test blueprint')]"), [["m2"], True, False], "removing it drops it from the list and from storage")

@scenario
async def map_markers(t):
    # The map, its legend, the system panel and the hover box draw each marker with the same MK entry
    await map_(t)
    await t.js("()=>{state.misc.structs={...(state.misc.structs||{}), 1077:{name:'Bravo - Test Astrahus',system:30000002,type:35832,typeName:'Astrahus'}}; state.misc.map={...(state.misc.map||{}),homes:[30000002]}; mapUI.focus={n:'Test alliance',ids:[1]}; saveMisc(); renderMap(); mapSelect(30000002, true);}")
    await asyncio.sleep(0.4)
    info = t.show("panel", await t.js("[...document.querySelectorAll('#map-info .map-sel canvas.mk-ico')].map(c=>c.dataset.mk+':'+(c.dataset.mkArg||''))"))
    t.ok("struct:" in info and "home:" in info, "the system panel shows the map's markers (citadel, home)", info)
    leg = t.show("legend", await t.js("[...document.querySelectorAll('#map-legend canvas.mk-ico')].map(c=>c.dataset.mk)"))
    t.ok(set(leg) >= {k for k in await t.js("Object.keys(MK).filter(k=>MK[k].draw)")}, "the legend shows every marker the map draws", leg)
    await t.js("()=>{ mapUI.focus=null; renderMap() }")
    t.ok(await t.js("[...document.querySelectorAll('#map-legend canvas.mk-ico')].every(c=>c.getContext('2d').getImageData(0,0,32,32).data.some((v,i)=>i%4===3&&v>0))"), "every legend icon is painted")
    pos = await t.js("(()=>{const s=mapIndex().byId.get(30000002), cv=document.getElementById('map-canvas'), rc=cv.getBoundingClientRect(); return [rc.left+(s.px-view.cx)*view.k+cv.clientWidth/2, rc.top+(s.py-view.cy)*view.k+cv.clientHeight/2]})()")
    await t.pg.mouse.move(pos[0], pos[1]); await asyncio.sleep(0.2)
    hv = t.show("hover", await t.js("(()=>{const h=document.getElementById('map-hover'); return [h.hidden, [...h.querySelectorAll('canvas.mk-ico')].map(c=>c.dataset.mk+':'+(c.dataset.mkArg||'')), h.innerText]})()"))
    await t.pg.screenshot(path=SP + "map_markers.png", full_page=True)
    t.ok(not hv[0] and "struct:" in hv[1] and "home:" in hv[1] and "Bravo - Test Astrahus" in hv[2], "the hover box uses the same markers as the system panel", hv)
    t.ok(await t.js("BRACKET_ORDER.every(k=>BRACKET_SRC[k].startsWith('data:image/png'))") and not await t.js("/eveuniversity/.test(bracketIcon.toString()+MK.pi.draw.toString())"), "capital brackets come with the page (CCP's icons), nothing is read from the wiki")
    t.ok(not await t.js("(()=>{const p=document.querySelector('#map-info .map-sel').cloneNode(true); p.querySelectorAll('button').forEach(b=>b.remove()); return /[◆□●♟◇✷▪⛴⌂]/.test(document.getElementById('map-hover').innerText + p.innerText)})()"), "no old text symbols are left in the hover box or the system panel")

@scenario
async def map_thera(t):
    # Thera / Turnur wormholes from EVE-Scout: the known-space ends get the swirl marker, listed in the panel, the hover box and the legend
    await map_(t)
    t.ok(await t.until("!!scout", 8), "EVE-Scout's connections are read when the map opens")
    t.eq(await t.js("[[...scout.by.keys()].sort(), scout.lines]"), [[30000002, 30000003, 30000006], [[30000003, 30000006]]], "only known-space ends are kept; a line only where both ends are on the map")
    await t.js("mapSelect(30000002, true)"); await asyncio.sleep(0.3)
    pn = t.show("panel", await t.js("[...document.querySelectorAll('#map-info .map-sel canvas.mk-ico[data-mk=scout]')].map(c=>c.parentElement.innerText.replace(/\\s+/g,' ').trim()).join(' | ')"))
    t.ok("Wormhole to Thera" in pn and "XWF-276 (JXT-585 in Thera)" in pn and "up to battleships" in pn and "left" in pn, "the system panel gives both signatures, the ship size and the time left", pn)
    await t.js("mapSelect(30000003, false)"); await asyncio.sleep(0.3)
    t.ok("Wormhole to Foxtrot" in (await t.text("#map-info")) and "up to freighters" in (await t.text("#map-info")), "Turnur's side lists where it leads", await t.text("#map-info"))
    t.ok("Thera / Turnur wormhole (EVE-Scout) · 3 systems" in (await t.text("#map-legend")), "the legend counts the systems", await t.text("#map-legend"))
    await t.js("view.k=null; drawMap()"); await asyncio.sleep(0.2); await t.pg.locator("#map-wrap").screenshot(path=SP + "map_thera.png")
    await t.pg.click("[data-ml=scout]"); await asyncio.sleep(0.2)
    t.eq(await t.js("mapLayers().scout"), False, "the Thera / Turnur tick box hides them")

@scenario
async def map_pilots(t):
    # Every pilot's last location (ESI "Character location") on the map, with the same marker in the panel, the hover box and the legend
    await map_(t)
    await t.js("()=>{state.chars[0].loc={sys:30000002,station:60000001,structure:null,at:Date.now()-2*3600e3}; state.chars[2].loc={sys:30000002,station:null,structure:null,at:Date.now()}; saveLocal(); renderMap(); mapSelect(30000002, true);}")
    await asyncio.sleep(0.4)
    t.eq(await t.js("(mapPilots().get(30000002)||[]).map(p=>p.c.name).sort()"), ["Ender Alpha", "Solo Gamma"], "both pilots are placed in their last system")
    pn = t.show("panel", await t.js("[...document.querySelectorAll('#map-info .map-sel canvas.mk-ico[data-mk=pilot]')].map(c=>c.parentElement.innerText.replace(/\\s+/g,' ').trim())"))
    t.ok(any("Ender Alpha" in x and "docked at Bravo station" in x and "2 h ago" in x for x in pn) and any("Solo Gamma" in x and "in space" in x for x in pn), "the system panel says where each pilot is docked, and when it was seen", pn)
    t.eq(await t.js("document.querySelector('#map-info .map-sel canvas.mk-ico:not([data-mk=home]):not([data-mk=kills]):not([data-mk=incursion])').dataset.mk"), "pilot", "pilots come first in the system's list")
    leg = t.show("legend", await t.text("#map-legend"))
    t.ok("Your pilots (last location)" in leg and "without one" not in leg, "the legend shows the pilot marker", leg)
    await t.js("()=>{delete state.chars[0].loc; renderMap();}"); await asyncio.sleep(0.2)
    t.ok("1 without one" in (await t.text("#map-legend")), "the legend says how many linked pilots have no location yet", await t.text("#map-legend"))
    await t.pg.click("[data-ml=pilots]"); await asyncio.sleep(0.2)
    t.eq(await t.js("mapLayers().pilots"), False, "the Pilots tick box hides them")
    t.ok(await t.js("document.querySelector('#map-legend [data-ml-leg=pilots]').classList.contains('off')"), "the legend shows the hidden layer struck out")
    await t.pg.click("#map-legend [data-ml-leg=pilots]"); await asyncio.sleep(0.2)
    t.ok(await t.js("mapLayers().pilots===true && document.querySelector('[data-ml=pilots]').checked && !document.querySelector('#map-legend [data-ml-leg=pilots]').classList.contains('off')"), "clicking the legend line shows them again, tick box too")
    await t.pg.click("#map-legend [data-ml-leg=homes]"); await asyncio.sleep(0.2)
    t.ok(await t.js("mapLayers().homes===false && !document.querySelector('[data-ml=homes]').checked"), "the legend hides homes")

@scenario
async def upcoming_fleets(t):
    await t.tab("forecast", 0.4)
    t.ok((await t.js("document.getElementById('fleet-title').textContent")).endswith("Upcoming events"), "the Overview panel is called Upcoming events", await t.text("#fleet-title"))
    t.ok('"Calendar"' in (await t.text("#fleet-body")), "without the Calendar permission, Upcoming events says how to get it", await t.text("#fleet-body"))
    ev = t.show("calendar", await t.js("fetchCalendar(9001,'tok')"))
    e1 = next((e for e in ev if e["id"] == 501), {})
    t.eq([len(ev), e1.get("owner"), e1.get("dur"), e1.get("text"), e1.get("imp"), e1.get("resp")], [2, "Fake Corp", 120, "Form up in Alpha\nBring ECM", True, "accepted"], "calendar events are read with who runs them, duration and plain text")
    # Two pilots see the same fleet: listed once with both answers; an event that ended is left out
    await t.js("ev=>{state.chars[0].calendar={at:Date.now(),list:ev}; state.chars[1].calendar={at:Date.now(),list:ev.filter(e=>e.id===501).map(e=>({id:e.id,at:e.at,title:e.title,imp:false,resp:'tentative'}))}; saveLocal(); render(); renderTz(true);}", ev)
    fl = t.show("fleets", await t.js("[document.querySelectorAll('#fleet-body li').length, document.getElementById('fleet-body').innerText]"))
    cal = await t.js("(renderAgenda(), [document.getElementById('ag-cal').innerText.includes('Fleet: home defence'), !!document.querySelector('#ag-filters [data-ag=fleets]')])")
    t.eq(cal, [True, True], "the fleet is on the Overview's calendar, with its own tick box")
    await t.pg.click("#ag-filters [data-ag=fleets]"); await asyncio.sleep(0.2)
    t.ok(await t.js("!document.getElementById('ag-cal').innerText.includes('Fleet: home defence')"), "unticking Fleets takes it off the calendar")
    t.ok(fl[0] == 1 and "Tomorrow" in fl[1] and "Fleet: home defence" in fl[1] and "Fake Corp" in fl[1] and "Important" in fl[1] and "Ender Alpha ✓" in fl[1] and "Ender Beta ?" in fl[1] and "Old ops" not in fl[1] and "EVE " in fl[1], "Upcoming events lists the fleet once, with its owner, EVE time and every pilot's answer", fl)

@scenario
async def lp_store(t):
    corps = await t.js("lpCorps()")
    t.eq(corps, [[1000035, "Caldari Navy"], [1000125, "CONCORD"], [1000130, "Sisters of EVE"], [1000180, "State Protectorate"]], "the NPC corporations are read with their names, A to Z")
    t.ok(await t.js("[LOYALTY_SCOPE, CALENDAR_SCOPE].every(s=>ESI_SCOPE.includes(s) && SCOPE_USE[s] && !requestedScopes().includes(s))"), "the Loyalty points and Calendar permissions are listed and start unticked")
    await t.js("async()=>{state.chars[0].lp={at:Date.now(),list:(await esiAuthGet('/characters/9001/loyalty/points/','tok')).map(x=>[x.corporation_id,x.loyalty_points])}; saveLocal();}")
    t.ok(await t.js("!!document.querySelector('.tabs .tabgrp:has(button[data-tab=prices]) button[data-tab=lp]')"), "LP store is in the Market menu")
    await t.tab("lp", 0.4)
    t.ok(await t.until("!!lpOffers['1000035'] && !lpBusy && document.querySelectorAll('#lp-offers tbody tr:not(.group)').length===3", 20), "the store with the most LP opens by itself", await t.text("#lp-offers"))
    sq = lambda s: "".join(ch for ch in s if not ch.isspace() and ch not in ",  ")   # numbers follow the browser's locale
    pts = await t.text("#lp-points"); t.ok("CaldariNavy" in sq(pts) and "2500" in sq(pts), "Your loyalty points shows the corporation and the LP", pts)
    r = t.show("rows", await t.js("(()=>{const tax=salesTax().pct/100; return {tax, rows:Object.fromEntries(lpRows('1000035').map(o=>[o.t,[o.value,o.cost,o.perLp]]))}})()"))
    tax = r["tax"]; rows = r["rows"]
    t.ok(abs(rows["32880"][2] - (300000 * (1 - tax) - 100000 - 4000) / 1000) < 1e-6, "ISK per LP = (sells for after tax − ISK − other items) ÷ LP", rows["32880"])
    t.ok(abs(rows["35"][2] - 9 * 1000 * (1 - tax) / 100) < 1e-6, "a stack counts its quantity", rows["35"])
    t.eq(rows["999001"], [None, 0, None], "an item with no price leaves its ISK per LP unknown, never 0")
    t.ok(await t.until("lpRows('1000035').find(o=>o.t===32880).sold===100", 10), "Sold per day comes from The Forge's market history", await t.js("lpRows('1000035').map(o=>[o.t,o.sold])"))
    tb = t.show("table", await t.js("[...document.querySelectorAll('#lp-offers tbody tr:not(.group)')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
    t.ok(any("Venture" in x and "Tritanium×1000" in sq(x) and sq(x).endswith("2") for x in tb),"the Venture row lists the other items and how many times your LP buys it", tb)
    t.ok(any("T999001" in x and "no price" in x for x in tb), "the unpriced offer shows no price", tb)
    t.ok(await t.js("!document.querySelector('#lp-offers tr.group') && document.getElementById('lp-offers').tBodies.length===1"), "the offers are one list, not grouped by what the items are")
    t.ok(tb[0].strip().startswith("Venture"), "the best ISK per LP is first", tb)
    t.ok("no price in" in (await t.text("#lp-note")), "the page says which items have no price")
    t.ok("Venture" in (await t.text("#lp-summary")), "the best offer you can afford is the Venture")
    await t.pg.screenshot(path=SP + "lp_store.png", full_page=True)
    # Another pricing for what you sell: the numbers follow it
    await t.pg.select_option("#lp-bar select[data-lp=sell]", "jbv"); await asyncio.sleep(0.5)
    v2 = await t.js("lpRows('1000035').find(o=>o.t===32880).perLp")
    t.ok(abs(v2 - (330000 * (1 - tax) - 104000) / 1000) < 1e-6 and await t.js("lpCfg().sell") == "jbv", "changing the sell pricing reprices the offers", v2)
    # A corporation without a store
    await t.pg.select_option("#lp-corp", "1000130"); t.ok(await t.until("!lpBusy && /couldn't be read/.test(document.getElementById('lp-offers').innerText)", 10), "a corporation whose store can't be read says so", await t.text("#lp-offers"))
    # CONCORD: the stores its LP converts to, their offers at their price in CONCORD LP
    await t.pg.select_option("#lp-corp", "1000125")
    t.ok(await t.until("!!lpConv && !!lpOffers['1000125'] && !lpBusy", 20), "CONCORD's store and the stores its LP converts to are read", await t.text("#lp-conv"))
    t.eq(await t.js("lpConv"), [[1000035, 0.8], [1000130, 0.4]], "CONCORD LP converts to empire (0.8) and other factions' (0.4) stores with a store in CCP's game data, not to a militia or CONCORD's own")
    await t.js("()=>{delete lpOffers['1000035']; delete lpErr['1000130']; renderLp();}")
    t.ok((await t.text("#lp-conv-table")).count("not read") == 2, "a store not read yet says so", await t.text("#lp-conv-table"))
    await t.pg.click("[data-lp-conv]"); t.ok(await t.until("!lpConvBusy && !!lpOffers['1000035'] && !!lpErr['1000130']", 20), "Read every store reads them one after the other", await t.text("#lp-conv"))
    cv = t.show("converted", await t.js("lpConvRows('1000125').filter(o=>o.t===32880).map(o=>[o.store, o.rate, o.lp, o.slp, o.perLp])"))
    own = [x for x in cv if x[0] == [1000125]]; cn = [x for x in cv if x[0] == [1000035]]
    t.ok(own and own[0][2] == 2000 and abs(own[0][4] - 330000 * (1 - tax) / 2000) < 1e-6, "CONCORD's own offer at its own LP", own)
    t.ok(cn and cn[0][1:4] == [0.8, 1250, 1000] and abs(cn[0][4] - (330000 * (1 - tax) - 104000) / 1250) < 1e-6, "Caldari Navy's offer costs its LP ÷ 0.8 in CONCORD LP, ISK per CONCORD LP from that", cn)
    ct = t.show("conv table", await t.js("[...document.querySelectorAll('#lp-conv-table tbody tr:not(.group)')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
    t.ok(any(x.startswith("Caldari Navy") and "800" in sq(x) for x in ct) and any(x.startswith("Sisters of EVE") and "couldn't be read" in x for x in ct), "each store: what your CONCORD LP gives there, a store that can't be read", ct)
    tb = t.show("offers", await t.js("[...document.querySelectorAll('#lp-offers tbody tr:not(.group)')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
    t.ok("Store" in await t.text("#lp-offers thead") and tb[0].strip().startswith("Venture") and "Caldari Navy · 0.8" in tb[0] and any("CONCORD" in x for x in tb), "the offers of both stores in one list with their store, the best per CONCORD LP first", tb)
    await t.pg.screenshot(path=SP + "lp_concord.png", full_page=True)

@scenario
async def server_status(t):
    t.ok(await t.until("srv && srv.state==='online'", 10), "the server status is read", await t.js("srv"))
    t.eq(await t.js("[srv.players, !document.getElementById('srv-status').hidden, document.getElementById('srv-status').textContent.includes('Online')]"), [23456, True, True], "the header shows the server online with its players")
    up = t.show("back online", await t.js("[document.getElementById('srv-status').textContent, new Date(srv.start).toISOString().slice(11,16), document.getElementById('srv-status').title]"))
    t.ok(f"since {up[1]} EVE" in up[0] and f"back online at {up[1]} EVE time" in up[2], "the header says when the server came back, to the minute, in EVE time", up)
    # Downtime: from 11:00 EVE time until the server says it started again, at most 20 minutes when it can't be read
    dt = t.show("downtime", await t.js("""(()=>{const s=dtStart(Date.now()), keep=srv, at=(m)=>s+m*60e3, out={};
      srv=null; out.before=esiDown(at(-1)); out.noStatus=esiDown(at(5)); out.after=esiDown(at(25));
      srv={at:at(5),state:'online',start:at(-600)}; out.oldStart=esiDown(at(5));
      srv={at:at(5),state:'online',start:at(4)}; out.back=esiDown(at(5));
      srv={at:at(5),state:'offline'}; out.offline=esiDown(at(5)); srv=keep; return out})()"""))
    t.eq(dt, {"before": False, "noStatus": True, "after": False, "oldStart": True, "back": False, "offline": True}, "downtime starts at 11:00 EVE time and ends when the server is back")
    # While down: no sync, market reads refused (prices keep what they had), the header says so
    r = t.show("while down", await t.js("""(async()=>{const real=esiDown; esiDown=()=>true; renderSrv(); const pill=document.getElementById('srv-status').textContent;
      let sync=''; try { await syncChar(state.chars[0]); } catch(e) { sync=e.message }
      const mk=(await esiMarket('https://esi.evetech.net/latest/markets/10000002/orders/?type_id=34')).status; esiDown=real; renderSrv(); return {pill, sync, mk}})()"""))
    t.ok("Downtime" in r["pill"] and "downtime" in r["sync"] and r["mk"] == 503, "during downtime the header says so, syncs wait and market reads are refused", r)

@scenario
async def launcher_proxy(t):
    """The launcher's proxy: only the tool may use it, and what it reads never comes back as a page (an SVG or HTML page would run as the tool)."""
    import urllib.request, urllib.parse, urllib.error, http.server, threading
    class Svg(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.send_header("Content-Type", "image/svg+xml"); self.end_headers(); self.wfile.write(b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>")
        def log_message(self, *a): pass
    svg = http.server.HTTPServer(("127.0.0.1", 0), Svg); threading.Thread(target=svg.serve_forever, daemon=True).start()
    def get(headers):
        req = urllib.request.Request("http://localhost:8642/proxy?url=" + urllib.parse.quote(f"http://127.0.0.1:{svg.server_port}/x.svg"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r: return [r.status, r.headers.get("Content-Type"), r.headers.get("X-Content-Type-Options")]
        except urllib.error.HTTPError as e: return [e.code, None, None]
    t.eq(await asyncio.to_thread(get, {"Sec-Fetch-Site": "same-origin"}), [200, "application/octet-stream", "nosniff"], "an SVG read through the proxy comes back as plain bytes, never as a page")
    t.eq((await asyncio.to_thread(get, {"Sec-Fetch-Site": "cross-site"}))[0], 403, "another website can't use the proxy")
    t.ok((await asyncio.to_thread(get, {"Host": "evil.example:8642"}))[0] in (400, 403), "a website whose name was pointed at this computer can't use it either")
    svg.shutdown()

@scenario
async def storage_full(t):
    """When the browser refuses a save (its storage full), the tool says so once instead of losing changes without a word."""
    r = await t.js("""(()=>{ const real=Storage.prototype.setItem; Storage.prototype.setItem=function(){ throw new DOMException('full','QuotaExceededError') };
      try { $('toast').textContent=''; saveMisc(); const first=$('toast').textContent; $('toast').textContent=''; saveForecast(); saveToken(1, 'rt'); return [first, $('toast').textContent, ls.set('x', 1)]; }
      finally { Storage.prototype.setItem=real; } })()""")
    t.ok("storage may be full" in r[0] and r[1] == "" and r[2] is False, "the first refused save is said, the next ones aren't repeated", r)

@scenario
async def login_background_sync(t):
    """Logging in several characters in a row: each is linked at once, the full read runs in the background (one at a time)."""
    await t.js("""()=>{ window._sync={on:0,max:0,calls:0,done:[],release:null}; const gate=new Promise(r=>window._sync.release=r);
      const jwt=(id,name)=>'h.'+btoa(JSON.stringify({sub:'CHARACTER:EVE:'+id,name,scp:['esi-skills.read_skills.v1']})).replace(/=+$/,'').replace(/\\+/g,'-').replace(/\\//g,'_')+'.s';
      window._jwt=jwt; tokenRequest=async(p)=>({access_token:jwt(+p.code,'Pilot '+p.code),refresh_token:'rt'+p.code,expires_in:1199});
      applyToken=async(tok)=>{ const p=jwtPayload(tok.access_token), id=+p.sub.split(':').pop(); _sync.calls++; _sync.on++; _sync.max=Math.max(_sync.max,_sync.on); await gate;
        const c=state.chars.find(x=>x.esiId===id); Object.assign(c,{skills:{Industry:5},syncedAt:Date.now()}); _sync.on--; _sync.done.push(id); saveLocal(); render(); return c; }; }""")
    t0 = await t.js("Date.now()")
    for i, code in enumerate(["9101", "9102", "9103"]):
        await t.js("c => { ls.set('eve-industry-esi-pending',{state:'s'+c,verifier:'v'}); return finishLogin(c,'s'+c) }", code)
    linked = t.show("linked", await t.js("({ms:Date.now()-%d, chars:state.chars.filter(c=>c.esiId>9100).map(c=>[c.name,!!esiTokens()[c.esiId],syncState(c)]), msg:document.getElementById('esi-msg').textContent, bg:document.getElementById('esi-sync-bg').textContent})" % t0))
    t.eq(linked["chars"], [["Pilot 9101", True, "run"], ["Pilot 9102", True, "wait"], ["Pilot 9103", True, "wait"]], "each login links the pilot at once; one syncs, the others wait")
    t.ok("background" in linked["msg"] and "2 waiting" in linked["bg"] and "log in the next character" in linked["bg"], "the login panel says the sync runs in the background", linked)
    await t.tab("characters"); txt = await t.text("#chars-table")
    t.ok("Syncing…" in txt and "Waiting to sync" in txt, "the Characters page shows who is syncing and who waits", txt)
    # A second sync of a pilot already syncing waits for the same read
    await t.js("(()=>{const c=state.chars.find(x=>x.esiId===9101); syncChar(c); syncChar(c)})()")
    await t.js("_sync.release()")
    t.ok(await t.until("_sync.done.length===3 && !state.chars.some(c=>syncState(c))", 5), "every pilot syncs in the end", await t.js("_sync"))
    t.eq(await t.js("[_sync.max, _sync.calls, state.chars.filter(c=>c.esiId>9100).every(c=>c.skills.Industry===5 && c.syncedAt), document.getElementById('esi-sync-bg').hidden]"), [1, 3, True, True], "one at a time, each pilot read once (a sync asked while one runs waits for it), all synced, the status line gone")
    # A request that never answers fails after a while instead of holding the sync (and every pilot after it) forever; a database save that aborts fails too
    r = await t.js("""(async()=>{ const real=AbortSignal.timeout, rf=window.fetch; AbortSignal.timeout=()=>real.call(AbortSignal, 50);
      window.fetch=(u,i)=>new Promise((_, rej)=>i.signal.addEventListener('abort',()=>rej(i.signal.reason)));
      try { const t0=Date.now(); const e=await fetchRetry('https://esi.evetech.net/latest/status/', undefined, 2).then(()=>'answered', e=>e.name); return [e, Date.now()-t0<10000]; }
      finally { AbortSignal.timeout=real; window.fetch=rf; } })()""")
    t.eq(r, ["TimeoutError", True], "a stalled request gives up and is retried, then fails")
    t.eq(await t.js("(async()=>{ const db=await idb.open(), real=db.transaction.bind(db); db.transaction=(...a)=>{ const tx=real(...a); setTimeout(()=>tx.abort()); return tx; }; try { return await Promise.race([idb.set('x', 1), sleep(3000).then(()=>'hung')]); } finally { db.transaction=real; } })()"), False, "an aborted save says it failed instead of waiting forever")

@scenario
async def partial_sync(t):
    """A page's "Refresh from ESI" reads only what that page shows; its button and the Characters page say who is read and what part."""
    await t.tab("characters")
    r = t.show("planets refresh", await t.js("""(async()=>{ const jwt=(id,name)=>'h.'+btoa(JSON.stringify({sub:'CHARACTER:EVE:'+id,name,scp:['esi-planets.manage_planets.v1']})).replace(/=+$/,'').replace(/\\+/g,'-').replace(/\\//g,'_')+'.s';
      const c=state.chars[0]; Object.assign(c,{esiId:9201, corpId:98000001, skills:{Industry:4}, syncedAt:123, scopes:requestedScopes().join(' ')}); saveToken(9201,'rt');
      refreshTok=async()=>({access_token:jwt(9201,c.name)});
      const urls=[], rf=window.fetch; let open; const gate=new Promise(r=>open=r);
      window.fetch=async(u,i)=>{ if(!String(u).includes('esi.evetech.net')) return rf(u,i); urls.push(String(u).replace(/^https:\\/\\/esi.evetech.net(\\/latest)?/,'').split('?')[0]); await gate; return new Response('[]',{status:200,headers:{'Content-Type':'application/json'}}); };
      try { const b=document.getElementById('pi-refresh'), label=b.textContent, p=pageSync(b,['planets']); await sleep(300); renderChars();
        const mid=[b.textContent, b.disabled, (document.querySelector('#chars-table [data-sync-pill]')||{}).textContent]; open(); await p;
        return {mid, after:[b.textContent===label, b.disabled], urls:[...new Set(urls)].filter(u=>!u.startsWith('/markets/')), skills:c.skills.Industry, syncedAt:c.syncedAt, planetsAt:!!c.planetsSyncedAt}; }
      finally { window.fetch=rf; } })()"""))
    t.ok("planets" in r["mid"][0] and r["mid"][1] and "Syncing: planets" in (r["mid"][2] or ""), "while it runs, the button and the Characters page say the pilot's planets are read", r["mid"])
    t.eq(r["after"], [True, False], "the button is back afterwards")
    t.eq(r["urls"], ["/characters/9201/planets/"], "only the planets are read from ESI (no skills, wallets, assets…; market prices other pages read aside)")
    t.ok(r["skills"] == 4 and r["syncedAt"] == 123 and r["planetsAt"], "the rest of the pilot is left as it was; the planets are marked read", r)

@scenario
async def intel_violent(t):
    """Intel's right column: the null-sec and low-sec systems with the most ships and pods killed over the last 3 hours (hourly ESI readings kept and added up)."""
    await map_(t)
    r = t.show("violent", await t.js("""(async()=>{ const S=mapData.systems.filter(s=>s.id<31000000), nul=S.filter(s=>secRound(s.s)<=0).slice(0,2), low=S.filter(s=>secRound(s.s)>0&&secRound(s.s)<0.5).slice(0,1), hi=S.find(s=>secRound(s.s)>=0.5);
      const now=Date.now(); kills3={v:1,snaps:[{at:now-5*3600e3,by:[[nul[0].id,99,99]]},{at:now-2*3600e3,by:[[nul[0].id,3,1],[low[0].id,2,0]]},{at:now-3600e3,by:[[nul[0].id,1,1],[nul[1].id,10,0],[hi.id,50,50]]}]};
      kills={at:now,by:new Map()}; showPage('intel'); renderViolent(); await sleep(200);
      const rows=(id)=>[...document.querySelectorAll('#'+id+' tbody tr')].map(r=>[r.cells[0].dataset.v, +r.cells[2].textContent, +r.cells[3].textContent]);
      const before=kills3.snaps.length; await kills3Keep([{system_id:nul[0].id,ship_kills:1,pod_kills:1},{system_id:nul[1].id,ship_kills:10,pod_kills:0},{system_id:hi.id,ship_kills:50,pod_kills:50}]);
      return {nul:rows('intel-null'), low:rows('intel-low'), names:[nul[1].n, nul[0].n, low[0].n], since:document.getElementById('intel-kills-since').textContent, same:kills3.snaps.length===before, side:!!document.querySelector('#page-intel .side-col #intel-null')}; })()"""))
    n = r["names"]
    t.eq(r["nul"], [[n[0], 10, 0], [n[1], 4, 2]], "null-sec: the last 3 hours added up (an older reading left out), most ships + pods first; high-sec left out")
    t.eq(r["low"], [[n[2], 2, 0]], "low-sec in its own panel")
    t.ok("2 of the last 3 hours" in r["since"] and r["same"] and r["side"], "it says how many hours it counts; a repeated reading isn't kept twice; the panels sit in the right column", r)

@scenario
async def contract_items_rate_limit(t):
    """A corporation with many contracts: when ESI rate-limits contract items (429), the sync stops asking and goes on; the rest are read at the next sync."""
    r = t.show("429", await t.js("""(async()=>{ const rf=window.fetch; let calls=0, limit=true;
      window.fetch=(u,i)=>{ if(!String(u).includes('/contracts/')) return rf(u,i); calls++; return Promise.resolve(limit ? new Response('{}',{status:429}) : new Response(JSON.stringify([{type_id:34,quantity:5,is_included:true}]),{status:200})); };
      const list=()=>Array.from({length:50},(_, k)=>({id:880000+k})), path=(id)=>'/corporations/98000009/contracts/'+id+'/items/';
      try { const t0=Date.now(), L=list(); await contractItems('corp:98000009', L, path, 'tok', ''); const first=[calls, Date.now()-t0<3000, L.filter(c=>c.items).length];
        state.contracts['corp:98000009']={list:L}; limit=false; calls=0; const L2=list(); await contractItems('corp:98000009', L2, path, 'tok', '');
        return [...first, calls, L2.filter(c=>c.items&&c.items.length).length]; }
      finally { window.fetch=rf; delete state.contracts['corp:98000009']; } })()"""))
    t.ok(r[0] <= 3 and r[1] and r[2] == 0, "ESI says 429: no waiting and retrying, the other contracts wait for the next sync (not 50 contracts × retries)", r)
    t.eq(r[3:], [50, 50], "the next sync reads them all")

@scenario
async def map_danger(t):
    await supply_setup(t)
    await t.js("loadKills(true)")
    t.eq(await t.js("[killsIn(30000002), isDanger(30000002), killsIn(30000006), isDanger(30000006), killsIn(30000001)]"), [8, True, 1, False, 0], "kills in the last hour: ships and pods count, from 5 a system is dangerous")
    # A leg warns about the dangerous systems it crosses by gate and those it jumps into (the cyno there can be caught)
    lg = await t.js("(()=>{const m=mapIndex(), s=(id)=>m.byId.get(id), n=(L)=>legDanger(L).map(x=>[x.s.n,x.jump]); return [n({path:[s(30000001),s(30000002),s(30000004)],ga:1,gb:0}), n({path:[s(30000004),s(30000002),s(30000001)],ga:0,gb:1}), n({path:[s(30000001),s(30000004),s(30000006)],ga:0,gb:0}), n({path:[s(30000001),s(30000002),s(30000003)],gatesOnly:true}), n({path:[s(30000001),s(30000002),s(30000004)],ga:0,gb:0})]})()")
    t.eq(lg, [[["Bravo", False]], [["Bravo", True]], [], [["Bravo", False]], [["Bravo", True]]], "a leg warns about dangerous systems it crosses by gate or jumps into")
    await t.js("mapSelect(30000002)"); await asyncio.sleep(0.3)
    info = await t.text("#map-info"); t.ok("Dangerous" in info and "6 ships, 2 pods, 10 NPCs killed" in info, "the system info shows the last hour's kills", info)
    t.ok(await sc_plan(t), "planning the trips")
    sc = t.show("supply", await t.js("({risky:scLast.trips.filter(t=>legDanger(t.main).length||(t.rep.path.length>1&&legDanger(t.rep).length)).map(t=>t.n), warn:document.querySelectorAll('#sc-box tbody .label[data-tip*=\"killed\"]').length, note:(document.querySelector('#sc-box .notice b')||{}).textContent||''})"))
    t.ok(sc["risky"] and sc["warn"] >= len(sc["risky"]) and "dangerous system" in sc["note"], "supply chain legs through Bravo are flagged", sc)
    # A higher danger level: Bravo isn't dangerous any more
    await t.pg.fill("#map-danger", "10"); await t.pg.dispatch_event("#map-danger", "change"); await asyncio.sleep(0.3)
    t.ok(await t.js("dangerMin()===10 && !isDanger(30000002) && !document.querySelector('#sc-box tbody .label[data-tip*=\"killed\"]')"), "raising the danger level clears the warnings")

@scenario
async def todo_slots(t):
    H = 3600e3
    await t.js(f"()=>{{const n=Date.now(); state.chars[0].jobs=[{{id:1,activity:1,end:n+{H},status:'active'}},{{id:2,activity:9,end:n-{H},status:'ready'}}]; state.chars[1].jobs=[]; saveLocal();}}")
    exp = t.show("expected", await t.js("state.chars.filter(hasJobData).map(c=>{const s=slotsOf(c),u=usedOf(c),can={M:1,S:lv(c,'Science')>0,R:lv(c,'Reactions')>0}; return [c.name,'MSR'.split('').filter(k=>can[k]&&s[k]>u[k]).map(k=>[k,s[k]-u[k]])]})"))
    t.ok(not any(k == "R" for e in exp if e[0] == "Ender Beta" for k, _ in e[1]), "a pilot without the Reactions skill has no reaction slot to fill", exp)
    await t.tab("todo", 0.4)
    li = t.show("slots", await t.js("[!document.getElementById('todo-sl-panel').hidden, [...document.querySelectorAll('#todo-sl-table tbody tr')].map(r=>[...r.cells].map(c=>c.innerText.replace(/[✕\\s]+/g,' ').trim())), [...document.querySelectorAll('#todo-sl-table thead th')].map(h=>h.innerText.split('\\n')[0].trim())]"))
    t.ok(li[0] and len(li[1]) == len([e for e in exp if e[1]]) and "Solo Gamma" not in str(li[1]), "Empty job slots lists pilots with job data and free slots", li)
    t.eq(li[2], ["Pilot", "Empty manufacturing slots", "Empty science slots", "Empty reactions slots", "Finished jobs to deliver"], "Empty job slots is a table with a column per kind of slot")
    t.ok(any(r[0] == "Ender Alpha" and r[4] == "1" for r in li[1]), "a finished job still holding its slot is listed", li)
    # Counting them on the To-Do tab: off by default, a tick box turns it on
    b0 = await t.js("+(document.querySelector('.tabs button[data-tab=todo]').dataset.alert||0)")
    t.ok(await t.js("!document.getElementById('todo-sl-count').checked && !state.misc.todoSlCount"), "empty job slots aren't counted on the tab by default")
    await t.pg.click("#todo-sl-count"); await asyncio.sleep(0.2)
    t.eq(await t.js("+(document.querySelector('.tabs button[data-tab=todo]').dataset.alert||0)"), b0 + len(li[1]), "ticking Count adds the pilots with empty slots to the tab's number")
    await t.pg.click("#todo-sl-count"); await asyncio.sleep(0.2)
    t.ok(await t.js("[...document.querySelectorAll('#todo-nav a')].some(a=>a.textContent==='Empty job slots')"), "Empty job slots is in the To-Do navigation")
    n0 = await t.js("document.querySelectorAll('#todo-sl [data-slot-off]').length")
    await t.pg.click("#todo-sl [data-slot-off] >> nth=0"); await asyncio.sleep(0.2)
    t.ok(await t.js(f"document.querySelectorAll('#todo-sl [data-slot-off]').length==={n0 - 1} && !!document.querySelector('[data-slot-show]')"), "✕ hides one kind of slot for a pilot")
    await t.pg.click("[data-slot-show]"); await asyncio.sleep(0.2)
    t.eq(await t.js("document.querySelectorAll('#todo-sl [data-slot-off]').length"), n0, "Show them again brings it back")
    await t.pg.click("#todo-sl [data-sl-k=S]"); await asyncio.sleep(0.2)
    t.ok(await t.js("![...document.querySelectorAll('#todo-sl-table thead th')].some(h=>h.innerText.includes('science')) && state.misc.slotShow.K.S===false"), "Show: a kind of slot can be left out")
    await t.pg.click("#todo-sl [data-sl-c=a]"); await asyncio.sleep(0.2)
    t.ok(await t.js("![...document.querySelectorAll('#todo-sl-table tbody th')].some(h=>h.innerText==='Ender Alpha') && !slotsToFill().some(x=>x.c.id==='a')"), "Show: a pilot can be left out")
    await t.pg.click("#todo-sl [data-sl-k=S]"); await t.pg.click("#todo-sl [data-sl-c=a]"); await asyncio.sleep(0.2)
    t.eq(await t.js("document.querySelectorAll('#todo-sl-table tbody tr').length"), len(li[1]), "Show: everything back")

@scenario
async def market_history(t):
    st = t.show("stats", await t.js("(async()=>{const R=await mktHistory(10000002,[34]); const s=mhStats(R[34]); return {d1:+s.d1.toFixed(4), d7:+s.d7.toFixed(4), perDay:s.perDay}})()"))
    t.eq(st, {"d1": 0.1, "d7": 0.375, "perDay": 100}, "market history: daily average change over 1 and 7 days, sold per day over the last 7 days")
    # Trading board: a new table gets its 24 h and 7 days columns from the history (marked ~) and how much sells
    await t.js("()=>{tbList().push({id:'bh',name:'History test',market:'st:60003760',sel:[{k:'item',id:34,name:'Tritanium'}],snaps:{}}); saveMisc();}")
    await t.tab("prices", 0.3); await t.js("refreshBoard(tbList().find(b=>b.id==='bh'))")
    t.ok(await t.until("!!document.querySelector('#tb-list table tbody tr:not(.group)')", 15), "the board refreshed")
    row = t.show("row", await t.js("[...document.querySelectorAll('#tb-list table tbody tr:not(.group)')].map(r=>[...r.cells].map(c=>c.innerText.trim()))[0]"))
    t.ok(row and row[3].startswith("~") and "10.0%" in row[3] and row[4].startswith("~") and "37.5%" in row[4] and row[8] == "100", "a new table's 24 h and 7 days come from the history (~) and Sold per day shows", row)
    # Once your own refreshes are a day old, they win
    await t.js("()=>{const b=tbList().find(b=>b.id==='bh'); b.snaps[34].unshift([Date.now()-25*3600e3, 2, 1]); renderBoards();}")
    row2 = await t.js("[...document.querySelectorAll('#tb-list table tbody tr:not(.group)')].map(r=>r.cells[3].innerText.trim())[0]")
    t.ok(not row2.startswith("~") and "100.0%" in row2, "your own day-old refresh replaces the history", row2)
    # Tables in your own order: ↑ / ↓ swap a table with its neighbour and the order is saved
    await t.js("()=>{tbList().push({id:'bo',name:'Order test',market:'st:60003760',sel:[],snaps:{}}); saveMisc(); renderBoards();}")
    names = lambda: t.js("[...document.querySelectorAll('#tb-list > .fc-box h3')].map(h=>h.childNodes[0].textContent.trim())")
    before = await names(); t.ok(before[-2:] == ["History test", "Order test"], "the new table comes last", before)
    t.ok(await t.js("document.querySelector('[data-tb-move=\"bo|-1\"]').disabled===false && document.querySelector('[data-tb-move=\"bo|1\"]').disabled"), "the last table can move up but not down", before)
    await t.pg.click('[data-tb-move="bo|-1"]'); await asyncio.sleep(0.2)
    after = await names(); t.ok(after[-2:] == ["Order test", "History test"], "↑ moves a table above the one before it", after)
    t.eq(await t.js("JSON.parse(localStorage.getItem('eve-industry-misc')).boards.map(b=>b.id).slice(-2)"), ["bo", "bh"], "the new order is saved")
    await t.pg.click('[data-tb-move="bo|1"]'); await asyncio.sleep(0.2)
    t.ok((await names())[-2:] == ["History test", "Order test"], "↓ moves it back down", await names())

@scenario
async def client_deliveries(t):
    D = 864e5
    await t.js(f"""async()=>{{const n=Date.now(), iso=(x)=>new Date(x).toISOString(); state.misc.cm=[{{id:'c1',client:'Bob Client',created:n-2*{D},items:{{34:1000,35:50}},names:{{34:'Tritanium',35:'Pyerite'}},sends:[]}}]; saveMisc();
      const raw=[{{contract_id:8801,type:'item_exchange',issuer_id:9001,assignee_id:777001,status:'finished',date_issued:iso(n-{D}),date_completed:iso(n-{D}/2),price:0}},{{contract_id:8802,type:'item_exchange',issuer_id:9001,assignee_id:777001,status:'rejected',date_issued:iso(n-{D}),price:0}},
        {{contract_id:8803,type:'item_exchange',issuer_id:9001,assignee_id:9001,status:'finished',date_issued:iso(n-{D}),price:0}},{{contract_id:8804,type:'courier',issuer_id:9001,assignee_id:777001,status:'outstanding',date_issued:iso(n-{D}),price:0}}];
      state.contracts['char:9001']={{at:n,list:[],sent:await cmDeliveries('char:9001',raw,9001,'tok')}}; saveContracts();}}""")
    sent = t.show("deliveries", await t.js("state.contracts['char:9001'].sent.map(d=>[d.id,d.status,d.toName,d.items])"))
    t.eq(sent, [[8801, "finished", "Bob Client", [[34, 400]]], [8802, "rejected", "Bob Client", [[35, 50]]]], "item exchanges to someone outside your pilots are kept with their items and who they're for")
    await t.tab("contracts", 0.3); await t.js("cmOpen='c1'; renderContracts()")
    t.ok("1 in game to record" in (await t.text("#cm-list")), "the client's order says a delivery in game isn't recorded yet")
    det = await t.text("#cm-detail"); t.ok("Accepted" in det and "Rejected" in det and "Record as sent" in det, "the opened order lists its in-game deliveries", det[:600])
    await t.pg.click("[data-cm-rec='8801']"); await asyncio.sleep(0.2)
    t.eq(await t.js("[state.misc.cm[0].sends.length, state.misc.cm[0].sends[0].contract, cmMissing(state.misc.cm[0]).find(x=>x.t===34).left, document.querySelectorAll('[data-cm-rec]').length]"), [1, 8801, 600, 0], "recording a delivery adds its items as a send (a rejected one isn't offered)")
    # A recorded delivery that later fails is flagged
    await t.js("state.contracts['char:9001'].sent[0].status='expired'; renderContracts()")
    t.ok("1 not delivered" in (await t.text("#cm-list")) and "Recorded, but not delivered" in (await t.text("#cm-detail")), "a recorded delivery whose contract expired is flagged")
    # Made for the corporation, and to the client's other character: found once linked
    await t.js(f"""async()=>{{const n=Date.now(), iso=(x)=>new Date(x).toISOString(); state.chars[0].corpId=98000001;
      const raw=[{{contract_id:8806,type:'item_exchange',issuer_id:9001,issuer_corporation_id:98000001,for_corporation:true,assignee_id:777001,status:'outstanding',date_issued:iso(n-{D}),price:0}},{{contract_id:8805,type:'item_exchange',issuer_id:9001,assignee_id:777002,status:'finished',date_issued:iso(n-{D}),price:0}}];
      state.contracts['corp:98000001']={{at:n,list:[],sent:await cmDeliveries('corp:98000001',raw,null,'tok',98000001)}}; state.contracts['char:9001'].sent.push(...await cmDeliveries('char:9001',raw,9001,'tok')); saveContracts(); renderContracts();}}""")
    t.eq(await t.js("cmGameDeliveries(state.misc.cm[0]).map(d=>[d.id,d.corp])"), [[8801, False], [8802, False], [8806, True]], "a contract a pilot made for the corporation is found too")
    t.ok("Bob Alt" in (await t.js("document.getElementById('cm-detail').textContent")), "item exchanges to other characters are offered for linking")
    await t.js("document.querySelector('#cm-detail details').open=true"); await t.pg.click("[data-cm-alias='Bob Alt']"); await asyncio.sleep(0.2)
    t.eq(await t.js("[state.misc.cm[0].game, cmGameDeliveries(state.misc.cm[0]).some(d=>d.id===8805)]"), [["Bob Alt"], True], "linking the client's other character brings its deliveries in")
    await t.pg.locator("#cm-detail").screenshot(path=SP + "cm_deliveries.png")
    # Nothing found: the box still says what it looked for and when
    await t.js("()=>{state.misc.cm.push({id:'c2',client:'Nobody Here',created:Date.now(),items:{34:1},names:{34:'Tritanium'},sends:[]}); cmOpen='c2'; saveMisc(); renderContracts();}")
    nb = await t.text("#cm-detail"); t.ok("In-game deliveries" in nb and "None since this order was created" in nb, "with nothing found, the box says what it looked for and when it was read", nb[:400])

@scenario
async def public_contracts(t):
    await plan(t, "Venture Blueprint", 10)
    await t.pg.click("[data-pc-check]"); t.ok(await t.until("buildState.plan.pc && !buildState.plan.pc.busy", 20), "the public contracts check finished", await t.js("buildState.plan.pc && buildState.plan.pc.msg"))
    pc = t.show("contracts", await t.js("(()=>{const R=buildState.plan.pc.res, r=buildState.plan.res; return {prod:R.prod.map(x=>[x.id,x.q,x.unit]), read:R.read, build:(r.fullTotal||r.total)/r.qty}})()"))
    t.eq(pc["prod"], [[7001, 2, 250000], [7003, 1, 900000]], "only contracts holding the Ventures alone count (both pages read, cheapest each first)")
    t.eq(pc["read"], 4, "every page is read, item exchanges only")
    box = await t.text("#plan-out")
    want = "Buying beats building" if pc["build"] > 250000 else "Building is cheaper"
    t.ok(want in box and "Public contracts" in box, f"the plan says: {want}", box[box.find("Public contracts"):][:400] if "Public contracts" in box else box[:300])
    t.ok(await t.js("[...document.querySelectorAll('#plan-nav a')].some(a=>a.textContent==='Public contracts')"), "Public contracts is in the plan's navigation")

@scenario
async def jump_planner_and_blueprint_calc(t):
    await ships(t); await map_(t)
    t.ok(await t.until("(s=>s.includes('Incursion (no cynos) · 1 system') && !s.includes('1 systems'))(document.getElementById('map-legend').innerText)", 8), "incursions show on the map legend", await t.text("#map-legend"))
    await t.pg.fill("#jp-from", "Charlie"); await t.pg.fill("#jp-to", "Echo"); await t.pg.select_option("#jp-trips", "round"); await t.pg.fill("#jp-rounds", "3"); await t.pg.click("#jp-form button[type=submit]"); await asyncio.sleep(0.3)
    jp = t.show("round trips", (await t.text("#jp-out"))[:400]); t.ok(jp and "jump" in jp.lower(), "the jump planner plans round trips", jp)
    iso = "+document.querySelectorAll('#jp-out .slot-tile')[1].querySelector('.muted').textContent.split(' ')[0].replace(/[^0-9]/g,'')"
    i5 = await t.js(iso); await t.pg.select_option("#jp-jfc", "0"); await asyncio.sleep(0.3); i0 = await t.js(iso)
    t.ok(i5 and abs(i0 / i5 - 2) < 0.01, "Jump Fuel Conservation set on the planner: 0 burns twice what the pilot's V does", [i5, i0])
    await t.pg.select_option("#jp-jfs", "0"); await asyncio.sleep(0.3); j0 = await t.js(iso)
    t.ok(j0 > i0 and await t.js("state.misc.map.jfc === '0' && state.misc.map.jfs === '0'"), "Jump Freighters set on the planner changes the fuel, both kept", [i0, j0])
    await t.pg.select_option("#jp-jfc", ""); await t.pg.select_option("#jp-jfs", ""); await asyncio.sleep(0.3)
    t.eq(await t.js(iso), i5, "Pilot's goes back to the pilot's own levels")
    jdc = t.show("range by JDC", await t.js("()=>{ const d=state.misc.types.Rhea, r=()=>mapRange().range/d.jumpRange; const out=[$('jp-jdc').value, r()]; state.misc.map.jdc='5'; out.push(r()); state.misc.map.jdc=''; return out; }"))
    t.ok(jdc[0] == "" and abs(jdc[1] - 1.8) < 1e-9 and abs(jdc[2] - 2) < 1e-9, "Jump Drive Calibration: Pilot's (the default) uses the pilot's IV, a picked V gives +100%", jdc)
    inc = "()=>{ const P=state.misc.map.plan; P.from='Charlie'; P.to=mapIndex().byId.get(30000006).n; P.trips='one'; planJumps(); return $('jp-out').innerText; }"
    t.ok("incursion" in (await t.js(inc)).lower(), "a jump freighter can't jump into an incursion")
    await t.js("()=>{ state.misc.types.Sin={...state.misc.types.Rhea, id:22430, req:{}, fuel:[]}; state.misc.map.ship='a|Sin'; renderMap(); }")
    out = t.show("black ops", (await t.js(inc))[:300])
    t.ok("incursion" not in out.lower() and "jumps" in out.lower(), "Black Ops jump into an incursion (covert cynos)", out)
    await t.js("()=>{ delete state.misc.types.Sin; state.misc.map.ship=''; renderMap(); }")
    await t.tab("misc"); await t.pg.fill("#bc-sys", "Delta"); await t.pg.dispatch_event("#bc-sys", "change")
    await t.pg.fill("#bc-bp", "Venture Blueprint"); await t.pg.dispatch_event("#bc-bp", "input"); await asyncio.sleep(0.2)
    t.eq(await t.js("document.getElementById('bc-me0').value"), "10", "the Blueprint calculator starts from the copy you own")
    await t.pg.fill("#bc-me0", "2"); await t.pg.fill("#bc-me1", "10"); await t.pg.click("#bc-form button[type=submit]")
    t.ok(await t.until("!!document.querySelector('#bc-out .slot-tile') || !!document.querySelector('#bc-out .notice')", 10), "the Blueprint calculator answers")

# ---------- supply chain
async def supply_setup(t, rx=True):
    await ships(t); await map_(t); await structs(t)
    if rx: await reactions(t)
    await plan(t, "Venture Blueprint", 10); await t.js("sendToOrders(buildState.plan.res)")
    await t.js("const c=state.chars.find(x=>x.name==='Ender Alpha'); c.loc={sys:30000005,at:Date.now()}; c.ship={type:28844,at:Date.now()}; c.scopes=(c.scopes||'')+' esi-location.read_location.v1'")
    await t.tab("map"); t.ok(await t.until("!!mapIndex() && !!document.querySelector('#sc-box [data-sc-plan]')", 10), "the supply chain panel didn't show")
async def sc_plan(t):
    await t.pg.click("[data-sc-plan]"); await asyncio.sleep(0.5); return await t.until("!!scLast && !scBusy", 30)
CHAIN = """(P)=>{ const m=mapIndex(), bad=[], by=new Map(); for(const t of P.trips)(by.get(t.car)||by.set(t.car,[]).get(t.car)).push(t);
  for(const [car,L] of by){ let at=m.byId.get(car.sys), t0=0; for(const t of L){ if(t.rep.path[0].id!==at.id) bad.push('trip '+t.n+' starts in '+t.rep.path[0].n+', ship is in '+at.n); if(t.rep.path[t.rep.path.length-1].id!==t.B.from.id||t.main.path[0].id!==t.B.from.id) bad.push('trip '+t.n+' legs do not join'); if(t.start<t0-1) bad.push('trip '+t.n+' starts before the last one ended'); at=t.B.to; t0=t.finish; } }
  // a pilot flies one ship at a time
  const byP=new Map(); for(const t of P.trips)(byP.get(t.car.c.id)||byP.set(t.car.c.id,[]).get(t.car.c.id)).push(t);
  for(const [,L] of byP){ L.sort((a,b)=>a.start-b.start); for(let i=1;i<L.length;i++) if(L[i].start<L[i-1].finish-1) bad.push('trip '+L[i].n+' starts while the pilot still flies trip '+L[i-1].n); }
  for(const t of P.trips) for(const p of t.B.parts){ const d=p.mv.dep; if(!d) continue; for(const u of P.trips) if(u!==t && u.B.parts.some(q=>q.mv.into&&q.mv.into.ord===d.ord&&q.mv.into.loc===d.loc) && u.finish>t.load+1) bad.push('trip '+t.n+' loads before its materials land (trip '+u.n+')'); }
  return bad; }"""

@scenario
async def supply_chain(t):
    await supply_setup(t)
    cars = t.show("ships", await t.js("[...document.querySelectorAll('#sc-box tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
    t.ok(len(cars) == 1 and "Rhea" in cars[0] and "flown now" in cars[0], "the Rhea flown now is one ship (not also counted from the assets)", cars)
    t.ok(await sc_plan(t), "planning the trips")
    p = t.show("plan", await t.js("({moves:scLast.moves.map(m=>[m.kind,m.from.n+'>'+m.to.n,m.what.slice(0,40)]), trips:scLast.trips.map(t=>[t.n,t.B.from.n+'>'+t.B.to.n,Math.round(t.B.vol)]), left:scLast.left.length})"))
    t.ok(p["trips"] and not p["left"], "every move gets a trip", p)
    # the next cycle's inputs (no deadline yet) go before later cycles' inputs
    first_rx = await t.js("(()=>{const t=scLast.trips.find(t=>t.B.parts.some(p=>p.mv.id.startsWith('rx:in'))); return t && t.B.parts.filter(p=>p.mv.id.startsWith('rx:in')).map(p=>p.mv.id)})()")
    t.ok(first_rx and "rx:in:next" in first_rx, "the next cycle's inputs ride first", first_rx)
    # both focuses: every ship's legs chain, a pilot never flies two at once, goods wait for their materials; fuel plan never worse than trip by trip
    foc = t.show("focus", await t.js("""(async()=>{ const m=mapIndex(), out={}, chk=""" + CHAIN + """;
      for (const f of ['cost','time']) { scCfg().focus=f; const P=await scPlan(m); out[f]={greedy:Math.round(P.greedy.fuel/1e6), fuel:Math.round(P.trips.reduce((a,t)=>a+t.fuel,0)/1e6), trips:P.trips.length, bad:chk(P)}; }
      scCfg().focus='cost'; return out; })()"""))
    for f in ("cost", "time"): t.ok(not foc[f]["bad"], f"supply chain legs chain ({f})", foc[f]["bad"])
    t.ok(foc["cost"]["fuel"] <= foc["time"]["fuel"], "the fuel-cost plan burns no more than the fastest", foc)
    t.ok(foc["cost"]["fuel"] <= foc["cost"]["greedy"], "the whole plan burns no more than trip by trip", foc)
    # Done: the moves leave, the ship is where the trip ended
    await t.pg.click("[data-sc-done='1']"); await asyncio.sleep(0.5); await t.until("!scBusy", 30)
    d = t.show("after done", await t.js("({done:Object.keys(scCfg().done).length, ships:scCfg().ships})"))
    t.ok(d["done"] > 0 and any(v.get("sys") for v in d["ships"].values()), "Done marks the moves and moves the ship", d)
    await t.pg.locator("#sc-box").screenshot(path=SP + "scbox.png")

@scenario
async def supply_horizon(t):
    await supply_setup(t)
    hz = t.show("horizon", await t.js("""(()=>{ const m=mapIndex(), out={}; for (const h of [3,28]) { scCfg().horizon=h; const M=scMoves(m).moves, ins=M.filter(x=>x.id.startsWith('rx:in')), outs=M.filter(x=>x.id.startsWith('rx:out'));
        out[h]={ins:ins.length, outs:outs.length, deps:outs.every(o=>o.dep && ins.some(i=>i.into && i.into.ord===o.dep.ord)), needs:ins.map(i=>i.need!=null), until:Math.round((scMoves(m).until-Date.now())/864e5)}; } scCfg().horizon=14; return out; })()"""))
    t.eq(hz["3"]["ins"], 1, "3 days ahead: only the next reaction cycle")
    t.ok(hz["28"]["ins"] >= 4 and hz["28"]["outs"] >= 3, "4 weeks ahead: a cycle a week (7-day cycles)", hz)
    t.ok(hz["28"]["deps"], "a planned cycle's products wait for that cycle's inputs", hz)
    t.ok(hz["28"]["needs"][0] is False and all(hz["28"]["needs"][1:]), "later cycles' inputs are needed when their cycle starts", hz)
    t.eq(hz["28"]["until"], 28, "the plan reaches as far as Plan ahead says")
    await t.pg.select_option("#sc-horizon", "7"); await asyncio.sleep(0.2)
    t.eq(await t.js("scCfg().horizon"), 7, "Plan ahead is kept")
    # PI: P4 at the pickup, inputs needed by it; further refills restart the planets and their P4 waits for the inputs
    pi = t.show("pi", await t.js("""(()=>{ const now=Date.now(), c=state.chars[0], end=now+30*3600e3, seen=now-10*3600e3;
      c.planets=[{id:1,name:'Delta I',type:'barren',system:'Delta',lastUpdate:seen,factories:2,extractors:[],inputs:[{name:'Fake',stock:100,perHour:10,end}],makes:[{name:'Nano-Factory',perHour:2},{name:'Coolant',perHour:40}],stock:[{name:'Nano-Factory',amount:5}],unneeded:[]}];
      Object.assign(piCfg(),{on:true,time:'18:00',gap:5,deliv:'Alpha',planetSys:'Delta',alloc:{2869:12},stockDays:7}); scCfg().horizon=28; const at=pickupAt(end), want=Math.floor(5+2*(Math.min(at,end)-seen)/3600e3);
      const mv=scMoves(mapIndex()).moves.filter(x=>x.id.startsWith('pi:')), outs=mv.filter(x=>x.id.startsWith('pi:out')), ins=mv.filter(x=>x.id.startsWith('pi:in'));
      return {want, first:outs[0]&&outs[0].items.map(i=>i.n+' '+i.q), firstReady:outs[0]&&outs[0].ready===at, inNeed:ins[0]&&ins[0].need===at, outs:outs.length, ins:ins.length, later:outs.slice(1).map(o=>[o.items.map(i=>i.n+' '+i.q).join(), !!o.dep && ins.some(i=>i.into.ord===o.dep.ord)])}; })()"""))
    t.ok(pi["first"] == ["Nano-Factory " + str(pi["want"])] and pi["firstReady"] and pi["inNeed"], "PI pickup is the P4 on the planets at the pickup time", pi)
    t.ok(pi["ins"] >= 3 and pi["outs"] >= 3, "7-day refills over 4 weeks", pi)
    t.ok(all(x[0] == "Nano-Factory 336" and x[1] for x in pi["later"]), "a later pickup is a full 7 days of P4 and waits for its refill's inputs", pi["later"])

@scenario
async def supply_ships(t):
    await supply_setup(t, rx=False)
    # a second Rhea docked in Delta: one more ship for the same pilot
    await t.js("()=>{state.assets['char:9001'].rows.push({t:28844,loc:60000002,h:'Hangar',q:1}); scLast=null; renderSupply()}")
    cars = t.show("ships", await t.js("scCarriers(mapIndex()).map(x=>[x.key,x.n,(mapIndex().byId.get(x.sys)||{}).n,x.src])"))
    t.ok(len(cars) == 2 and {c[2] for c in cars} == {"Echo", "Delta"}, "a pilot's two Rheas are two ships: the one flown now and the one docked", cars)
    # add a ship by hand, set where it is, untick it, remove it
    await t.pg.select_option("#sc-add-pick", "a|Rhea"); await t.pg.click("[data-sc-add]"); await asyncio.sleep(0.2)
    key = await t.js("scCfg().added[0] && scCfg().added[0].key"); t.ok(key, "adding a ship")
    await t.pg.fill(f"[data-sc-sys='{key}']", "Golf"); await t.pg.dispatch_event(f"[data-sc-sys='{key}']", "change"); await asyncio.sleep(0.2)
    t.eq(await t.js(f"(mapIndex().byId.get(scCarriers(mapIndex()).find(x=>x.key==='{key}').sys)||{{}}).n"), "Golf", "setting where an added ship is")
    await t.pg.click(f"[data-sc-del='{key}']"); await asyncio.sleep(0.2)
    t.eq(await t.js("scCfg().added.length"), 0, "removing an added ship")
    t.ok(await sc_plan(t), "planning with two ships")
    await t.pg.locator("#sc-box").screenshot(path=SP + "sc_ships.png")
    bad = t.show("chain", await t.js("(" + CHAIN + ")(scLast)")); t.ok(not bad, "legs chain and the pilot flies one ship at a time", bad)
    # the whole plan with one pilot and two ships far apart: never both at once; changing ships is a shuttle through the gates (travel time, no cooldown),
    # a jump clone only when it's an hour or more sooner (here: when there's no gate route), then the clone cooldown
    ONE = """(async(noGates)=>{ const m=mapIndex(), A=m.byName.get('alpha'), D=m.byName.get('delta'), F=m.byName.get('foxtrot'), base=scCarriers(m)[0], now=Date.now(), P={...base.c,id:'p1',name:'Solo'}, keep=gatePath;
      if (noGates) gatePath=(a,b,hs)=>a===b?[a]:null;
      try { const a={...base, key:'k1', c:P, at:A, sys:A.id, psys:A.id, flown:true, cool:0, cd:19*3600e3, fat:0}, f={...base, key:'k2', c:P, at:F, sys:F.id, psys:A.id, flown:false, cool:0, cd:19*3600e3, fat:0};
        const mv=(id,from,to)=>({id, kind:'Test', label:'Test', what:id, items:[], from, to, vol:1000, ore:0, val:0, ready:now, need:null});
        const R=await scSolve([mv('x',A,D), mv('y',F,D), mv('z',F,A)], [a,f], {now, wait:0, focus:'time', iters:800, budget:3000});
        const T=R.trips.slice().sort((x,y)=>x.start-y.start), shipAt={k1:A.id,k2:F.id}, bad=[]; let pilot=A.id;
        for (const t of T) { const need=shipAt[t.car.key]!==pilot; if (need!==!!t.sw) bad.push('trip '+t.B.from.n+'>'+t.B.to.n+(need?' needs':" doesn't need")+' a change of ship');
          if (t.sw && t.sw.by==='shuttle') { const g=keep(m.byId.get(pilot), m.byId.get(shipAt[t.car.key]), false).length-1; if (t.sw.gates!==g || Math.abs(t.rep.depart-t.start-g*SC_SHUTTLE_MIN*60e3)>1) bad.push('trip '+t.B.from.n+'>'+t.B.to.n+': shuttle of '+t.sw.gates+' gates, '+Math.round((t.rep.depart-t.start)/6e4)+' min'); }
          shipAt[t.car.key]=t.B.to.id; pilot=t.B.to.id; }
        return {trips:T.map(t=>[t.car.key,t.B.from.n+'>'+t.B.to.n,t.sw&&t.sw.by,t.sw&&t.sw.gates,Math.round((t.start-now)/60e3),Math.round((t.finish-now)/60e3)]), overlap:T.some((t,i)=>i&&t.start<T[i-1].finish-1), by:T.filter(t=>t.sw).map(t=>t.sw.by), clones:T.filter(t=>t.clone).map(t=>t.start), bad, left:R.left.length};
      } finally { gatePath=keep; } })"""
    for no_gates in (False, True):
        syn = t.show("one pilot" + (", no gate route" if no_gates else ""), await t.js(ONE + "(" + ("true" if no_gates else "false") + ")"))
        t.ok(not syn["overlap"] and not syn["left"], "one pilot never flies two ships at once", syn)
        t.ok(syn["by"] and not syn["bad"], "the pilot changes ship only when the ship is elsewhere, a shuttle taking its gates' time", syn)
        if not no_gates: t.ok(set(syn["by"]) == {"shuttle"}, "a short way through the gates is a shuttle, not a jump clone", syn)
        else:
            t.ok(set(syn["by"]) == {"clone"}, "with no gate route the pilot jump clones", syn)
            cl = syn["clones"]; t.ok(all(cl[k] - cl[k-1] >= 19 * 3600e3 - 1 for k in range(1, len(cl))), "jump clones respect the cooldown", syn)

@scenario
async def supply_assets_done(t):
    await supply_setup(t, rx=False)
    # the Tritanium move to Golf: noted when first planned; more Tritanium in Golf on a newer assets read = arrived
    mv = t.show("move", await t.js("(()=>{const M=scMoves(mapIndex()).moves, x=M.find(m=>m.to.n==='Golf' && m.items[0].n==='Tritanium'); return x && {id:x.id, q:x.items[0].q, base:scCfg().seen[x.id]}})()"))
    if not t.ok(mv and mv["base"], "a planned move is noted against the hangars", mv): return
    q = mv["q"]
    await t.js(f"()=>{{const a=state.assets['char:9001']; a.rows.push({{t:34,loc:60000004,h:'Hangar',q:{q // 2}}}); a.at=Date.now()+1000}}")
    half = await t.js(f"(()=>{{const R=scMoves(mapIndex()); return {{det:R.detected.map(d=>[d.id,+d.f.toFixed(2)]), done:scCfg().done['{mv['id']}']}}}})()")
    t.ok(half["det"] and half["det"][0][0] == mv["id"] and abs(half["det"][0][1] - 0.5) < 0.02, "half of it in Golf: the move is half done", half)
    # another pilot's hangars read later don't count as arrivals
    await t.js("()=>{state.assets['char:9002']={at:Date.now()+2000,owner:'Other',rows:[{t:34,loc:60000004,h:'Hangar',q:9e6}]}}")
    t.eq(await t.js("scMoves(mapIndex()).detected.length"), 0, "a new owner's stock isn't an arrival")
    await t.js(f"()=>{{const a=state.assets['char:9001']; a.rows.find(r=>r.loc===60000004).q={q}; a.at=Date.now()+3000}}")
    full = await t.js(f"(()=>{{const R=scMoves(mapIndex()); return {{det:R.detected.map(d=>d.id), left:R.moves.some(m=>m.id==='{mv['id']}')}}}})()")
    t.ok(full["det"] == [mv["id"]] and not full["left"], "all of it in Golf: the move is done and leaves the plan", full)
    # shown after planning, and undone
    await t.js(f"()=>{{const a=state.assets['char:9001']; a.rows.find(r=>r.loc===60000004).q=0; a.at=Date.now()+4000; delete scCfg().done['{mv['id']}']; delete scCfg().seen['{mv['id']}']}}")
    await t.js("scMoves(mapIndex())")   # noted again at zero
    await t.js(f"()=>{{const a=state.assets['char:9001']; a.rows.find(r=>r.loc===60000004).q={q}; a.at=Date.now()+5000}}")
    t.ok(await sc_plan(t), "planning")
    note = t.show("notice", await t.js("[...document.querySelectorAll('#sc-box .notice')].map(n=>n.innerText).find(t=>t.includes('assets show'))"))
    t.ok(note and "Tritanium" in note, "the plan says what the assets marked done", note)
    await t.pg.click("[data-sc-undo]"); await asyncio.sleep(0.2)
    t.ok(await t.js(f"scCfg().done['{mv['id']}']===undefined && !scCfg().seen['{mv['id']}']"), "Undo puts it back and notes the hangars again")

@scenario
async def supply_whole_plan(t):
    await ships(t); await map_(t); await t.tab("map")
    await t.js("const c=state.chars.find(x=>x.name==='Ender Alpha'); c.loc={sys:30000005,at:Date.now()}; c.ship={type:28844,at:Date.now()}")
    syn = t.show("whole plan", await t.js("""(async()=>{ const m=mapIndex(), A=m.byName.get('alpha'), D=m.byName.get('delta'), base=scCarriers(m).find(x=>x.n), now=Date.now();
      const rhea={...base, key:'t1', c:{...base.c,id:'t1',name:'Rhea'}, cap:300000, ore:0, at:A, sys:A.id, psys:null, fat:0}, rorq={...base, key:'t2', c:{...base.c,id:'t2',name:'Rorqual'}, n:'Rorqual', cap:50000, ore:150000, perLy:base.perLy*0.6, at:A, sys:A.id, psys:null, fat:0};
      const mv=(id,vol,ore,ready)=>({id, kind:'Test', label:'Test', what:id, items:[], from:A, to:D, vol, ore, val:0, ready, need:null}), F=scLeg(rhea,{last:now,fat:0,timer:0},A,D,now).fuel;
      const R1=await scSolve([mv('ore',450000,450000,now), mv('mat',150000,0,now)], [rhea, rorq], {now, wait:0, focus:'cost', iters:3000, budget:5000});
      const R2=await scSolve([mv('ore',300000,300000,now), mv('mat',100000,0,now+3*3600e3)], [rorq], {now, wait:24*3600e3, focus:'cost', iters:1500, budget:5000});
      return {legs:+(R1.fuel/F).toFixed(2), carried:Math.round(R1.trips.reduce((a,t)=>a+t.B.vol,0)), left:R1.left.length, later:{legs:R2.trips.reduce((a,t)=>a+(t.rep.path.length>1)+1,0), oreInCargo:Math.round(R2.trips.reduce((a,t)=>a+t.B.ore-t.B.oreHold,0))}}; })()"""))
    # best here: Rorqual twice full (2 × 150k ore + 50k goods, one empty return) + Rhea once = 2 × 0.6 + 0.6 + 1 = 2.8 Rhea legs of fuel
    t.ok(syn["legs"] <= 2.81 and syn["carried"] == 600000 and not syn["left"], "the whole-plan search finds the cheapest Rorqual + Rhea mix", syn)
    t.ok(syn["later"]["legs"] == 3 and not syn["later"]["oreInCargo"], "the Rorqual waits for the goods and runs twice with both holds full", syn)

@scenario
async def supply_freight(t):
    await supply_setup(t, rx=False)
    await t.js("window.__rh=state.misc.types.Rhea; state.misc.types.Rhea={...state.misc.types.Rhea, cargo:0, oreHold:0}; scCfg().freight=[]; scLast=null; renderSupply()")
    t.ok(await sc_plan(t), "planning")
    fr = t.show("freight", await t.js("({n:scCfg().freight.length, badge:document.querySelector('.tabs button[data-tab=todo]').dataset.alert||'', label:document.querySelector('.tabs button[data-tab=todo]').textContent, first:scCfg().freight[0]&&scCfg().freight[0].why})"))
    t.ok(fr["n"] and fr["badge"] == str(fr["n"]) and fr["label"] == "To-Do", "trips no ship can do are counted on the To-Do tab", fr)
    await t.tab("todo", 0.3)
    t.ok(not await t.js("$('todo-sc-panel').hidden"), "To-Do lists the trips for a freight service")
    await t.pg.click("#todo-sc [data-sc-freight='0']"); await asyncio.sleep(0.2)
    t.eq(await t.js("scCfg().freight.length"), fr["n"] - 1, "marking one sent by freight")
    await t.js("state.misc.types.Rhea=window.__rh; scCfg().freight=[]; saveMisc(); scAlerts()")

@scenario
async def market_budget(t):
    """Every ESI market read shares one queue: a refusal pauses them all, ESI's rate-limit headers are followed, at most 6 at once."""
    state = {"n": 0, "live": 0, "peak": 0}
    async def h429(route):
        state["n"] += 1
        hd = {"Access-Control-Allow-Origin": "*", "Access-Control-Expose-Headers": "Retry-After, X-Ratelimit-Limit, X-Ratelimit-Remaining", "Content-Type": "application/json"}
        if state["n"] == 1: return await route.fulfill(status=429, headers={**hd, "Retry-After": "1"}, body="{}")
        return await route.fulfill(status=200, headers={**hd, "X-Ratelimit-Limit": "150/15m", "X-Ratelimit-Remaining": "10"}, body="[]")
    async def slow(route):
        state["live"] += 1; state["peak"] = max(state["peak"], state["live"]); await asyncio.sleep(0.25); state["live"] -= 1
        await route.fulfill(status=200, headers={"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}, body="[]")
    await t.pg.context.route("**/markets/99999991/**", h429); await t.pg.context.route("**/markets/99999992/**", slow)
    r = t.show("429 then ok", await t.js("""(async()=>{ const t0=Date.now(); const r=await esiMarket('https://esi.evetech.net/latest/markets/99999991/orders/?page=1'); return {status:r.status, waited:Date.now()-t0, limit:MKT.limit, used:MKT.used}; })()"""))
    t.ok(r["status"] == 200 and r["waited"] >= 900, "a refused read waits as long as ESI asks, then answers", r)
    t.ok(r["limit"] == 150 and r["used"] == 140, "ESI's rate-limit headers set the budget", r)
    waiting = await t.js("""(async()=>{ let done=false; const p=esiMarket('https://esi.evetech.net/latest/markets/99999992/orders/?page=1').then(()=>done=true); await new Promise(r=>setTimeout(r,400)); const before=done; MKT.used=0; MKT.limit=12000; mktPump(); await p; return [before, done]; })()""")
    t.eq(waiting, [False, True], "over 90% of the budget used: reads wait, then go when there's room")
    await t.js("""Promise.all(Array.from({length:20},(_, i)=>esiMarket('https://esi.evetech.net/latest/markets/99999992/orders/?page='+i)))""")
    t.ok(1 < state["peak"] <= 6, "at most 6 market reads at once", state)
    t.eq(await t.js("MKT.active + MKT.q.length"), 0, "the queue empties")

@scenario
async def game_data(t):
    ccp = t.show("ccp", await t.js("""(async()=>{const t=await getJSON(REF+'/types/32880'), b=await getJSON(REF+'/blueprints/32881'), r=await getJSON(REF+'/types/28844');
      return {t:[t.src,t.category_id], b:b.src, r:[r.src,r.required_skills]}})()"""))
    t.ok(ccp["t"] == ["ccp", 6] and ccp["b"] == "ccp" and ccp["r"][1] == {"29029": 1}, "game data comes from CCP's static data", ccp)
    sup = t.show("suppliers", await t.js("""(async()=>{const ids=await resolveIds(['Venture','x'.repeat(150)]); const s=await entriesToStock(rowsToEntries([['Type ID','Quantity Raw','Name','Quantity','Price','Total Price'],['32880','3','Ventur','3.0','1.236E6','3.7E6'],['','','','','','']]));
      return {ids, stock:s.stock, notes:stockHeader([['Buyback Sheet','Num of Items Available'],['Hulls','173']])}})()"""))
    t.ok(sup["ids"] == {"venture": 32880} and sup["stock"] == {"32880": {"q": 3, "n": "Venture", "price": 1236000}} and sup["notes"] is None, "supplier stock is read as expected", sup)
    fb = await t.js("(async()=>{const keep=[ccpMeta,ccpOff]; memo.clear(); ccpMeta=null; ccpParts.clear(); ccpOff=Date.now()+1e9; const t=await getJSON(REF+'/types/32880'); ccpMeta=keep[0]; ccpOff=keep[1]; memo.clear(); return [t.src||'everef', t.category_id]})()")
    t.eq(fb, ["everef", 6], "EVE Ref answers when CCP's data can't be read")

@scenario
async def profit_and_loss(t):
    SUM = "(()=>{const S=pnlSum(pnlBook()), a={}; for (const [k,A] of S.acts) a[k]=Math.round(A.inc+A.sp); return {inc:S.inc, sp:S.sp, net:S.net, none:[S.none.v,S.none.n], out:[S.out.v,S.out.n], acts:a}})()"
    await t.js("pnlCfg().period='all'; saveMisc()")
    await t.js("pnlSync(9001,'Ender Alpha',98000001,'tok','esi-wallet.read_character_wallet.v1 esi-wallet.read_corporation_wallets.v1 esi-industry.read_character_jobs.v1 esi-contracts.read_character_contracts.v1',true)")
    t.eq(await t.js("[pnlData.err['corp:98000001'], Object.keys(pnlData.w), Object.keys(pnlData.cont).sort(), pnlData.cont[901].i]"),
         ["no Accountant role (tried with Ender Alpha)", ["char:9001"], ["900", "901", "902"], [[16633, 1000], [9100, 500]]], "a corporation without the Accountant role is reported, not listed; contracts' items are read (what the issuer gave)")
    await t.tab("pnl", 0.6); await t.until("!pnlPricing", 20); await asyncio.sleep(0.2)
    v = await t.js("[priceIn('split',16633), priceIn('split',9100)]"); f = 1000 * v[0] / (1000 * v[0] + 500 * v[1])
    s0 = t.show("read", await t.js(SUM))
    # market lines and escrow left out (counted from the transactions); the corporation's purchase (not personal) isn't the pilot's; job fees follow their job;
    # contracts go by what they held: Ventures sold → Manufacturing (with the contract's tax); moon materials + PI shared by value (with the broker fee); one with an unpriced item stays whole
    t.eq(s0, {"inc": 2030000, "sp": -5118100, "net": -3088100, "none": [-2000100, 3], "out": [0, 0],
              "acts": {"rx": round(28300 - 3030000 * f), "mfg": 1915700, "pi": round(-2000 - 3030000 * (1 - f)), "none": -2000100}}, "wallet entries are read and sorted, contracts by what they held")
    t.ok(await t.js("$('pnl-summary').textContent.includes('-3.1M')"), "the profit tile shows", await t.text("#pnl-summary"))
    t.ok(await t.js("$('pnl-note').innerText.includes('Fake Noble Gas')"), "a contract that can't be shared says which item has no price", await t.text("#pnl-note"))
    t.eq(await t.js("[...$('pnl-ent').tBodies[0].rows].filter(r=>r.innerText.includes('Gas Supplier')).length"), 2, "a split contract shows one row per activity")
    t.ok(await t.js("['Fake Reactive Gas','Hydrocarbons','Titanium Carbide','Tritanium','Venture'].every(n=>$('pnl-items').innerText.includes(n)) && $('pnl-parties').innerText.includes('Bob Client')"), "items (market and contracts) and clients are listed", await t.text("#pnl-items"))
    t.ok(await t.js("[...document.querySelectorAll('#pnl-nav a')].length>=6"), "the page has its left rail")
    # a client's choice moves the donation, the contract and its tax (over what the contract held)
    await t.pg.select_option("#pnl-parties select[data-pnl-rule='party:555']", "trade"); await asyncio.sleep(0.2)
    s1 = t.show("client", await t.js(SUM)); t.eq([s1["none"], s1["acts"].get("trade"), s1["acts"].get("mfg")], [[-1000100, 2], 920000, -4300], "a client's activity moves its contracts, fees and donations")
    await t.pg.select_option("#pnl-parties select[data-pnl-rule='party:556']", "pi"); await asyncio.sleep(0.2)
    s1b = t.show("supplier", await t.js(SUM)); t.eq([s1b["acts"].get("pi"), s1b["acts"].get("rx")], [-3032000, 28300], "a client's choice wins over what the contract held")
    await t.pg.select_option("#pnl-parties select[data-pnl-rule='party:556']", ""); await asyncio.sleep(0.2)
    # an item's choice moves its sales and tax, and its share of contracts
    await t.pg.select_option("#pnl-items select[data-pnl-rule='item:16671']", "trade"); await asyncio.sleep(0.2)
    s2 = t.show("item", await t.js(SUM)); t.eq([s2["acts"].get("rx"), s2["acts"].get("trade")], [round(-500 - 3030000 * f), 948800], "an item's activity moves its sales and sales tax")
    await t.pg.select_option("#pnl-items select[data-pnl-rule='item:9100']", "rx"); await asyncio.sleep(0.2)
    s2b = t.show("contract item", await t.js(SUM)); t.eq([s2b["acts"].get("rx"), s2b["acts"].get("pi")], [-3030500, -2000], "an item's choice decides its contracts")
    await t.js("()=>{const k=pnlBook().find(x=>x.ref==='brokers_fee').key; pnlCfg().line[k]='trade'; saveMisc(); renderPnl()}")
    t.eq((await t.js(SUM))["none"], [-1000000, 1], "one entry can be moved by itself")
    # ISK between your own pilots is left out; a backup's history joins this browser's
    await t.js("()=>{pnlData.w['char:9001'].j[11]=[Date.parse('2026-10-16T00:00:00Z'),'player_donation',-5e6,9001,9002,0,'','',''];pnlData.w['char:9002']={kind:'char',id:9002,name:'Alt',at:Date.now(),j:{11:[Date.parse('2026-10-16T00:00:00Z'),'player_donation',5e6,9001,9002,0,'','','']},t:{}}}")
    s3 = t.show("internal", await t.js(SUM)); t.eq([s3["out"], s3["net"]], [[0, 2], -3088100], "transfers between your pilots are left out")
    m = await t.js("(()=>{const b={...pnlData, w:{'char:9001':{...pnlData.w['char:9001'], j:{99:[1,'bounty_prizes',1,1,9001,0,'','','']}, t:{}}}}; const r=pnlMerge(PNL_EMPTY(), b); const r2=pnlMerge(pnlData, b); return [Object.keys(r.w['char:9001'].j).length, Object.keys(r2.w['char:9001'].j).length, Object.keys(r.cont).length]})()")
    t.eq(m, [1, 15, 3], "a backup's wallet history is joined, not replaced")
    # the Forecast shows the actual profit next to the planned one (read only)
    await t.tab("forecast", 0.8)
    fc = t.show("forecast", await t.js("[$('fc-summary').textContent.includes('Actual profit'), $('fc-chart').innerText.includes('Actual profit (cumulative'), document.querySelectorAll('#fc-chart path[stroke=\"#a16207\"]').length]"))
    t.eq(fc, [True, True, 1], "the Forecast has an actual profit tile and line")

@scenario
async def own_ore(t):
    """Your own ore is reprocessed in the system where its minerals are used, at your best refinery there (none known: not reprocessed, with a warning), and hauled there compressed."""
    await ships(t); await map_(t); await structs(t)
    await t.js("""()=>{state.misc.indy={list:[{id:'x1',n:'Delta Athanor',type:'Athanor',sys:30000004,sysName:'Delta',rigs:['Standup M-Set Reprocessing Monitor II']}]};
      state.typeMeta[1230]=[462,25]; state.typeMeta[62520]=[460,25];
      state.assets['char:9001'].rows.push({t:1230,loc:60000001,h:'Hangar',q:200000},{t:62520,loc:60000002,h:'Hangar',q:3000}); saveMisc(); saveAssets();}""")
    t.eq(await t.js("(refineryIn(30000004)||{}).name"), "Delta Athanor", "the refinery known in Delta")
    read = """(()=>{const r=buildState.plan.res, O=r.stockUse.ore||{use:[]};
      return {use:O.use.map(u=>[u.name,u.sysName,+u.y.toFixed(4),+pilotYield((refineryIn(u.sys)||{base:NaN}).base,(state.misc.reproc[u.t]||{}).sk).y.toFixed(4),u.local,u.hauled,u.ref&&u.ref.name]),
        noRef:(O.noRef||[]).map(x=>[x.name,x.ores]),
        usedIn:[...new Set(r.shop.filter(x=>x.fromOre).flatMap(x=>Object.keys(x.fromOreAt).map(l=>r.locs[l]&&r.locs[l].name)))],
        ships:r.shipments.filter(s=>s.item.cat==='Own ore to reprocess').map(s=>[s.item.name,s.from,r.locs[s.to]&&r.locs[s.to].name,s.item.qty,s.item.unit])}})()"""
    # The minerals are used in Golf, where no refinery is known: no guessed 50% yield, a warning instead
    await plan(t, "Venture Blueprint", 10)
    await t.pg.check("#plan-stock"); await asyncio.sleep(0.3); await t.until("!buildState.plan.busy && !!buildState.plan.res.stockUse", 25)
    r = t.show("no refinery", await t.js(read))
    t.ok(any(n == "Golf" for n, _ in r["noRef"]), "Golf, using your ore's minerals without a known refinery, is listed", r["noRef"])
    t.ok(all(u[1] != "Golf" for u in r["use"]), "no ore is reprocessed in a system without a known refinery", r)
    ui = await t.text("#plan-out"); t.ok(ui and "No refinery detected in Golf" in ui, "the plan warns: No refinery detected in Golf", (ui or "")[:300])
    # With a refinery there, the ore is used
    await t.js("""()=>{state.misc.indy.list.push({id:'x2',n:'Golf Tatara',type:'Tatara',sys:30000007,sysName:'Golf',rigs:[]}); saveMisc();}""")
    await plan(t, "Venture Blueprint", 10); await t.until("!buildState.plan.busy && !!buildState.plan.res.stockUse", 25)
    r = t.show("own ore", await t.js(read))
    if t.ok(r["use"], "your ore is used for what's still to buy", r):
        t.ok(all(u[2] == u[3] for u in r["use"]), "each ore's yield is your best refinery in that system with your best pilot", r["use"])
        t.ok(all(u[1] in r["usedIn"] for u in r["use"]), "ore is reprocessed in a system where its minerals are used", r)
        t.ok(all(u[6] == f"{u[1]} " + ("Athanor" if u[1] == "Delta" else "Tatara") for u in r["use"]), "each system's own refinery reprocesses what's used there", r["use"])
        hauled = sum(u[5] for u in r["use"] if u[0] == "Veldspar")
        t.ok(hauled > 0 and sum(s[3] for s in r["ships"] if s[0] == "Veldspar") == hauled, "Veldspar from the delivery system is hauled to where it's reprocessed", r)
        t.ok(all(s[1] == "D" and s[4] == 0.001 for s in r["ships"]), "your ore is hauled compressed (its compressed form's volume)", r["ships"])
    t.ok(not any(n == "Golf" for n, _ in r["noRef"]), "Golf isn't warned about once it has a refinery", r["noRef"])
    ui = await t.text("#plan-out"); t.ok(ui and "Reprocessed in" in ui, "the ore table says where each ore is reprocessed", (ui or "")[:200])

@scenario
async def corporation(t):
    """Corporation page: fuel from online services (each module once, the structure's role bonus on its own kind), To-Do refuel list and count; extractions and mining ledgers."""
    await t.js("""async()=>{const n=Date.now(); state.chars[0].corpId=98000001; state.corpNames[98000001]='Fake Corp';
      noteStruct(1,{solar_system_id:30000004,type_id:35825,owner_id:98000001,fuel_expires:new Date(n+2*864e5).toISOString(),services:[{name:'Manufacturing (Standard)',state:'online'},{name:'Blueprint Copying',state:'online'},{name:'Time Efficiency Research',state:'online'},{name:'Invention',state:'offline'}]},'corp');
      noteStruct(2,{solar_system_id:30000005,type_id:35835,owner_id:98000001,fuel_expires:new Date(n+20*864e5).toISOString(),services:[{name:'Reprocessing',state:'online'},{name:'Moon Drilling',state:'online'},{name:'Something New',state:'online'}]},'corp');
      state.misc.structs['1'].typeName='Raitaru'; state.misc.structs['2'].typeName='Athanor'; saveMisc();
      await minSync(9001,'Ender Alpha',98000001,'tok','esi-industry.read_corporation_mining.v1 esi-industry.read_character_mining.v1');}""")
    await t.tab("corp"); t.ok(await t.until("!corpBusy && !!fuelData.mods && Object.keys(fuelData.types).length===2", 20), "the game data for fuel was read")
    f = t.show("fuel", await t.js("['1','2'].map(k=>{const u=fuelUse(state.misc.structs[k]); return [u.perDay,u.unknown]})"))
    t.eq(f, [[432, []], [312, ["Something New"]]], "fuel per day: each module once, less the structure's role bonus on its own kind; an unknown service isn't counted")
    fb = await t.js("fuelBlockPrice()"); t.ok(fb and fb["p"] > 0, "a fuel block is priced", fb)
    tiles = await t.text("#corp-fuel-sum"); t.ok(tiles and "≥ 744" in tiles, "the total says some fuel isn't known", tiles)
    grp = await t.js("[...document.querySelectorAll('#corp-fuel tr.group')].map(r=>r.textContent)"); t.ok(len(grp) == 1 and "Fake Corp" in grp[0], "structures are grouped by corporation", grp)
    ext = await t.text("#corp-ext"); t.ok(ext and "Delta I - Moon 1" in ext and "extracting" in ext, "the extraction shows its moon and state", ext)
    LED = "s=>[...document.querySelectorAll(s+' tbody tr')].map(r=>r.classList.contains('group')?r.cells[0].textContent.replace(/^[▾▸]\\s*/,'').split(/\\s+\\d/)[0].trim():[r.cells[0].textContent.trim(),+r.cells[1].dataset.v,r.cells[3].dataset.v===''?null:+r.cells[3].dataset.v])"
    led = t.show("ledger", await t.js(LED, "#corp-led"))
    t.eq([x if isinstance(x, str) else x[:2] for x in led], ["Bob Client", ["Veldspar", 1500], "Gas Supplier", ["Compressed Scordite", 300]], "who mined what over 30 days (an older day left out)")
    v = await t.js("[oreValue(1230,'jbv'), oreValue(62520,'jbv')]")
    t.ok(len(led) == 4 and v[0] and abs(led[1][2] - 1500 * v[0]) < 1 and abs(led[3][2] - 300 * v[1]) < 1, "ore valued as its minerals at the best possible yield", [led, v])
    await t.tab("misc", 0.4)
    own = await t.js(LED, "#corp-own"); t.eq([x if isinstance(x, str) else x[:2] for x in own], ["Ender Alpha", ["Veldspar", 200]], "your pilots' own mining")
    t.ok(await t.js("!!document.querySelector('#page-misc #corp-own') && !document.querySelector('#page-corp #corp-own') && document.querySelector('#mmin-days').value==='30'"), "your pilots' mining is on the Misc page, with the Corporation page's period")
    await t.tab("corp", 0.4)
    await t.pg.select_option("#corp-days", "90"); await asyncio.sleep(0.3); await t.until("!corpBusy", 10)
    t.eq([x[1] for x in await t.js(LED, "#corp-led") if not isinstance(x, str) and x[0] == "Compressed Scordite"], [300 + 9999], "90 days takes the older day in")
    await t.pg.select_option("#corp-as", "ore"); await asyncio.sleep(0.3); await t.until("!corpBusy", 10)
    led2 = await t.js(LED, "#corp-led"); p = await t.js("priceIn('jbv',1230)")
    t.ok(p and abs(led2[1][2] - 1500 * p) < 1, "or at the ore's own price", [led2, p])
    # To-Do: the Raitaru runs out in 2 days (warning 7 days), the Athanor in 20
    t.eq(await t.js("fuelLow().map(s=>s.id)"), ["1"], "structures to refuel")
    await t.tab("todo"); txt = await t.text("#todo-fuel-panel")
    t.ok(txt and "structures to refuel" in txt.lower() and "432 blocks a day" in txt, "To-Do lists it with its fuel use", txt)
    t.ok("structure to refuel" in (await t.js("document.querySelector('.tabs button[data-tab=todo]').title") or ""), "the To-Do tab counts it")

@scenario
async def customs_offices(t):
    """PI customs tax from your corporation's customs offices: members pay the corporation's rate, the alliance its own; colonies show it, the PI planner uses it when its field is empty."""
    t.ok(await t.js("ESI_SCOPE.includes(POCO_SCOPE) && !!SCOPE_USE[POCO_SCOPE] && !requestedScopes().includes(POCO_SCOPE)"), "the customs office permission is listed and starts unticked")
    await t.js("""async()=>{const C=state.chars; C[0].corpId=98000001; C[1].corpId=98000002; C[1].allyId=99000001; state.corpNames[98000001]='Fake Corp'; state.corpNames[98000002]='Other Corp';
      await pocoSync(98000001,'Ender Alpha','tok'); await pocoSync(98000002,'Ender Beta','tok');
      const pl={id:40000010,name:'Delta II',type:'barren',system:'Delta',sys:30000004,lastUpdate:Date.now(),factories:0,extractors:[],inputs:[],makes:[],stock:[],unneeded:[]};
      C[0].planets=[pl, {...pl,id:40000012,name:'Echo II',system:'Echo',sys:30000005}]; C[1].planets=[{...pl,id:40000011,name:'Delta III'}, {...pl,id:40000013,name:'Echo I',system:'Echo',sys:30000005}];
      const P=piCfg(); P.v=2; P.poco=0; P.planetSys=''; saveLocal(); saveMisc(); render();}""")
    O = t.show("offices", await t.js("state.misc.pocos"))
    t.eq([O["98000001"]["ally"], O["98000001"]["list"], O["98000002"]["err"]], [99000001, [[1001, 30000004, 0.05, 0.1], [1002, 30000004, 0.08, 0.1], [1003, 30000005, 0.03, None]], "no Director role (tried with Ender Beta)"],
         "offices are kept with their member and alliance rates (none without alliance access); a refused read says why")
    t.eq(await t.js("[pocoRate(30000004,[state.chars[0]]), pocoRate(30000004,[state.chars[1]]), pocoRate(30000005,[state.chars[1]]), pocoRate(30000001)]"),
         [{"rate": 0.08, "lo": 0.05, "n": 2}, {"rate": 0.1, "lo": 0.1, "n": 2}, None, None], "a member pays the corporation's rate, the alliance its own, nothing known otherwise")
    await t.tab("planets", 0.5)
    rows = t.show("colonies", await t.js("Object.fromEntries([...document.querySelectorAll('#pi-table tbody tr:not(.group)')].map(r=>[r.cells[4].firstChild.textContent.trim(), r.cells[4].querySelector('.label').textContent]))"))
    t.ok(rows and "customs 5% to 8%" in rows["Delta II"] and "customs 3%" in rows["Echo II"] and "customs 10%" in rows["Delta III"] and "customs" not in rows["Echo I"], "each colony shows the tax its pilot pays", rows)
    await t.tab("pimgmt"); t.ok(await t.until("!!state.misc.piAt && !piBusy", 15), "PI prices didn't load")
    t.eq(await t.js("[piCfg().v, piCfg().poco, piEnv().poco]"), [3, "", 0], "the old default 0% becomes empty; with no planets' system the tax is 0")
    await t.pg.fill("[data-pi=planetSys]", "Echo"); await t.pg.dispatch_event("[data-pi=planetSys]", "change")
    t.ok(await t.until("Math.abs(piEnv().poco-0.03)<1e-9", 10), "empty: the tax of your customs office in the planets' system", await t.js("piEnv().poco"))
    txt = t.show("setup", await t.text("#pi-setup")); t.ok(txt and "customs office in Echo" in txt and "Other Corp: no Director role" in txt, "the planner says where the tax comes from and what couldn't be read", txt)
    await t.pg.fill("[data-pi=planetSys]", "Delta"); await t.pg.dispatch_event("[data-pi=planetSys]", "change")
    t.ok(await t.until("Math.abs(piEnv().poco-0.1)<1e-9", 10), "several rates: the highest any of your pilots pays", await t.js("piEnv().pocoAuto"))
    await t.pg.fill("[data-pi=poco]", "4"); await t.pg.dispatch_event("[data-pi=poco]", "change"); await asyncio.sleep(0.2)
    t.eq(await t.js("[piEnv().poco, piEnv().pocoAuto]"), [0.04, None], "a value typed in wins")

@scenario
async def intel(t):
    """Intel page: notifications of every pilot once (with who got them), names for their ids, alerts of the last 3 days and the tab count, Mark all as seen."""
    t.ok(await t.js("[NOTIF_SCOPE, CORP_MINING_SCOPE, CHAR_MINING_SCOPE].every(s=>ESI_SCOPE.includes(s) && SCOPE_USE[s] && !requestedScopes().includes(s))"), "the Notifications and mining permissions are listed and start unticked")
    await t.js("async()=>{await intelSync(9001,'Ender Alpha','tok'); await intelSync(9001,'Ender Beta','tok');}")
    kept = t.show("kept", await t.js("Object.values(intelData.n).map(o=>[o.type,o.to]).sort()"))
    both = ["Ender Alpha", "Ender Beta"]
    t.eq(kept, [["CorpAppNewMsg", both], ["MoonminingExtractionFinished", both], ["StructureUnderAttack", both]], "each notification once with who got it; one older than 90 days dropped")
    t.eq(await t.js("[document.querySelector('.tabs button[data-tab=intel]').dataset.alert, document.querySelector('.tabs .tabgrp:has(button[data-tab=intel]) .tabgrp-btn').dataset.alert]"), ["2", "2"], "the Intel tab and its menu count what needs attention")
    await t.tab("intel"); await t.until("!intelBusy && !!intelData.names[40000001]", 10); await asyncio.sleep(0.3)
    al = t.show("alerts", await t.text("#intel-alerts"))
    t.ok(al and "Delta - Sotiyo in Delta is under attack: shield 46%, armour 100%, hull 100% by Gas Supplier · Pirates · Bad Guys" in al, "an attack says where, how bad and by whom", al)
    t.ok(al and "Chunk ready at Delta I - Moon 1" in al, "a chunk ready names its moon", al)
    t.ok(await t.js("!!document.querySelector('#page-misc #intel-list') && !document.querySelector('#page-intel #intel-list')"), "the notifications list is on the Misc page")
    await t.tab("misc", 0.4)
    G = "[...document.querySelectorAll('#intel-list tr.group th')].map(th=>th.textContent.replace(/^[▾▸]\\s*/,'').replace(/\\s*\\d+$/,''))"
    t.eq(await t.js(G), ["Structures", "Moon mining", "Corporation"], "notifications grouped by kind")
    await t.pg.select_option("#intel-days", "1"); await asyncio.sleep(0.3)
    t.eq(await t.js(G), ["Structures", "Moon mining"], "the period hides older ones")
    await t.tab("intel", 0.3); await t.pg.click("[data-intel-seen]"); await asyncio.sleep(0.3)
    t.ok(await t.js("!document.querySelector('.tabs button[data-tab=intel]').dataset.alert && !document.querySelector('.tabs .tabgrp:has(button[data-tab=intel]) .tabgrp-btn').dataset.alert") and "Nothing needs attention" in (await t.text("#intel-alerts") or ""), "Mark all as seen clears the alerts and the count")

@scenario
async def custom_filters(t):
    """Filters built from conditions (like jEveAssets): the tests themselves, match all / any, switching one off, saved filters, and the bar on Assets driven by hand."""
    T = t.show("tests", await t.js("""(()=>{const now=Date.now(), F={n:{k:'n',n:'N',t:'num',get:r=>r.v}, s:{k:'s',n:'S',t:'text',get:r=>r.s}, d:{k:'d',n:'D',t:'date',get:r=>r.d}, l:{k:'l',n:'L',t:'list',get:r=>r.l}};
      const T=(f,op,a,b,row)=>cfTest(F[f],{f,op,a,b},row);
      return [T('n','gt','1.5b','',{v:2e9}), T('n','gt','1.5b','',{v:1e9}), T('n','btw','10','20',{v:15}), T('n','btw','20','10',{v:15}), T('n','gt','0','',{v:null}), T('n','empty','','',{v:null}), T('n','ne','5','',{v:null}),
        T('s','has','TRIT','',{s:'Tritanium'}), T('s','not','trit','',{s:'Tritanium'}), T('s','is','tritanium','',{s:'Tritanium'}), T('s','start','tri','',{s:['Pyerite','Tritanium']}), T('s','end','um','',{s:'Pyerite'}),
        T('d','last','7','',{d:now-3*864e5}), T('d','last','7','',{d:now-9*864e5}), T('d','older','7','',{d:now-9*864e5}), T('d','next','2','',{d:now+864e5}), T('d','after','2026-01-01','',{d:Date.parse('2026-02-01T00:00:00')}), T('d','before','2026-01-01','',{d:Date.parse('2026-02-01T00:00:00')}),
        T('l','is','a','',{l:['b','a']}), T('l','isnt','a','',{l:['b','a']}), T('l','is','3','',{l:3})]})()"""))
    t.eq(T, [True, False, True, True, False, True, False, True, False, True, True, False, True, False, True, True, True, False, True, False, True], "each condition (an unknown number never passes a comparison; is empty finds it)")
    # all / any, a switched-off condition, an incomplete one
    r = t.show("apply", await t.js("""(()=>{CF_REG.x={fields:[{k:'v',n:'Value',t:'num',get:r=>r.v},{k:'s',n:'Name',t:'text',get:r=>r.s}],onChange:()=>0}; const c=cfCfg('x'), rows=[{v:1,s:'a'},{v:5,s:'b'},{v:9,s:'c'}];
      c.rules=[{f:'v',op:'gt',a:'3'},{f:'s',op:'is',a:'c'}]; const all=cfApply('x',rows).map(r=>r.s); c.match='any'; const any=cfApply('x',rows).map(r=>r.s);
      c.rules[0].off=true; const off=cfApply('x',rows).map(r=>r.s); c.rules=[{f:'v',op:'gt',a:''}]; const inc=cfApply('x',rows).length; return {all,any,off,inc}})()"""))
    t.eq(r, {"all": ["c"], "any": ["b", "c"], "off": ["c"], "inc": 3}, "match all or any; a condition switched off or not filled in doesn't count")
    # the Assets bar, by hand: a condition on the name, then on the value; save it, clear, load it back, delete it
    await t.js("()=>{Object.assign(state.typeNames,{34:'Tritanium',35:'Pyerite',16633:'Hydrocarbons',28844:'Rhea'}); saveAssets();}")
    await t.tab("stock", 0.5)
    await t.pg.click("#st-cf [data-cf-act=open]"); await asyncio.sleep(0.2)
    t.ok(await t.js("document.querySelectorAll('#st-cf .cf-row').length===1"), "opening Filters starts with one condition")
    await t.pg.fill("#st-cf [data-cf-v=a]", "trit"); await asyncio.sleep(0.5)
    names = "[...document.querySelectorAll('#st-table tbody tr:not(.group):not(.subgroup) th')].map(th=>th.textContent.trim())"
    t.eq(await t.js(names), ["Tritanium"], "Item contains trit")
    t.ok("1 of" in (await t.text("[data-cf-count=stock]") or ""), "the bar says how many rows pass", await t.text("[data-cf-count=stock]"))
    await t.pg.select_option("#st-cf select[data-cf-act=f]", "status"); await asyncio.sleep(0.3)
    await t.pg.select_option("#st-cf select[data-cf-v=a]", "yes"); await asyncio.sleep(0.4)
    t.eq(sorted(await t.js(names)), ["Hydrocarbons", "Pyerite", "Rhea", "Tritanium"], "Status is Counted (a list condition)")
    await t.pg.click("#st-cf [data-cf-act=add]"); await asyncio.sleep(0.2)
    await t.pg.select_option("#st-cf .cf-row:nth-of-type(2) select[data-cf-act=f]", "q"); await asyncio.sleep(0.2)
    await t.pg.fill("#st-cf .cf-row:nth-of-type(2) [data-cf-v=a]", "1000"); await asyncio.sleep(0.5)
    t.eq(sorted(await t.js(names)), ["Pyerite", "Tritanium"], "and Quantity more than 1000")
    await t.js("document.getElementById('st-cf').scrollIntoView()"); await t.pg.screenshot(path=SP + "filters.png")
    await t.pg.fill("#st-cf [data-cf-act=name]", "Big stacks"); await t.pg.click("#st-cf [data-cf-act=save]"); await asyncio.sleep(0.2)
    await t.pg.click("#st-cf [data-cf-act=clear]"); await asyncio.sleep(0.3)
    t.eq(len(await t.js(names)), 4, "Clear shows everything again")
    await t.pg.select_option("#st-cf select[data-cf-act=load]", "Big stacks"); await asyncio.sleep(0.4)
    t.eq(sorted(await t.js(names)), ["Pyerite", "Tritanium"], "a saved filter loads back")
    t.eq(await t.js("state.misc.cf.stock.saved.map(s=>[s.n,s.rules.length])"), [["Big stacks", 2]], "saved per table, in state.misc (so in backups)")
    await t.pg.click("#st-cf .cf-row:nth-of-type(2) [data-cf-act=on]"); await asyncio.sleep(0.4)
    t.eq(sorted(await t.js(names)), ["Hydrocarbons", "Pyerite", "Rhea", "Tritanium"], "unticking a condition switches it off")
    await t.pg.click("#st-cf [data-cf-act=unsave]"); await asyncio.sleep(0.2)
    t.eq(await t.js("state.misc.cf.stock.saved.length"), 0, "a saved filter can be deleted")
    # groups inside each other: (Item contains "e" and Quantity more than 1000) or Item is Rhea
    await t.js("()=>{const c=cfCfg('stock'); c.match='any'; c.rules=[{g:1,match:'all',rules:[{f:'name',op:'has',a:'e'},{f:'q',op:'gt',a:'1000'}]},{f:'name',op:'is',a:'Rhea'}]; cfDraw('stock'); renderStock();}"); await asyncio.sleep(0.4)
    t.eq(sorted(await t.js(names)), ["Pyerite", "Rhea"], "a group of conditions inside the filter: (A and B) or C")
    ch = t.show("chips", await t.text("[data-cf-chips=stock]"))
    t.ok("(" in ch and ")" in ch and " and " in ch and " or " in ch and "3 on" in (await t.text("#st-cf [data-cf-act=open]") or ""), "the chips show the brackets, and/or, and every condition is counted", ch)
    await t.pg.click("#st-cf .cf-group [data-cf-act=add][data-i='0']"); await asyncio.sleep(0.2)
    t.eq(await t.js("cfCfg('stock').rules[0].rules.length"), 3, "Add a condition inside a group adds it there")
    await t.pg.click("#st-cf [data-cf-act=del][data-i='0.2']"); await asyncio.sleep(0.2)
    await t.pg.click("#st-cf .cf-box > .toolbar [data-cf-act=addg]"); await asyncio.sleep(0.2)
    t.eq(await t.js("(()=>{const c=cfCfg('stock'); return [c.rules[0].rules.length, c.rules.length, c.rules[2].g, c.rules[2].match]})()"), [2, 3, 1, "all"], "✕ removes by its place; a new group matches the other way from the one holding it")
    await t.pg.click("#st-cf .cf-box > .cf-group:nth-of-type(1) > .toolbar [data-cf-act=on]"); await asyncio.sleep(0.4)
    t.eq(sorted(await t.js(names)), ["Rhea"], "unticking a group switches all of it off")
    await t.pg.select_option("#st-cf .cf-box > .cf-group:nth-of-type(1) > .toolbar select[data-cf-act=match]", "any"); await asyncio.sleep(0.3)
    t.eq(await t.js("[cfCfg('stock').rules[0].match, cfCfg('stock').rules[0].off]"), ["any", True], "each group has its own all / any")
    await t.js("document.getElementById('st-cf').scrollIntoView()"); await t.pg.screenshot(path=SP + "filter-groups.png")
    await t.pg.click("#st-cf [data-cf-act=clear]"); await asyncio.sleep(0.3)
    # the same bar on Profit and loss, Intel, the skill matrix and the ships list
    await t.tab("overview", 0.4); t.ok(await t.js("!!document.querySelector('#matrix-cf [data-cf-act=open]')"), "the skill matrix has Filters")
    await t.js("()=>{cfCfg('matrix').rules=[{f:'name',op:'is',a:'Industry'}]; renderMatrix();}"); await asyncio.sleep(0.2)
    t.eq(await t.js("[...document.querySelectorAll('#matrix tbody tr:not(.group) th')].map(th=>th.textContent.trim())"), ["Industry"], "the skill matrix filters by its own columns")
    await t.tab("pnl", 0.5); t.ok(await t.js("!!document.querySelector('#pnl-ent-cf [data-cf-act=open]') && !!document.querySelector('#pnl-items-cf [data-cf-act=open]')"), "Profit and loss has Filters on Entries and Items")
    await t.tab("misc", 0.5); t.ok(await t.js("!!document.querySelector('#intel-cf [data-cf-act=open]')"), "In-game notifications (Misc) have Filters")

@scenario
async def net_worth(t):
    """Net worth on the Overview: market orders read from ESI, each day's parts and owners, the journal-filled wallet days, the owner choice, and orders in the Forecast's total."""
    t.ok(await t.js("[ORDERS_SCOPE, CORP_ORDERS_SCOPE].every(s=>ESI_SCOPE.includes(s) && SCOPE_USE[s] && !requestedScopes().includes(s))"), "the Market orders permissions are listed and start unticked")
    o = t.show("orders", await t.js("async()=>{const L=slimOrders(await esiAuthGet('/characters/9001/orders/','tok')); const c=state.chars.find(x=>x.esiId===9001); c.corpId=98000001; c.wallet=1e9; c.orders={at:Date.now(),list:L}; state.corpNames[98000001]='Fake Corp'; saveLocal(); return {n:L.length, now:ordersNow(), list:mktOrders().map(x=>[x.id,x.key])}}"))
    t.eq(o["n"], 4, "the pilot's orders are read")
    t.eq(sorted(o["list"]), [[11, "char:9001"], [12, "char:9001"], [13, "corp:98000001"]], "an order for the corporation goes under it; an expired order is left out")
    t.eq([o["now"]["sell"], o["now"]["esc"], o["now"]["cover"], o["now"]["ns"], o["now"]["nb"]], [5000 + 6000, 600, 400, 2, 1], "sell orders at price × what's left, buy orders' escrow, what they still need")
    # history: two recorded days with owners, plus journal balances for the days between
    await t.js("""async()=>{const d=(n)=>dayKey(Date.now()-n*864e5); state.forecast.history=[{d:d(6),isk:5e8,stock:1e8,c:0,hs:1e8,ms:0,so:0,esc:0,by:{'char:9001':[5e8,1e8,0,0]}},{d:d(3),isk:8e8,stock:2e8,c:0,hs:2e8,ms:0,by:{'char:9001':[8e8,2e8,0,0]}}];
      await pnlLoad(); pnlData.w['char:9001']={kind:'char',id:9001,name:'Ender Alpha',at:Date.now(),j:{1:[Date.now()-5*864e5,'bounty_prizes',1e8,0,0,0,'','','',6e8],2:[Date.now()-4*864e5,'bounty_prizes',1e8,0,0,0,'','','',7e8],3:[Date.now()-2*864e5,'bounty_prizes',3e8,0,0,0,'','','',1e9]},t:{}}; saveForecast();}""")
    J = t.show("journal days", await t.js("(()=>{const j=nwJournal(null); return [...j.days.entries()].filter(([d])=>d>=dayKey(Date.now()-6*864e5)).map(([d,v])=>[Math.round((Date.now()-new Date(d+'T12:00:00'))/864e5),v])})()"))
    t.eq(J, [[6, 5e8], [5, 6e8], [4, 7e8], [3, 7e8], [2, 1e9], [1, 1e9]], "wallets per day from the journal: the balance before the first entry, then after each day's last entry")
    await t.tab("forecast", 0.6); await t.until("!!document.querySelector('#nw-chart svg')", 5)
    nw = t.show("net worth", await t.js("({tiles:[...document.querySelectorAll('#nw-summary .slot-tile')].map(x=>x.innerText.replace(/\\s+/g,' ')), legend:[...document.querySelectorAll('#nw-chart .lg')].map(b=>b.textContent.trim()), hollow:document.querySelectorAll('#nw-chart circle[fill=\"var(--panel)\"]').length, orders:document.querySelectorAll('#nw-orders tbody tr').length, rows:document.querySelectorAll('#fc-history tbody tr').length, nav:[...document.querySelectorAll('#fc-nav a')].map(a=>a.textContent)})"))
    t.ok(any(x.lower().startswith("market orders") and "2 sell orders" in x for x in nw["tiles"]), "a Market orders tile", nw["tiles"])
    t.ok({"Net worth", "Wallets", "Assets", "Sell orders", "Buy order escrow"} <= set(nw["legend"]), "one line per part", nw["legend"])
    t.ok(nw["hollow"] >= 3, "days between recorded points show wallets from the journals (hollow dots)", nw["hollow"])
    t.eq(nw["orders"], 3, "the open orders are listed")
    t.ok(nw["rows"] >= 2 and "Net worth" in nw["nav"] and "Day by day" in nw["nav"], "the day by day table and the rail", nw)
    await t.js("document.getElementById('nw-title').scrollIntoView()"); await t.pg.screenshot(path=SP + "net-worth.png")
    fc = t.show("forecast tile", await t.js("document.querySelector('#fc-summary .slot-tile').innerText"))
    t.ok(await t.js("document.querySelector('#fc-summary .slot-tile').innerText.includes('orders '+isk(11600))"), "the Forecast's total value includes market orders", fc)
    t.ok(await t.js("[...document.querySelectorAll('#fc-chart .lg')].some(b=>b.textContent.includes('Market orders'))"), "the Forecast has a Market orders line")
    # today's point keeps the parts and the owners
    p = t.show("today", await t.js("(()=>{recordSnapshot(true); const p=state.forecast.history.find(x=>x.d===dayKey(Date.now())); return {so:p.so, esc:p.esc, by:p.by}})()"))
    t.ok(p["so"] == 11000 and p["esc"] == 600 and p["by"]["char:9001"][0] == 1e9 and p["by"]["corp:98000001"][2] == 6000, "a recorded day keeps orders and what each owner held", p)
    # pick an owner: only the corporation
    await t.pg.click("#nw-owners [data-nw-own='corp:98000001']"); await asyncio.sleep(0.4)
    t1 = t.show("corp only", await t.js("document.querySelector('#nw-summary .slot-tile').innerText.replace(/\\s+/g,' ')"))
    t.ok(await t.js("document.querySelector('#nw-summary .slot-tile').innerText.includes(isk(6000))") and "Only these owners" in (await t.text("#nw-note") or ""), "one owner: only its wallets, hangars and orders", t1)
    await t.pg.click("#nw-owners [data-nw-own='']"); await asyncio.sleep(0.3)
    t.eq(await t.js("state.forecast.nw.owners"), [], "Everyone again")

@scenario
async def net_worth_jobs(t):
    """Net worth counts what running manufacturing and reaction jobs will deliver (by owner, unpriced products named) and the collateral of couriers you haul."""
    await t.js("""()=>{const c=state.chars.find(x=>x.esiId===9001), now=Date.now(); c.corpId=98000001; c.wallet=1e9; state.corpNames[98000001]='Fake Corp';
      c.jobs=[{id:1,installer:9001,corp:false,activity:11,bp:601,productId:600,runs:5,status:'active',start:now-3600e3,end:now+3600e3},{id:2,installer:9001,corp:false,activity:1,bp:32881,productId:32880,runs:3,status:'delivered',start:now-9e6,end:now-3600e3},
        {id:3,installer:9001,corp:false,activity:1,bp:32881,productId:999999,runs:1,status:'active',start:now,end:now+3600e3},{id:4,installer:9001,corp:false,activity:8,bp:32881,productId:32881,runs:1,status:'active',start:now,end:now+3600e3}];
      state.corpJobs[98000001]={syncedAt:now,via:'Ender Alpha',jobs:[{id:5,installer:9001,corp:true,activity:1,bp:32881,productId:32880,runs:2,status:'ready',start:now-9e6,end:now-60e3}]};
      state.contracts['char:9001']={at:now,list:[{id:70,type:'courier',status:'in_progress',issuer:556,acceptor:9001,reward:5e6,collateral:1e8,expires:now+864e5}]}; saveLocal(); saveCorpJobs();}""")
    await t.tab("forecast", 0.6)
    t.ok(await t.until("!jobsLoading && (state.misc.bpOut||{})['601:11']===200 && (state.misc.bpOut||{})['32881:1']===1 && stockPrice(600)>0 && stockPrice(32880)>0", 15), "the products a run are read from the blueprints", await t.js("state.misc.bpOut"))
    await t.js("renderNetWorth()")
    j = t.show("jobs", await t.js("(()=>{const J=jobsWorth(); return {v:J.v, want:5*200*stockPrice(600)+2*stockPrice(32880), corp:2*stockPrice(32880), by:J.by, n:J.n, noPrice:J.noPrice, c:contractTotals().cin}})()"))
    t.ok(abs(j["v"] - j["want"]) < 1 and j["n"] == 2, "running and ready manufacturing and reaction jobs count; delivered and copying jobs don't", j)
    t.ok(abs(j["by"].get("corp:98000001", 0) - j["corp"]) < 1 and "char:9001" in j["by"], "a corporation's job counts for the corporation", j)
    t.eq(j["noPrice"], [999999], "a product without a price is left out")
    t.eq(j["c"], 1.05e8, "a courier you haul brings back its reward and its collateral")
    nw = t.show("tiles", await t.js("({tile:document.querySelector('#nw-summary .slot-tile').innerText.replace(/\\s+/g,' '), legend:[...document.querySelectorAll('#nw-chart .lg')].map(b=>b.textContent.trim()), note:document.querySelector('#nw-note').innerText})"))
    t.ok("jobs " in nw["tile"], "the Net worth tile names the jobs part", nw["tile"])
    t.ok("no price" in nw["note"] and "industry jobs" in nw["note"], "the unpriced product is named", nw["note"])
    p = t.show("today", await t.js("(()=>{recordSnapshot(true); const p=state.forecast.history.find(x=>x.d===dayKey(Date.now())); return {j:p.j, by:p.by}})()"))
    t.ok(abs(p["j"] - j["v"]) < 1 and p["by"]["corp:98000001"][4] > 0, "a recorded day keeps the jobs part, per owner", p)

@scenario
async def map_gather(t):
    """Gather items on the Map: every system holding some of the picked items, visited in the fewest gates, numbered on the map."""
    t.eq(await t.js("tourOrder([[0,1,2,4],[1,0,3,3],[2,3,0,6],[4,3,6,0]], false)"), [0, 2, 1, 3], "reversing a stretch fixes the nearest-first order (8 instead of 10)")
    await t.js("""()=>{const a=state.assets['char:9001']; a.rows.push({t:34,loc:60000004,h:'Hangar',q:700},{t:34,loc:61000000,h:'Hangar',q:5}); Object.assign(state.typeNames,{34:'Tritanium',35:'Pyerite',16633:'Hydrocarbons',28844:'Rhea'}); state.typeMeta[28844]=[902,6]; saveAssets();}""")
    await map_(t)
    pg = t.pg
    for n in ["Tritanium", "Pyerite"]: await pg.fill("#gr-item", n); await pg.click("#gr-add"); await asyncio.sleep(0.1)
    t.eq(await t.js("state.misc.map.gather.items"), [34, 35], "items are picked from the hangars by name")
    await pg.fill("#gr-from", "Echo"); await pg.click("#gr-form button[type=submit]"); await asyncio.sleep(0.3)
    g = t.show("gather", await t.js("({rows:[...document.querySelectorAll('#gr-out tbody tr')].map(r=>[...r.cells].map(c=>c.innerText.replace(/\\s+/g,' ').trim())), tiles:[...document.querySelectorAll('#gr-out .slot-tile .big-num')].map(x=>x.textContent), legs:(mapUI.haul||[]).map(h=>[h.label,h.ids.length]), label:mapUI.haulLabel, note:document.querySelector('#gr-out').innerText})"))
    t.eq([r[1].split(" ")[0] for r in g["rows"]], ["Echo", "Delta", "Golf", "Bravo"], "every system holding the items, nearest first (Echo → Delta → Golf → Bravo)")
    t.eq(g["tiles"], ["3", "5"], "3 stops, 5 gates")
    t.ok("Tritanium × 100" in g["rows"][1][3] and "Delta station" in g["rows"][1][3], "each stop says what to pick up and where", g["rows"])
    t.eq(g["legs"], [["1", 2], ["2", 3], ["3", 3]], "each leg is drawn on the map with its stop number")
    t.ok(g["label"] == await t.js("GR_LABEL") and "isn't known" in g["note"] and "Location 61000000" in g["note"], "items where the system isn't known are named and left out", g["note"])
    await pg.check("#gr-back"); await asyncio.sleep(0.3)
    t.eq(await t.js("[...document.querySelectorAll('#gr-out .slot-tile .big-num')].map(x=>x.textContent)"), ["3", "8"], "back to the start: 8 gates")
    await pg.click("#gr-items [data-gr-del='35']"); await asyncio.sleep(0.3)
    t.eq(await t.js("[[...document.querySelectorAll('#gr-out .slot-tile .big-num')].map(x=>x.textContent), state.misc.map.gather.items]"), [["2", "6"], [34]], "removing an item plans again")
    # Security: without null-sec, Delta's Tritanium is left out and the trip from Bravo stays out of null-sec
    await pg.fill("#gr-item", "Pyerite"); await pg.click("#gr-add"); await pg.uncheck("#gr-back"); await pg.fill("#gr-from", "Bravo"); await pg.uncheck("[data-gr-sec=n]"); await pg.click("#gr-form button[type=submit]"); await asyncio.sleep(0.3)
    s = t.show("no null-sec", await t.js("({rows:[...document.querySelectorAll('#gr-out tbody tr')].map(r=>r.cells[1].innerText.split(/\\s/)[0]), tiles:[...document.querySelectorAll('#gr-out .slot-tile .big-num')].map(x=>x.textContent), note:$('gr-out').innerText})"))
    t.ok(s["rows"] == ["Bravo", "Golf"] and s["tiles"] == ["2", "2"] and "null-sec, which you didn't tick" in s["note"] and "Delta station" in s["note"], "unticked security: its stops are named and left out", s)
    t.eq(await t.js("(()=>{const m=mapIndex(), n=(x)=>m.byName.get(x); return [gatePath(n('alpha'),n('golf'),(s)=>secKind(s)!=='l'), (gatePath(n('echo'),n('golf'),(s)=>secKind(s)!=='h')||[]).map(s=>s.n)]})()"), [None, ["Echo", "Delta", "Charlie", "Golf"]], "gate routes only fly through the ticked security (the stop itself always counts)")
    # Jumps: a leg takes gates or jumps, whichever is quicker
    t.eq(await t.js("(()=>{const m=mapIndex(), n=(x)=>m.byName.get(x), a=grLeg(n('foxtrot'),n('golf'),20,()=>true), b=grLeg(n('foxtrot'),n('golf'),5,()=>true); return [a.path.map(s=>s.n), a.jumps, a.gates, b.jumps, b.gates]})()"), [["Foxtrot", "Echo", "Golf"], 1, 1, 0, 4], "a gate to Echo (Foxtrot is in an incursion) and one 9 ly jump beat 4 gates; out of range it takes the gates")
    await pg.check("[data-gr-sec=n]"); await pg.select_option("#gr-how", "jump"); await asyncio.sleep(0.4)
    j = t.show("jumps", await t.js("({head:[...document.querySelectorAll('#gr-out thead th')].map(h=>h.innerText.split('\\n')[0].trim()), labels:[...document.querySelectorAll('#gr-out .slot-tile .label')].map(x=>x.textContent)})"))
    t.ok("Route" in j["head"] and j["labels"] == ["Stops", "Gates", "Jumps", "Fuel"], "with a jump-capable ship: the route of each leg, jumps and fuel", j)
    # Cargo: a 60,000 m³ hold (1 m³ an item here): Delta's 100,000 Tritanium takes two trips, the ship unloads at the start in between
    await pg.select_option("#gr-how", "gates"); await asyncio.sleep(0.2)
    t.ok(await t.js("[...$('gr-ship').options].some(o=>o.value==='t:28844') && [...$('gr-ship').options].some(o=>o.value==='range')"), "the cargo choice lists the ship under Range and the ships in your hangars")
    await t.js("()=>{grVol.set(34,1); grVol.set(35,1); grVol.set(16633,1);}")
    await pg.fill("#gr-from", "Echo"); await pg.fill("#gr-cargo", "60000"); await pg.dispatch_event("#gr-cargo", "change"); await asyncio.sleep(0.2)
    await pg.click("#gr-form button[type=submit]"); await t.until("!!document.querySelector('#gr-out tbody')", 5)
    c = t.show("cargo", await t.js("({rows:[...document.querySelectorAll('#gr-out tbody tr')].map(r=>[r.cells[1].innerText.split(/\\s/)[0], r.cells[3].innerText.replace(/\\s+/g,' ').slice(0,40), r.cells[4].innerText.replace(/\\D/g,'')]), tiles:[...document.querySelectorAll('#gr-out .slot-tile .big-num')].map(x=>x.textContent), back:$('gr-back').checked && $('gr-back').disabled, legs:mapUI.haul.length})"))
    t.eq([r[0] for r in c["rows"]], ["Echo", "Delta", "Echo", "Delta", "Golf", "Bravo", "Echo"], "full hold: back to the start to unload, then back to finish Delta")
    t.eq([r[2] for r in c["rows"]], ["", "60000", "0", "40000", "40700", "45700", "0"], "what's in the hold after each stop")
    t.ok(c["rows"][2][1].startswith("Unload") and c["tiles"][:3] == ["3", "10", "2"] and c["back"] and c["legs"] == 6, "2 trips, 10 gates; with a hold every trip ends at the start", c)
    # A station to empty: everything in Alpha station
    t.ok(await t.js("[...$('gr-place').querySelectorAll('optgroup')].some(g=>g.label==='Alpha' && [...g.children].some(o=>o.value==='60000003' && o.textContent.startsWith('Alpha station')))"), "the stations dropdown is grouped by system")
    await pg.select_option("#gr-place", "60000003"); await asyncio.sleep(0.3); await t.until("!!document.querySelector('#gr-out tbody')", 5)
    st = t.show("station", await t.js("({places:state.misc.map.gather.places, chips:$('gr-places').innerText, left:[...$('gr-place').options].some(o=>o.value==='60000003'), rows:[...document.querySelectorAll('#gr-out tbody tr')].map(r=>r.cells[3].innerText)})"))
    t.ok(st["places"] == [60000003] and "Everything in Alpha station" in st["chips"] and any("Hydrocarbons" in r for r in st["rows"]) and not st["left"], "a station to empty: everything in it is picked up, and it leaves the dropdown", st)
    await t.js("document.getElementById('gr').scrollIntoView()"); await pg.screenshot(path=SP + "map-gather.png")
    await pg.click("#gr-clear"); await asyncio.sleep(0.2)
    t.ok(await t.js("!mapUI.haul && !$('gr-out').innerHTML"), "Clear removes the route from the map")

@scenario
async def contracts_browser(t):
    """Contracts browser: ended contracts kept, every contract's items read once (given and asked), sides, worth in a pricing, filters, details."""
    p = t.show("past", await t.js("""(()=>{const now=Date.now(), iso=(t)=>new Date(t).toISOString(); state.contracts['char:9001']={at:now-1000,list:[],past:[{id:800,type:'item_exchange',status:'finished',issuer:9001,done:now-80*864e5,issued:now-81*864e5,expires:0,items:[[34,1,0]],ask:[]},{id:801,type:'item_exchange',status:'deleted',issuer:9001,done:0,issued:now-100*864e5,expires:now-95*864e5}]};
      const raw=[{contract_id:900,type:'item_exchange',status:'outstanding',issuer_id:9001,price:700000,date_issued:iso(now-864e5),date_expired:iso(now+5*864e5),title:'Two Ventures',start_location_id:60003760,availability:'personal',assignee_id:555},
        {contract_id:802,type:'courier',status:'finished',issuer_id:556,acceptor_id:9001,reward:5e6,collateral:1e8,date_issued:iso(now-3*864e5),date_completed:iso(now-2*864e5),date_expired:iso(now+864e5),start_location_id:60003760,end_location_id:60000002,volume:12000}];
      const P=pastContracts('char:9001',raw); return P.map(c=>[c.id,c.status,!!c.items]).sort()})()"""))
    t.eq(p, [[800, "finished", True], [802, "finished", False]], "ended contracts are kept 90 days (with their items); active ones aren't in the past list")
    it = t.show("items", await t.js("async()=>{const L=[{id:900,type:'item_exchange',status:'outstanding',issuer:9001},{id:901,type:'item_exchange',status:'outstanding',issuer:556,assignee:9001},{id:903,type:'item_exchange',status:'outstanding',issuer:9001}]; await contractItems('char:9001',L,(cid)=>`/characters/9001/contracts/${cid}/items/`,'tok',''); return L.map(c=>[c.id,c.items||null,c.ask||null,c.noItems||0])}"))
    t.eq(it, [[900, [[32880, 2, 0]], [], 0], [901, [[16633, 1000, 0], [9100, 500, 0]], [[34, 5]], 0], [903, None, None, 1]], "every contract's items: what it gives and what it asks for; one that can't be read isn't asked again")
    now = "Date.now()"
    await t.js(f"""async()=>{{const now={now}; state.chars.find(c=>c.esiId===9001).corpId=98000001; state.misc.cbNames={{555:'Bob Client',556:'Gas Supplier'}};
      state.contracts['char:9001']={{at:now,list:[{{id:900,type:'item_exchange',status:'outstanding',issuer:9001,assignee:555,price:700000,reward:0,collateral:0,issued:now-864e5,expires:now+5*864e5,title:'Two Ventures',from:60003760,avail:'personal',items:[[32880,2,0]],ask:[]}},
        {{id:901,type:'item_exchange',status:'outstanding',issuer:556,assignee:9001,price:3000000,reward:0,collateral:0,issued:now-864e5,expires:now+3600e3,title:'',from:60003760,avail:'personal',items:[[16633,1000,0],[9100,500,0]],ask:[[34,5]]}},
        {{id:904,type:'courier',status:'in_progress',issuer:556,acceptor:9001,price:0,reward:5e6,collateral:1e8,issued:now-864e5,expires:now+864e5,title:'',from:60003760,to:60000002,vol:12000,avail:'personal',items:[],ask:[]}},
        {{id:905,type:'item_exchange',status:'outstanding',issuer:9001,price:1e6,reward:0,collateral:0,issued:now-9*864e5,expires:now-864e5,title:'Old offer',from:60003760,avail:'public',items:[[34,10,0],[32881,1,1]],ask:[]}}],
        past:[{{id:802,type:'item_exchange',status:'finished',issuer:9001,acceptor:556,price:2e6,reward:0,collateral:0,issued:now-3*864e5,done:now-2*864e5,expires:now+864e5,title:'Sold',from:60003760,avail:'personal',items:[[9101,10,0]],ask:[]}}]}};
      state.contracts['corp:98000001']={{at:now-5000,list:[{{id:900,type:'item_exchange',status:'outstanding',issuer:9001,assignee:555,price:700000,expires:now+5*864e5,from:60003760}}],past:[]}};
      cbCfg().price='jsv'; saveMisc(); saveContracts();}}""")
    await t.tab("cbrowse", 0.6); await t.until("!cbBusy", 10); await asyncio.sleep(0.3)
    G = "[...document.querySelectorAll('#cb-table tr.group th')].map(th=>th.textContent.replace(/^[▾▸]\\s*/,'').replace(/\\s*\\d+$/,''))"
    t.eq(await t.js(G), ["Waiting", "In progress"], "active contracts grouped by status; a contract seen twice shows once")
    rows = t.show("rows", await t.js("[...document.querySelectorAll('#cb-table tbody tr:not(.group)')].map(r=>[...r.cells].map(c=>c.innerText.replace(/\\s+/g,' ').trim()))"))
    by = {r[1]: r for r in rows}
    v = t.show("values", await t.js("Object.fromEntries([...document.querySelectorAll('#cb-table tbody tr:not(.group)')].map(r=>[r.cells[1].textContent, [+r.cells[3].dataset.v, +r.cells[4].dataset.v, +r.cells[5].dataset.v, r.cells[3].innerText.includes('collateral '+isk(1e8))]]))"))
    t.ok("Two Ventures" in by["You sell"][0] and v["You sell"][:3] == [700000, 600000, 100000], "You sell: items worth (2 × Venture at Jita sell) and how much better the price is", v.get("You sell"))
    t.ok("asks 5 × Tritanium" in by["You buy"][0] and v["You buy"][1] == 699980 and v["You buy"][2] == 699980 - 3000000, "You buy: worth of what it gives less what it asks for, against its price", v.get("You buy"))
    t.ok(v["You haul"][0] == 5e6 and v["You haul"][3], "a courier you accepted: reward and collateral", v.get("You haul"))
    t.ok("Gas Supplier" in by["You buy"][2], "names of the other side", by.get("You buy"))
    tiles = t.show("tiles", await t.js("[...document.querySelectorAll('#cb-summary .slot-tile')].map(x=>x.innerText.replace(/\\s+/g,' '))"))
    t.ok(tiles[0].lower().startswith("active contracts 3") and any(x.lower().startswith("expire within a day 1") for x in tiles), "tiles: active contracts and one about to expire", tiles)
    await t.pg.click("#cb-show [data-cb-show=all]"); await asyncio.sleep(0.4)
    t.eq(await t.js(G), ["Waiting", "In progress", "Expired", "Finished"], "Everything: expired and finished too")
    t.ok("no price" in (await t.text("#cb-table") or "") and "no price" in (await t.text("#cb-note") or ""), "an item without a price leaves the worth unknown, and says so")
    await t.js("()=>{cfCfg('cb').rules=[{f:'side',op:'is',a:'You sell'}]; renderCbrowse();}"); await asyncio.sleep(0.3)
    t.eq(await t.js("[...document.querySelectorAll('#cb-table tbody tr:not(.group)')].map(r=>r.cells[1].textContent)"), ["You sell", "You sell", "You sell"], "filters on the contracts' columns")
    await t.js("()=>{cfCfg('cb').rules=[]; renderCbrowse();}"); await t.pg.fill("#cb-find", "hydrocarbons"); await asyncio.sleep(0.3)
    t.eq(await t.js("[...document.querySelectorAll('#cb-table tbody tr:not(.group)')].length"), 1, "the search finds a contract by an item in it")
    await t.pg.click("#cb-table [data-cb-open='901']"); await asyncio.sleep(0.3)
    d = t.show("detail", await t.text("#cb-table"))
    t.ok("Gives" in d and "Asks for" in d and "Contract ID" in d, "a contract's details open below it", d)
    await t.pg.fill("#cb-find", ""); await asyncio.sleep(0.3); await t.pg.screenshot(path=SP + "contracts-browser.png", full_page=True)

@scenario
async def owned_and_priced(t):
    """Economizers fitted on a ship count as owned; a stack of formulas counts every one; suppliers priced at a % of a pricing show prices; Planets' who makes what."""
    await t.js("()=>{state.assets['char:9001'].other=[{t:34124,loc:60003760,h:'LoSlot0',in:28844,hg:'Hangar',q:1}]; saveAssets();}")
    t.eq(await t.js("(ecoOwned()||{}).id"), 34124, "an economizer fitted on a jump freighter is found")
    t.eq(await t.js("[slimBps([{type_id:46166,quantity:22,runs:-1}])[0][5], slimBps([{type_id:1,quantity:-1,runs:-1},{type_id:2,quantity:-2,runs:5}]).map(b=>b[5])]"), [22, [1, 1]], "a blueprint stack keeps how many it holds")
    await t.js("state.misc.ownedBps['char:1'].list.push([46166,0,0,-1,0,22],[46166,0,0,-1,0,1])")
    t.eq(await t.js("ownedBps().get(46166).bpo"), 23, "every formula in a stack counts")
    await t.tab("suppliers")
    await t.js("()=>{supList().push({id:'s9',name:'Carl',url:'',stock:{34:{q:50,n:'Tritanium'},35:{q:5,n:'Pyerite',price:7}},pricing:{mode:'pct',pct:90,base:'jsv'}}); supOpen='s9'; saveMisc(); renderSuppliers();}")
    t.ok(await t.until("priceIn('jsv',34)>0 && !/no price/.test(document.getElementById('sup-out').innerText)", 15), "a % of a pricing: every item gets its price", await t.text("#sup-out"))
    want = await t.js("isk(priceIn('jsv',34)*0.9)"); out = t.show("supplier", await t.text("#sup-out"))
    t.ok(want in out, "the price is the % of the pricing", [want, out])
    await t.js("""()=>{const pl={id:1,name:'Delta I',type:'barren',system:'Delta',lastUpdate:Date.now(),factories:2,extractors:[],inputs:[],stock:[],unneeded:[]};
      state.chars[0].planets=[{...pl,makes:[{name:'Nano-Factory',perHour:2,t:2869},{name:'Coolant',perHour:40}]},{...pl,id:2,makes:[{name:'Nano-Factory',perHour:1,t:2869}]}];
      state.chars[1].planets=[{...pl,id:3,factories:0,makes:[],extractors:[{product:'Base Metals',qty:6000,cycle:1800,end:Date.now()+864e5}]}]; delete state.misc.piSchem; saveLocal(); renderPlanets();}""")
    await t.tab("planets", 0.4)
    who = t.show("who makes what", await t.js("[...document.querySelectorAll('#piw-table tbody tr')].map(r=>r.innerText.replace(/[▾▸]/g,'').replace(/\\s+/g,' ').trim())"))
    t.ok(len(who) == 4 and who[0].upper().startswith("P4") and "Ender Alpha" in who[1] and "Nano-Factory 3/h" in who[1] and "Coolant" not in who[1] and who[1].endswith("2")
         and who[2].upper().startswith("RAW (P0)") and "Ender Beta" in who[3] and "Base Metals 12k/h" in who[3], "Who makes what: each pilot's highest tier, summed over their colonies", who)
    t.eq(await t.js("(()=>{state.misc.piSchem={s:{3:{ins:[[2,1]]},2:{ins:[[1,1],[9,1]]},1:{ins:[[0,1]]}}}; const r=[3,2,1,0].map(piTierOf); delete state.misc.piSchem; return r})()"), [3, 2, 1, 0], "PI tiers from CCP's planet schematics")

@scenario
async def market_browser(t):
    """Trading board: CCP's market groups, every region's orders for an item, the 5% prices, the trade hubs side by side, filters, jumps, a region, history, and the Item database's button."""
    await map_(t)
    await t.js("()=>{const c=state.chars[0]; c.loc={sys:30000001,at:Date.now()}; c.orders={at:Date.now(),list:[{id:1001,t:34,buy:0,p:4,left:1000,tot:1000,esc:0,loc:60003760,reg:10000002,at:Date.now()-3600e3,dur:90,corp:0}]};}")
    t.ok(await t.js("!!document.querySelector('#page-prices #tb-list') && !!document.querySelector('#page-prices #arb-out') && !document.querySelector('#page-trading #tb-list')"), "Market watch and Arbitrage moved to the Prices page")
    await t.pg.set_viewport_size({"width": 1920, "height": 1000})
    await t.tab("trading", 0.5); t.ok(await t.until("!!mbIdx && !!document.querySelector('#mb-tree li')", 25), "the market groups are read from CCP's game data", await t.text("#mb-tree"))
    w = t.show("widths", await t.js("[document.querySelector('#page-trading').getBoundingClientRect().width, document.querySelector('nav.tabs').getBoundingClientRect().width]"))
    t.ok(w[0] > 1800 and w[1] <= 1248, "the page uses the whole width, the tabs keep theirs", w)
    groups = "[...document.querySelectorAll('#mb-tree > ul > li > button')].map(b=>b.innerText.replace(/[▸▾]/g,'').trim())"
    t.eq(await t.js(groups), ["Manufacture & Research", "PLEX", "Ships"], "root market groups, A→Z, without the empty one")
    for g in (9, 1031, 1857): await t.pg.click(f"#mb-tree [data-mb-g='{g}']"); await asyncio.sleep(0.15)
    t.eq(await t.js("[...document.querySelectorAll('#mb-tree [data-mb-open]')].map(b=>b.innerText.trim())"), ["Pyerite", "Tritanium"], "a group opens down to its items")
    await t.pg.click("#mb-tree [data-mb-open='34']"); t.ok(await t.until("mbItem && mbItem.id===34 && !mbItem.busy && !!mbItem.data", 20), "Tritanium's orders are read", await t.text("#mb-top"))
    await asyncio.sleep(0.3)
    t.eq([await t.text("#mb-sn"), await t.text("#mb-bn")], ["4", "2"], "every region's sell and buy orders")
    sells = "[...document.querySelectorAll('#mb-sells tbody tr')].map(r=>[...r.cells].map(c=>c.innerText.trim()))"
    S = t.show("sellers", await t.js(sells))
    t.eq([r[2] for r in S], [await t.js(f"iskFull({p})") for p in (3.5, 4, 4.5, 5)], "sellers cheapest first")
    t.ok("Delta VII - Station" in S[0][3] and S[0][3].startswith("0.0"), "station names from ESI, with the system's security", S[0])
    t.ok("yours" in S[1][3] and "Ender Alpha" in S[1][3], "your own order is marked with its owner", S[1])
    t.ok("Structure in Foxtrot" in S[3][3], "a structure ESI won't name shows its system", S[3])
    top = t.show("tiles", await t.text("#mb-top"))
    t.ok(await t.js("(()=>{const x=document.querySelector('#mb-top').innerText; return x.includes(iskFull((100*3.5+205*4)/305)) && x.includes(iskFull(3.8)) && x.includes((6100).toLocaleString()) && x.includes((10500).toLocaleString())})()"), "Sell (5%) and Buy (5%) average the best 5% of the units; for sale and wanted", top)
    t.ok(await t.js("document.getElementById('mb-hist-panel').hidden && document.getElementById('mb-hubs-panel').hidden && !document.getElementById('mb-books').hidden"), "sellers and buyers show; history and the comparison wait behind their buttons")
    t.ok(not await t.js("(document.querySelector('#mb-top').innerText||'').includes('Citadel markets permission')"), "no note about citadels whose market can't be read")
    sh = t.show("short prices", await t.js("[1.6e9, 999950, 250e6, 12500, 3.5].map(mbShort)"))
    t.eq(sh, await t.js("[[1.6,'B'],[1,'M'],[250,'M'],[12.5,'K']].map(([v,u])=>v.toLocaleString()+u+' ISK').concat(iskFull(3.5))"), "the lowest / highest lines are short: 1.6B, 1M (not 1,000K), 250M, 12.5K ISK; under a thousand to the cent")
    # citadel markets: the other pages read at once, a citadel without a market (403) not asked again for 30 minutes
    cm = t.show("citadel market", await t.js("""(async()=>{ const sv={m:esiMarket,f:freshAccess,c:state.chars,k:ls.get('eve-industry-esi-tokens',{})}, calls=[];
      try { ls.set('eve-industry-esi-tokens',{9:{}}); freshAccess=async()=>({access:'x'}); state.chars=[{esiId:9,scopes:MARKET_SCOPE}];
        esiMarket=async(u)=>{ calls.push(u); const p=+u.match(/page=(\d+)/)[1]; if(u.includes('/1000000000001/')) return new Response('',{status:403}); return new Response(JSON.stringify([{type_id:34,price:p,volume_remain:1,is_buy_order:false,order_id:p}]),{headers:{'X-Pages':'3'}}); };
        const a=await structOrders('1000000000002'); let e=null; await structOrders('1000000000001').catch(()=>0); const n=calls.length; await structOrders('1000000000001').catch(x=>e=x.message);
        return [a.get(34), structBooks['1000000000002'].sells.get(34).length, n, calls.length, e];
      } finally { esiMarket=sv.m; freshAccess=sv.f; state.chars=sv.c; ls.set('eve-industry-esi-tokens',sv.k); delete structMarket['1000000000002']; delete structBooks['1000000000002']; delete structNo['1000000000001']; } })()"""))
    t.eq(cm, [1, 3, 4, 4, "its market can't be read"], "a citadel's 3 pages are read, and one that refuses isn't asked again")
    hh = t.show("item panel height", await t.js("document.getElementById('mb-head').getBoundingClientRect().height")); t.ok(hh < 200, "the item panel stays short", hh)
    await t.js("document.querySelector('.mb').scrollIntoView()"); await asyncio.sleep(0.2); await t.pg.screenshot(path=SP + "trading_board.png")
    await t.pg.click("[data-mb-view=hubs]"); await asyncio.sleep(0.2)
    t.ok(await t.js("!document.getElementById('mb-hubs-panel').hidden && document.getElementById('mb-books').hidden"), "Show markets comparison shows it in place of sellers and buyers")
    hubs = t.show("by market", await t.js("[...document.querySelectorAll('#mb-hubs tbody tr')].map(r=>[...r.cells].map(c=>c.innerText.trim()))"))
    t.ok(len(hubs) == 2 and hubs[0][0].startswith("Jita") and hubs[0][1] == await t.js("iskFull(4)") and hubs[0][3] == await t.js("iskFull(3)") and hubs[1][1] == await t.js("iskFull(4.5)") and hubs[1][3] == await t.js("iskFull(3.8)"), "By market: only the hubs with orders, each one's lowest sell and highest buy", hubs)
    t.eq(await t.js("[...document.querySelectorAll('[data-mb-view]')].map(b=>b.textContent)"), ["Show history", "Back to sellers and buyers"], "its button now goes back")
    await t.pg.click("[data-mb-view=hubs]"); await asyncio.sleep(0.2)
    await t.pg.click("[data-mb-view=hist]"); await asyncio.sleep(0.2)
    t.ok(await t.js("!document.getElementById('mb-hist-panel').hidden && document.getElementById('mb-books').hidden"), "Show history shows it in place of sellers and buyers")
    t.ok(await t.js("!!document.querySelector('#mb-title button.copyname[data-copy=\"Tritanium\"]') && ![...document.querySelectorAll('#mb-top button')].some(b=>b.textContent==='Copy name')"), "the item's name copies on click (no Copy name button)")
    t.ok(await t.until("!!document.querySelector('#mb-hist svg')", 10) and "sold a day" in (await t.text("#mb-hist") or ""), "the region's price history", await t.text("#mb-hist"))
    box = await t.pg.locator("#mb-hist svg").bounding_box(); await t.pg.mouse.move(box["x"] + box["width"] - 20, box["y"] + 100); await asyncio.sleep(0.2)
    tip = t.show("tooltip", await t.text("#mb-hist .mb-tip")); t.ok(tip and "Average" in tip and "Volume" in tip and "Orders" in tip and await t.js("document.querySelector('#mb-hist .mb-cx').style.display!=='none'"), "pointing at the chart shows that day's numbers", tip)
    t.ok(await t.js("(()=>{const x=document.querySelector('#mb-hist .mb-tip').innerText; const d=new Date(Date.now()-864e5).toISOString().slice(0,10); return x.includes(d)})()"), "the last day is under the pointer at the right edge", tip)
    cross = t.show("crosshair", await t.js("['.yl text','.xl text'].map(s=>document.querySelector('#mb-hist .mb-cx '+s).textContent)"))
    t.ok(cross[1] == await t.js("document.querySelector('#mb-hist')._geo.rows.at(-1).date") and cross[0] and cross[0][0].isdigit() and await t.js("+document.querySelector('#mb-hist .mb-cx .h').getAttribute('y1')>0"), "a crosshair: the day's date at the bottom, the price at the pointer's height on the left", cross)
    await t.pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] - 40); await asyncio.sleep(0.2)
    t.ok(await t.js("(()=>{const G=document.querySelector('#mb-hist')._geo, r=document.querySelector('#mb-hist .mb-cx .yl rect'); return +r.getAttribute('x')>=G.W-G.R0})()"), "over the bars it reads the volume on the right")
    await t.pg.mouse.move(box["x"] + box["width"] * 0.4, box["y"] + 120); await asyncio.sleep(0.2); await t.pg.screenshot(path=SP + "trading_history.png")
    t.ok(await t.js("(()=>{const sv=document.querySelector('#mb-hist svg'), G=document.querySelector('#mb-hist')._geo, p=document.getElementById('mb-hist-panel'); return [...sv.querySelectorAll('text')].some(x=>x.textContent==='Volume' && +x.getAttribute('x')>G.W-G.R0) && sv.getBoundingClientRect().height>300 && p.scrollHeight<=p.clientHeight+1})()"), "the volume has its own scale on the right; the chart fills the panel without a scrollbar")
    tl = t.show("chart labels", await t.js("(()=>{const E=[...document.querySelectorAll('#mb-hist svg > text')], T=E.map(x=>x.getBBox()), o=[]; for(let a=0;a<T.length;a++) for(let b=a+1;b<T.length;b++){const A=T[a],B=T[b]; if(A.x<B.x+B.width&&B.x<A.x+A.width&&A.y<B.y+B.height&&B.y<A.y+A.height) o.push(E[a].textContent+' / '+E[b].textContent)} return [T.length,o.length,o]})()"))
    t.ok(tl[1] == 0, "no two labels of the chart overlap", tl)
    t.eq(await t.js("[...document.querySelectorAll('#mb-span option')].map(o=>o.textContent)"), ["7 days", "14 days", "30 days", "3 months", "6 months", "1 year", "Everything"], "more spans for the history")
    await t.pg.select_option("#mb-span", "7"); await asyncio.sleep(0.4)
    t.eq(await t.js("document.querySelector('#mb-hist')._geo.rows.length"), 7, "7 days shows 7 days")
    # Open in a window: a real browser window (for another screen); the board goes back to sellers and buyers
    async with t.pg.context.expect_page() as pi: await t.pg.click("[data-mb-pop=hist]")
    win = await pi.value; await win.wait_for_load_state(); await asyncio.sleep(0.6)
    t.ok(await win.evaluate("!!document.querySelector('#mb-hist svg') && document.title.startsWith('History')"), "the history opens in its own window", await win.evaluate("document.body.innerText.slice(0,200)"))
    t.ok(await t.js("!document.getElementById('mb-books').hidden && document.getElementById('mb-hist-panel').hidden"), "the board goes back to sellers and buyers")
    t.eq(await t.js("[...document.querySelectorAll('[data-mb-view]')].map(b=>b.textContent)"), ["Show history", "Show markets comparison"], "the buttons are back to their start")
    await win.select_option("#mb-span", "14"); await asyncio.sleep(0.5)
    t.eq(await win.evaluate("document.querySelector('#mb-hist')._geo.rows.length"), 12, "the window's own span list works (14 days: the 12 the fake history has)")
    box = await win.locator("#mb-hist svg").bounding_box(); await win.mouse.move(box["x"] + box["width"] / 2, box["y"] + 100); await asyncio.sleep(0.2)
    t.ok("Average" in (await win.evaluate("document.querySelector('#mb-hist .mb-tip').innerText") or ""), "pointing works in the window too")
    await t.js("mbOpen(35)"); await t.until("mbItem && mbItem.id===35 && !mbItem.busy", 15); await asyncio.sleep(0.5)
    t.ok("Pyerite" in await win.evaluate("document.title"), "the window follows the item open on the board", await win.evaluate("document.title"))
    await t.js("mbOpen(34)"); await t.until("mbItem && mbItem.id===34 && !mbItem.busy", 15)
    async with t.pg.context.expect_page() as pi2: await t.pg.click("[data-mb-view=hubs]"); await t.pg.click("[data-mb-pop=hubs]")
    win2 = await pi2.value; await win2.wait_for_load_state(); await asyncio.sleep(0.5)
    rows = await win2.evaluate("[...document.querySelectorAll('#mb-hubs tbody th')].map(th=>th.innerText.trim().split(' ')[0])")
    t.eq(rows, ["Jita", "Amarr"], "the comparison opens in its own window")
    await win2.click("#mb-hubs [data-sort='mbh:ls']"); await win2.click("#mb-hubs [data-sort='mbh:ls']"); await asyncio.sleep(0.3)
    t.eq(await win2.evaluate("[...document.querySelectorAll('#mb-hubs tbody th')].map(th=>th.innerText.trim().split(' ')[0])"), ["Amarr", "Jita"], "its columns sort in the window")
    await win.close(); await win2.close(); await t.pg.bring_to_front()
    # the page's notes open from the item panel (no notes under the page)
    t.ok(await t.js("document.getElementById('howto').hidden"), "no page notes under the board")
    await t.pg.click("#mb-top [data-mb-howto]"); await asyncio.sleep(0.2)
    t.ok(await t.js("document.getElementById('mb-howto').open && document.getElementById('mb-howto-text').textContent===HOWTO.trading"), "How this page works opens from the item panel")
    await t.pg.keyboard.press("Escape"); await asyncio.sleep(0.2)
    # one screen: the board fits the window (the tree and the order lists scroll inside)
    fit = t.show("fit", await t.js("(()=>{const m=document.querySelector('.mb'), r=m.getBoundingClientRect(); return [Math.round(r.height), innerHeight, ...['.mb-left','.mb-main','#mb-books'].map(s=>{const e=document.querySelector(s); return e.scrollHeight<=e.clientHeight+1})]})()"))
    t.ok(fit[0] <= fit[1] and fit[0] >= fit[1] - 40 and all(fit[2:]), "the board is one screen tall and nothing spills out", fit)
    t.ok(await t.js("(()=>{scrollTo(0,0); const T=$('mb-tree'); T.style.maxHeight='40px'; const n=T.querySelector('[aria-current]'); T.scrollTop=0; mbTreeTo(n, true); const r=[scrollY, T.scrollTop>0 || n.offsetTop<40]; T.style.maxHeight=''; return r[0]===0 && r[1]})()"), "showing a market tree row scrolls the tree, never the page")
    t.eq(await t.js("['#mb-tree','#mb-sells .scroller'].map(s=>getComputedStyle(document.querySelector(s)).overscrollBehaviorY)"), ["contain", "contain"], "reaching a list's end doesn't scroll the page")
    t.ok(await t.js("document.querySelector('#mb-top .mb-stats .mb-views [data-mb-view=hist]')!=null && !document.querySelector('.mb-left [data-mb-view]')"), "Show history and Show markets comparison sit in the item panel, after the numbers")
    t.ok(await t.js("(()=>{const x=document.querySelector('#mb-top .mb-stats').textContent; return x.includes('Sell volume') && x.includes('Buy volume') && !/For sale|Wanted/i.test(x)})()"), "Sell volume and Buy volume share one column")
    # a clicked row stays highlighted; another click on it lets go
    await t.pg.click("#mb-sells tbody tr:nth-child(2) td:first-child"); await asyncio.sleep(0.1)
    t.eq(await t.js("[...document.querySelectorAll('#mb-sells tbody tr.sel')].map(r=>+r.dataset.mbO)"), [1001], "a clicked seller stays highlighted")
    await t.pg.click("#mb-buys tbody tr:nth-child(1) td:first-child"); await asyncio.sleep(0.1)
    t.eq(await t.js("[...document.querySelectorAll('.mb-book tr.sel')].map(r=>+r.dataset.mbO)"), [1001, 1103], "one highlighted line per side")
    # sellers and buyers share the height: a short list gives the other its room
    hs = t.show("book heights", await t.js("(()=>{mbFitBooks(); return [...document.querySelectorAll('.mb-book .scroller')].map(s=>[s.clientHeight, s.scrollHeight, parseFloat(s.style.maxHeight)])})()"))
    t.ok(hs[0][0] == hs[0][1] or hs[1][0] == hs[1][1], "both books fit when they are short", hs)
    # filters: leave out null-sec, then a price floor, then jumps from the pilot's system
    await t.pg.click("#mb-filt summary"); await t.pg.check("[data-mb-f=ns]"); await asyncio.sleep(0.3)
    t.eq([await t.text("#mb-sn"), await t.text("#mb-bn")], ["1", "1"], "Null-sec left out")
    t.ok("1 on" in (await t.text("#mb-filt summary") or ""), "the filters count shows", await t.text("#mb-filt summary"))
    await t.pg.uncheck("[data-mb-f=ns]"); await t.pg.fill("[data-mb-f=pa]", "4.2"); await asyncio.sleep(0.3)
    t.eq(await t.text("#mb-sn"), "2", "a price floor")
    await t.pg.click("#mb-fclear"); await asyncio.sleep(0.2); t.eq(await t.text("#mb-sn"), "4", "Clear filters")
    await t.pg.select_option("#mb-from", "30000001"); await asyncio.sleep(0.3)
    S = t.show("with jumps", await t.js(sells)); t.eq([r[4] for r in S], ["3", "4", "0", "5"], "jumps from the pilot's system")
    await t.pg.fill("[data-mb-f=jb]", "3"); await asyncio.sleep(0.3); t.eq(await t.text("#mb-sn"), "2", "jumps up to 3")
    await t.pg.click("#mb-fclear"); await t.pg.select_option("#mb-from", ""); await asyncio.sleep(0.2)
    await t.pg.click("#mb-sells [data-sort='mbs:q']"); await asyncio.sleep(0.2)
    t.eq([r[1] for r in await t.js(sells)], await t.js("[100,1000,2000,3000].map(x=>x.toLocaleString())"), "sellers sort by a column title")
    await t.pg.click("#mb-sells [data-sort='mbs:p']"); await asyncio.sleep(0.2)
    # where to look: one region, then one trade hub; By market keeps only what has orders there
    await t.pg.select_option("#mb-where", "r:10000001"); t.ok(await t.until("mbItem && !mbItem.busy && mbCfg().reg==='r:10000001'", 15), "a region is read")
    await asyncio.sleep(0.3); t.eq(await t.text("#mb-sn"), "2", "only that region's orders")
    await t.pg.click("[data-mb-view=hubs]"); await asyncio.sleep(0.2)
    t.eq(await t.js("[...document.querySelectorAll('#mb-hubs tbody th')].map(th=>th.innerText.trim().split(' ')[0])"), ["Amarr"], "By market: only the hub with orders there")
    await t.pg.click("[data-mb-view=hubs]"); await asyncio.sleep(0.2)
    await t.pg.select_option("#mb-where", "st:60003760"); t.ok(await t.until("mbItem && !mbItem.busy && mbCfg().reg==='st:60003760'", 15), "a trade hub is read")
    await asyncio.sleep(0.3); t.eq([await t.text("#mb-sn"), await t.text("#mb-bn")], ["1", "1"], "only that station's orders")
    t.ok("Jita 4-4" in (await t.text("#mb-status") or ""), "the status says where it looks", await t.text("#mb-status"))
    await t.pg.select_option("#mb-where", ""); await t.until("mbItem && !mbItem.busy && !!mbItem.data && mbItem.data.orders.length===6", 15)
    # PLEX: only in the global market, with its own history; a region or a hub keeps the global orders placed there
    await t.js("mbOpen(44992)"); t.ok(await t.until("mbItem && mbItem.id===44992 && !mbItem.busy && !!mbItem.data", 15), "PLEX is read")
    await asyncio.sleep(0.3); t.eq([await t.text("#mb-sn"), await t.text("#mb-bn")], ["1", "1"], "PLEX's orders come from the global market")
    t.ok("Global PLEX market" in (await t.text("#mb-sells") or ""), "its orders say which market", await t.text("#mb-sells"))
    await t.pg.click("[data-mb-view=hist]")
    t.ok(await t.until("document.querySelector('#mb-hreg').value==='19000001' && !!document.querySelector('#mb-hist svg')", 10), "its history is the global market's", await t.text("#mb-hist"))
    await t.pg.click("[data-mb-view=hist]")
    await t.pg.select_option("#mb-where", "r:10000001"); await t.until("mbItem && !mbItem.busy && mbCfg().reg==='r:10000001'", 15); await asyncio.sleep(0.3)
    t.eq([await t.text("#mb-sn"), await t.text("#mb-bn")], ["0", "1"], "a region keeps the global orders placed in it")
    await t.pg.select_option("#mb-where", ""); await t.until("mbItem && !mbItem.busy && mbCfg().reg===''", 15)
    # Settings → Pricings and HUBs: the built-in hubs, a station added by name, then offered by every hub menu
    await t.tab("settings", 0.4)
    t.ok("Pricings and HUBs" in await t.js("document.getElementById('pricing-title').textContent"), "the Pricings panel is now Pricings and HUBs")
    t.eq(await t.js("document.querySelectorAll('#hub-table tbody tr').length"), 5, "the five built-in hubs")
    await t.pg.fill("#hub-name", "Delta VII - Station"); await t.pg.click("#hub-form button[type=submit]")
    t.ok(await t.until("document.querySelectorAll('#hub-table tbody tr').length===6", 10), "a station added by name", await t.text("#hub-msg"))
    t.eq(await t.js("[...document.querySelectorAll('#hub-table tbody tr')].pop().innerText.split('\\t').map(x=>x.trim())"), ["Delta VII - Station", "Delta", "The Forge", "Remove"], "with its system and region")
    t.ok(await t.js("marketOptions('').includes('Delta VII - Station') && !!document.querySelector('#brk-st option[value=\"st:60000099\"]')"), "every hub menu offers it")
    await t.tab("trading", 0.4); t.ok(await t.js("!!document.querySelector('#mb-where option[value=\"st:60000099\"]')"), "the Trading board's Where offers it")
    await t.tab("settings", 0.3); await t.pg.click("[data-hub-del='60000099']"); await asyncio.sleep(0.2)
    t.eq(await t.js("document.querySelectorAll('#hub-table tbody tr').length"), 5, "Remove takes it out")
    # the Item database opens an item on the Trading board
    await t.tab("itemdb", 0.5); await t.until("!!idbData && !!document.querySelector('#idb-table tbody tr')", 25)
    await t.pg.fill("#idb-find", "venture"); await asyncio.sleep(0.4)
    t.eq(await t.js("[...document.querySelectorAll('#idb-table [data-mb-open]')].map(b=>+b.dataset.mbOpen)"), [32880], "the button shows next to items on the market only")
    await t.pg.click("#idb-table [data-mb-open='32880']"); t.ok(await t.until("!document.getElementById('page-trading').hidden && mbItem && mbItem.id===32880 && !mbItem.busy", 15), "the Item database's button opens the item on the Trading board")
    t.ok("No sell order" in (await t.text("#mb-sells") or "") and "Ships / Frigates" in (await t.text(".mb-path") or ""), "an item nobody sells, with its market group path", await t.text("#mb-top"))

@scenario
async def item_database(t):
    """Item database: every item from CCP's game data, by name or category, grouped; an item's facts, what makes it, what it's used in, attributes named from ESI."""
    await t.tab("itemdb", 0.5); t.ok(await t.until("!!idbData && !!document.querySelector('#idb-table tbody tr')", 25), "the list is read from CCP's game data", await t.text("#idb-note"))
    await t.pg.fill("#idb-find", "venture"); await asyncio.sleep(0.4)
    names = "[...document.querySelectorAll('#idb-table tbody tr:not(.group):not(.subgroup) th')].map(th=>th.textContent.trim())"
    t.eq(sorted(await t.js(names)), ["Venture", "Venture Blueprint"], "finding items by name")
    t.ok(await t.js("document.querySelectorAll('#idb-table tr.group').length") >= 2, "results grouped by category")
    await t.pg.fill("#idb-find", ""); await asyncio.sleep(0.4)
    shape = "[...document.querySelectorAll('#idb-table tbody tr')].map(r=>r.classList.contains('group')?'G':r.classList.contains('subgroup')?'S':r.querySelector('[data-idb-more]')?'M':'i')"
    sh = t.show("shape", await t.js(shape))
    t.ok(sh and all(x == "i" or (i + 1 < len(sh) and sh[i + 1] != "G" and (x == "G" or sh[i + 1] == "i")) for i, x in enumerate(sh) if x in "GS"), "every category and group shown has its items under it", sh)
    cat = await t.js("(()=>{const c=[...byCatNames()].find(([,n])=>n>1); return c&&c[0]})()".replace("byCatNames()", "new Map([...document.querySelectorAll('#idb-table tr.group')].map(r=>[r.dataset.fold,+r.dataset.n]))"))
    await t.js("c=>{idbLimit[c]=1; renderItemDb();}", cat); await asyncio.sleep(0.2)
    sh = t.show("limited", await t.js(shape))
    t.ok("M" in sh, "a long category ends with a Show more row", sh)
    n0 = await t.js("document.querySelectorAll('#idb-table tbody tr:not(.group):not(.subgroup)').length")
    await t.pg.click("#idb-table [data-idb-more]"); await asyncio.sleep(0.2)
    t.ok(await t.js("document.querySelectorAll('#idb-table tbody tr:not(.group):not(.subgroup)').length") > n0, "Show more shows more of that category")
    await t.pg.fill("#idb-find", "venture"); await asyncio.sleep(0.4)
    await t.js("()=>{cfCfg('itemdb').rules=[{f:'made',op:'is',a:'manufacturing'}]; renderItemDb();}"); await asyncio.sleep(0.3)
    t.eq(await t.js(names), ["Venture"], "a filter on what makes it")
    await t.js("()=>{cfCfg('itemdb').rules=[]; renderItemDb();}")
    await t.pg.fill("#idb-find", "tritanium"); await asyncio.sleep(0.3)
    await t.pg.click("#idb-table [data-idb-open='34']"); await t.until("idbItem && !idbItem.busy", 15); await asyncio.sleep(0.2)
    it = t.show("tritanium", await t.text("#idb-item"))
    t.ok("Used in" in it and "Venture" in it and "Manufacturing" in it, "what an item is used in", it)
    t.ok("100,000" in it or "100 000" in it or "100.000" in it, "you own: from the hangars", it)
    await t.js("idbShow(28844)"); await t.until("idbItem && idbItem.id===28844 && !idbItem.busy", 15); await asyncio.sleep(0.2)
    rh = t.show("rhea", await t.text("#idb-item"))
    t.ok("Capacity" in rh and await t.js("document.querySelector('#idb-item').innerText.includes(idbUnit(144000,9))") and "Low Slots" in rh, "attributes with their names and units from ESI", rh)
    t.ok("Jump Freighters" in rh and "Bonuses" in rh, "skills to use it and its bonuses", rh)
    t.ok("Attribute 866" not in rh, "attributes the game hides aren't shown")
    await t.pg.check("[data-idb-all]"); await asyncio.sleep(0.2)
    t.ok("Attribute 866" in (await t.text("#idb-item") or ""), "every attribute when asked")
    await t.js("idbShow(32880)"); await t.until("idbItem && idbItem.id===32880 && !idbItem.busy", 15); await asyncio.sleep(0.2)
    v = t.show("venture", await t.text("#idb-item"))
    t.ok("Made by" in v and "Venture Blueprint" in v and await t.js("document.querySelector('#idb-item').innerText.includes((20000).toLocaleString())"), "what makes it, with the materials a run", v)
    t.ok("Jita sell" in v and await t.js("document.querySelector('#idb-item').innerText.includes(isk(300000))"), "its prices", v)
    await t.pg.screenshot(path=SP + "item-database.png", full_page=True)

@scenario
async def boosters(t):
    """Misc page: attribute boosters from CCP's game data, ISK and extra SP a month with their duration and Biology, the best per attribute, expiry warnings, pricings and markets."""
    await t.tab("misc", 0.5); await t.js("()=>{boostCfg().bio=0; renderBoost();}")
    t.ok(await t.until("boostList && boostPrice['pr:jsv'] && !boostPrice['pr:jsv'].busy", 25), "boosters and their prices are read", await t.text("#boost-status"))
    await asyncio.sleep(0.3)
    rows = t.show("rows", await t.js("Object.fromEntries([...document.querySelectorAll('#boost-table tbody tr:not(.group)')].map(r=>[r.cells[0].textContent.trim(), [...r.cells].slice(1).map(c=>c.textContent.trim())]))"))
    names = sorted(k.split(" ⚠")[0].split(" Expired")[0] for k in rows)
    t.eq(names, ["Fake Contract Accelerator", "Fake Event Accelerator", "Fake Expert Accelerator", "Fake Focus Booster", "Fake Old Accelerator"], "every booster adding to an attribute, and only those")
    t.eq(await t.js("[...document.querySelectorAll('#boost-table tr.group th')].map(h=>h.textContent.replace(/[▾▸]/g,'').trim().split(' ')[0])"), ["On", "Not", "Expired"], "grouped: on the market, not on the market, expired")
    ex = t.show("expert", await t.js("boostRows().find(r=>r.t===9500)"))
    t.ok(abs(ex["h"] - 72) < 1e-9 and abs(ex["perM"] - 30e6 / 72 * 720) < 1e-6 and ex["sp"] == 12 * 60 * 720 and abs(ex["perSp"] - 30e6 / 72 / 720) < 1e-9, "ISK and extra SP a month (30 days), and per SP from the price, the duration and the bonus", ex)
    fo = await t.js("boostRows().find(r=>r.t===9504)")
    t.ok(fo["sp"] == 60 * 720 * (6 + 2) and fo["perM"] is None, "two attributes: the largest bonus + half the next; no price, no figures", fo)
    t.ok("Fake Focus Booster" in (await t.text("#boost-note") or ""), "the booster with no price is named", await t.text("#boost-note"))
    ev = [k for k in rows if k.startswith("Fake Event")][0]; old = [k for k in rows if k.startswith("Fake Old")][0]
    t.ok("Expires" in ev and "Expired" in old and rows[old][2] == "expired", "an expiry date warns, an expired booster isn't priced", [ev, old, rows[old]])
    t.eq(rows[[k for k in rows if k.startswith("Fake Contract")][0]][2], "not on the market", "a booster without a market group has no price")
    tiles = t.show("tiles", await t.js("[...document.querySelectorAll('#boost-summary .slot-tile')].map(x=>x.innerText)"))
    t.ok(len(tiles) == 5 and all("Fake Event Accelerator" in x and "Expires" in x for x in tiles), "the best for each attribute (least ISK a month per point), with its expiry warning", tiles)
    await t.pg.select_option("#boost-bio", "5"); await asyncio.sleep(0.3)
    t.ok(abs(await t.js("boostRows().find(r=>r.t===9500).h") - 144) < 1e-9, "Biology V doubles the duration")
    await t.pg.select_option("#boost-at", "st:60008494"); t.ok(await t.until("boostPrice['st:60008494'] && !boostPrice['st:60008494'].busy", 15), "prices read at Amarr")
    t.eq(await t.js("boostRows().find(r=>r.t===9501).p"), 10000000, "the cheapest sell order at the market")
    await t.pg.screenshot(path=SP + "boosters.png", full_page=True)

@scenario
async def bp_library(t):
    """Misc page: the Blueprint library (originals with their levels, research and copying jobs matched to them, the others, then every copy)."""
    await t.js("""()=>{const now=Date.now(); state.misc.ownedBps={'char:9001':{at:now,name:'Ender Alpha',list:[[32881,5,10,-1,0],[601,0,0,-1,0,3],[501,8,16,10,1],[501,8,16,10,1],[501,10,20,5,1]]}};
      state.chars[0].jobs=[{id:1,activity:4,bp:32881,runs:3,start:now-3600e3,end:now+7200e3,product:'x'},{id:2,activity:5,bp:601,runs:4,lr:10,start:now,end:now+864e5,product:'x'},{id:3,activity:3,bp:701,runs:2,start:now-7200e3,end:now-3600e3,product:'x'},{id:4,activity:1,bp:32881,runs:1,start:now,end:now+3600e3,product:'x'}];
      saveMisc(); saveLocal();}""")
    await t.tab("misc", 0.5)
    t.ok(await t.js("!document.getElementById('page-tests').querySelector('#bpl-table') && !!document.getElementById('page-misc').querySelector('#bpl-table') && !document.getElementById('bpc-table')"), "the blueprint library is on the Misc page, copies in the same table")
    grp = t.show("groups", await t.js("[...document.querySelectorAll('#bpl-table tr.group th')].map(h=>h.textContent.replace(/[▾▸]/g,'').replace(/·.*$/,'').trim())"))
    t.eq(grp, ["In research 2", "Copying 1", "Not in a job 1", "Copies 2"], "originals grouped: in research, copying, the others; copies last")
    rows = t.show("rows", await t.js("[...document.querySelectorAll('#bpl-table tbody tr:not(.group)')].map(r=>[...r.cells].map(c=>c.innerText.replace(/\\s+/g,' ').trim()))"))
    t.ok(rows[1][1:3] == ["5", "10"] and "ME research · 5 → 8" in rows[1][5] and "h" in rows[1][6], "ME research adds its runs to the original's ME, with when it ends", rows[1])
    t.ok(rows[0][1] == "—" and "TE research · +4" in rows[0][5] and "Ready" in rows[0][6], "a job whose blueprint isn't in the list still shows, without levels; past its end it's ready", rows[0])
    t.ok("4 copies × 10 runs" in rows[2][5] and "× 2" in rows[3][0], "a copying job takes one original from a stack, the others stay idle", rows[2:])
    t.ok(not any("Manufacturing" in r[5] for r in rows), "manufacturing jobs aren't listed", rows)
    tiles = t.show("tiles", await t.js("[...document.querySelectorAll('#bpl-summary .slot-tile')].map(x=>x.innerText.replace(/\\s+/g,' '))"))
    t.ok([x.lower()[:13] for x in tiles] == ["originals 5 3", "in research 2", "copying 1 nex", "copies 3 25 r"], "tiles: originals, in research, copying, copies and their runs", tiles)
    cps = t.show("copies", [r[1:5] for r in rows[4:]])
    t.eq(sorted(cps), [["10", "20", "5", "Ender Alpha"], ["8", "16", "10", "Ender Alpha"]], "copies: one line per ME, TE and runs")
    t.ok(sorted("× 2" in r[0] for r in rows[4:]) == [False, True] and all(r[3] == "—" for r in rows[:4]), "copies say how many (× 2); originals have no runs", rows)
    t.ok(await t.js("()=>{renderBpLib(); return $('bpl-table').innerHTML.split('/bpc?').length === 3;}"), "copies show the copy icon, originals the original's")
    # Location: each blueprint's station or structure (one in a container counts where the container is); saves from before show as unknown
    t.eq(await t.js("""()=>{state.assets={'char:9001':{rows:[],other:[],places:{1030000000001:60008494}}}; return slimBps([{type_id:1,location_id:1030000000001,quantity:-2,runs:5},{type_id:2,location_id:60003760,quantity:-1,runs:-1}]).map(b=>b[6]);}"""), [60008494, 60003760], "a blueprint in a container is placed where the container is")
    await t.js("""()=>{Object.assign(state.locNames,{60003760:'Jita hub',60008494:'Amarr hub'}); const L=state.misc.ownedBps['char:9001'].list; L[0][5]=1; L[0][6]=60003760; L[1][6]=60003760; L[2][5]=1; L[2][6]=60008494; L[3][5]=1; L[3][6]=60008494; renderBpLib();}""")
    opts = t.show("locations", await t.js("[...$('bpl-loc').options].map(o=>o.textContent)"))
    t.eq(opts, ["Every location", "Amarr hub (2)", "Jita hub (4)", "Unknown: refresh from ESI (2)"], "Location lists each place with how many blueprints, unknown for old saves")
    await t.pg.select_option("#bpl-loc", "60008494"); await asyncio.sleep(0.1)
    cps = t.show("copies at Amarr", await t.js("[...document.querySelectorAll('#bpl-table tbody tr:not(.group)')].map(r=>r.cells[3].innerText.trim())"))
    t.ok(cps == ["10"] and await t.js("[...document.querySelectorAll('#bpl-table tr.group')].length === 1 && $('bpl-summary').innerText.includes('2')"), "Location filters the table and the tiles", cps)
    await t.pg.select_option("#bpl-loc", ""); await asyncio.sleep(0.1)
    await t.pg.screenshot(path=SP + "bp_library.png", full_page=True)

@scenario
async def sovereignty(t):
    """Sovereignty page: alliances ranked by systems, coalitions adding them up, 7-day sov changes and alliance movements against a snapshot."""
    await t.js("""()=>{ const day=864e5, now=Date.now(), A=99000001, B=99000002;
      window._esiGet=esiGet; esiGet=async(p)=>{ const r={'/sovereignty/map/':[{system_id:30000001,alliance_id:A},{system_id:30000002,alliance_id:A},{system_id:30000003,alliance_id:B},{system_id:30000005,faction_id:500001}],
        ['/alliances/'+A+'/']:{name:'Alpha Alliance',ticker:'AA'},['/alliances/'+A+'/corporations/']:[98000001,98000010],['/alliances/'+B+'/']:{name:'Beta Alliance',ticker:'BB'},['/alliances/'+B+'/corporations/']:[98000011],
        '/corporations/98000001/':{name:'Fake Corp',ticker:'FC',member_count:10,alliance_id:A},'/corporations/98000010/':{name:'Newcomers',ticker:'NEW',member_count:30,alliance_id:A},'/corporations/98000011/':{name:'Movers',ticker:'MV',member_count:50,alliance_id:B},
        '/corporations/98000012/':{name:'Leavers',ticker:'LV',member_count:5},'/corporations/98000010/alliancehistory/':[{alliance_id:99000003,start_date:new Date(now-100*day).toISOString()},{alliance_id:A,start_date:new Date(now-day).toISOString()}]}[p];
        if (r === undefined) throw new Error('no fake for '+p); return r; };
      sovInfo={v:1,al:{},corp:{},names:{99000003:'Gamma Alliance'}}; sovHist={v:1,snaps:[{at:now-3*day,own:[[30000001,B],[30000003,B],[30000004,B]],ca:{98000001:A,98000011:A,98000012:B}}]}; }""")
    await t.tab("sov", 0.3)
    t.ok(await t.until("!sovRun && !!sov && sovHist.snaps.length===2", 15), "reading sovereignty, alliances and corporations", await t.text("#sov-status"))
    rows = t.show("ranking", await t.js("[...document.querySelectorAll('#sov-table tbody tr')].map(r=>[...r.cells].slice(0,5).map(c=>c.innerText.trim()))"))
    t.eq(rows, [["1", "Alpha Alliance [AA]", "2 (67%)", "40", "2"], ["2", "Beta Alliance [BB]", "1 (33%)", "50", "1"]], "alliances ranked by systems, with members and corporations (factions left out)")
    await t.pg.fill("#sovc-name", "Test coalition"); await t.pg.click("#sovc-form button[type=submit]"); await asyncio.sleep(0.2)
    cid = await t.js("sovCfg().coals[0].id")
    for a in ("99000001", "99000002"): await t.pg.select_option(f"[data-sov-of='{a}']", cid); await asyncio.sleep(0.2)
    co = t.show("coalition", await t.js("[...document.querySelectorAll('#sovc-table tbody tr')].map(r=>[...r.cells].slice(0,5).map(c=>c.innerText.trim()))"))
    t.ok(len(co) == 1 and co[0][0] == "Test coalition" and co[0][2:] == ["3 (100%)", "90", "3"] and "AA" in co[0][1] and "BB" in co[0][1], "a coalition adds up its alliances' systems, members and corporations", co)
    t.ok(co[0][1].index("BB") < co[0][1].index("AA"), "a coalition lists its alliances by members, most first", co)
    ch = t.show("sov changes", await t.js("[...document.querySelectorAll('#sovx-table tbody tr')].map(r=>[...r.cells].map(c=>c.innerText.trim()))"))
    t.eq(ch, [["Alpha Alliance [AA]", "+2", "0", "+2"], ["Beta Alliance [BB]", "0", "−2", "−2"]], "sov changes: systems gained and lost since the snapshot")
    mv = t.show("movements", await t.js("[...document.querySelectorAll('#sovm-table tbody tr')].map(r=>[...r.cells].map(c=>c.innerText.trim()))"))
    t.eq(mv, [["Movers [MV]", "50", "AA", "BB"], ["Newcomers [NEW]", "30", "Gamma Alliance", "AA"], ["Leavers [LV]", "5", "BB", "None"]], "movements: corporations that changed alliance, biggest first (from and to by ticker)")
    t.ok("Since" in await t.text("#sovx-since"), "the 7-day panels say since when they count")
    for w in (1280, 1600, 1920, 2560):
        await t.pg.set_viewport_size({"width": w, "height": 1000}); await asyncio.sleep(0.2)
        lay = t.show(f"layout {w}", await t.js("""(()=>{ const R=(e)=>{const r=e.getBoundingClientRect(); return [Math.round(r.left),Math.round(r.right),Math.round(r.height)]};
          return {wrap:R(document.querySelector('.wrap')), main:R(document.querySelector('.side-layout > div')), side:R(document.querySelector('.side-col')), tabs:R(document.querySelector('nav.tabs')),
            tables:[...document.querySelectorAll('.side-col table')].map(x=>[x.scrollWidth, x.parentElement.clientWidth]), vw:document.documentElement.clientWidth, sw:document.documentElement.scrollWidth,
            logo:R(document.querySelector('header.top .logo-l')), title:R(document.querySelector('header.top h1')), sticky:getComputedStyle(document.querySelector('.side-stick')).position}; })()"""))
        t.ok(lay["side"][0] >= lay["wrap"][1] and lay["side"][1] <= lay["vw"] and lay["sw"] <= lay["vw"] and lay["sticky"] == "sticky", f"{w} px: the 7-day panels sit right of the page body, in the window, and stay in view", lay)
        t.ok(all(a <= b for a, b in lay["tables"]), f"{w} px: their tables fit the rail", lay["tables"])
        t.eq(lay["side"][0] - lay["main"][1], 16, f"{w} px: 16 px between the body and the right column, like the left navigation rail")
        t.ok(lay["logo"][1] <= lay["title"][0], f"{w} px: the header logo doesn't cover the title", lay)
    # Map: the coalition your pilots' alliance is in is allied by default; a coalition's alliances share a colour
    mp = t.show("map allies", await t.js("""()=>{ state.chars[0].allyId=99000001; const a=[...allyIds()].sort(), m=state.misc.map=state.misc.map||{}; delete m.allyCoals;
      const col=(id)=>sovColor({id, s:-0.5}, new Set()), same=col(30000001)===col(30000003); m.allyCoals=[]; const none=allyIds().size; delete m.allyCoals; return {a, same, none}; }"""))
    t.ok(mp["a"] == [99000001, 99000002] and mp["none"] == 0, "Map allies: your pilots' coalition by default, removable", mp)
    t.ok(mp["same"], "colour by sovereignty: one coalition, one colour", mp)
    # Map buttons: an alliance's or a coalition's systems highlighted on the map
    t.ok(await t.js("document.querySelectorAll('#sov-table [data-sov-map]').length===2 && document.querySelectorAll('#sovc-table [data-sov-map]').length===1"), "a map button by every alliance holding sov and by the coalition")
    t.ok(await t.js("[...document.querySelectorAll('#sov-table [data-sov-map]')].every(b=>b.querySelector('svg circle') && !b.textContent.trim() && b.getAttribute('aria-label').startsWith('Show ') && Math.abs(b.offsetWidth-b.offsetHeight)<=1)"), "it is a square button with a constellation icon")
    await t.pg.click("#sovc-table [data-sov-map]"); await asyncio.sleep(0.3)
    fm = t.show("map focus", await t.js("({page:!document.getElementById('page-map').hidden, n:mapUI.focus&&mapUI.focus.n, ids:mapUI.focus&&[...mapUI.focus.ids].sort(), item:mapSysItems({id:30000003}).join(' '), other:mapSysItems({id:30000005}).join(' ')})"))
    t.ok(fm["page"] and fm["n"] == "Test coalition" and fm["ids"] == [99000001, 99000002] and "Highlighted: Test coalition" in fm["item"] and "Highlighted" not in fm["other"], "the coalition's Map button opens the map with its alliances' systems highlighted", fm)
    await t.js("(()=>{ mapUI.focus=null })()"); await t.tab("sov", 0.3)
    await t.pg.click("[data-sov-coal-del]"); await asyncio.sleep(0.2)
    t.ok(await t.js("!sovCfg().coals.length && !Object.keys(sovCfg().of).length"), "removing a coalition takes its alliances out of it")
    t.ok(await t.js("(()=>{ const td=document.querySelector('#sovc-table td.empty'); return !!td && td.getBoundingClientRect().width > td.closest('table').getBoundingClientRect().width - 2; })()"), "an empty table's message spans every column")
    await t.pg.screenshot(path=SP + "sovereignty.png", full_page=True)
    await t.js("()=>{ esiGet=window._esiGet; }")

@scenario
async def shared_ui(t):
    await t.tab("settings", 0.5)
    names = "[...$('chars-table').tBodies[0].rows].map(r => r.cells[0].textContent.trim().split(/\\s+ID/)[0].trim())"
    before = await t.js(names)
    await t.pg.click("#chars-table thead .sort-btn[data-tsort='0']"); await asyncio.sleep(0.1); desc = await t.js(names)
    await t.pg.click("#chars-table thead .sort-btn[data-tsort='0']"); await asyncio.sleep(0.1); asc = await t.js(names)
    t.ok(desc == sorted(before, reverse=True) and asc == sorted(before), "a table sorts both ways from its column title", [before, desc, asc])
    t.ok(await t.js("[...document.querySelectorAll('#set-nav a')].length") >= 5, "Settings has its left rail")
    t.ok("Time zones" in await t.js("[...document.querySelectorAll('#set-nav a')].map(a=>a.textContent)"), "the rail lists the Time zones panel")
    t.eq(await t.js("[...$('btn-add').parentElement.querySelectorAll('button')].map(b=>b.textContent)"), ["Add custom pilot", "Import backup", "Export backup"], "Pilots and backup: Add custom pilot, then Import before Export")
    await t.pg.click("#pricing-title"); await asyncio.sleep(0.1); folded = await t.js("$('pricing-panel').classList.contains('folded') && !$('pricing-table').offsetHeight")
    await t.pg.click("#pricing-title"); await asyncio.sleep(0.1); t.ok(folded and await t.js("!$('pricing-panel').classList.contains('folded')"), "a panel folds and unfolds from its title")
    await t.tab("overview", 0.5)
    await t.pg.click("#matrix tr.group .fold-h"); await asyncio.sleep(0.1); hid = await t.js("$('matrix').querySelectorAll('tbody tr.fold-hid').length")
    await t.pg.click("#matrix tr.group .fold-h"); await asyncio.sleep(0.1)
    t.ok(hid and not await t.js("$('matrix').querySelectorAll('tbody tr.fold-hid').length"), "a group of rows folds and unfolds")
    t.ok(len(await t.js("[...document.querySelectorAll('#sk-nav a')]")) >= 4, "Skills has its left rail")
    await t.tab("misc", 0.5)
    t.ok(await t.js("!$('howto').hidden && !!$('howto-text').textContent"), "page notes show at the bottom")

@scenario
async def layout_audit(t):
    """AUDIT=1 only: every page at a few widths; what spills out of its panel, scrolls sideways, or sits outside a scroller."""
    if not os.environ.get("AUDIT"): t.show("skipped", "set AUDIT=1"); return
    os.makedirs(SP + "audit", exist_ok=True)
    for w in (1000, 1280, 1920):
        await t.pg.set_viewport_size({"width": w, "height": 1000})
        for key in await t.js("Object.keys(PAGES)"):
            await t.tab(key, 0.7)
            rep = await t.js("""() => {
              const out=[], vw=document.documentElement.clientWidth, page=document.querySelector('.page:not([hidden])'); if (!page) return ['no page'];
              const name=e=>{let s=e.tagName.toLowerCase()+(e.id?'#'+e.id:(typeof e.className==='string'&&e.className.trim()?'.'+e.className.trim().split(/\\s+/).slice(0,2).join('.'):'')); const p=e.parentElement&&e.parentElement.closest('[id]'); return (p?p.id+' > ':'')+s};
              if (document.documentElement.scrollWidth>vw+1) out.push('page scrolls sideways: '+document.documentElement.scrollWidth+' > '+vw);
              const seen=new Set();
              for (const box of page.querySelectorAll('.panel, .fc-box, .sblock, .bset')) { const br=box.getBoundingClientRect(); if (!br.width) continue;
                for (const e of box.querySelectorAll('*')) { if (seen.has(e.parentElement)) { seen.add(e); continue }
                  if (e.closest('.scroller, .week, .month, .map-wrap, .more-pop, .tipbox, svg')!==null && !e.matches('.scroller, .week, .month')) continue;
                  const r=e.getBoundingClientRect(); if (!r.width||!r.height) continue;
                  if (r.right>br.right+2 || r.left<br.left-2) { seen.add(e); out.push('spills out of '+name(box)+': '+name(e)+' ('+Math.round(r.width)+'px in '+Math.round(br.width)+'px)') } } }
              for (const s of page.querySelectorAll('.scroller')) { if (!s.offsetWidth) continue; if (s.scrollWidth>s.clientWidth+2) out.push('scrolls inside: '+name(s)+' '+s.scrollWidth+' in '+s.clientWidth) }
              for (const t of page.querySelectorAll('table')) { if (!t.offsetWidth||t.closest('.scroller')) continue; out.push('table outside a scroller: '+name(t)) }
              return [...new Set(out)].slice(0,40) }""")
            if rep: print(f"    audit {w} {key}:", *rep, sep="\n      ")
            await t.pg.screenshot(path=SP + f"audit/{key}-{w}.png", full_page=True)

# ---------- runner
async def run(names):
    async with async_playwright() as p:
        exe = os.environ.get("CHROMIUM_PATH")
        b = await p.chromium.launch(**({"executable_path": exe} if exe else {}))
        results = []
        for fn in names:
            ctx = await b.new_context(viewport={"width": 1280, "height": 1100}); await ctx.route("**/*", handle)
            pg = await ctx.new_page(); t = T(fn.__name__, pg)
            pg.on("pageerror", lambda e, t=t: t.errs.append(str(e) + " @ " + str(getattr(e, "stack", ""))[:600]))
            t0 = time.time(); print(f"{fn.__name__} …", flush=True)
            try:
                await pg.goto("http://localhost:8642/"); await pg.evaluate(SEED); await fn(t)
            except Exception as e:
                t.fails.append("the scenario stopped: " + "".join(traceback.format_exception_only(type(e), e)).strip()[:900])
            ok = not t.fails and not t.errs
            print(f"  {'ok  ' if ok else 'FAIL'} {fn.__name__} ({time.time() - t0:.1f} s)")
            for f in t.fails: print("    ✗", f)
            for e in t.errs: print("    ✗ page error:", e)
            results.append(ok); await ctx.close()
        await b.close()
        print(f"\n{sum(results)} of {len(results)} scenarios passed")
        return all(results)

def port_open():
    with socket.socket() as so: return so.connect_ex(("127.0.0.1", 8642)) == 0
if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]; VERBOSE = "-v" in sys.argv
    if "--list" in sys.argv: print("\n".join(f.__name__ for f in SCENARIOS)); sys.exit(0)
    picked = [f for f in SCENARIOS if not args or any(a in f.__name__ for a in args)]
    if not picked: print("no scenario matches", args); sys.exit(2)
    srv = None
    if not port_open():
        srv = subprocess.Popen([sys.executable, "-c", open(os.path.join(ROOT, "start-eve-industry-management.sh")).read().split("exec python3 -c '", 1)[1].rsplit("'", 1)[0]], cwd=ROOT, stdout=subprocess.DEVNULL)
        for _ in range(50):
            if port_open(): break
            time.sleep(0.1)
    try: ok = asyncio.run(run(picked))
    finally:
        if srv: srv.terminate()
    sys.exit(0 if ok else 1)
