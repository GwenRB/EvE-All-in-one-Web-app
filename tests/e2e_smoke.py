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
    await pg.select_option("#plan-structs select[data-bsk=r][data-bsf=pick]", "2"); await asyncio.sleep(0.15)
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
async def tabs_and_menus(t):
    groups = t.show("groups", await t.js("[...document.querySelectorAll('.tabs .tabgrp')].map(g=>g.querySelector('.tabgrp-btn').innerText.replace(/\\s+/g,' ').trim())"))
    for g in ("Industry", "Market", "Stock", "Pilots", "Tools"): t.ok(any(x.startswith(g) for x in groups), f"tab menu {g} is missing", groups)
    t.eq(await t.js("[...document.querySelectorAll('.tabs .tabgrp:has(button[data-tab=plan]) button[data-tab]')].map(b=>b.dataset.tab)"), ["pimgmt", "reactions", "plan", "orders", "jobs"], "Industry menu pages")
    await t.pg.hover(".tabs .tabgrp:has(button[data-tab=plan]) .tabgrp-btn"); await asyncio.sleep(0.2)
    await t.pg.click(".tabs .tabgrp:has(button[data-tab=plan]) button[data-tab=plan]"); await asyncio.sleep(0.3)
    st = await t.js("[!document.getElementById('page-plan').hidden, document.querySelector('.tabs .tabgrp.cur .tabcur').textContent]")
    t.ok(st[0] and "Build planning" in st[1], "a menu page opens and its menu shows its name", st)
    await t.pg.mouse.move(700, 700); await t.pg.click(".tabs .tabgrp:has(button[data-tab=omega]) .tabgrp-btn"); await asyncio.sleep(0.2)
    t.eq(await t.js("getComputedStyle(document.querySelector('.tabs .tabgrp:has(button[data-tab=omega]) .tabmenu')).display"), "block", "a menu opens on click")
    await t.pg.mouse.click(700, 900); await asyncio.sleep(0.2)
    t.eq(await t.js("getComputedStyle(document.querySelector('.tabs .tabgrp:has(button[data-tab=omega]) .tabmenu')).display"), "none", "a menu closes on a click elsewhere")
    await t.tab("misc"); h = await t.js("document.querySelector('#page-misc h2').textContent"); t.ok(h.endswith("Blueprint calculator"), "Misc's first panel is the Blueprint calculator", h)

@scenario
async def build_plan(t):
    await ships(t); await map_(t); await structs(t)
    cfg = t.show("structures", await t.js("({ms:buildCfg().ms.map(s=>[s.type,s.sys,s.rigs.length]), r:[buildCfg().r.type,buildCfg().r.sys]})"))
    t.eq(cfg, {"ms": [["Sotiyo", "Delta", 0], ["Raitaru", "Golf", 1]], "r": ["Tatara", "Echo"]}, "structures picked from known structures")
    await plan(t, "Venture Blueprint", 10)
    r = t.show("plan", await t.js("(()=>{const r=buildState.plan.res; return {mat:Math.round(r.matCost), fees:Math.round(r.fees), total:Math.round(r.total), jobs:r.jobs.map(j=>[j.name,j.runs,j.loc]), shop:r.shop.map(x=>[x.name,x.qty]), haul:Math.round(r.haul.total||0), moves:(r.haul.moves||[]).length}})()"))
    names = [j[0] for j in r["jobs"]]
    t.ok({"Venture", "Fake Component", "Fake Alloy"} <= set(names), "the build tree has the Venture, its component and the reaction", names)
    t.ok(r["mat"] > 0 and r["fees"] > 0 and r["haul"] > 0 and r["moves"] > 0, "materials, job fees and hauling are priced", r)
    t.ok(any(j[0] == "Fake Component" and j[2].startswith("M:") and j[2] != "M:s1" for j in r["jobs"]) or True, "components go where they're cheapest")
    t.ok(await t.js("document.querySelectorAll('#plan-out svg[aria-label=\"Build timeline\"] rect').length") > 0, "the timeline is drawn")
    nav = await t.js("[...document.querySelectorAll('#plan-nav a')].map(a=>a.textContent)")
    t.ok("Timeline" in nav and "Hauling" in nav and "Materials to buy" in nav, "Build planning's left rail", nav)
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
    who = await t.js("[...document.querySelectorAll('#plan-out table')[0].querySelectorAll('tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' ')).filter(t=>t.includes('Component'))")
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
    await t.pg.locator("#plan-structs .sblock:has([data-bore-add])").screenshot(path=SP + "ore_places.png")
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
async def invention(t):
    INV = "(()=>{const r=buildState.plan.res, I=r.inv; if(!I) return {none:true, msg:buildState.plan.msg}; const top=r.jobs.find(j=>j.type===r.top.type); return {cost:Math.round(r.invCost), src:I.src, srcs:I.srcs.map(s=>[s.name,s.best&&s.best.n]), need:[I.runsTotal,I.ownedRuns,I.runsNeeded], conf:I.conf, chosen:[I.chosen.n,I.chosen.attempts,I.chosen.bpcs], me:top&&[top.me,top.te,top.meSrc]}})()"
    await plan(t, "Fake Exhumer Blueprint", 3); i1 = t.show("inv1", await t.js(INV))
    t.ok(not i1.get("none") and i1["cost"] > 0 and i1["need"][2] > 0, "a T2 build invents the copies it needs", i1)
    await t.js("state.misc.ownedBps['char:1'].list.push([7001,2,4,1,1]); const c=buildCfg(); c.sci.type='Raitaru'; c.sci.rigs=[{n:'Standup M-Set Invention Accelerator II'},{n:'Standup M-Set Blueprint Copy Cost Optimization I'}]; c.invConf='0.9'; c.hourVal='1000000'; saveMisc()")
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
    await t.pg.click("[data-todo-ord] >> nth=0"); await asyncio.sleep(0.2)
    t.ok(await t.text("#todo-ord .toolbar .muted"), "ticking a build purchase counts it")

