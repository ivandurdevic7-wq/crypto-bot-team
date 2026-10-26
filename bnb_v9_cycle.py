"""BNB V9 research cycle with real GeckoTerminal quotes and PAPER-only ledger.
No transactions, no wallets. Missing sell simulation blocks sale, missing buy security blocks purchase.
"""
import json, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone
from bnb_v9_paper_ledger import initial, value
from bnb_v9_market_scan import request as market_request, BASE
from bnb_master_v9_policy import decide, START_EUR
from bnb_v9_risk import metrics
from bnb_v9_security_sources import check as security_check

FILE=Path(__file__).with_name("bnb_v9_cycle_status.json")
def run():
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        state=json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else initial()
        if state.get("mode")!="PAPER":raise ValueError("LIVE blocked")
        if not isinstance(state.get("positions"),dict):raise ValueError("Invalid positions")
        if not isinstance(state.get("trades"),list):raise ValueError("Invalid trades")
    except (OSError,ValueError,TypeError,json.JSONDecodeError):
        # Never silently reset an existing corrupted ledger.
        if FILE.exists():raise
        state=initial()
    decisions=[];errors=[];count=0;security_checked=0
    rotation=datetime.now(timezone.utc).hour % 6
    for pos in state['positions'].values():pos['quote_verified']=False
    # Refresh existing positions with actual quotes where available; do not fake exits.
    for addr,pos in list(state["positions"].items()):
        try:
            pairs=market_request(BASE+"/networks/bsc/tokens/"+addr+"/pools?page=1")
            pools=pairs.get("data") or []
            observed=[]
            for pool in pools:
                a=pool.get("attributes") or {}
                price=float(a.get("base_token_price_usd") or 0)
                liq=float(a.get("reserve_in_usd") or 0)
                if price>0 and liq>0:observed.append((liq,price))
            if not observed:raise ValueError("No verified quote")
            # USD price is reported, but EUR conversion is required before marking a EUR position.
            fx=market_request("https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD")
            rate=float(fx["rates"]["USD"])
            if rate<=0:raise ValueError("Missing FX")
            price=max(observed)[1]/rate
            pos["last_eur"]=price
            pos["quote_verified"]=True
            pos["peak_eur"]=max(float(pos.get("peak_eur",price)),price)
            # No sale: honeypot simulation and fresh executable route not yet connected.
            from bnb_v9_exits import exit_signal
            signal,_=exit_signal(pos,{"price_eur":price})
            if signal not in ("HOLD","NO_DATA"):
                decisions.append({"token":pos.get("token"),"action":"SELL_PENDING_VERIFICATION","reason":signal})
        except Exception as e:
            errors.append("Position "+addr[:10]+": "+str(e)[:100])
    try:
        data=market_request(BASE+"/networks/bsc/trending_pools?page=1&include=base_token,dex")
        includes={x.get("id"):x.get("attributes",{}) for x in data.get("included",[])}
        for pool in (data.get("data") or [])[:20]:
            rel=pool.get("relationships") or {}
            dex=((rel.get("dex") or {}).get("data") or {}).get("id","")
            if "pancake" not in str(dex).lower():continue
            t=((rel.get("base_token") or {}).get("data") or {}).get("id")
            meta=includes.get(t,{})
            address=meta.get("address")
            if not isinstance(address,str) or not address.startswith("0x") or len(address)!=42:continue
            attr=pool.get("attributes") or {}
            fields={"symbol":meta.get("symbol"),"address":address,"price_usd":attr.get("base_token_price_usd"),
                    "liquidity_usd":attr.get("reserve_in_usd"),
                    "volume_24h_usd":(attr.get("volume_usd") or {}).get("h24"),
                    "change_1h_pct":(attr.get("price_change_percentage") or {}).get("h1")}
            try: risk=metrics(state)
            except ValueError as error:
                risk={"equity_eur":value(state),"daily_loss_pct":None,"weekly_loss_pct":None}
                errors.append("Risk accounting: "+str(error))
            portfolio={"equity_eur":risk["equity_eur"],"cash_eur":state["cash_eur"],
                       "open_positions":len(state["positions"]),"daily_loss_pct":risk["daily_loss_pct"],
                       "weekly_loss_pct":risk["weekly_loss_pct"],"loss_streak":state.get("loss_streak")}
            if count % 6 == rotation and security_checked < 3:
                security_checked+=1
                proof=security_check(address)
                fields.update(proof["data"])
                if not proof["safe"]:
                    errors.append("Security "+address[:10]+": "+", ".join(proof["reasons"][:2]))
            decision=decide(fields,{},portfolio)
            # Insufficient information means SKIP, and never a paper buy.
            if decision["action"]!="SKIP":raise AssertionError("Unverified token cannot pass")
            decisions.append(decision);count+=1
    except Exception as e:errors.append("Discovery: "+str(e)[:120])
    try: state["risk"]=metrics(state)
    except ValueError as error:
        state["risk"]={"status":"BLOCKED","reason":str(error)}
        errors.append("Risk accounting: "+str(error))
    state["scan"]={"security_checked":security_checked,"at_utc":now,"screened":count,"decisions":decisions[-60:],
                   "errors":errors,"status":"RESEARCH_ONLY" if count else "NO_DATA"}
    state["estimated_eur"]=round(value(state),2)
    FILE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"mode":"PAPER","screened":count,"positions":len(state["positions"]),
                      "new_buys":0,"status":state["scan"]["status"],"errors":errors},ensure_ascii=False))
if __name__=="__main__":run()
