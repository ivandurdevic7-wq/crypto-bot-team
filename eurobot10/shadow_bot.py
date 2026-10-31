"""Odvojeni SHADOW simulator; nikad ne izvrsava stvarne trgovine."""
import json, time, uuid, datetime
from pathlib import Path
import bot
PATH=Path(__file__).with_name("shadow_state.json")
def fresh(): return {"cash":[66.67,66.67,66.66],"positions":[],"history":[],"last_scan":None}
def note(s,m): s["history"].insert(0,{"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"message":m});s["history"]=s["history"][:100]
def price_value(p): return p["units"]*p["last"]/1.10*0.995
def cycle():
 s=json.loads(PATH.read_text()) if PATH.exists() else fresh()
 if sum(s["cash"])>200.01 or len(s["cash"])!=3: raise ValueError("Nevazeci PAPER kapital")
 for p in list(s["positions"]):
  try:
   pool=next((x for x in bot.pairs(p["chain"],p["address"]) if x.get("pairAddress")==p["pair"]),None)
   if not pool: continue
   last=float(pool["priceUsd"])
   if last<=0: continue
   p["last"]=last
   value=price_value(p); growth=value/p["stake"]-1
   if growth<=-0.05 or growth>=0.10:
    s["cash"][p["bot"]]+=value;s["positions"].remove(p)
    note(s,"SHADOW prodaja "+p["symbol"]+" PnL "+str(round(value-p["stake"],2))+" EUR")
  except Exception as e: note(s,"SKIP refresh "+type(e).__name__)
 try:
  profiles=bot.get("https://api.dexscreener.com/token-profiles/latest/v1")
  if not isinstance(profiles,list): raise ValueError("Nema popisa")
 except Exception as e: profiles=[];note(s,"SKIP discovery "+type(e).__name__)
 seen=set()
 for token in profiles:
  chain=token.get("chainId");addr=token.get("tokenAddress","")
  if chain not in bot.CHAINS or not bot.valid(chain,addr) or (chain,addr) in seen: continue
  seen.add((chain,addr))
  if len(seen)>10: break
  try:
   pools=bot.pairs(chain,addr)
   if not pools or not bot.risk(chain,addr):continue
   for b in range(3):
    if s["cash"][b]<1 or any(p["bot"]==b and p["address"]==addr and p["chain"]==chain for p in s["positions"]):continue
    chosen=next((p for p in pools if bot.market(p,b)),None)
    if not chosen:continue
    price=float(chosen["priceUsd"])
    amount=min(10,s["cash"][b])
    if price<=0 or amount<1:continue
    s["cash"][b]-=amount
    s["positions"].append({"id":str(uuid.uuid4()),"chain":chain,"address":addr,"bot":b,"symbol":(chosen.get("baseToken") or {}).get("symbol","?"),"dexId":chosen.get("dexId","unknown"),"pair":chosen["pairAddress"],"price":price,"last":price,"stake":amount,"units":amount*0.995*1.10/price})
    note(s,"SHADOW auto kupnja "+chain+" "+str(chosen.get("dexId","unknown"))+" bot "+str(b+1)+" "+str(round(amount,2))+" EUR")
  except Exception as e:note(s,"SKIP candidate "+type(e).__name__)
 s["last_scan"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 PATH.write_text(json.dumps(s,ensure_ascii=False,indent=2)+"\n")
 print("SHADOW",len(s["positions"]),"positions; free",sum(s["cash"]))
if __name__=="__main__":cycle()
