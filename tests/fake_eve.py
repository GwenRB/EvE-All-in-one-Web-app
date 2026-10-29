"""Fake EVE for the end-to-end tests: every network call the app makes (ESI, EVE Ref, CCP's static data, the launcher's news, images) answered
from the tables below. 7 fake systems Alpha…Golf, a Venture build chain, reaction formulas, PI items, a Rhea, decryptors, ores.
Used by e2e_smoke.py: `await ctx.route("**/*", handle)`."""
import json, os, time
from urllib.parse import urlparse, parse_qs
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
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
NAMES.update({1000035:"Caldari Navy",1000125:"CONCORD",1000130:"Sisters of EVE",1000180:"State Protectorate",777001:"Bob Client",777002:"Bob Alt"})
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
# ore (category 25) for buying ore instead of minerals: compressed ores are tiny, the plain one isn't
NAMES.update({62516:"Compressed Veldspar",62520:"Compressed Scordite",1230:"Veldspar",3385:"Reprocessing",3389:"Reprocessing Efficiency",60377:"Simple Ore Processing"})
for k,g,v,mats,pr in [(62516,462,0.001,{34:400},8.0),(62520,460,0.001,{34:150,35:90},14.0),(1230,462,0.1,{34:400},6.0)]:
    TYPES[k]={"group_id":g,"category_id":25,"volume":v,"portion_size":100,"market_group_id":518,"dogma_attributes":dd({790:60377}),"type_materials":{str(m):{"material_type_id":m,"quantity":q} for m,q in mats.items()}}; PRICE[k]=pr
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
# Wallet journal and transactions of pilot 9001 (Profit and loss): a reaction product sold, minerals bought, their market lines and escrow (left out),
# sales tax, two job fees (job 77 a reaction, 78 manufacturing), a donation to and a contract from client 555 with its sales tax, a broker fee, a planet tax
NAMES.update({555:"Bob Client",777:"Market Buyer",778:"Market Seller",1000132:"Secure Commerce Commission"})
_JE=lambda i,ref,amt,p1=9001,p2=1000132,cid=None,ct=None,reason="":{"id":i,"date":"2026-10-15T12:%02d:00Z"%i,"ref_type":ref,"amount":amt,"first_party_id":p1,"second_party_id":p2,**({"context_id":cid,"context_id_type":ct} if cid else {}),**({"reason":reason} if reason else {}),"description":ref}
WALLET_J=[_JE(1,"market_transaction",30000,777,9001,501,"market_transaction_id"),_JE(2,"transaction_tax",-1200,cid=501,ct="market_transaction_id"),_JE(3,"industry_job_tax",-500,cid=77,ct="industry_job_id"),
  _JE(4,"industry_job_tax",-300,cid=78,ct="industry_job_id"),_JE(5,"player_donation",-1000000,9001,555,reason="for the Rorqual"),_JE(6,"market_escrow",-50000),_JE(7,"brokers_fee",-100),
  _JE(8,"planetary_export_tax",-2000),_JE(9,"contract_price",2000000,555,9001,900,"contract_id"),_JE(10,"contract_sales_tax",-80000,cid=900,ct="contract_id"),
  _JE(12,"contract_price",-3000000,9001,556,901,"contract_id"),_JE(13,"contract_brokers_fee",-30000,cid=901,ct="contract_id"),_JE(14,"contract_price",-1000000,9001,557,902,"contract_id")]
# What the contracts held: 900 two Ventures sold to Bob; 901 bought from a supplier, moon materials and a PI item (split between Reactions and Planets);
# 902 a moon material and a PI item with no price anywhere (can't be split); 903 isn't readable any more
NAMES.update({556:"Gas Supplier",557:"Other Supplier",9100:"Fake Reactive Gas",9101:"Fake Noble Gas"})
for k in (9100,9101): TYPES[k]={"group_id":1032,"category_id":43,"volume":0.1}
PRICE[9100]=400.0
CONTRACT_ITEMS={8801:[(34,400,True)],8802:[(35,50,True)],8805:[(35,20,True)],8806:[(34,100,True)],900:[(32880,2,True)],901:[(16633,1000,True),(9100,500,True),(34,5,False)],902:[(16633,10,True),(9101,10,True)]}
WALLET_T=[{"transaction_id":501,"date":"2026-10-15T12:01:00Z","type_id":16671,"quantity":10,"unit_price":3000.0,"is_buy":False,"client_id":777,"location_id":60003760,"is_personal":True,"journal_ref_id":1},
  {"transaction_id":502,"date":"2026-10-15T12:20:00Z","type_id":34,"quantity":1000,"unit_price":4.0,"is_buy":True,"client_id":778,"location_id":60003760,"is_personal":True,"journal_ref_id":20},
  {"transaction_id":503,"date":"2026-10-15T12:21:00Z","type_id":35,"quantity":5,"unit_price":9.0,"is_buy":True,"client_id":778,"location_id":60003760,"is_personal":False,"journal_ref_id":21}]
