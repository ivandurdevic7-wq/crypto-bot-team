"""BNB V9 read-only market scanner. PAPER only; no simulated buys without approval."""
import json, urllib.request, urllib.error, time
from datetime import datetime, timezone
from pathlib import Path
from bnb_master_v9_policy import decide, START_EUR, WEIGHTS

BASE="https://api.geckoterminal.com/api/v2"
STATE=Path(__file__).with_name("bnb_v9_scan.json")
def request(url):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"BNB-V9-Paper-Research/1.0"})
    with urllib.request.urlopen(req,timeout=12) as response:
        return json.load(response)
def scan():
    stamp=datetime.now(timezone.utc).isoformat(timespec="seconds")
    results=[];warnings=[];total=0
    try:
        source=request(BASE+"/networks/bsc/trending_pools?page=1&include=base_token,dex")
        includes={x.get("id"):x.get("attributes",{}) for x in source.get("included",[])}
        for pool in source.get("data",[])[:20]:
            rel=pool.get("relationships") or {}
            dex=((rel.get("dex") or {}).get("data") or {}).get("id","")
            if "pancake" not in str(dex).lower():continue
            tokenref=((rel.get("base_token") or {}).get("data") or {}).get("id")
            tok=includes.get(tokenref,{})
            address=tok.get("address")
            if not address or not str(address).startswith("0x"):continue
            attr=pool.get("attributes") or {}
            entry={"symbol":tok.get("symbol"),"address":address,
                  "price_usd":attr.get("base_token_price_usd"),
                  "liquidity_usd":attr.get("reserve_in_usd"),
                  "volume_24h_usd":(attr.get("volume_usd") or {}).get("h24"),
                  "change_1h_pct":(attr.get("price_change_percentage") or {}).get("h1")}
            # Missing security fields MUST remain missing, never assumed safe.
            assessment=decide(entry,{},{"equity_eur":START_EUR,"cash_eur":START_EUR,
                "open_positions":0,"daily_loss_pct":0,"weekly_loss_pct":0,"loss_streak":0})
            assert assessment["action"]=="SKIP"
            results.append(assessment);total+=1
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        warnings.append("Source unavailable: "+str(exc)[:120])
    state={"mode":"PAPER","version":"9.0 research-only","at_utc":stamp,
           "initial_eur":START_EUR,"cash_eur":START_EUR,"positions":[],"trades":[],
           "screened":total,"decisions":results,"warnings":warnings,
           "status":"RESEARCH_ONLY" if total else "NO_DATA"}
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"V9 {state['status']}; candidates examined {total}; purchases 0; no LIVE orders")
if __name__=="__main__":scan()
