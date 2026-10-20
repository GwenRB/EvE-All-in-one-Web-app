"""End-to-end smoke test for EVE Industry Management (single-file app).

Every network call (ESI, EVE Ref, CCP's static data, images) is answered by the fake data
below, so no account or internet access is needed. The script walks through most pages,
prints what they show (look for regressions in the printed values), saves screenshots to
tests/out/, and exits with status 1 if the page threw any JavaScript error.

Run:  python3 tests/e2e_smoke.py        (starts the launcher itself if port 8642 is free)
Needs: pip install playwright && playwright install chromium   (or set CHROMIUM_PATH)
"""
import asyncio, json, os, sys, subprocess, socket, time
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
SP=os.path.join(HERE,"out")+os.sep; os.makedirs(SP, exist_ok=True)   # screenshots
FIX=os.path.join(HERE,"fixtures")+os.sep
def dd(d): return {str(k):{"attribute_id":k,"value":v} for k,v in d.items()}
NAMES={32881:"Venture Blueprint",501:"Fake Component Blueprint",601:"Fake Alloy Reaction Formula",4314:"Nitrogen Fuel Block Blueprint",999:"Dominix Blueprint",
       32880:"Venture",500:"Fake Component",600:"Fake Alloy",4051:"Nitrogen Fuel Block",34:"Tritanium",35:"Pyerite",16633:"Hydrocarbons",3380:"Industry",3392:"Mechanical Engineering",45746:"Reactions",30000142:"Jita"}
BPS={32881:{"manufacturing":{"materials":{"34":{"type_id":34,"quantity":20000},"500":{"type_id":500,"quantity":10},"4051":{"type_id":4051,"quantity":3}},"products":{"32880":{"type_id":32880,"quantity":1}},"time":3600,"required_skills":{"3380":1}}},
     501:{"manufacturing":{"materials":{"35":{"type_id":35,"quantity":100},"600":{"type_id":600,"quantity":5}},"products":{"500":{"type_id":500,"quantity":1}},"time":600,"required_skills":{"3392":1}}},
     601:{"reaction":{"materials":{"16633":{"type_id":16633,"quantity":100}},"products":{"600":{"type_id":600,"quantity":200}},"time":10800,"required_skills":{"45746":1}}},
     4314:{"manufacturing":{"materials":{"35":{"type_id":35,"quantity":10}},"products":{"4051":{"type_id":4051,"quantity":40}},"time":300,"required_skills":{"3380":1}}}}
TYPES={32880:{"group_id":237,"category_id":6,"produced_by_blueprints":{"32881":{"blueprint_type_id":32881,"blueprint_activity":"manufacturing"}},"packaged_volume":2500},
       500:{"group_id":334,"category_id":17,"produced_by_blueprints":{"501":{"blueprint_type_id":501,"blueprint_activity":"manufacturing"}},"volume":1},
       600:{"group_id":429,"category_id":4,"produced_by_blueprints":{"601":{"blueprint_type_id":601,"blueprint_activity":"reaction"}},"volume":0.2},
       4051:{"group_id":1136,"category_id":4,"produced_by_blueprints":{"4314":{"blueprint_type_id":4314,"blueprint_activity":"manufacturing"}},"volume":5},
       34:{"group_id":18,"category_id":4,"volume":0.01},35:{"group_id":18,"category_id":4,"volume":0.01},16633:{"group_id":427,"category_id":4,"volume":0.05},
       32881:{"group_id":105,"category_id":9},501:{"group_id":105,"category_id":9},601:{"group_id":1888,"category_id":24},4314:{"group_id":105,"category_id":9}}
PRICE={34:4.0,35:9.0,16633:500.0,4051:15000.0,32880:300000.0,500:20000.0,600:3000.0}
LYm=9.4607e15
SYS={30000001:("Alpha",0,0,0,0.9,20000001),30000002:("Bravo",3,0,1,0.6,20000001),30000003:("Charlie",6,0,-2,0.3,20000002),30000004:("Delta",9,0,4,0.0,20000002),30000005:("Echo",14,0,0,-0.4,20000003),30000006:("Foxtrot",20,0,3,-0.8,20000003),30000007:("Golf",5,0,8,0.04,20000002)}
CON={20000001:10000001,20000002:10000001,20000003:10000002}
LINKS=[(30000001,30000002),(30000002,30000003),(30000003,30000004),(30000004,30000005),(30000005,30000006),(30000003,30000007)]
for sid,v in SYS.items(): NAMES[sid]=v[0]
NAMES.update({10000001:"The Forge",10000002:"Delve",20000001:"Con A",20000002:"Con B",20000003:"Con C",28844:"Rhea",29029:"Jump Freighters",20526:"Caldari Freighter",21611:"Jump Drive Calibration",21610:"Jump Fuel Conservation"})
TYPES[28844]={"group_id":902,"category_id":6,"required_skills":{"29029":1},"dogma_attributes":dd({866:17888,867:5,868:10000,38:144000,12:3,1137:0}),"traits":{"role_bonuses":{"2":{"bonus":90,"bonus_text":{"en":"reduction to effective distance traveled for jump fatigue"}}},"types":{"29029":{"2":{"bonus":10,"bonus_text":{"en":"reduction in jump fuel requirement"}}}}}}
TYPES[1319]={"dogma_attributes":dd({149:1.275})}
PRICE[17888]=600.0
NAMES.update({7000:"Fake Exhumer",7001:"Fake Exhumer Blueprint",20410:"Datacore - Mechanical Engineering",20411:"Datacore - Caldari Starship Engineering",3398:"Caldari Starship Engineering",21791:"Caldari Encryption Methods",34201:"Accelerant Decryptor",34202:"Attainment Decryptor",34203:"Augmentation Decryptor",34204:"Parity Decryptor",34205:"Process Decryptor",34206:"Symmetry Decryptor",34207:"Optimized Attainment Decryptor",34208:"Optimized Augmentation Decryptor"})
BPS[32881]["invention"]={"materials":{"20410":{"type_id":20410,"quantity":2},"20411":{"type_id":20411,"quantity":2}},"products":{"7001":{"type_id":7001,"quantity":1,"probability":0.3}},"time":60000,"required_skills":{"3392":1,"3398":1,"21791":1}}
BPS[7001]={"manufacturing":{"materials":{"32880":{"type_id":32880,"quantity":1},"500":{"type_id":500,"quantity":5},"34":{"type_id":34,"quantity":1000}},"products":{"7000":{"type_id":7000,"quantity":1}},"time":7200,"required_skills":{"3380":5}}}
TYPES[7000]={"group_id":543,"category_id":6,"produced_by_blueprints":{"7001":{"blueprint_type_id":7001,"blueprint_activity":"manufacturing"}},"packaged_volume":3750}
TYPES[7001]={"group_id":105,"category_id":9,"produced_by_blueprints":{"32881":{"blueprint_type_id":32881,"blueprint_activity":"invention"}}}
NAMES.update({7100:"Fake Subsystem",7101:"Fake Subsystem Blueprint",7201:"Intact Fake Relic",7202:"Wrecked Fake Relic"})
TYPES[7100]={"group_id":954,"category_id":32,"produced_by_blueprints":{"7101":{"blueprint_type_id":7101,"blueprint_activity":"manufacturing"}},"volume":40}
TYPES[7101]={"group_id":973,"category_id":9,"produced_by_blueprints":{"7201":{"blueprint_type_id":7201,"blueprint_activity":"invention"},"7202":{"blueprint_type_id":7202,"blueprint_activity":"invention"}}}
TYPES[7201]={"group_id":971,"category_id":34}; TYPES[7202]={"group_id":971,"category_id":34}
BPS[7201]={"invention":{"materials":{"20410":{"type_id":20410,"quantity":3},"20411":{"type_id":20411,"quantity":3}},"products":{"7101":{"type_id":7101,"quantity":20,"probability":0.26}},"time":3600,"required_skills":{"3392":1,"3398":1,"21791":1}}}
BPS[7202]={"invention":{"materials":{"20410":{"type_id":20410,"quantity":3},"20411":{"type_id":20411,"quantity":3}},"products":{"7101":{"type_id":7101,"quantity":3,"probability":0.14}},"time":3600,"required_skills":{"3392":1,"3398":1,"21791":1}}}
BPS[7101]={"manufacturing":{"materials":{"34":{"type_id":34,"quantity":5000},"500":{"type_id":500,"quantity":2}},"products":{"7100":{"type_id":7100,"quantity":1}},"time":3600,"required_skills":{"3380":1}}}
for i,(k,pm,me,te,rn) in enumerate([(34201,1.2,2,10,1),(34202,1.8,-1,4,4),(34203,0.6,-2,2,9),(34204,1.5,1,-2,3),(34205,1.1,3,6,0),(34206,1.0,1,8,2),(34207,1.9,1,-2,2),(34208,0.9,2,0,7)]):
    TYPES[k]={"group_id":1304,"category_id":35,"dogma_attributes":dd({1112:pm,1113:me,1114:te,1124:rn})}; PRICE[k]=500000.0
