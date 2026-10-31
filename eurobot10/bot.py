import json, os, time, urllib.request, re, datetime, sys
from pathlib import Path
DATA=Path(__file__).with_name("state.json")
CHAINS={"bsc","solana"}
def initial(): return {"cash":[66.67,66.67,66.66],"positions":[],"pending":[],"history":[]}
def get(url):
 req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"EUROBOT10-PAPER"})
 with urllib.request.urlopen(req,timeout=12) as r: return json.load(r)
def log(s,msg):
 s["history"].insert(0,{"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"message":msg})
 s["history"]=s["history"][:120]
def valid(chain,addr):
 return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}",addr)) if chain=="bsc" else bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}",addr))
def pairs(chain,addr):
 result=get("https://api.dexscreener.com/token-pairs/v1/"+chain+"/"+addr)
 if not isinstance(result,list):return []
 return sorted([p for p in result if p.get("chainId")==chain and (p.get("baseToken") or {}).get("address","").lower()==addr.lower()],key=lambda x:float((x.get("liquidity") or {}).get("usd") or 0),reverse=True)
def risk(chain,addr):
 if chain=="bsc":
  obj=get("https://api.gopluslabs.io/api/v1/token_security/56?contract_addresses="+addr)
  if str(obj.get("code"))!="1":return False
  d=(obj.get("result") or {}).get(addr.lower()) or {}
  for k in ("is_honeypot","is_mintable","is_blacklisted","is_proxy","hidden_owner","can_take_back_ownership","slippage_modifiable","transfer_pausable"):
   if str(d.get(k))!="0":return False
  if str(d.get("is_open_source"))!="1":return False
  try:return float(d["buy_tax"])<=0.05 and float(d["sell_tax"])<=0.05
  except (KeyError,TypeError,ValueError):return False
 obj=get("https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses="+addr)
 if str(obj.get("code"))!="1":return False
 d=(obj.get("result") or {}).get(addr) or {}
 return all(str(d.get(k))=="0" for k in ("mintable","freezable"))
def market(p,bot):
 try:
  price=float(p["priceUsd"]);liquidity=float(p["liquidity"]["usd"]);volume=float(p["volume"]["h24"])
  age=time.time()*1000-float(p["pairCreatedAt"]);h=float(p["priceChange"]["h1"])
 except (KeyError,TypeError,ValueError):return False
 if not (price>0 and liquidity>=50000 and volume>=20000 and age>=86400000):return False
 if bot==0:return -2<=h<=3
 if bot==1:return 0.2<=h<=6
 try:buys=float(p["txns"]["h1"]["buys"])
 except (KeyError,TypeError,ValueError):return False
 return 1<=h<=10 and buys>=50
def current(s):
 for p in list(s["positions"]):
  try:
   candidates=pairs(p["chain"],p["address"])
   match=next((x for x in candidates if x.get("pairAddress")==p["pair"]),None)
   if not match:continue
   usd=float(match["priceUsd"])
   if usd<=0:continue
   p["last"]=usd
   p["updated"]=time.time()
   fx=1.10
   value=p["units"]*usd/fx*0.995
   ret=value/p["stake"]-1
   if ret<=-0.05 or ret>=0.10:
    s["cash"][p["bot"]]+=value;s["positions"].remove(p)
    log(s,f"PAPER prodaja {p['chain']} {p['symbol']}: {value-p['stake']:+.2f} EUR")
  except Exception as e:log(s,"SKIP cijena: "+str(e)[:85])
DISCOVERY_URLS = (
 ("profiles","https://api.dexscreener.com/token-profiles/latest/v1"),
 ("boosts_latest","https://api.dexscreener.com/token-boosts/latest/v1"),
 ("boosts_top","https://api.dexscreener.com/token-boosts/top/v1"),
)
def discover():
 seen=set();tokens=[];sources={}
 for name,url in DISCOVERY_URLS:
  try:
   rows=get(url)
   if not isinstance(rows,list):raise ValueError("API response is not a list")
   sources[name]={"received":len(rows),"error":None}
   for item in rows:
    if not isinstance(item,dict):continue
    chain=item.get("chainId");address=item.get("tokenAddress","")
    if chain not in CHAINS or not valid(chain,address):continue
    key=(chain,address.lower())
    if key in seen:continue
    seen.add(key);tokens.append((chain,address,name))
  except Exception as exc:
   sources[name]={"received":0,"error":str(exc)[:120]}
 return tokens[:24],sources

def security_reason(chain,addr):
 if chain=="bsc":
  obj=get("https://api.gopluslabs.io/api/v1/token_security/56?contract_addresses="+addr)
  if str(obj.get("code"))!="1":return "GoPlus: neuspjesan odgovor"
  d=(obj.get("result") or {}).get(addr.lower()) or {}
  for key in ("is_honeypot","is_mintable","is_blacklisted","is_proxy","hidden_owner","can_take_back_ownership","slippage_modifiable","transfer_pausable"):
   if str(d.get(key))!="0":return "GoPlus: "+key+" nije potvrdeno 0"
  if str(d.get("is_open_source"))!="1":return "GoPlus: otvoreni kod nije potvrden"
  for key in ("buy_tax","sell_tax"):
   try:
    value=float(d[key])
    if not 0<=value<=.05:return "GoPlus: "+key+" izvan 0-5%"
   except (KeyError,TypeError,ValueError):return "GoPlus: "+key+" nepoznat"
  return None
 obj=get("https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses="+addr)
 if str(obj.get("code"))!="1":return "GoPlus Solana: neuspjesan odgovor"
 d=(obj.get("result") or {}).get(addr) or {}
 for key in ("mintable","freezable"):
  if str(d.get(key))!="0":return "GoPlus Solana: "+key+" nije potvrdeno 0"
 return None

