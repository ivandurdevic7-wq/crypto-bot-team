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
from bnb_v9_quote_check import compare as crosscheck
from bnb_v9_paper_ledger import buy as paper_buy
from bnb_v9_exits import paper_exit

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
            # Always assess TP/SL. A sell requires independent verified route,
            # sellability and actual fee/impact/gas inputs; missing evidence blocks fill.
            from bnb_v9_exits import exit_signal
            market={"price_eur":price}
            signal,_=exit_signal(pos,market)
            if signal not in ("HOLD","NO_DATA"):
                proof=security_check(addr)
                quote_check=crosscheck(addr, max(observed)[1], max(observed)[0])
                quote={"price_eur":price,"sell_tax_pct":proof["data"].get("sell_tax_pct"),
                       "impact_pct":None,"slippage_pct":None,"gas_eur":None,
                       "sell_simulation_ok":proof["data"].get("honeypot_sell_ok") is True,
                       "fresh_quote":quote_check["verified"]}
                state,execution=paper_exit(state,addr,market,quote)
                decisions.append({"token":pos.get("token"),"action":execution,
                                  "requested_exit":signal,
                                  "reason":"No verified executable sell costs/route" if execution.startswith("SELL_BLOCKED") else execution})
        except Exception as e:
            errors.append("Position "+addr[:10]+": "+str(e)[:100])
    # BNB market veto from actual WBNB pool data; missing market quote remains a veto.
    bnb_change_24h_pct=None
    try:
        wbnb=market_request(BASE+"/networks/bsc/tokens/0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c/pools?page=1")
        choices=[]
        for bp in wbnb.get("data") or []:
            ba=bp.get("attributes") or {}
            liquidity=float(ba.get("reserve_in_usd") or 0)
            change=float((ba.get("price_change_percentage") or {}).get("h24"))
            if liquidity>=30000 and __import__("math").isfinite(change):
                choices.append((liquidity,change))
        if choices:bnb_change_24h_pct=max(choices)[1]
    except (ValueError,TypeError,OverflowError,KeyError,AttributeError,urllib.error.URLError) as ex:
        errors.append("BNB market regime unavailable: "+str(ex)[:90])
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
            age_min=None
            created=attr.get("pool_created_at")
            if created:
                try:
                    timestamp=datetime.fromisoformat(str(created).replace("Z","+00:00"))
                    if timestamp.tzinfo is not None:
                        elapsed=(datetime.now(timezone.utc)-timestamp).total_seconds()/60
                        if elapsed>=0: age_min=round(elapsed,2)
                except (ValueError, TypeError, OverflowError):pass
            fields={"symbol":meta.get("symbol"),"address":address,"price_usd":attr.get("base_token_price_usd"),
                    "liquidity_usd":attr.get("reserve_in_usd"),"age_min":age_min,
                    "volume_24h_usd":(attr.get("volume_usd") or {}).get("h24"),
                    "change_1h_pct":(attr.get("price_change_percentage") or {}).get("h1"),
                    "bnb_change_24h_pct":bnb_change_24h_pct}
            try: risk=metrics(state)
            except ValueError as error:
                risk={"equity_eur":value(state),"daily_loss_pct":None,"weekly_loss_pct":None}
                errors.append("Risk accounting: "+str(error))
            portfolio={"equity_eur":risk["equity_eur"],"cash_eur":state["cash_eur"],
                       "open_positions":len(state["positions"]),"daily_loss_pct":risk["daily_loss_pct"],
                       "weekly_loss_pct":risk["weekly_loss_pct"],"loss_streak":state.get("loss_streak",0 if not state["trades"] else None),
                       "halted":risk.get("daily_halt",True) or risk.get("weekly_halt",True)}
            if count % 6 == rotation and security_checked < 3:
                security_checked+=1
                proof=security_check(address)
                fields.update(proof["data"])
                pool_address=attr.get("address") or ((pool.get("relationships") or {}).get("pool") or {}).get("data",{}).get("id") or str(pool.get("id","")).removeprefix("bsc_")
                quotes=crosscheck(address,fields["price_usd"],fields["liquidity_usd"],pool_address=pool_address)
                if not quotes["verified"]:
                    errors.append("Quote "+address[:10]+": "+", ".join(quotes["reasons"][:2]))
                if not proof["safe"]:
                    errors.append("Security "+address[:10]+": "+", ".join(proof["reasons"][:2]))
                fields["fresh_quotes_ok"]=quotes["verified"]
                # Never invent missing LP locks, ownership or market-risk evidence.
            decision=decide(fields,{},portfolio)
            if decision["action"]=="PAPER_BUY_READY":
                # Execution is guarded by independently confirmed sell simulation,
                # verified risk metrics and a freshly priced EUR executable quote.
                # Missing inputs are explicitly rejected by paper_buy.
                state,execution=paper_buy(state,decision,{}, {})
                decisions.append({"token":decision["token"],"action":execution,
                                  "reason":"Executable quote and verified costs unavailable; no simulated fill" if execution!="PAPER_BUY" else "Verified PAPER fill"})
            decisions.append(decision);count+=1
    except Exception as e:errors.append("Discovery: "+str(e)[:120])
    solana_screened=0
    try:
        sol=market_request(BASE+"/networks/solana/trending_pools?page=1&include=base_token,dex")
        sol_includes={x.get("id"):x.get("attributes",{}) for x in sol.get("included",[])}
        for pool in (sol.get("data") or [])[:20]:
            token_ref=((pool.get("relationships") or {}).get("base_token") or {}).get("data") or {}
            meta=sol_includes.get(token_ref.get("id"),{})
            addr=meta.get("address")
            if not isinstance(addr,str) or not (32<=len(addr)<=44):continue
            a=pool.get("attributes") or {}
            decisions.append({"action":"SKIP","chain":"solana",
                "token":meta.get("symbol") or "?","address":addr,
                "price_usd":a.get("base_token_price_usd"),
                "liquidity_usd":a.get("reserve_in_usd"),
                "reason":"Solana token risk, mint/freeze, holders and executable route not independently verified",
                "vetoes":["Solana security/execution verification unavailable"],
                "data_gaps":["solana_security","solana_execution"]})
            solana_screened+=1
    except Exception as e:
        errors.append("Solana discovery: "+str(e)[:120])
    try: state["risk"]=metrics(state)
    except ValueError as error:
        state["risk"]={"status":"BLOCKED","reason":str(error)}
        errors.append("Risk accounting: "+str(error))
    # Distinguish unimplemented execution evidence from unsafe market candidates.
    execution_blockers=[
        "Fresh executable buy/sell route with EUR quote, price impact, slippage and gas",
        "Verified LP lock and creator/holder concentration for candidates",
        "Independent manipulation, sniper and market-risk evidence",
        "Solana-specific token security and executable route",
        "Real agent scores derived from verified observations"
    ]
    audit=state.setdefault("decision_journal",[])
    if not isinstance(audit,list):raise ValueError("Corrupt decision journal")
    for item in decisions:
        audit.append({"at_utc":now,"chain":item.get("chain","bsc"),
                      "action":item.get("action"),"token":item.get("token"),
                      "address":item.get("address"),
                      "reasons":item.get("vetoes") or [item.get("reason")] if item.get("reason") else item.get("vetoes",[])})
    # Bound the retained journal so GitHub cycle commits stay manageable.
    state["decision_journal"]=audit[-1000:]
    buys_this_cycle=sum(d.get("action")=="PAPER_BUY" for d in decisions)
    state["scan"]={"bnb_change_24h_pct":bnb_change_24h_pct,"execution_ready":False,"execution_blockers":execution_blockers,"solana_screened":solana_screened,"security_checked":security_checked,"at_utc":now,"screened":count,"decisions":decisions[-60:],
                   "errors":errors,"status":"PAPER_ACTIVE" if buys_this_cycle else ("RESEARCH_ONLY" if count or solana_screened else "NO_DATA"),
                   "new_buys":buys_this_cycle}
    # Never publish a stale portfolio value as a verified current balance.
    if state["risk"].get("status")=="BLOCKED":
        state["estimated_eur"]=None
        state["valuation_status"]="UNVERIFIED"
    else:
        state["estimated_eur"]=round(state["risk"]["equity_eur"],2)
        state["valuation_status"]="VERIFIED"
    FILE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"mode":"PAPER","screened":count,"solana_screened":solana_screened,"positions":len(state["positions"]),
                      "new_buys":buys_this_cycle,"status":state["scan"]["status"],"errors":errors},ensure_ascii=False))
if __name__=="__main__":run()