# Corporation page: service modules (fuel per hour, attribute 2109) and two structure types with their role bonus (2339); a moon and its ore
NAMES.update({35878:"Standup Manufacturing Plant I",35891:"Standup Research Lab I",35899:"Standup Reprocessing Facility I",45009:"Standup Moon Drill I",35825:"Raitaru",35835:"Athanor",4246:"Hydrogen Fuel Block",4247:"Helium Fuel Block"})
for k,g,f in [(35878,1415,12),(35891,1415,12),(35899,1322,10),(45009,1887,5)]: TYPES[k]={"group_id":g,"category_id":66,"dogma_attributes":dd({2109:f})}
TYPES[35825]={"group_id":1404,"category_id":65,"dogma_attributes":dd({2339:-25})}; TYPES[35835]={"group_id":1406,"category_id":65,"dogma_attributes":dd({2339:-20})}
# Attribute boosters (Tests page, group 303): +8 for 3 days, +10 for a day that expires in 2030, one not on the market, one expired in 2016,
# one adding to two attributes with no price, and one adding no attribute (left out)
NAMES.update({9500:"Fake Expert Accelerator",9501:"Fake Event Accelerator",9502:"Fake Contract Accelerator",9503:"Fake Old Accelerator",9504:"Fake Focus Booster",9505:"Fake Speed Booster"})
for k,b,ms,mg,ex in [(9500,[8]*5,259200000,2487,None),(9501,[10]*5,86400000,2487,21915),(9502,[12]*5,86400000,None,None),(9503,[10]*5,86400000,2487,17032),(9504,[0,0,0,6,4],86400000,2487,None),(9505,[0]*5,86400000,2487,None)]:
    TYPES[k]={"group_id":303,"category_id":20,"volume":1,**({"market_group_id":mg} if mg else {}),"dogma_attributes":dd({**{175+i:v for i,v in enumerate(b)},330:ms,**({2422:ex} if ex else {})})}