def market_reason(p,b):
 try:
  price=float(p["priceUsd"]);liq=float(p["liquidity"]["usd"]);volume=float(p["volume"]["h24"])
  age=time.time()*1000-float(p["pairCreatedAt"]);change=float(p["priceChange"]["h1"])
 except (KeyError,TypeError,ValueError):return "trziste: nedostaje cijena/likvidnost/volumen/starost/promjena"
 if price<=0:return "trziste: nevaljana cijena"
 if liq<50000:return "trziste: likvidnost ispod 50000 USD"
 if volume<20000:return "trziste: 24h volumen ispod 20000 USD"
 if age<86400000:return "trziste: par mladi od 24 sata"
 if b==0 and not -2<=change<=3:return "Cuvar: 1h promjena izvan [-2%,3%]"
 if b==1 and not .2<=change<=6:return "Trend: 1h promjena izvan [0.2%,6%]"
 if b==2:
  try:buys=float(p["txns"]["h1"]["buys"])
  except (KeyError,TypeError,ValueError):return "Momentum: nedostaje broj 1h kupnji"
  if not(1<=change<=10 and buys>=50):return "Momentum: 1h promjena ili broj kupnji ne prolazi"
 return None

def scan(s):
 tokens,sources=discover()
 counters={"candidates":len(tokens),"pairs_found":0,"security_pass":0,"market_pass":0,"proposals":0,"errors":0}
 diagnostics=[]
 for chain,addr,source in tokens:
  item={"chain":chain,"address":addr,"source":source,"dexId":None,"symbol":None,"status":"SKIP","reason":None,"strategies":{}}
  try:
   ps=pairs(chain,addr)
   if not ps:
    item["reason"]="DexScreener: nema odgovarajuceg osnovnog para"
    continue
   counters["pairs_found"]+=1
   p=ps[0]
   item["dexId"]=p.get("dexId","unknown")
   item["symbol"]=(p.get("baseToken") or {}).get("symbol","?")
   problem=security_reason(chain,addr)
   if problem:
    item["reason"]=problem
    continue
   counters["security_pass"]+=1
   for b in range(3):
    why=market_reason(p,b)
    if not why and s["cash"][b]<1:why="nedovoljno PAPER sredstava"
    if not why and any(x["chain"]==chain and x["address"]==addr and x["bot"]==b for x in s["positions"]+s["pending"]):why="postojeca pozicija/prijedlog"
    item["strategies"][str(b+1)]=why or "PASS"
    if why:continue
    counters["market_pass"]+=1
    from uuid import uuid4
    s["pending"].append({"id":str(uuid4()),"chain":chain,"address":addr,"bot":b,"symbol":item["symbol"],"pair":p["pairAddress"],"dexId":item["dexId"],"price":float(p["priceUsd"]),"expires":time.time()+3600})
    counters["proposals"]+=1
    log(s,f"PAPER prijedlog: {chain} {addr} na {item['dexId']} bot {b+1}; ceka DA")
   if any(v=="PASS" for v in item["strategies"].values()):
    item["status"]="PASS";item["reason"]="kandidat predlozen"
   else:item["reason"]="nijedna strategija nije prosla"
  except Exception as exc:
   counters["errors"]+=1
   item["reason"]="API/obrada: "+str(exc)[:160]
  finally:
   diagnostics.append(item)
 s["pending"]=s["pending"][-30:]
 s["diagnostics"]={"sources":sources,"summary":counters,"tokens":diagnostics,"at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
 log(s,"DIJAGNOSTIKA: "+", ".join(f"{k}={v}" for k,v in counters.items()))
def approve(s,pid,confirmation):
 if confirmation!="DA":log(s,"SKIP: nema izričite potvrde DA");return
 q=next((x for x in s["pending"] if x["id"]==pid),None)
 if not q or time.time()>q["expires"]:log(s,"SKIP: prijedlog nije dostupan/istekao");return
 try:
  ps=pairs(q["chain"],q["address"])
  p=next((x for x in ps if x.get("pairAddress")==q["pair"]),None)
  if not p or not risk(q["chain"],q["address"]) or not market(p,q["bot"]):raise ValueError("veto nakon provjere")
  price=float(p["priceUsd"])
  if abs(price/q["price"]-1)>0.03:raise ValueError("cijena se promijenila >3%")
  amount=min(10,s["cash"][q["bot"]])
  if amount<1:raise ValueError("nema sredstava")
  units=amount*.995*1.10/price
  from uuid import uuid4
  s["cash"][q["bot"]]-=amount
  s["positions"].append({"id":str(uuid4()),"chain":q["chain"],"address":q["address"],"bot":q["bot"],"symbol":q["symbol"],"pair":q["pair"],"dexId":q["dexId"],"price":price,"last":price,"stake":amount,"units":units})
  s["pending"].remove(q)
  log(s,f"PAPER KUPNJA {q['chain']} {q['symbol']}, {amount:.2f} EUR uz DA")
 except Exception as e:log(s,"SKIP kupnja: "+str(e)[:90])
def main():
 s=json.loads(DATA.read_text()) if DATA.exists() else initial()
 s["pending"]=[x for x in s["pending"] if x["expires"]>time.time()]
 mode=os.environ.get("MODE","scan")
 if mode=="approve":approve(s,os.environ.get("APPROVE_ID",""),os.environ.get("APPROVE_DA",""))
 else:current(s);scan(s)
 s["last_scan"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 DATA.write_text(json.dumps(s,ensure_ascii=False,indent=2)+"\n")
 print("PAPER:",mode,"positions",len(s["positions"]),"pending",len(s["pending"]))
if __name__=="__main__":main()
