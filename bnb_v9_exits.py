"""Exit signals for V9 PAPER positions; no real orders.
Decisions use observed prices; actual SELL must pass separate executable quote checks.
"""
from datetime import datetime, timezone
from bnb_v9_paper_ledger import num, sell

def exit_signal(position, market, now=None):
    now=now or datetime.now(timezone.utc)
    price=num(market.get("price_eur"))
    entry=num(position.get("entry_eur"))
    peak=num(position.get("peak_eur"))
    if price is None or entry is None or entry<=0 or peak is None or peak<=0:
        return "NO_DATA", 0.0
    if any(market.get(k) is True for k in ("liquidity_crash","honeypot","owner_takeover",
                                             "rapid_dump","whale_dump","sell_tax_spike")):
        return "EMERGENCY",1.0
    gain=price/entry-1
    if gain<=-.15:return "STOP_LOSS",1.0
    if market.get("liquidity_drop_pct") is not None:
        fall=num(market["liquidity_drop_pct"])
        if fall is not None and fall>30:return "EMERGENCY_LIQUIDITY",1.0
    if not position.get("tp1") and gain>=.25:return "TAKE_PROFIT_25",.3
    if not position.get("tp2") and gain>=.50:return "TAKE_PROFIT_50",3/7
    if position.get("tp1") and gain<=0:return "BREAKEVEN",1.0
    if position.get("tp2") and price<=peak*.88:return "TRAILING_12",1.0
    opened=position.get("opened_at")
    if opened:
        try:
            age=(now-datetime.fromisoformat(opened)).total_seconds()
            if age>=86400 and gain<.10:return "TIME_STOP_24H",1.0
        except (ValueError,TypeError):return "NO_DATA",0.0
    return "HOLD",0.0

def paper_exit(state,address,market,quote):
    if state.get("mode")!="PAPER" or address not in state.get("positions",{}):
        return state,"SKIP: no PAPER position"
    position=state["positions"][address]
    signal,fraction=exit_signal(position,market)
    if signal in ("HOLD","NO_DATA"):return state,signal
    # Fail closed if simulated sell cannot be verified.
    if quote.get("sell_simulation_ok") is not True or quote.get("fresh_quote") is not True:
        return state,"SELL_BLOCKED: unverifiable exit"
    new,status=sell(state,address,quote,signal,fraction)
    if status=="PAPER_SELL" and address in new["positions"]:
        if signal=="TAKE_PROFIT_25":new["positions"][address]["tp1"]=True
        if signal=="TAKE_PROFIT_50":new["positions"][address]["tp2"]=True
    return new,status

def test():
    from bnb_v9_paper_ledger import initial,buy
    from datetime import timedelta
    a="0x"+"a"*40
    start=datetime(2026,10,26,tzinfo=timezone.utc)
    p={"entry_eur":1,"peak_eur":1.5,"opened_at":start.isoformat(),"tp1":False,"tp2":False}
    assert exit_signal(p,{"price_eur":.84})==("STOP_LOSS",1.0)
    assert exit_signal(p,{"price_eur":1.25})==("TAKE_PROFIT_25",.3)
    assert exit_signal(dict(p,tp1=True),{"price_eur":1.5})==("TAKE_PROFIT_50",3/7)
    assert exit_signal(dict(p,tp1=True,tp2=True),{"price_eur":1.3})==("TRAILING_12",1.0)
    assert exit_signal(p,{"price_eur":1.02},start+timedelta(hours=25))==("TIME_STOP_24H",1.0)
    assert exit_signal(p,{"price_eur":1.1,"honeypot":True})==("EMERGENCY",1.0)
    assert exit_signal(p,{})==("NO_DATA",0.0)
    state=initial();state["positions"][a]={"qty":10,"entry_eur":1,"last_eur":1,"peak_eur":1,"cost_eur":10,"token":"TEST"}
    no,status=paper_exit(state,a,{"price_eur":.8},{})
    assert status.startswith("SELL_BLOCKED") and no==state
    q={"price_eur":.8,"sell_tax_pct":0,"impact_pct":.2,"slippage_pct":.3,"gas_eur":.05,"sell_simulation_ok":True,"fresh_quote":True}
    yes,status=paper_exit(state,a,{"price_eur":.8},q)
    assert status=="PAPER_SELL" and a not in yes["positions"] and state["positions"][a]["qty"]==10
    print("V9 PAPER exits PASS, no LIVE orders")
if __name__=="__main__":test()