PRICE[20410]=100000.0; PRICE[20411]=120000.0; PRICE[7000]=200000000.0
BPS[32881]["research_material"]={"time":210}
# reaction fixtures
NAMES.update({9001:"Titanium Chromide Reaction Formula",9002:"Silicon Diborite Reaction Formula",46204:"Titanium Carbide Reaction Formula",9004:"Unrefined Thing Reaction Formula",
  16654:"Titanium Chromide",16658:"Silicon Diborite",16671:"Titanium Carbide",16638:"Titanium",16641:"Chromium",16636:"Silicon",16635:"Evaporite Deposits",4312:"Oxygen Fuel Block",9005:"Unrefined Thing"})
for k,g in {16654:428,16658:428,16671:429,16638:427,16641:427,16636:427,16635:427,4312:1136,9005:428}.items(): TYPES[k]={"group_id":g,"category_id":4,"volume":0.01 if g==429 else 0.05 if g!=1136 else 5}
for k in (9001,9002,46204,9004): TYPES[k]={"group_id":1888,"category_id":24}
TYPES[16654]["produced_by_blueprints"]={"9001":{"blueprint_type_id":9001,"blueprint_activity":"reaction"}}
TYPES[16658]["produced_by_blueprints"]={"9002":{"blueprint_type_id":9002,"blueprint_activity":"reaction"}}
TYPES[9005]["produced_by_blueprints"]={"9004":{"blueprint_type_id":9004,"blueprint_activity":"reaction"}}
TYPES[16671]["produced_by_blueprints"]={"46204":{"blueprint_type_id":46204,"blueprint_activity":"reaction"}}
mk=lambda mats,prod,q:{"reaction":{"materials":{str(t):{"type_id":t,"quantity":n} for t,n in mats},"products":{str(prod):{"type_id":prod,"quantity":q}},"time":10800,"required_skills":{"45746":1}}}
BPS[9001]=mk([(16638,100),(16641,100),(4312,5)],16654,200)
BPS[9002]=mk([(16636,100),(16635,100),(4312,5)],16658,200)
BPS[46204]=mk([(16654,100),(16658,100),(4312,5)],16671,10000)
BPS[9004]=mk([(16638,100),(4312,5)],9005,100)
PRICE.update({2398:400.0,2393:400.0,3645:400.0,3693:9000.0,3695:9000.0,3691:9000.0,9838:9000.0,2869:1500000.0,2868:1400000.0,2867:1300000.0,2312:9000.0,2317:9000.0,2329:9000.0,3689:9000.0,3775:9000.0,9840:9000.0,9842:9000.0,2321:9000.0,2327:9000.0,3697:9000.0,57456:9000.0,57465:5000000.0,57468:3000000.0,30370:1500.0,30373:3000.0,57452:50000.0,4051:20000.0,16638:1500.0,16641:1200.0,16636:900.0,16635:700.0,4312:20000.0,16654:2400.0,16658:1900.0,16671:60.0,9001:20000000.0,9002:20000000.0,46204:30000000.0})
async def handle(route):
    u=route.request.url
    if "developers.eveonline.com" in u and not u.startswith("http://localhost"): return await route.abort()
    if u.startswith("http://localhost:8642/proxy") and "developers.eveonline.com" in u:
        tgt=parse_qs(urlparse(u).query)["url"][0]
        if tgt.endswith("latest.jsonl"): return await route.fulfill(status=200, headers={"Content-Type":"text/plain"}, body='{"_key":"sde","buildNumber":3100000,"releaseDate":"2026-10-01"}\n')
        return await route.fulfill(status=200, headers={"Content-Type":"application/zip"}, body=open(FIX+"sde.zip","rb").read())
    if u.startswith("http://localhost:8642"): return await route.continue_()
    if "fonts." in u or "images.evetech" in u: return await route.abort()
    def j(o, status=200, pages=None):
        h={"Access-Control-Allow-Origin":"*","Content-Type":"application/json","Access-Control-Expose-Headers":"X-Pages"}
        if pages: h["X-Pages"]=str(pages)
        return route.fulfill(status=status, headers=h, body=json.dumps(o))
    path=urlparse(u).path.replace("/latest","")
    if u.rstrip("/").endswith("everef.net/blueprints"): return await j(list(BPS)+[999])
    if "everef.net/blueprints/" in u:
        bid=int(u.split("/blueprints/")[1].strip("/").split("?")[0]); return await j({"blueprint_type_id":bid,"activities":BPS.get(bid,{})})
    if "everef.net/groups/428" in u: return await j({"message":"Forbidden"},403)
    if "/universe/groups/428/" in u: return await j({"group_id":428,"name":"Intermediate Materials","types":[16654,16658,9005]})
    if "everef.net/groups/429" in u: return await j({"group_id":429,"name":{"en":"Composite"},"type_ids":[16671]})
    if "everef.net/categories/24" in u: return await j({"message":"Forbidden"},403)
    if "/universe/categories/24/" in u: return await j({"category_id":24,"name":"Reaction","groups":[1888,1890]})
    if "everef.net/groups/1888" in u: return await j({"group_id":1888,"name":{"en":"Composite Reaction Formulas"},"type_ids":[9001,9002,46204,9004]})
    if "everef.net/groups/1890" in u: return await j({"message":"Forbidden"},403)
    if "/universe/groups/1890/" in u: return await j({"group_id":1890,"name":"Biochemical Reaction Formulas","types":[9999]})
    if "/markets/10000002/history" in u: return await j([{"date":"2026-10-%02d"%d,"volume":5000000,"average":1} for d in range(1,31)])
    if "everef.net/types/" in u:
        tid=int(u.split("/types/")[1].strip("/").split("?")[0]); return await j({"type_id":tid,"name":{"en":NAMES.get(tid,f"T{tid}")},**TYPES.get(tid,{})})
    if "universe/names" in u: ids=json.loads(route.request.post_data); return await j([{"id":i,"name":NAMES.get(i,f"T{i}")} for i in ids])
    if "universe/ids" in u:
        nm=json.loads(route.request.post_data); low={x.lower() for x in nm}
        sysl=[{"id":k,"name":v[0]} for k,v in SYS.items() if v[0].lower() in low]+([{"id":30000142,"name":"Jita"}] if "jita" in low else [])
        inv=[{"id":28844,"name":"Rhea"}] if "rhea" in low else []
        inv+=[{"id":k,"name":NAMES[k]} for k in range(34201,34209) if NAMES[k].lower() in low]
        inv+= [{"id":1319,"name":"Expanded Cargohold II"}] if "expanded cargohold ii" in low else []
        inv+= [{"id":k,"name":v} for k,v in {32880:"Venture",34:"Tritanium",35:"Pyerite",16633:"Hydrocarbons"}.items() if v.lower() in low]
        return await j({"systems":sysl,"inventory_types":inv})
    if "everef.net/solar_systems" in u:
        tail=u.split("/solar_systems")[1].split("?")[0].strip("/")
        if not tail: return await j(list(SYS))
        sid=int(tail); n,x,y,z,sec,c=SYS[sid]; nb=[b for a,b in LINKS if a==sid]+[a for a,b in LINKS if b==sid]
        return await j({"name":{"en":n},"position":{"x":x*LYm,"y":y*LYm,"z":z*LYm},"position2_d":{"x":x*LYm,"y":z*LYm},"security_status":sec,"constellation_id":c,"region_id":CON[c],"stargates_to_system_ids":nb})
    if "/incursions" in path: return await j([{"constellation_id":20000003,"infested_solar_systems":[30000006],"staging_solar_system_id":30000006,"state":"established"}])
    if "/sovereignty/map" in path: return await j([])
    if "/universe/systems/" in path:
        sid=int(path.split("/")[3]); return await j({"security_status":SYS.get(sid,("",0,0,0,0.9,0))[4]})
    if "/universe/systems/30000142" in path: return await j({"security_status":0.95})
    if "/industry/systems" in path: return await j([{"solar_system_id":30000142,"cost_indices":[{"activity":"manufacturing","cost_index":0.05},{"activity":"reaction","cost_index":0.02}]},{"solar_system_id":30000004,"cost_indices":[{"activity":"manufacturing","cost_index":0.03}]},{"solar_system_id":30000005,"cost_indices":[{"activity":"reaction","cost_index":0.01}]}])
    if "markets/prices" in path: return await j([{"type_id":k,"average_price":v,"adjusted_price":v*0.9} for k,v in PRICE.items()])
    if "/markets/10000002/orders" in path:
        tid=int(parse_qs(urlparse(u).query)["type_id"][0]); p=PRICE.get(tid,0)
        return await j([{"location_id":60003760,"price":p*1.1},{"location_id":60003760,"price":p},{"location_id":1,"price":p*0.5}] if p else [], pages=1)
    return await j([],404)