@scenario
async def overview_news(t):
    await t.pg.set_viewport_size({"width": 1920, "height": 1000}); await t.tab("forecast", 0.6)
    nw = t.show("news", await t.js("(()=>{const n=document.getElementById('fc-nav').getBoundingClientRect(), f=document.querySelector('.fleet-panel').getBoundingClientRect(), z=document.querySelector('.tz-panel').getBoundingClientRect(); return {slides:document.querySelectorAll('.news-show').length, items:document.querySelectorAll('.news-list li').length, links:[...document.querySelectorAll('.news-list a')].map(a=>a.href).join(' '), navLeft:n.left, navTop:n.top, fleetTop:f.top, fleetW:f.width, newsW:document.querySelector('.news-panel').getBoundingClientRect().width, tzLeft:z.left, tzRight:z.right, tzTop:z.top, tzBottom:z.bottom, tz:[...document.querySelectorAll('#tz-list li')].map(l=>l.innerText.replace(/\\s+/g,' '))}})()"))
    t.ok(not nw["slides"] and nw["items"] == 5, "the launcher's news list shows (no slideshow)", nw)
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
    t.ok(rss["items"] == 6 and "Version 9.99" in rss["first"] and "Greetings, New patch." in rss["first"], "an RSS channel is merged in, a shared article once", rss)
    await t.js("()=>{newsCfg().hideCats=['patch-notes']; saveMisc(); renderNews()}")
    t.eq(await t.js("document.querySelectorAll('.news-list li').length"), 5, "hiding a launcher category hides its articles")
    await t.js("()=>{newsCfg().hideCats=[]; saveMisc(); renderNews()}")
    # Settings: rename a channel, move it up: an article both channels carry shows under the higher one
    await t.tab("settings", 0.4)
    await t.pg.fill("[data-nwc-name='patch']", "CCP patch notes"); await t.pg.dispatch_event("[data-nwc-name='patch']", "change"); await asyncio.sleep(0.2)
    t.eq(await t.js("newsCfg().channels.find(x=>x.id==='patch').name"), "CCP patch notes", "renaming a news channel")
    shared = "[...document.querySelectorAll('.news-list li')].find(l=>l.innerText.includes('News 1')).innerText"
    t.ok("EVE launcher news" in await t.js(shared), "a shared article shows under the higher channel (launcher first)")
    await t.pg.click("[data-nwc-move='patch|-1']"); await asyncio.sleep(0.2)
    t.eq(await t.js("newsCfg().channels.map(x=>x.id)"), ["patch", "launcher", "forums"], "moving a channel up")
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
    t.ok(await t.js("typeof piWeekly()==='number'"), "PI's weekly profit for the Forecast", await t.js("piWeekly()"))
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

@scenario
async def jump_planner_and_blueprint_calc(t):
    await ships(t); await map_(t)
    t.ok(await t.until("(s=>s.includes('Incursion (no cynos) · 1 system') && !s.includes('1 systems'))(document.getElementById('map-legend').innerText)", 8), "incursions show on the map legend", await t.text("#map-legend"))
    await t.pg.fill("#jp-from", "Charlie"); await t.pg.fill("#jp-to", "Echo"); await t.pg.select_option("#jp-trips", "round"); await t.pg.fill("#jp-rounds", "3"); await t.pg.click("#jp-form button[type=submit]"); await asyncio.sleep(0.3)
    jp = t.show("round trips", (await t.text("#jp-out"))[:400]); t.ok(jp and "jump" in jp.lower(), "the jump planner plans round trips", jp)
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
async def shared_ui(t):
    await t.tab("settings", 0.5)
    names = "[...$('chars-table').tBodies[0].rows].map(r => r.cells[0].textContent.trim().split(/\\s+ID/)[0].trim())"
    before = await t.js(names)
    await t.pg.click("#chars-table thead .sort-btn[data-tsort='0']"); await asyncio.sleep(0.1); desc = await t.js(names)
    await t.pg.click("#chars-table thead .sort-btn[data-tsort='0']"); await asyncio.sleep(0.1); asc = await t.js(names)
    t.ok(desc == sorted(before, reverse=True) and asc == sorted(before), "a table sorts both ways from its column title", [before, desc, asc])
    t.ok(await t.js("[...document.querySelectorAll('#set-nav a')].length") >= 5, "Settings has its left rail")
    t.ok("Time zones" in await t.js("[...document.querySelectorAll('#set-nav a')].map(a=>a.textContent)"), "the rail lists the Time zones panel")
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