PRICE.update({9500:30000000.0,9501:10000000.0,9503:1000.0})
def build_sde():
    """CCP's static data zip, faked from the tables above (the same items EVE Ref answers for), plus fixtures/sde.zip's own lines
    (its reaction formulas and planet schematics win where both have an entry). The app reads items, blueprints and the map from it."""
    import io, zipfile
    fx = zipfile.ZipFile(FIX+"sde.zip"); files = {}
    for n in fx.namelist(): files[n] = {json.loads(l)["_key"]: json.loads(l) for l in fx.read(n).decode().splitlines() if l.strip()}
    def add(n, k, o): files.setdefault(n, {}).setdefault(k, {"_key": k, **o})
    acts = lambda a: {k: {"time": v.get("time", 0), **({"materials": [{"typeID": int(t), "quantity": m["quantity"]} for t, m in v["materials"].items()]} if "materials" in v else {}),
        **({"products": [{"typeID": int(t), "quantity": m["quantity"], **({"probability": m["probability"]} if "probability" in m else {})} for t, m in v["products"].items()]} if "products" in v else {}),
        **({"skills": [{"typeID": int(s), "level": l} for s, l in v["required_skills"].items()]} if "required_skills" in v else {})} for k, v in a.items()}
    for b, a in BPS.items(): add("blueprints.jsonl", b, {"activities": acts(a), "blueprintTypeID": b, "maxProductionLimit": 100})
    add("blueprints.jsonl", 999, {"activities": {}, "blueprintTypeID": 999})
    cats, groups = {}, {}
    for t in sorted(set(TYPES) | set(NAMES)):
        if 30000000 <= t < 40000000 or 10000000 <= t < 30000000: continue   # systems, regions, constellations
        T = TYPES.get(t, {}); g = T.get("group_id")
        if g is not None: groups.setdefault(g, T.get("category_id"))
        if T.get("category_id") is not None: cats.setdefault(T["category_id"], True)
        add("types.jsonl", t, {"name": {"en": NAMES.get(t, f"T{t}")}, "published": True, **({"groupID": g} if g is not None else {}), **({"volume": T["volume"]} if "volume" in T else {}),
            **({"packagedVolume": T["packaged_volume"]} if "packaged_volume" in T else {}), **({"portionSize": T["portion_size"]} if "portion_size" in T else {}), **({"marketGroupID": T["market_group_id"]} if "market_group_id" in T else {})})
        d = [{"attributeID": int(k), "value": v["value"]} for k, v in T.get("dogma_attributes", {}).items()]
        for (s, l), (sa, la) in zip(T.get("required_skills", {}).items(), [(182, 277), (183, 278), (184, 279)]): d += [{"attributeID": sa, "value": int(s)}, {"attributeID": la, "value": l}]
        if d: add("typeDogma.jsonl", t, {"dogmaAttributes": d})
        if "traits" in T:
            bl = lambda x: [{"bonus": b.get("bonus"), "bonusText": b["bonus_text"]} for b in (x.values() if isinstance(x, dict) else x)]
            add("typeBonus.jsonl", t, {"roleBonuses": bl(T["traits"].get("role_bonuses", {})), "types": [{"_key": int(s), "_value": bl(x)} for s, x in T["traits"].get("types", {}).items()]})
        if "type_materials" in T: add("typeMaterials.jsonl", t, {"materials": [{"materialTypeID": int(m["material_type_id"]), "quantity": m["quantity"]} for m in T["type_materials"].values()]})
    for g, c in groups.items(): add("groups.jsonl", g, {"name": {"en": f"Group {g}"}, "published": True, **({"categoryID": c} if c is not None else {})})
    for c in cats: add("categories.jsonl", c, {"name": {"en": f"Category {c}"}, "published": True})
    # NPC corporations (faction, loyalty store) and the Caldari militia: CONCORD LP converts to Caldari Navy (0.8) and Sisters of EVE (0.4), not to the militia
    for k, f in ((1000035, 500001), (1000125, 500006), (1000130, 500016), (1000180, 500001)): add("npcCorporations.jsonl", k, {"name": {"en": NAMES[k]}, "factionID": f, "lpOfferTables": [1]})
    add("factions.jsonl", 500001, {"name": {"en": "Caldari State"}, "corporationID": 1000035, "militiaCorporationID": 1000180})
    files.setdefault("marketGroups.jsonl", {}); files.setdefault("typeMaterials.jsonl", {}); files.setdefault("npcStations.jsonl", {})
    for sid, (n, x, y, z, sec, c) in SYS.items():
        add("mapSolarSystems.jsonl", sid, {"name": {"en": n}, "position": {"x": x*LYm, "y": y*LYm, "z": z*LYm}, "position2D": {"x": x*LYm, "y": z*LYm}, "securityStatus": sec, "constellationID": c, "regionID": CON[c]})
    for c, r in CON.items(): add("mapConstellations.jsonl", c, {"name": {"en": NAMES[c]}, "regionID": r})
    for r in set(CON.values()): add("mapRegions.jsonl", r, {"name": {"en": NAMES[r]}})
    for i, (a, b) in enumerate(LINKS):
        add("mapStargates.jsonl", 50000000 + 2*i, {"solarSystemID": a, "destination": {"solarSystemID": b, "stargateID": 50000001 + 2*i}})
        add("mapStargates.jsonl", 50000001 + 2*i, {"solarSystemID": b, "destination": {"solarSystemID": a, "stargateID": 50000000 + 2*i}})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, rows in files.items(): z.writestr(n, "".join(json.dumps(o) + "\n" for o in rows.values()))
    return buf.getvalue()
