"""PAPER ledger: simulated fills only; NEVER sends orders or accesses wallets."""
import copy, math
from datetime import datetime, timezone
from bnb_master_v9_policy import AUTONOMOUS_PAPER, LIVE_ENABLED
def num(x):
    try:
        if isinstance(x,bool):return None
        v=float(x)
        return v if math.isfinite(v) else None
    except (TypeError,ValueError,OverflowError):return None
def initial():return {"mode":"PAPER","cash_eur":200.0,"positions":{},"trades":[],"loss_streak":0}
def value(s):return s["cash_eur"]+sum(p["qty"]*p["last_eur"] for p in s["positions"].values())
def buy(state,decision,quote,checks):
    s=copy.deepcopy(state)
    if LIVE_ENABLED or not AUTONOMOUS_PAPER or s.get("mode")!="PAPER":return s,"BLOCKED"
    if decision.get("action")!="PAPER_BUY_READY" or decision.get("vetoes") or decision.get("data_gaps"):return s,"SKIP: risk decision"
    required=("fresh_quote","security_rechecked","sell_simulation_ok","liquidity_ok","bnb_market_ok")
    if any(checks.get(k) is not True for k in required):return s,"SKIP: final checks"
    addr=decision.get("address")
    if not isinstance(addr,str) or len(addr)!=42 or addr in s["positions"] or len(s["positions"])>=4:return s,"SKIP: positions"
    size=num(decision.get("size_eur"))
    price=num(quote.get("price_eur")); impact=num(quote.get("impact_pct"))
    slip=num(quote.get("slippage_pct")); tax=num(quote.get("buy_tax_pct"));gas=num(quote.get("gas_eur"))
    if any(v is None for v in (size,price,impact,slip,tax,gas)):return s,"SKIP: quote gaps"
    if not(size>0 and price>0 and gas>=0 and 0<=impact<=1.5 and 0<=slip<=3 and 0<=tax<=8):return s,"SKIP: quote limits"
    total=value(s)
    if size>min(20,total*.2,total*.015/.15) or size+gas>s["cash_eur"]-total*.4:return s,"SKIP: capital"
    qty=size*(1-.0025)*(1-tax/100)/(price*(1+(impact+slip)/100))
    s["cash_eur"]-=size+gas
    s["positions"][addr]={"qty":qty,"entry_eur":price,"last_eur":price,"peak_eur":price,"cost_eur":size+gas,"token":decision.get("token"),"opened_at":datetime.now(timezone.utc).isoformat(),"tp1":False,"tp2":False,"quote_verified":True,"realized_pnl_eur":0.0}
    s["trades"].append({"side":"BUY","address":addr,"eur":size+gas,"mode":"PAPER"})
    return s,"PAPER_BUY"
def sell(state,address,quote,reason,fraction=1):
    s=copy.deepcopy(state)
    if s.get("mode")!="PAPER" or address not in s["positions"]:return s,"SKIP: no position"
    price=num(quote.get("price_eur"));tax=num(quote.get("sell_tax_pct"))
    impact=num(quote.get("impact_pct"));slip=num(quote.get("slippage_pct"));gas=num(quote.get("gas_eur"))
    if any(v is None for v in (price,tax,impact,slip,gas)):return s,"SKIP: missing sale simulation"
    if not(price>0 and 0<=tax<=15 and 0<=impact<=10 and 0<=slip<=10 and gas>=0 and 0<fraction<=1):return s,"SKIP: sale limits"
    p=s["positions"][address]; qty=p["qty"]*fraction
    allocated_cost=p["cost_eur"]*fraction
    proceeds=qty*price*(1-(tax+impact+slip)/100)*(1-.0025)-gas
    if proceeds<0:return s,"SKIP: proceeds"
    s["cash_eur"]+=proceeds;p["qty"]-=qty;p["cost_eur"]*=1-fraction
    realized_pnl=round(proceeds-allocated_cost,8)
    p["realized_pnl_eur"]=round(p.get("realized_pnl_eur",0.0)+realized_pnl,8)
    # Streak counts completed losing positions, not partial TP fills.
    fully_closed=p["qty"]<1e-9
    if fully_closed:
        previous=s.get("loss_streak",0)
        s["loss_streak"]=(previous+1 if p["realized_pnl_eur"]<0 else 0) if isinstance(previous,int) and previous>=0 else None
    if p["qty"]<1e-9:del s["positions"][address]
    s["trades"].append({"side":"SELL","address":address,"qty":qty,"eur":proceeds,
                        "realized_pnl_eur":realized_pnl,"fully_closed":fully_closed,
                        "reason":reason,"mode":"PAPER"})
    return s,"PAPER_SELL"
def tests():
    base=initial();d={"action":"PAPER_BUY_READY","token":"TEST","address":"0x"+"a"*40,"vetoes":[],"data_gaps":[],"size_eur":20}
    q={"price_eur":1,"impact_pct":.2,"slippage_pct":.3,"buy_tax_pct":0,"gas_eur":.05}
    checks=dict.fromkeys(("fresh_quote","security_rechecked","sell_simulation_ok","liquidity_ok","bnb_market_ok"),True)
    assert buy(base,d,q,{})[1].startswith("SKIP")
    s,result=buy(base,d,q,checks)
    assert result=="PAPER_BUY" and base["cash_eur"]==200 and len(s["positions"])==1 and s["cash_eur"]>=80
    s,result=sell(s,d["address"],{"price_eur":1.25,"sell_tax_pct":0,"impact_pct":.2,"slippage_pct":.3,"gas_eur":.05},"TARGET",.3)
    assert result=="PAPER_SELL" and len(s["trades"])==2
    assert s["trades"][-1]["realized_pnl_eur"]>0 and s["loss_streak"]==0
    assert buy(initial(),{"action":"SKIP"},q,checks)[1].startswith("SKIP")
    # Profitable partial exit followed by a losing final exit: whole-position PnL decides streak.
    s2,_=buy(initial(),d,q,checks)
    s2,_=sell(s2,d["address"],{"price_eur":2,"sell_tax_pct":0,"impact_pct":0,"slippage_pct":0,"gas_eur":0},"TP",.5)
    s2,_=sell(s2,d["address"],{"price_eur":.6,"sell_tax_pct":0,"impact_pct":0,"slippage_pct":0,"gas_eur":0},"EXIT",1)
    assert s2["loss_streak"]==0
    print("PAPER ledger tests PASS; LIVE blocked")
if __name__=="__main__":tests()
