"""Independent, read-only early token discovery, NOT a buy signal.
Bounded public DexScreener sample; no polling guarantee. Never authenticates, trades, or touches main PAPER ledger.
"""
import datetime as dt,json,os,time,urllib.request
from pathlib import Path
BASE="https://api.dexscreener.com"
OUT=Path(__file__).resolve().parent/"early_watch_observations.json"
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Cuvar500-EarlyWatch-Research/1"})
    with urllib.request.urlopen(req,timeout=12) as response:
        return json.load(response)
def discover():
    profiles=fetch(BASE+"/token-profiles/latest/v1")
    if not isinstance(profiles,list):raise ValueError("Unexpected profiles format")
    tokens=[]
    for row in profiles:
        chain=row.get("chainId")
        address=row.get("tokenAddress")
        if chain in ("bsc","solana") and address:
            tokens.append((chain,address))
    return list(dict.fromkeys(tokens))[:40]
def main():
    now=int(time.time())
    previous={}
    if OUT.exists():
        raw=json.loads(OUT.read_text())
        previous=raw.get("tokens",{})
    observed={}
    errors=[]
    for chain,address in discover():
        key=chain+":"+(address.lower() if chain=="bsc" else address)
        try:
            pairs=fetch(BASE+"/token-pairs/v1/"+chain+"/"+address)
            if not isinstance(pairs,list):raise ValueError("bad pairs")
            valid=[p for p in pairs if p.get("chainId")==chain and p.get("baseToken",{}).get("address","").lower()==address.lower()]
            if not valid:continue
            p=max(valid,key=lambda x:float((x.get("liquidity") or {}).get("usd") or 0))
            created=p.get("pairCreatedAt")
            if not isinstance(created,(float,int)) or created>now*1000 or created<=0:continue
            age_h=(now-created/1000)/3600
            if age_h>24:continue
            previous_row=previous.get(key,{})
            observed[key]={"chain":chain,"token":address,"pair":p.get("pairAddress"),"first_seen_utc":previous_row.get("first_seen_utc",dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat()),"last_seen_utc":dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),"pair_age_hours":round(age_h,2),"liquidity_usd":(p.get("liquidity") or {}).get("usd"),"volume_h24_usd":(p.get("volume") or {}).get("h24"),"status":"OBSERVE_ONLY_NOT_SAFETY_APPROVED"}
        except Exception as exc:errors.append({"token":key,"error":str(exc)[:160]})
    # Retain earlier observations for 7 days for comparisons without pretending continuous coverage.
    for key,row in previous.items():
        if key not in observed:
            try:
                age=(now-dt.datetime.fromisoformat(row["last_seen_utc"]).timestamp())/3600
                if age<168:observed[key]=row
            except (KeyError,ValueError,TypeError):pass
    result={"generated_at_utc":dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),"mode":"DISCOVERY_ONLY","coverage":"Sampled latest token profiles, NOT exhaustive or real-time","new_observations":sum(k not in previous for k in observed),"checked_tokens":len(observed),"errors":errors[:10],"tokens":observed}
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("EARLY_WATCH_SUMMARY="+json.dumps({k:v for k,v in result.items() if k!="tokens"},sort_keys=True))
if __name__=="__main__":main()