async def main():
    async with async_playwright() as p:
        exe=os.environ.get("CHROMIUM_PATH")
        b=await p.chromium.launch(**({"executable_path":exe} if exe else {}))
        ctx=await b.new_context(viewport={"width":1280,"height":1100}); await ctx.route("**/*", handle)
        pg=await ctx.new_page(); errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)+" @ "+str(getattr(e,"stack",""))[:600]))
        await pg.goto("http://localhost:8642/")
        await pg.evaluate("""()=>{state.chars=[{id:'a',name:'Ender Alpha',esiId:9001,skills:{'Caldari Starship Engineering':4,'Caldari Encryption Methods':3,'Industry':5,'Mechanical Engineering':4,'Reactions':3,'Mass Production':2,'Jump Freighters':4,'Jump Fuel Conservation':5,'Jump Drive Calibration':4}, fatigue:{expire:Date.now()+45*60000, at:Date.now()}},{id:'b',name:'Ender Beta',skills:{'Industry':3,'Mechanical Engineering':1}},{id:'g',name:'Solo Gamma',skills:{'Reactions':5}}];
          state.misc.ownedBps={'char:1':{at:Date.now(),name:'Ender Alpha',list:[[32881,10,20,-1,0],[501,8,16,10,1],[601,0,0,-1,0]]}};
          state.assets={'char:9001':{at:Date.now(),owner:'Ender Alpha',rows:[{t:28844,loc:60003760,h:'Hangar',q:1},{t:34,loc:60000002,h:'Hangar',q:100000},{t:35,loc:60000001,h:'Hangar',q:5000},{t:16633,loc:60000003,h:'Hangar',q:50}]}};
          state.misc.locSys={60003760:30000001,60000002:30000004,60000001:30000002,60000003:30000001}; state.locNames={...state.locNames,60000002:'Delta station',60000001:'Bravo station',60000003:'Alpha station'};
          state.misc.structs={'1':{id:'1',name:'Delta - Sotiyo',system:30000004,typeName:'Sotiyo',src:['corp']},'2':{id:'2',name:'Echo - Tatara',system:30000005,typeName:'Tatara',src:['corp']}}; saveLocal(); saveMisc(); render();}""")
        await pg.evaluate("()=>{state.forecast.history=[{d:'2026-10-10',isk:1e9,stock:0},{d:'2026-10-11',isk:2e9,stock:0},{d:'2026-10-12',isk:3e9,stock:0}]; saveForecast(); renderForecast();}")
        await pg.click("#fc-history [data-fc-hdel='2026-10-11']"); await pg.wait_for_timeout(100)
        h1=await pg.evaluate("state.forecast.history.map(x=>x.d)")
        await pg.click("#fc-hclear"); await pg.click("#fc-hclear"); await pg.wait_for_timeout(100)
        print("history:", h1, "->", await pg.evaluate("state.forecast.history.map(x=>x.d)"))
        print("tabs:", await pg.evaluate("[...document.querySelectorAll('.tabs button')].map(b=>b.textContent).join(' | ')"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=plan]').click()")
        for i in range(20):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!!bp.names && document.querySelectorAll('#plan-names option').length>0"): break
        print("datalist:", await pg.evaluate("[...document.querySelectorAll('#plan-names option')].map(o=>o.value+' '+o.textContent)"))
        print("skillcheck list:", await pg.evaluate("[...document.querySelectorAll('#bp-names option')].slice(0,2).map(o=>o.value+' '+o.textContent)"))
        await pg.fill("#plan-bp","Venture Blueprint"); await pg.dispatch_event("#plan-bp","input")
        print("own:", await pg.inner_text("#plan-own"))
        await pg.fill("#plan-qty","10")
        # load misc ship data and the map first
        await pg.evaluate("document.querySelector('.tabs button[data-tab=misc]').click()")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!miscLoading && state.misc.types && state.misc.types.Rhea && state.misc.types.Rhea.v===MISC_V"): break
        await pg.evaluate("document.querySelector('.tabs button[data-tab=map]').click()"); await pg.click("#map-load")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!!mapData"): break
        await pg.wait_for_timeout(500)
        print("incursion legend:", await pg.evaluate("document.getElementById('map-legend').innerText.includes('incursion')"), await pg.evaluate("incursions && [...incursions.sys]"))
        await pg.fill("#jp-from","Charlie"); await pg.fill("#jp-to","Foxtrot"); await pg.click("#jp-form button[type=submit]"); await pg.wait_for_timeout(200)
        print("to incursion:", (await pg.inner_text("#jp-out"))[:120])
        await pg.fill("#jp-to","Echo"); await pg.select_option("#jp-trips","round"); await pg.fill("#jp-rounds","3"); await pg.click("#jp-form button[type=submit]"); await pg.wait_for_timeout(300)
        print("round trips:", (await pg.inner_text("#jp-out")).replace("\n"," / ")[:600])
        print("waits:", (await pg.inner_text("#jp-out")).split("JUMP")[0][-600:].replace("\n"," / ") if False else await pg.evaluate("(document.querySelector('#jp-out .notice')||{}).innerText||''"))
        print("fatinfo:", await pg.inner_text("#jp-fatinfo"), await pg.evaluate("document.getElementById('jp-fat').value"))
        await pg.locator("#jp").screenshot(path=SP+"jp2.png")
        await pg.evaluate("document.querySelector('.tabs button[data-tab=plan]').click()"); await pg.wait_for_timeout(300)
        print("sys suggestions:", await pg.evaluate("[...document.querySelectorAll('#build-sys option')].slice(0,4).map(o=>o.value+' '+o.textContent)"))
        await pg.select_option("#plan-structs select[data-bsk^='ms:'][data-bsf=pick]","1"); await pg.wait_for_timeout(200)
        await pg.select_option("#plan-structs select[data-bsk=r][data-bsf=pick]","2"); await pg.wait_for_timeout(200)
        await pg.fill("#plan-structs [data-bset='haul.from']","Bravo"); await pg.dispatch_event("#plan-structs [data-bset='haul.from']","change"); await pg.wait_for_timeout(200)
        await pg.click("#ms-add"); await pg.wait_for_timeout(200)
        sk=await pg.evaluate("'ms:'+buildCfg().ms[1].id")
        await pg.select_option(f"#plan-structs select[data-bsk='{sk}'][data-bsf=type]","Raitaru"); await pg.wait_for_timeout(100)
        await pg.fill(f"#plan-structs input[data-bsk='{sk}'][data-bsf=sys]","Golf"); await pg.dispatch_event(f"#plan-structs input[data-bsk='{sk}'][data-bsf=sys]","change"); await pg.wait_for_timeout(100)
        blk=pg.locator(f"#plan-structs .sblock:has([data-bsk='{sk}'])")
        await pg.evaluate("()=>{const c=buildCfg(); c.ms[1].rigs=[{n:'Standup M-Set Advanced Component Manufacturing Material Efficiency II'}]; saveMisc(); renderBuildSettings(true);}"); await pg.wait_for_timeout(200)
        await pg.locator("#plan-structs-panel").screenshot(path=SP+"structs2.png")
        print("cfg:", await pg.evaluate("JSON.stringify({ms:buildCfg().ms,r:buildCfg().r,sci:buildCfg().sci})"))
        await pg.click("#plan-form button[type=submit]")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        r=await pg.evaluate("JSON.stringify({mat:buildState.plan.res&&buildState.plan.res.matCost, fees:buildState.plan.res&&buildState.plan.res.fees, jobs:buildState.plan.res&&buildState.plan.res.jobs.map(j=>[j.name,j.runs,j.me,j.meSrc,Math.round(j.fee)]), shop:buildState.plan.res&&buildState.plan.res.shop.map(x=>[x.name,x.qty,x.price])})")
        print("res:", r, "| msg:", await pg.evaluate("buildState.plan.msg"))
        print("haul moves (gates<=4):", await pg.evaluate("JSON.stringify((buildState.plan.res.haul.moves||[]).map(x=>[x.r.path[0].n+'>'+x.r.path[x.r.path.length-1].n,x.unload.map(i=>i.name).join('+').slice(0,40),x.r.how,Math.round(x.r.cost)]))"), await pg.evaluate("buildState.plan.res.haul.note||''"))
        pass
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        await pg.locator("#plan-out").screenshot(path=SP+"plan_haul.png")
        print("haul moves (no gates):", await pg.evaluate("JSON.stringify((buildState.plan.res.haul.moves||[]).map(x=>[x.r.path[0].n+'>'+x.r.path[x.r.path.length-1].n,x.unload.map(i=>i.name).join('+').slice(0,40),x.r.how,Math.round(x.r.cost)]))"), await pg.evaluate("Math.round(buildState.plan.res.haul.total)"))
        # remove a rig
        await pg.check("#plan-stock"); 
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy && !!buildState.plan.res && !!buildState.plan.res.stockUse"): break
        print("stock:", await pg.evaluate("JSON.stringify(buildState.plan.res.stockUse.items.map(x=>[x.name,x.need,x.fromLocal,x.fromD,x.qty,x.elsewhere.map(e=>e.name+':'+e.q)]))"))
        print("stock box:", (await pg.inner_text("#pl-stock + *")).replace("\n"," / ")[:300] if await pg.evaluate("!!document.getElementById('pl-stock')") else None)
        print("away:", await pg.evaluate("(document.querySelector('#plan-out .notice b')||{}).textContent"), await pg.evaluate("[...document.querySelectorAll('#plan-out .notice span')].map(x=>x.textContent).join(' | ').slice(0,300)"))
        print("nav:", await pg.evaluate("[...document.querySelectorAll('#plan-nav a')].map(a=>a.textContent)"))
        print("timeline rows:", await pg.evaluate("document.querySelectorAll('#plan-out svg[aria-label=\"Build timeline\"] rect').length"), await pg.evaluate("document.querySelector('#plan-out .slot-tile .big-num') && [...document.querySelectorAll('#plan-out .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' ')).filter(t=>/Estimated|Hauling/.test(t))"))
        print("cargo buttons:", await pg.evaluate("[...document.querySelectorAll('#plan-out button.cargo')].slice(0,4).map(b=>b.textContent)"))
        await pg.screenshot(path=SP+"plan_full.png", full_page=True)
        await pg.click("#plan-nav a[data-nav=pl-haul]"); await pg.wait_for_timeout(800)
        print("nav active:", await pg.evaluate("(document.querySelector('#plan-nav a.on')||{}).textContent"))
        await pg.screenshot(path=SP+"plan_nav.png")
        await pg.uncheck("#plan-stock")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        print("jobs where:", await pg.evaluate("JSON.stringify(buildState.plan.res.jobs.map(j=>[j.name,j.where,Math.round(j.rigMe*100)/100]))"))
        print("moves:", await pg.evaluate("JSON.stringify(buildState.plan.res.haul.moves.map(x=>[x.x+'>'+x.y, x.load.map(i=>i.name+'x'+i.qty).join(','), x.unload.map(i=>i.name+'x'+i.qty).join(','), x.r.how]))"))
        k1=await pg.evaluate("'ms:'+buildCfg().ms[1].id")
        n0=await pg.evaluate("buildCfg().ms[1].rigs.length"); await pg.click(f"#plan-structs [data-bsk='{k1}'][data-rigdel='0']"); await pg.wait_for_timeout(300)
        print("rigs:", n0, "->", await pg.evaluate("buildCfg().ms[1].rigs.length"))
        await pg.evaluate("()=>{const c=buildCfg(); c.ms[1].rigs=[{kind:'me',tier:'t2',cover:'advcomp'}]; saveMisc(); rerunBuilds();}")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        await pg.click("#plan-out [data-haul-map]"); await pg.wait_for_timeout(500)
        print("map haul:", await pg.evaluate("JSON.stringify(mapUI.haul)"), await pg.evaluate("!document.getElementById('page-map').hidden"))
        await pg.locator("#map-wrap").screenshot(path=SP+"haulmap.png")
        await pg.evaluate("document.querySelector('.tabs button[data-tab=plan]').click()"); await pg.wait_for_timeout(200)
        # invented item
        await pg.fill("#plan-bp","Fake Exhumer Blueprint"); await pg.fill("#plan-qty","3"); await pg.click("#plan-form button[type=submit]")
        for i in range(40):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        print("inv:", await pg.evaluate("JSON.stringify({cost:buildState.plan.res.invCost, chosen:buildState.plan.res.inv&&buildState.plan.res.inv.chosen.n, rows:buildState.plan.res.inv&&buildState.plan.res.inv.rows.map(r=>[r.n,+(r.prob*100).toFixed(1),r.runsPer,r.bpcs,+r.attempts.toFixed(2),Math.round(r.invCost),Math.round(r.matDelta)]), topJob: buildState.plan.res.jobs[0] && [buildState.plan.res.jobs[0].name, buildState.plan.res.jobs[0].me, buildState.plan.res.jobs[0].meSrc]})"), "| msg:", await pg.evaluate("buildState.plan.msg"))
        async def runplan(name, q):
            await pg.fill("#plan-bp",name); await pg.fill("#plan-qty",str(q)); await pg.click("#plan-form button[type=submit]")
            for i in range(60):
                await pg.wait_for_timeout(300)
                if await pg.evaluate("!buildState.plan.busy"): break
        INV = "JSON.stringify((()=>{const r=buildState.plan.res, I=r.inv; if(!I) return {none:true, msg:buildState.plan.msg}; const top=r.jobs.find(j=>j.type===r.top.type); return {cost:Math.round(r.invCost), src:I.src, srcs:I.srcs.map(s=>[s.name,s.best&&s.best.n,Math.round(s.best&&s.best.net)]), need:[I.runsTotal,I.ownedRuns,I.runsNeeded], conf:I.conf, chosen:[I.chosen.n,I.chosen.attempts,I.chosen.bpcs,Math.round(I.chosen.hours*10)/10], rInv:I.rInv, me:top&&[top.me,top.te,top.meSrc]}})())"
        print("inv1:", await pg.evaluate(INV))
        print("tl1:", await pg.evaluate("JSON.stringify(sciParts(buildState.plan.res, []).map(p=>[p.j.type,p.runs,Math.round(p.dur)]))"))
        await pg.evaluate("state.misc.ownedBps['char:1'].list.push([7001,2,4,1,1]); const c=buildCfg(); c.sci.type='Raitaru'; c.sci.rigs=[{n:'Standup M-Set Invention Accelerator II'},{n:'Standup M-Set Blueprint Copy Cost Optimization I'}]; c.invConf='0.9'; c.hourVal='1000000'; saveMisc()")
        await runplan("Fake Exhumer Blueprint", 3)
        print("inv2:", await pg.evaluate(INV))
        print("tl2:", await pg.evaluate("JSON.stringify(sciParts(buildState.plan.res, []).map(p=>[p.j.type,p.runs,Math.round(p.dur)]))"))
        print("inv2 ui:", await pg.evaluate("document.getElementById('pl-inv') && document.getElementById('pl-inv').parentElement.innerText.match(/(\\d+ runs? to build[^.]*\\.)/)"), await pg.evaluate("[...document.querySelectorAll('[data-bset=invConf] option')].map(o=>o.textContent)"))
        await pg.evaluate("const c=buildCfg(); c.invConf='avg'; saveMisc()")
        await runplan("Fake Subsystem Blueprint", 30)
        print("inv3:", await pg.evaluate(INV))
        await pg.evaluate("document.getElementById('pl-inv').scrollIntoView()"); await pg.wait_for_timeout(300)
        y=await pg.evaluate("document.getElementById('pl-inv').getBoundingClientRect().top+scrollY")
        await pg.screenshot(path=SP+"plan_inv3.png", full_page=True, clip={"x":0,"y":y-10,"width":1280,"height":700})
        await pg.select_option("[data-bset=relic]","7202"); 
        for i in range(60):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        print("inv4:", await pg.evaluate(INV))
        await pg.evaluate("const c=buildCfg(); c.relic='auto'; c.sci.rigs=[]; c.hourVal=''; saveMisc(); state.misc.ownedBps['char:1'].list.pop()")
        await runplan("Fake Exhumer Blueprint", 3)
        await pg.screenshot(path=SP+"plan_inv.png", full_page=True)
        print("overflow:", await pg.evaluate("(()=>{const W=document.documentElement.clientWidth;return [document.documentElement.scrollWidth, W, [...document.querySelectorAll('#page-plan *')].filter(e=>e.getBoundingClientRect().right>W+2).slice(-8).map(e=>e.tagName+'.'+e.className+'#'+e.id+' '+Math.round(e.getBoundingClientRect().right))]})()"))
        await pg.fill("#plan-bp","Venture Blueprint"); await pg.fill("#plan-qty","10"); await pg.click("#plan-form button[type=submit]")
        for i in range(40):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        print("formula cell:", await pg.evaluate("[...document.querySelectorAll('#plan-out table')[0].querySelectorAll('tbody tr')].map(r=>r.children[4].innerText).join(' | ')"))
        print("jobs rig:", await pg.evaluate("JSON.stringify(buildState.plan.res.jobs.map(j=>[j.name,j.me,j.rigMe]))"))
        print("who table:", await pg.evaluate("[...document.querySelectorAll('#plan-out table')[0].querySelectorAll('tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
        await pg.screenshot(path=SP+"plan.png", full_page=True)
        # toggle fuel block to build
        await pg.click("#plan-out [data-btoggle='4051']")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        print("after toggle jobs:", await pg.evaluate("buildState.plan.res.jobs.map(j=>j.name+' x'+j.runs)"))
        # override pilot
        await pg.select_option("#plan-out select[data-bwho='500']", "b"); await pg.wait_for_timeout(200)
        print("override:", await pg.evaluate("[...document.querySelectorAll('#plan-out table')[0].querySelectorAll('tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' ')).filter(t=>t.includes('Component'))"))
        # quotation
        await pg.evaluate("document.querySelector('.tabs button[data-tab=misc]').click()"); await pg.wait_for_timeout(200)
        await pg.fill("#quote-bp","Venture Blueprint"); await pg.click("#quote-form button[type=submit]")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.quote.busy"): break
        await pg.fill("#quote-margin","20"); await pg.dispatch_event("#quote-margin","change"); await pg.wait_for_timeout(200)
        print("quote:", (await pg.inner_text("#quote-out")).replace("\n"," / ")[:700])
        await pg.screenshot(path=SP+"quote.png", full_page=True)
        await pg.evaluate("document.querySelector('.tabs button[data-tab=notes]').click()"); await pg.fill("#notes-text","Hello notes"); await pg.wait_for_timeout(700)
        print("notes:", await pg.evaluate("localStorage.getItem('eve-industry-notes')"), await pg.inner_text("#notes-status"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=planets]').click()"); await pg.fill("#pi-gap","3"); await pg.dispatch_event("#pi-gap","change")
        print("gap:", await pg.evaluate("state.misc.pi"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=reactions]').click()")
        for i in range(40):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!!(state.misc.rxnData && state.misc.rxnData.f && document.querySelector('#rx-pick table'))"): break
        await pg.fill("#rx-setup [data-rx=sys]","Delta"); await pg.dispatch_event("#rx-setup [data-rx=sys]","change"); await pg.wait_for_timeout(1500)
        print("rx source:", await pg.evaluate("JSON.stringify([state.misc.rxnData.src, state.misc.rxnData.build, state.misc.rxnData.note||null])"), await pg.evaluate("[...document.querySelectorAll('#rx-setup p.muted')].map(p=>p.innerText).find(t=>/Recipes/.test(t))"))
        print("rx formulas:", await pg.evaluate("state.misc.rxnData.f.map(f=>state.misc.rxnData.names[f.p]+' x'+f.per)"))
        await pg.evaluate("()=>{state.misc.rigData={v:1,at:Date.now(),list:[{n:'Standup L-Set Composite Reactor Efficiency II',size:3,rxn:true,cover:['composite'],me:2.4,te:24,tier:'II',fits:[1406],hi:1,lo:1,nu:1.1},{n:'Standup L-Set Biochemical Reactor Efficiency I',size:3,rxn:true,cover:['biochem'],me:2,te:20,tier:'I',fits:[1406],hi:1,lo:1,nu:1.1},{n:'Standup M-Set Composite Reactor Material Efficiency I',size:2,rxn:true,cover:['composite'],me:2,te:0,tier:'I',fits:[1406],hi:1,lo:1,nu:1.1}]}; renderRx();}")
        await pg.wait_for_timeout(300)
        print("rx rig options:", await pg.evaluate("[...document.querySelectorAll('[data-rx-rigadd] option')].map(o=>o.textContent)"))
        await pg.select_option("[data-rx-rigadd]","Standup L-Set Composite Reactor Efficiency II"); await pg.wait_for_timeout(400)
        await pg.select_option("[data-rx-rigadd]","Standup L-Set Biochemical Reactor Efficiency I"); await pg.wait_for_timeout(400)
        print("rx rigs:", await pg.evaluate("JSON.stringify(rxCfg().rigs)"))
        print("rx tiles:", await pg.evaluate("[...document.querySelectorAll('#rx-setup .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))"))
        print("rx nav:", await pg.evaluate("[...document.querySelectorAll('#rx-nav a')].map(a=>a.textContent)"))
        print("rx rows:", await pg.evaluate("[...document.querySelectorAll('#rx-pick tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
        await pg.fill("[data-rx-n='16671']","2"); await pg.dispatch_event("[data-rx-n='16671']","change"); await pg.wait_for_timeout(500)
        await pg.fill("[data-rx-n='57465']","1"); await pg.dispatch_event("[data-rx-n='57465']","change"); await pg.wait_for_timeout(500)
        print("rx totals:", await pg.evaluate("[...document.querySelectorAll('#rx-pick > .slot-tiles .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))"))
        await pg.click("[data-rx-row='16671'] th"); await pg.wait_for_timeout(300)
        await pg.click("[data-rx-cat='neuro']"); await pg.wait_for_timeout(300)
        print("rx hidden:", await pg.evaluate("JSON.stringify(rxCfg().hideCats)"), await pg.evaluate("[...document.querySelectorAll('#rx-pick > .scroller tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' ')).slice(0,8)"))
        print("rx breakdown:", await pg.evaluate("(document.querySelector('#rx-pick tbody tr td[colspan]')||{}).innerText"))
        print("rx shop:", await pg.evaluate("[...document.querySelectorAll('#rx-shop h3, #rx-shop tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
        print("rx multibuy:", await pg.evaluate("[...document.querySelectorAll('#rx-shop button.cargo')].map(b=>b.dataset.copy)"))
        print("rx react bu:", await pg.evaluate("[...document.querySelectorAll('#rx-react h3, #rx-react tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' ')).slice(0,6)"))
        await pg.click("[data-rx-view=fc]"); await pg.wait_for_timeout(300)
        print("rx react fc:", await pg.evaluate("[...document.querySelectorAll('#rx-react h3, #rx-react tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' ')).slice(0,8)"))
        await pg.click("[data-rx-count^='fc|'] >> nth=0"); await pg.click("[data-rx-count^='fc|'] >> nth=0"); await pg.wait_for_timeout(200)
        print("rx counts:", await pg.evaluate("[...document.querySelectorAll('[data-rx-count]')].map(b=>b.dataset.rxCount+'='+b.textContent)"), await pg.evaluate("[...document.querySelectorAll('#rx-react .toolbar .muted')].map(x=>x.textContent)"))
        print("rx nav2:", await pg.evaluate("[...document.querySelectorAll('#rx-nav a')].map(a=>a.textContent+(a.classList.contains('sub')?'*':''))"))
        await pg.select_option("[data-rx=sellHow]","contract"); await pg.wait_for_timeout(300)
        print("rx sell:", await pg.evaluate("[...document.querySelectorAll('[data-rx=sellHow] option')].map(o=>o.textContent)"), await pg.evaluate("[...document.querySelectorAll('#rx-pick > .slot-tiles .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))[3]"))
        await pg.click("[data-rx=shipIn]"); await pg.wait_for_timeout(300)
        await pg.fill("[data-rx=deliv]","Alpha"); await pg.dispatch_event("[data-rx=deliv]","change"); await pg.wait_for_timeout(2500)
        print("rx haul jf:", await pg.evaluate("JSON.stringify(rxHaulInfo && {mode:rxHaulInfo.mode, rt:Math.round(rxHaulInfo.rt||0), cap:rxHaulInfo.cap, note:rxHaulInfo.note, ship:rxHaulInfo.ship})"), await pg.evaluate("[...document.querySelectorAll('#rx-pick > .slot-tiles .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))[2]"))
        await pg.select_option("[data-rx=haulMode]","courier"); await pg.wait_for_timeout(1500)
        print("rx haul courier:", await pg.evaluate("JSON.stringify(rxHaulInfo && {mode:rxHaulInfo.mode, rate:rxHaulInfo.rate})"), await pg.evaluate("[...document.querySelectorAll('#rx-pick > .slot-tiles .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))[2]"))
        print("rx nav3:", await pg.evaluate("[...document.querySelectorAll('#rx-nav a')].map(a=>a.textContent)"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=forecast]').click()"); await pg.wait_for_timeout(600)
        print("dbg:", await pg.evaluate("(()=>{try{const C=state.misc.rxn; return JSON.stringify({picks:C.picks, v:rxD().v, w:rxPlan(rxEnv()).perDay, gone:state.forecast.rxGone, acts:state.forecast.activities.length})}catch(e){return 'ERR '+e.message+' '+e.stack.slice(0,300)}})()"))
        print("fc acts:", await pg.evaluate("document.getElementById('fc-acts').innerText.replace(/\\s+/g,' ')"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=todo]').click()"); await pg.wait_for_timeout(600)
        print("todo:", await pg.evaluate("document.getElementById('todo-rx').innerText.replace(/\\s+/g,' ').slice(0,400)"))
        await pg.click("[data-todo-rx] >> nth=0"); await pg.wait_for_timeout(300)
        print("todo after:", await pg.evaluate("document.querySelector('#todo-rx .toolbar .muted').textContent"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=reactions]').click()"); await pg.wait_for_timeout(500)
        print("rx react:", await pg.evaluate("[...document.querySelectorAll('#rx-react h3, #rx-react tr')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
        await pg.screenshot(path=SP+"rxfull.png", full_page=False)
        print("rx formula icons:", await pg.evaluate("[...document.querySelectorAll('#rx-shop img')].map(i=>i.getAttribute('src')).filter(s=>/bp\\?/.test(s))"))
        await pg.evaluate("()=>{state.chars[0].omegaUntil=Date.now()+3*864e5; state.misc.orders=[{id:'o1',at:Date.now(),name:'Venture',type:32880,qty:2,status:'planned',materials:[{t:34,n:'Tritanium',q:5000,stock:1000,buy:4000,cost:1}],jobs:[]}]; state.misc.cm=[{id:'c1',client:'Bob',created:Date.now(),items:{34:1000,35:50},sends:[{items:{34:400}}]}]; saveMisc();}")
        await pg.evaluate("document.querySelector('.tabs button[data-tab=todo]').click()"); await pg.wait_for_timeout(600)
        print("todo panels:", await pg.evaluate("[...document.querySelectorAll('#page-todo section')].map(s=>(s.hidden?'[hidden] ':'')+s.querySelector('h2').textContent+': '+s.innerText.replace(/\\s+/g,' ').slice(0,220))"))
        await pg.click("[data-todo-ord] >> nth=0"); await pg.wait_for_timeout(300)
        print("todo ord:", await pg.evaluate("document.querySelector('#todo-ord .toolbar .muted').textContent"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=misc]').click()"); await pg.wait_for_timeout(300)
        print("misc first:", await pg.evaluate("document.querySelector('#page-misc h2').textContent"), "tabs:", await pg.evaluate("[...document.querySelectorAll('.tabs button')].some(b=>b.dataset.tab==='wallets')"))
        await pg.set_viewport_size({"width":1920,"height":1000}); await pg.evaluate("document.querySelector('.tabs button[data-tab=forecast]').click()"); await pg.wait_for_timeout(500)
        print("news:", await pg.evaluate("JSON.stringify(document.querySelector('.news-panel').getBoundingClientRect())"), await pg.evaluate("JSON.stringify(document.querySelector('#page-forecast').getBoundingClientRect())"))
        await pg.evaluate("window.scrollTo(0, 2000)"); await pg.wait_for_timeout(500)
        print("news scrolled:", await pg.evaluate("JSON.stringify(document.querySelector('.news-panel').getBoundingClientRect())"), await pg.evaluate("JSON.stringify(document.getElementById('to-top').getBoundingClientRect())"))
        await pg.screenshot(path=SP+"news.png")
        print("fc nav:", await pg.evaluate("[...document.querySelectorAll('#fc-nav a')].map(a=>a.textContent+(a.classList.contains('sub')?'*':''))"), await pg.evaluate("JSON.stringify(document.getElementById('fc-nav').getBoundingClientRect())"), await pg.evaluate("JSON.stringify(document.querySelector('.news-panel').getBoundingClientRect())"))
        await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(200); await pg.screenshot(path=SP+"fcnav.png")
        await pg.evaluate("document.querySelector('.tabs button[data-tab=reactions]').click()"); await pg.wait_for_timeout(500)
        await pg.click("[data-rx-sort='slot']"); await pg.wait_for_timeout(300)
        print("rx sort:", await pg.evaluate("[...document.querySelectorAll('#rx-pick thead th')].map(t=>t.textContent).join(' | ')"), await pg.evaluate("!!document.querySelector('[data-rx=sort]')"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=misc]').click()"); await pg.wait_for_timeout(400)
        await pg.fill("#bc-sys","Delta"); await pg.dispatch_event("#bc-sys","change"); await pg.wait_for_timeout(200)
        await pg.fill("#bc-bp","Venture Blueprint"); await pg.dispatch_event("#bc-bp","input"); await pg.wait_for_timeout(200)
        print("bc own:", await pg.evaluate("[document.getElementById('bc-own').textContent, document.getElementById('bc-me0').value]"))
        await pg.fill("#bc-me0","2"); await pg.fill("#bc-me1","10"); await pg.click("#bc-form button[type=submit]")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!!document.querySelector('#bc-out .slot-tile') || !!document.querySelector('#bc-out .notice')"): break
        print("bc mfg opts:", await pg.evaluate("[...document.querySelectorAll('#bc-mfg option')].map(o=>o.textContent)"))
        await pg.select_option("#bc-mfg", index=1); await pg.wait_for_timeout(1500)
        print("bc out:", await pg.evaluate("document.getElementById('bc-out').innerText.replace(/\\s+/g,' ').slice(0,900)"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=pimgmt]').click()")
        for i in range(40):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!!state.misc.piAt && !piBusy"): break
        await pg.fill("[data-pi-n='2869']","12"); await pg.dispatch_event("[data-pi-n='2869']","change"); await pg.wait_for_timeout(300)
        await pg.fill("[data-pi-n='2867']","2"); await pg.dispatch_event("[data-pi-n='2867']","change"); await pg.wait_for_timeout(300)
        print("pi dbg:", await pg.evaluate("JSON.stringify([jitaCache[2869], jitaCache[3693], state.misc.piAt, piStatus])"))
        print("pi tiles:", await pg.evaluate("[...document.querySelectorAll('#pi-pick .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))"))
        print("pi rows:", await pg.evaluate("[...document.querySelectorAll('#pi-pick tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' ')).slice(0,8)"))
        print("pi setup:", await pg.evaluate("document.getElementById('pi-setup').innerText.replace(/\\s+/g,' ').slice(0,900)"))
        print("pi groups:", await pg.evaluate("[...document.querySelectorAll('#pi-pick tbody tr.group')].map(r=>r.innerText)"))
        await pg.fill("[data-pi=stockDays]","14"); await pg.dispatch_event("[data-pi=stockDays]","change"); await pg.wait_for_timeout(300)
        await pg.check("[data-pi=shipIn]"); await pg.wait_for_timeout(300)
        await pg.fill("[data-pi=deliv]","Alpha"); await pg.dispatch_event("[data-pi=deliv]","change"); await pg.wait_for_timeout(300)
        await pg.fill("[data-pi=planetSys]","Delta"); await pg.dispatch_event("[data-pi=planetSys]","change"); await pg.wait_for_timeout(2500)
        print("pi haul:", await pg.evaluate("JSON.stringify(piHaulInfo && {mode:piHaulInfo.mode, rt:piHaulInfo.rt, note:piHaulInfo.note, same:piHaulInfo.same})"))
        await pg.select_option("[data-pi=haulMode]","courier"); await pg.wait_for_timeout(1500)
        print("pi haul c:", await pg.evaluate("JSON.stringify(piHaulInfo && {mode:piHaulInfo.mode, rate:piHaulInfo.rate, note:piHaulInfo.note})"))
        await pg.select_option("[data-pi=inP]","jsv"); await pg.wait_for_timeout(1500)
        print("pi cfg:", await pg.evaluate("JSON.stringify(state.misc.pi)"))
        print("pi tiles2:", await pg.evaluate("[...document.querySelectorAll('#pi-pick .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))"))
        print("pi shop:", await pg.evaluate("document.getElementById('pi-shop').innerText.replace(/\\s+/g,' ').slice(0,1200)"))
        print("pi out:", await pg.evaluate("document.getElementById('pi-out').innerText.replace(/\\s+/g,' ').slice(0,300)"))
        print("pi batch:", await pg.evaluate("document.getElementById('pi-batch').innerText.replace(/\\s+/g,' ').slice(0,300)"))
        print("pi nav:", await pg.evaluate("[...document.querySelectorAll('#pi-nav a')].map(a=>a.textContent)"), await pg.evaluate("!!document.getElementById('pi-hist')||!!document.getElementById('pi-stock-text')"))
        print("pi weekly:", await pg.evaluate("piWeekly()"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=forecast]').click()"); await pg.wait_for_timeout(800)
        print("fc acts:", await pg.evaluate("JSON.stringify(state.forecast.activities.map(a=>[a.name,a.linked,a.weekly]))"))
        print("pi src:", await pg.evaluate("[PI_SRC, JSON.stringify(PI_HOURLY[2868]), JSON.stringify(PI_HOURLY[2876]), piRecErr]"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=pimgmt]').click()"); await pg.wait_for_timeout(500)
        print("pi rows sde:", await pg.evaluate("[...document.querySelectorAll('#pi-pick tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' '))"), await pg.evaluate("document.getElementById('pi-setup').innerText.match(/Recipes[^\\n]*/)[0]"))
        print("groups:", await pg.evaluate("[...document.querySelectorAll('.tabs .tabgrp')].map(g=>g.querySelector('.tabgrp-btn').innerText.replace(/\\s+/g,' ')+(g.classList.contains('cur')?'*':'')+(g.hidden?'(hidden)':''))"))
        await pg.hover(".tabs .tabgrp:has(button[data-tab=plan]) .tabgrp-btn"); await pg.wait_for_timeout(300); await pg.screenshot(path=SP+"tabs.png", clip={"x":0,"y":0,"width":1400,"height":420})
        await pg.click(".tabs .tabgrp:has(button[data-tab=plan]) button[data-tab=plan]"); await pg.wait_for_timeout(400)
        print("after click:", await pg.evaluate("[!document.getElementById('page-plan').hidden, document.querySelector('.tabs .tabgrp.cur .tabcur').textContent, getComputedStyle(document.querySelector('.tabs .tabgrp:has(button[data-tab=plan]) .tabmenu')).display]"))
        await pg.mouse.move(700,700); await pg.click(".tabs .tabgrp:has(button[data-tab=omega]) .tabgrp-btn"); await pg.wait_for_timeout(200)
        print("click open:", await pg.evaluate("getComputedStyle(document.querySelector('.tabs .tabgrp:has(button[data-tab=omega]) .tabmenu')).display"))
        await pg.mouse.click(700,900); await pg.wait_for_timeout(200)
        print("closed:", await pg.evaluate("getComputedStyle(document.querySelector('.tabs .tabgrp:has(button[data-tab=omega]) .tabmenu')).display"))
        print("top bar:", await pg.evaluate("[...document.querySelectorAll('.tabs > *')].map(x=>x.innerText.replace(/\\s+/g,' '))"), await pg.evaluate("[...document.querySelectorAll('.tabs .tabgrp:has(button[data-tab=plan]) button[data-tab]')].map(b=>b.textContent)"), await pg.evaluate("document.querySelector('header .toolbar').innerText"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=settings]').click()"); await pg.click("#btn-add"); await pg.fill("#add-name","Hand Pilot"); await pg.click("#add-form button[type=submit]"); await pg.wait_for_timeout(300)
        print("added:", await pg.evaluate("state.chars.map(c=>c.name)"), await pg.evaluate("[!!document.querySelector('#page-settings #btn-export'), !!document.querySelector('#page-settings #btn-import')]"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=contracts]').click()"); await pg.wait_for_timeout(200)
        await pg.fill("#cm-client","Bob Trader"); await pg.fill("#cm-goods","Tritanium x100"); await pg.click("#cm-create") if await pg.query_selector("#cm-create") else None; await pg.wait_for_timeout(1500)
        await pg.evaluate("cmRemember('Old Client'); cmRemember('bob'); renderContracts()"); print("cm status:", await pg.evaluate("document.getElementById('cm-status').textContent")); print("clients:", await pg.evaluate("[...document.querySelectorAll('#cm-clients option')].map(o=>o.value)"), await pg.evaluate("state.misc.cmClients"))
        # ---- citadel pricing: no Jita prices written in
        await pg.evaluate("structMarket['1000000000001']={at:Date.now()+1e9,min:new Map([[34,5.5],[2398,300]]),max:new Map([[34,5]])}; structBooks['1000000000001']={at:Date.now()+1e9,sells:new Map([[34,[[5.5,1e9]]]]),buyB:new Map()}; state.misc.pricings=[...(state.misc.pricings||[]),{id:'cX',name:'Cit sell',kind:'cit',sid:'1000000000001',side:'sell'}]; saveMisc()")
        print("priceIn cit:", await pg.evaluate("[priceIn('p:cX',34), priceIn('p:cX',35), priceIn('jsv',35)]"))
        await pg.evaluate("const c=buildCfg(); c.price='p:cX'; saveMisc(); document.querySelector('.tabs button[data-tab=plan]').click()"); await pg.wait_for_timeout(300)
        await pg.fill("#plan-bp","Venture Blueprint"); await pg.fill("#plan-qty","10"); await pg.click("#plan-form button[type=submit]")
        for i in range(60):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        print("cit plan:", await pg.evaluate("JSON.stringify((()=>{const r=buildState.plan.res; return {mat:Math.round(r.matCost), unpriced:r.unpriced.map(x=>x.name), shop:r.shop.map(x=>[x.name,x.price]), fs:r.finalStep&&r.finalStep.missing.length}})())"))
        print("cit plan ui:", await pg.evaluate("[...document.querySelectorAll('#plan-out .slot-tile')].slice(0,2).map(t=>t.innerText.replace(/\\s+/g,' '))"), await pg.evaluate("(document.querySelector('#plan-out .notice[style*=bad]')||{}).innerText"))
        await pg.evaluate("const c=buildCfg(); c.price='jbv'; saveMisc(); const R=rxCfg(); R.inP='p:cX'; saveMisc(); document.querySelector('.tabs button[data-tab=reactions]').click()"); await pg.wait_for_timeout(1500)
        print("cit rx:", await pg.evaluate("[...document.querySelectorAll('#rx-pick > .slot-tiles .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))"), await pg.evaluate("((document.querySelector('#rx-pick .notice[style*=bad]')||{}).innerText||'').slice(0,200)"), await pg.evaluate("[...document.querySelectorAll('#rx-pick tbody tr[data-rx-row]')].slice(0,3).map(r=>r.innerText.replace(/\\s+/g,' '))"))
        print("cit rx fc:", await pg.evaluate("rxWeekly()"))
        await pg.evaluate("rxCfg().inP='split'; saveMisc(); piCfg().inP='p:cX'; saveMisc(); document.querySelector('.tabs button[data-tab=pimgmt]').click()"); await pg.wait_for_timeout(1500)
        print("cit pi:", await pg.evaluate("[...document.querySelectorAll('#pi-pick .slot-tile')].map(t=>t.innerText.replace(/\\s+/g,' '))"), await pg.evaluate("[...document.querySelectorAll('#pi-pick tbody tr:not(.group)')].slice(0,2).map(r=>r.innerText.replace(/\\s+/g,' '))"), await pg.evaluate("((document.querySelector('#pi-shop .notice[style*=bad]')||{}).innerText||'').slice(0,160)"), await pg.evaluate("piWeekly()"))
        await pg.evaluate("piCfg().inP='split'; saveMisc(); state.stockCfg.price='p:cX'; document.querySelector('.tabs button[data-tab=stock]').click()"); await pg.wait_for_timeout(1500)
        print("cit assets:", await pg.evaluate("[...document.querySelectorAll('#st-table tbody tr')].slice(0,3).map(r=>r.innerText.replace(/\\s+/g,' '))"), await pg.evaluate("((document.querySelector('#st-note .notice[style*=bad]')||{}).innerText||'').slice(0,200)"))
        await pg.evaluate("state.stockCfg.price='jbv'")
        await pg.evaluate("document.querySelector('.tabs button[data-tab=trading]').click()"); await pg.wait_for_timeout(400)
        print("arb on trading:", await pg.evaluate("[!!document.querySelector('#page-trading #arb-title'), !document.querySelector('#page-prices #arb-title'), document.getElementById('arb-src').options.length, document.getElementById('arb-dst').options.length, document.getElementById('arb-rate').value, getComputedStyle(document.getElementById('arb-go')).display]"))
        # ---- doctrines
        await pg.evaluate("state.misc.structs=state.misc.structs||{}; state.misc.structs['1000000000001']={id:'1000000000001',name:'Test Fortizar',system:30000142}; structMarket['1000000000001']={at:Date.now()+1e9,min:new Map(),max:new Map()}; structBooks['1000000000001']={at:Date.now()+1e9,sells:new Map([[32880,[[1e6,3]]],[1319,[[5e5,10]]],[34,[[5,1000]]]]),buyB:new Map()}; saveMisc(); document.querySelector('.tabs button[data-tab=fittings]').click()"); await pg.wait_for_timeout(300)
        await pg.fill("#fit-text","[Venture, Doctrine Venture]\nExpanded Cargohold II\nExpanded Cargohold II\n\nTritanium x500\nPyerite x100"); await pg.click("#fit-add")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("state.fits.some(f=>f.name==='Doctrine Venture')"): break
        print("doc fit:", await pg.evaluate("JSON.stringify(state.fits.find(f=>f.name==='Doctrine Venture'))"), await pg.evaluate("$('fit-status').textContent"))
        await pg.evaluate("state.fits.push({id:'fold',name:'Old Venture',ship:'Venture',shipId:32880,req:{},items:['Expanded Cargohold II','Hydrocarbons'],unknown:[],addedAt:1}); saveFits(); renderFits()")
        await pg.check("[data-fit-doc]:near(:text('Doctrine Venture'))") if False else None
        await pg.evaluate("document.querySelectorAll('[data-fit-doc]').forEach(cb=>{ if(['fold'].includes(cb.dataset.fitDoc) || state.fits.find(f=>f.id===cb.dataset.fitDoc).name==='Doctrine Venture'){ cb.checked=true; cb.dispatchEvent(new Event('change',{bubbles:true})); } })"); await pg.wait_for_timeout(300)
        print("doc marked:", await pg.evaluate("state.fits.filter(f=>f.doctrine).map(f=>f.name)"), await pg.evaluate("[...document.querySelectorAll('#fit-list .tag')].map(t=>t.textContent)"))
        await pg.evaluate("document.querySelector('.tabs button[data-tab=shortages]').click()")
        for i in range(30):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!!document.querySelector('#doc-box table')"): break
        print("doc out:", await pg.evaluate("document.getElementById('doc-box').innerText.replace(/\\s+/g,' ').slice(0,1200)"))
        await pg.fill("[data-doc-keep] >> nth=0","4"); await pg.dispatch_event("[data-doc-keep] >> nth=0","change"); await pg.wait_for_timeout(300)
        print("doc n4:", await pg.evaluate("[...document.querySelectorAll('#doc-box tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
        await pg.evaluate("state.fits.find(f=>f.id==='fold').doctrine=true; saveFits(); renderDoctrines()")
        for i in range(20):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!!document.querySelector('#doc-box table') && state.fits.find(f=>f.id==='fold').contents"): break
        await pg.wait_for_timeout(300)
        print("doc old:", await pg.evaluate("[...document.querySelectorAll('#doc-box tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' '))"), await pg.evaluate("JSON.stringify(state.fits.find(f=>f.id==='fold').contents)"))
        await pg.locator("#doc-box").screenshot(path=SP+"doctrine.png")
        await pg.evaluate("document.querySelector('.tabs button[data-tab=characters]').click()"); await pg.wait_for_timeout(300)
        print("rx lvl:", await pg.evaluate("[...document.querySelectorAll('.pilot dl.kv')].map(d=>[...d.querySelectorAll('dt')].map((t,i)=>t.textContent+'='+d.querySelectorAll('dd')[i].textContent).filter(x=>/Reactions/.test(x)).join())"))
        print("top bar2:", await pg.evaluate("[...document.querySelectorAll('.tabs > *')].map(x=>x.innerText.replace(/\\s+/g,' '))"))
        # ---- supply chain
        await pg.evaluate("document.querySelector('.tabs button[data-tab=plan]').click()"); await pg.wait_for_timeout(300)
        await pg.fill("#plan-bp","Venture Blueprint"); await pg.fill("#plan-qty","10"); await pg.click("#plan-form button[type=submit]")
        for i in range(60):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!buildState.plan.busy"): break
        await pg.evaluate("sendToOrders(buildState.plan.res)")
        print("errs before sc:", errs)
        print("order route:", await pg.evaluate("JSON.stringify((()=>{const o=ordList()[ordList().length-1]; return o.route && {locs:o.route.locs, span:o.route.span, moves:o.route.moves.map(m=>[m.from,m.to,m.n,m.q,Math.round(m.vol),m.ready,m.need])}})())"))
        await pg.evaluate("const c=state.chars.find(x=>x.name==='Ender Alpha'); c.loc={sys:30000005,at:Date.now()}; c.ship={type:28844,at:Date.now()}; c.scopes=(c.scopes||'')+' esi-location.read_location.v1'")
        await pg.evaluate("document.querySelector('.tabs button[data-tab=map]').click()")
        for i in range(40):
            await pg.wait_for_timeout(300)
            if await pg.evaluate("!!mapIndex() && !!document.querySelector('#sc-box [data-sc-plan]')"): break
        print("sc cars:", await pg.evaluate("[...document.querySelectorAll('#sc-box tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' '))"))
        await pg.click("[data-sc-plan]")
        for i in range(60):
            await pg.wait_for_timeout(500)
            if await pg.evaluate("!!scLast && !scBusy"): break
        print("sc plan:", await pg.evaluate("JSON.stringify({moves:scLast.moves.map(m=>[m.kind,m.from.n+'>'+m.to.n,Math.round(m.vol),m.what.slice(0,40),new Date(m.ready).toISOString().slice(5,16),m.need&&new Date(m.need).toISOString().slice(5,16)]), trips:scLast.trips.map(t=>[t.n,t.car.c.name,t.B.from.n+'>'+t.B.to.n,Math.round(t.B.vol),new Date(t.start).toISOString().slice(5,16),new Date(t.main.arrive).toISOString().slice(5,16),t.rep.jumps,t.main.jumps,t.late]), left:scLast.left.length, skipped:scLast.skipped})"))
        print("sc ui:", await pg.evaluate("document.getElementById('sc-box').innerText.replace(/\\s+/g,' ').slice(0,1500)"))
        await pg.click("[data-sc-map]"); await pg.wait_for_timeout(800)
        await pg.locator("#map-wrap").screenshot(path=SP+"scmap.png")
        await pg.locator("#sc-box").screenshot(path=SP+"scbox.png")
        await pg.click("[data-sc-done='1']")
        for i in range(60):
            await pg.wait_for_timeout(500)
            if await pg.evaluate("!scBusy"): break
        print("sc after done:", await pg.evaluate("JSON.stringify({done:scCfg().done, pilots:scCfg().pilots, trips:scLast.trips.map(t=>[t.n,t.car.c.name,t.B.from.n+'>'+t.B.to.n])})"))
        print("skills tab:", await pg.evaluate("document.querySelector('.tabs button[data-tab=overview]').textContent"))
        print("check pages:", await pg.evaluate("[...document.querySelectorAll('.tabs button')].map(b=>b.dataset.tab).join(',')"), await pg.evaluate("!!document.querySelector('#page-overview .matrix-head')"), await pg.evaluate("[...document.querySelectorAll('#page-misc h2')].map(h=>h.textContent).join(' | ')"))
        print("fc name:", await pg.evaluate("state.forecast.activities.map(a=>a.name)"))
        print("errors", errs)
        await b.close()
        return errs
def port_open():
    with socket.socket() as so: return so.connect_ex(("127.0.0.1", 8642)) == 0
if __name__ == "__main__":
    srv = None
    if not port_open():
        srv = subprocess.Popen([sys.executable, "-c", open(os.path.join(ROOT, "start-eve-industry-management.sh")).read().split("exec python3 -c '",1)[1].rsplit("'",1)[0]], cwd=ROOT, stdout=subprocess.DEVNULL)
        for _ in range(50):
            if port_open(): break
            time.sleep(0.1)
    try: errs = asyncio.run(main())
    finally:
        if srv: srv.terminate()
    sys.exit(1 if errs else 0)
