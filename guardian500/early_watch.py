"""Independent, read-only early token discovery, NOT a buy signal or safety clearance; research snapshots only; previous observations restored via branch-specific cache; validate second-snapshot coverage.
Bounded public DexScreener sample; no polling guarantee. Never authenticates, trades, or touches main PAPER ledger.
"""
import datetime as dt,json,math,time,urllib.request
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
def metric(value):
    try:
        result=float(value)
        return result if math.isfinite(result) and result>=0 else None
    except (TypeError,ValueError,OverflowError):
        return None
def compare(previous,current):
    """Comparable snapshots only: same selected pool, newer observation."""
    if not previous or previous.get("pair")!=current.get("pair"):
        return {"status":"NO_COMPARABLE_PREVIOUS_SAMPLE"}
    try:
        elapsed=(dt.datetime.fromisoformat(current["last_seen_utc"])-dt.datetime.fromisoformat(previous["last_seen_utc"])).total_seconds()
    except (ValueError,TypeError,KeyError):
        return {"status":"UNKNOWN_INTERVAL"}
    if elapsed<=0:return {"status":"UNKNOWN_INTERVAL"}
    before=metric(previous.get("liquidity_usd"));after=metric(current.get("liquidity_usd"))
    def delta(x,y):return round(100*(y/x-1),2) if x is not None and x>0 and y is not None else None
    result={"status":"COMPARABLE","elapsed_minutes":round(elapsed/60,2),"liquidity_change_pct":delta(before,after)}
    for side in ("buys","sells"):
        a=metric(previous.get("txns_m5_"+side));z=metric(current.get("txns_m5_"+side))
        result["txns_m5_"+side+"_change"]=round(z-a) if a is not None and z is not None else None
    result["note"]="m5 trades are rolling-window counts; deltas are NOT net new trades."
    return result
def risk_alerts(previous,current,comparison):
    """Observational warnings; never a trade recommendation."""
    alerts=[]
    if comparison.get("status")!="COMPARABLE":
        return [{"kind":"INSUFFICIENT_COMPARABLE_DATA","level":"UNKNOWN"}]
    age=metric(comparison.get("elapsed_minutes"))
    if age is None or age>60:
        return [{"kind":"STALE_COMPARISON","level":"UNKNOWN"}]
    change=comparison.get("liquidity_change_pct")
    if change is not None and change<=-25:
        alerts.append({"kind":"LIQUIDITY_DROP","level":"CAUTION","change_pct":change})
    buys=metric(current.get("txns_m5_buys"))
    sells=metric(current.get("txns_m5_sells"))
    if buys is None or sells is None:
        alerts.append({"kind":"TRADE_ACTIVITY_UNKNOWN","level":"UNKNOWN"})
    elif buys+sells>=20 and sells>=3*max(1,buys):
        alerts.append({"kind":"SELL_HEAVY_ACTIVITY","level":"CAUTION","m5_buys":int(buys),"m5_sells":int(sells)})
    elif buys+sells>=20 and buys>=3*max(1,sells):
        alerts.append({"kind":"BUY_HEAVY_ACTIVITY","level":"NOTICE","m5_buys":int(buys),"m5_sells":int(sells)})
    return alerts
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
            row={"chain":chain,"token":address,"pair":p.get("pairAddress"),"first_seen_utc":previous_row.get("first_seen_utc",dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat()),"last_seen_utc":dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),"pair_age_hours":round(age_h,2),"liquidity_usd":(p.get("liquidity") or {}).get("usd"),"volume_h24_usd":(p.get("volume") or {}).get("h24"),"status":"OBSERVE_ONLY_NOT_SAFETY_APPROVED","txns_m5_buys":(p.get("txns") or {}).get("m5",{}).get("buys"),"txns_m5_sells":(p.get("txns") or {}).get("m5",{}).get("sells")}
            row["snapshot_comparison"]=compare(previous_row,row)
            row["risk_alerts"]=risk_alerts(previous_row,row,row["snapshot_comparison"])
            observed[key]=row
        except Exception as exc:errors.append({"token":key,"error":str(exc)[:160]})
    # Retain earlier observations for 7 days for comparisons without pretending continuous coverage.
    for key,row in previous.items():
        if key not in observed:
            try:
                age=(now-dt.datetime.fromisoformat(row["last_seen_utc"]).timestamp())/3600
                if age<168:observed[key]=row
            except (KeyError,ValueError,TypeError):pass
    result={"generated_at_utc":dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),"mode":"DISCOVERY_ONLY","coverage":"Sampled latest token profiles, NOT exhaustive or real-time","new_observations":sum(k not in previous for k in observed),"comparable_snapshots":sum(row.get("snapshot_comparison",{}).get("status")=="COMPARABLE" for row in observed.values()),"checked_tokens":len(observed),"liquidity_drop_alerts":sum(any(a["kind"]=="LIQUIDITY_DROP" for a in row.get("risk_alerts",[])) for row in observed.values()),"sell_heavy_alerts":sum(any(a["kind"]=="SELL_HEAVY_ACTIVITY" for a in row.get("risk_alerts",[])) for row in observed.values()),"errors":errors[:10],"tokens":observed}
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("EARLY_WATCH_SUMMARY="+json.dumps({k:v for k,v in result.items() if k!="tokens"},sort_keys=True))
if __name__=="__main__":main()