SDE_ZIP = None
CCP_OFF = False   # True: CCP's static data can't be reached (only the reactions/PI fixture is served), to check the EVE Ref fallback
async def handle(route):
    global SDE_ZIP
    u=route.request.url
    if "developers.eveonline.com" in u and not u.startswith("http://localhost"): return await route.abort()
    if u.startswith("http://localhost:8642/proxy") and "developers.eveonline.com" in u:
        tgt=parse_qs(urlparse(u).query)["url"][0]
        if tgt.endswith("latest.jsonl"): return await route.fulfill(status=200, headers={"Content-Type":"text/plain"}, body='{"_key":"sde","buildNumber":3100000,"releaseDate":"2026-10-01"}\n')
        if CCP_OFF: return await route.fulfill(status=200, headers={"Content-Type":"application/zip"}, body=open(FIX+"sde.zip","rb").read())
        if SDE_ZIP is None: SDE_ZIP = build_sde()
        return await route.fulfill(status=200, headers={"Content-Type":"application/zip"}, body=SDE_ZIP)
    if u.startswith("http://localhost:8642/proxy") and "launcher.eveonline.com" in u:
        return await route.fulfill(status=200, headers={"Content-Type":"application/json"}, body=json.dumps([{"id":"n%d"%i,"title":"News %d"%i,"category":"patch-notes" if i==2 else "news","publishingDate":"2026-10-%02dT14:00:00.000Z"%(20-i),"metaDescription":"About news %d"%i,"src":"https://images.ctfassets.net/x/%d.png"%i,"url":"https://www.eveonline.com/news/view/n%d"%i+("?utm_source=launcher" if i==1 else "")} for i in range(1,6)]))
    if u.startswith("http://localhost:8642/proxy") and "www.eveonline.com" in u and "rss" in u:
        return await route.fulfill(status=200, headers={"Content-Type":"application/xml"}, body='\ufeff<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>EVE Online patch-notes</title>'
            '<item><title>News 1</title><link>https://www.eveonline.com/news/view/n1</link><pubDate>Mon, 19 Oct 2026 14:00:00 GMT</pubDate><description>&lt;p&gt;Same as the launcher&lt;/p&gt;</description></item>'
            '<item><title>Patch Notes - Version 9.99</title><link>https://www.eveonline.com/news/view/pn999</link><pubDate>Tue, 20 Oct 2026 15:00:00 GMT</pubDate><description>&lt;p&gt;Greetings,&lt;/p&gt;&lt;p&gt;New patch.&lt;/p&gt;&lt;img src="//images.ctfassets.net/x/pn.png" /&gt;</description></item></channel></rss>')
    if u.startswith("http://localhost:8642/proxy") and "reddit.com" in u:
        return await route.fulfill(status=200, headers={"Content-Type":"application/octet-stream"}, body='<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/"><title>top scoring links : Eve</title>'
            '<entry><author><name>/u/pilot</name></author><content type="html">&lt;!-- SC_OFF --&gt;&lt;div class=&quot;md&quot;&gt;&lt;p&gt;Ten crates opened.&lt;/p&gt;&lt;/div&gt;&lt;!-- SC_ON --&gt; &amp;#32; submitted by &amp;#32; &lt;a href=&quot;https://www.reddit.com/user/pilot&quot;&gt; /u/pilot &lt;/a&gt; &lt;br/&gt; &lt;span&gt;&lt;a href=&quot;https://v.redd.it/x&quot;&gt;[link]&lt;/a&gt;&lt;/span&gt; &amp;#32; &lt;span&gt;&lt;a href=&quot;https://www.reddit.com/r/Eve/comments/1x/crates/&quot;&gt;[comments]&lt;/a&gt;&lt;/span&gt;</content>'
            '<id>t3_1x</id><link href="https://www.reddit.com/r/Eve/comments/1x/crates/" /><updated>2026-10-01T12:00:00+00:00</updated><published>2026-10-01T12:00:00+00:00</published><title>Buying 10 crates</title></entry></feed>')
    if u.startswith("http://localhost:8642"): return await route.continue_()
    if "fonts." in u or "images.evetech" in u or "ctfassets" in u: return await route.abort()
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
    if "/markets/10000002/history" in u and int(parse_qs(urlparse(u).query)["type_id"][0]) not in (34,35,32880): return await j([{"date":"2026-10-%02d"%d,"volume":5000000,"average":1} for d in range(1,31)])
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
    # Amarr and Dodixie (Import calculator): sell orders with quantities, Amarr 30 at the price + 20 at +5%, Dodixie 5 at +50%; no buy orders
    if "/markets/10000043/orders" in path or "/markets/10000032/orders" in path:
        tid=int(parse_qs(urlparse(u).query)["type_id"][0]); p=PRICE.get(tid,0)
        if "order_type=buy" in u or not p: return await j([], pages=1)
        return await j([{"location_id":60008494,"price":p,"volume_remain":30},{"location_id":60008494,"price":p*1.05,"volume_remain":20}] if "10000043" in path else [{"location_id":60011866,"price":p*1.5,"volume_remain":5}], pages=1)
    # wallets (Profit and loss): pilot 9001's journal and market transactions, its jobs with completed ones; the corporation refuses (no Accountant role)
    if path.startswith("/characters/9001/wallet/journal"): return await j(WALLET_J, pages=1)
    if path.startswith("/characters/9001/wallet/transactions"): return await j(WALLET_T)
    if path.startswith("/characters/9001/industry/jobs"): return await j([{"job_id":77,"activity_id":9},{"job_id":78,"activity_id":1}] if "include_completed" in u else [])
    if (path.startswith("/characters/9001/contracts/") or path.startswith("/corporations/98000001/contracts/")) and path.rstrip("/").endswith("/items"):
        cid=int(path.split("/")[4]); L=CONTRACT_ITEMS.get(cid)
        return await (j([{"record_id":i,"type_id":t,"quantity":q,"is_included":inc,"is_singleton":False} for i,(t,q,inc) in enumerate(L)]) if L else j({"error":"Contract not found!"},404))
    if path.startswith("/characters/9001/skillqueue"):   # out of order on purpose: queue_position sets the order; the last level has no dates (paused)
        return await j([{"skill_id":3392,"finished_level":5,"queue_position":1,"start_date":"2030-01-02T00:00:00Z","finish_date":"2030-01-05T00:00:00Z"},{"skill_id":3380,"finished_level":5,"queue_position":0,"start_date":"2020-01-01T00:00:00Z","finish_date":"2030-01-02T00:00:00Z"},{"skill_id":45746,"finished_level":4,"queue_position":2}])
    # calendar: one fleet tomorrow (with details), one event that ended yesterday (left out); dates relative to now
    if path.startswith("/characters/9001/calendar/"):
        tail=path.rstrip("/").split("/")[-1]; now=time.time()
        iso=lambda s: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(s))
        if tail=="calendar": return await j([{"event_id":501,"event_date":iso(now+86400),"title":"Fleet: home defence","importance":1,"event_response":"accepted"},{"event_id":502,"event_date":iso(now-2*86400),"title":"Old ops","importance":0,"event_response":"declined"}])
        if tail=="501": return await j({"event_id":501,"date":iso(now+86400),"duration":120,"owner_id":98000001,"owner_name":"Fake Corp","owner_type":"corporation","importance":1,"text":"Form up <b>in Alpha</b><br>Bring ECM","title":"Fleet: home defence","response":"accepted"})
        return await j({"error":"not found"},404)
    # server status (started a minute ago, so the daily downtime check sees it back) and kills in the last hour (Bravo is dangerous)
    if path.rstrip("/")=="/status": return await j({"players":23456,"server_version":"3100000","start_time":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()-60))})
    if path.rstrip("/")=="/universe/system_kills": return await j([{"system_id":30000002,"ship_kills":6,"pod_kills":2,"npc_kills":10},{"system_id":30000006,"ship_kills":1,"pod_kills":0,"npc_kills":0}])
    # market history (The Forge) for Tritanium, Pyerite and the Venture: yesterday +10% on the day before, +37.5% on 8 days ago; 100 sold a day this week
    if path.startswith("/markets/10000002/history"):
        tid=int(parse_qs(urlparse(u).query)["type_id"][0]); p=PRICE.get(tid)
        if tid not in (34,35,32880) or not p: return await j({"error":"Type not found"},404)
        day=lambda i: time.strftime("%Y-%m-%d", time.gmtime(time.time()-i*86400))
        return await j([{"date":day(i),"average":p*(1.1 if i==1 else 0.8 if i>=8 else 1.0),"highest":p,"lowest":p,"order_count":5,"volume":100 if i<=7 else 50} for i in range(12,0,-1)])
    # public contracts in The Forge (2 pages): 2 Ventures at 250k each, one asking for something back, one at 900k, one holding Tritanium, a courier
    if path.startswith("/contracts/public/items/"):
        cid=int(path.rstrip("/").split("/")[-1]); L={7001:[(32880,2,True)],7002:[(32880,1,True),(34,1000,False)],7003:[(32880,1,True)],7005:[(34,10,True)]}.get(cid)
        return await (j([{"record_id":i,"type_id":t,"quantity":q,"is_included":inc} for i,(t,q,inc) in enumerate(L)]) if L else j({"error":"not found"},404))
    if path.startswith("/contracts/public/10000002"):
        pg=int(parse_qs(urlparse(u).query).get("page",["1"])[0]); exp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()+5*86400))
        c=lambda i,ty,pr,v,ti="": {"contract_id":i,"type":ty,"price":pr,"volume":v,"title":ti,"start_location_id":60003760,"date_expired":exp}
        return await j([c(7001,"item_exchange",500000,5000),c(7002,"item_exchange",100000,2500,"cheap"),c(7004,"courier",0,2500)] if pg==1 else [c(7003,"item_exchange",900000,2500),c(7005,"item_exchange",50000,2500)], pages=2)
    # loyalty: pilot 9001's LP, the NPC corporations, one store (a priced offer with another item, an item with no price, a stack)
    if path.startswith("/characters/9001/loyalty/points"): return await j([{"corporation_id":1000035,"loyalty_points":2500},{"corporation_id":1000125,"loyalty_points":1000}])
    if path.rstrip("/")=="/corporations/npccorps": return await j([1000035,1000125,1000130,1000180])
    if path.startswith("/loyalty/stores/1000035/offers"): return await j([{"offer_id":1,"type_id":32880,"quantity":1,"lp_cost":1000,"isk_cost":100000,"required_items":[{"type_id":34,"quantity":1000}]},{"offer_id":2,"type_id":999001,"quantity":1,"lp_cost":500,"isk_cost":0,"required_items":[]},{"offer_id":3,"type_id":35,"quantity":1000,"lp_cost":100,"isk_cost":0,"required_items":[]}])
    if path.startswith("/loyalty/stores/1000125/offers"): return await j([{"offer_id":9,"type_id":32880,"quantity":1,"lp_cost":2000,"isk_cost":0,"required_items":[]}])
    if path.startswith("/loyalty/stores/"): return await j({"error":"Not found"},404)
    if "/corporations/98000001/wallets/" in path: return await j({"error":"forbidden"},403)
    # customs offices of corporation 98000001 (alliance 99000001): two in Delta (5% and 8% for members, 10% for the alliance), one in Echo (3%, no alliance access); 98000002 refuses (no Director)
    if path.rstrip("/")=="/corporations/98000001": return await j({"name":"Fake Corp","alliance_id":99000001})
    if path.rstrip("/")=="/corporations/98000001/customs_offices":
        o=lambda i,s,c,a: {"office_id":i,"system_id":s,"corporation_tax_rate":c,"alliance_tax_rate":a if a is not None else 0.5,"allow_alliance_access":a is not None,"allow_access_with_standings":False,"standing_level":"neutral","reinforce_exit_start":18,"reinforce_exit_end":20}
        return await j([o(1001,30000004,0.05,0.1),o(1002,30000004,0.08,0.1),o(1003,30000005,0.03,None)], pages=1)
    if path.rstrip("/")=="/corporations/98000002/customs_offices": return await j({"error":"Character does not have required role(s)"},403)
    # moon mining of corporation 98000001: one extraction (chunk tomorrow), one moon drill's ledger (two miners, one day too old for 30 days); pilot 9001's own ledger
    iso=lambda s: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(s)); day=lambda i: time.strftime("%Y-%m-%d", time.gmtime(time.time()-i*86400)); now=time.time()
    if path.rstrip("/")=="/corporation/98000001/mining/extractions": return await j([{"moon_id":40000001,"structure_id":1,"extraction_start_time":iso(now-5*86400),"chunk_arrival_time":iso(now+86400),"natural_decay_time":iso(now+86400+3*3600)}], pages=1)
    if path.rstrip("/")=="/corporation/98000001/mining/observers": return await j([{"observer_id":1001,"observer_type":"structure","last_updated":day(1)}], pages=1)
    if path.rstrip("/")=="/corporation/98000001/mining/observers/1001": return await j([{"character_id":777001,"type_id":1230,"quantity":1000,"last_updated":day(2),"recorded_corporation_id":98000001},{"character_id":777001,"type_id":1230,"quantity":500,"last_updated":day(3),"recorded_corporation_id":98000001},{"character_id":556,"type_id":62520,"quantity":300,"last_updated":day(1),"recorded_corporation_id":98000002},{"character_id":556,"type_id":62520,"quantity":9999,"last_updated":day(40),"recorded_corporation_id":98000002}], pages=1)
    if path.rstrip("/")=="/characters/9001/mining": return await j([{"date":day(2),"solar_system_id":30000004,"type_id":1230,"quantity":200}], pages=1)
    if path.rstrip("/")=="/universe/moons/40000001": return await j({"moon_id":40000001,"name":"Delta I - Moon 1","system_id":30000004})
    # notifications of pilot 9001: the Sotiyo attacked an hour ago, a chunk ready, a corporation application 5 days ago, one too old to keep
    if path.rstrip("/")=="/characters/9001/notifications":
        ft=lambda s: int((s*1000+11644473600000)*1e4); now=now//3600*3600   # the same answer for every pilot within the hour
        n=lambda i,ty,ago,tx: {"notification_id":i,"type":ty,"sender_id":1000125,"sender_type":"corporation","timestamp":iso(now-ago),"text":tx,"is_read":False}
        return await j([n(1,"StructureUnderAttack",3600,"allianceName: Bad Guys\narmorPercentage: 100.0\ncharID: 556\ncorpName: Pirates\nhullPercentage: 100.0\nshieldPercentage: 45.5\nsolarsystemID: 30000004\nstructureID: &id001 1\nstructureShowInfoData:\n- showinfo\n- 35825\n- *id001\nstructureTypeID: 35825\n"),
            n(2,"MoonminingExtractionFinished",7200,"autoTime: %d\nmoonID: 40000001\nsolarSystemID: 30000004\nstructureID: 1\nstructureTypeID: 35835\n" % ft(now+3*3600)),
            n(3,"CorpAppNewMsg",5*86400,"applicationText: hi\ncharID: 777001\ncorpID: 98000001\n"), n(4,"StructureFuelAlert",100*86400,"solarsystemID: 30000004\nstructureID: 1\n")])
    # market orders of pilot 9001 (Net worth): a sell order (1,000 Tritanium left at 5), a buy order (100 Pyerite at 10, 600 in escrow), one for the corporation,
    # one that expired; the corporation's own list is refused (no Accountant or Trader role)
    if path.rstrip("/")=="/characters/9001/orders":
        o=lambda i,t,buy,p,left,tot,esc=None,corp=False,ago=86400,dur=90: {"order_id":i,"type_id":t,"is_buy_order":buy,"price":p,"volume_remain":left,"volume_total":tot,**({"escrow":esc} if esc is not None else {}),"location_id":60003760,"region_id":10000002,"issued":iso(now-ago),"duration":dur,"range":"station","is_corporation":corp}
        return await j([o(11,34,False,5.0,1000,2000),o(12,35,True,10.0,100,100,600.0),o(13,16633,False,600.0,10,10,corp=True),o(14,34,False,4.0,50,50,ago=40*86400,dur=30)])
    if path.rstrip("/")=="/corporations/98000001/orders": return await j({"error":"Character does not have required role(s)"},403)
    # dogma attributes (Item database): two with names, the rest unknown
    if path.startswith("/dogma/attributes/"):
        aid=int(path.rstrip("/").split("/")[-1]); A={38:{"attribute_id":38,"name":"capacity","display_name":"Capacity","unit_id":9,"published":True},12:{"attribute_id":12,"name":"lowSlots","display_name":"Low Slots","published":True},1137:{"attribute_id":1137,"name":"rigSlots","display_name":"","published":False}}
        return await (j(A[aid]) if aid in A else j({"error":"not found"},404))
    return await j([],404)
