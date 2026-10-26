"""PAPER portfolio drawdown accounting. UTC daily/weekly anchors and fail-closed quotes."""
from datetime import datetime, timezone
from math import isfinite

def metrics(state, now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("UTC timezone required")
    if state.get("mode")!="PAPER":raise ValueError("Only PAPER permitted")
    cash=state.get("cash_eur")
    if not isinstance(cash,(int,float)) or not isfinite(cash) or cash<0:raise ValueError("Invalid cash")
    total=float(cash)
    for p in state.get("positions",{}).values():
        if p.get("quote_verified") is not True:raise ValueError("Unverified position price")
        qty=p.get("qty");price=p.get("last_eur")
        if any(not isinstance(v,(int,float)) or not isfinite(v) or v<0 for v in (qty,price)):
            raise ValueError("Invalid quote")
        total+=qty*price
    day=now.date().isoformat()
    week=f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
    history=state.setdefault("risk_history",{"days":{},"weeks":{},"peak_eur":total})
    days=history.setdefault("days",{})
    weeks=history.setdefault("weeks",{})
    days.setdefault(day,{"start_eur":total})
    weeks.setdefault(week,{"start_eur":total})
    history["peak_eur"]=max(float(history.get("peak_eur",total)),total)
    def loss(start):
        if not isinstance(start,(int,float)) or start<=0 or not isfinite(start):
            raise ValueError("Invalid capital baseline")
        return max(0,(start-total)*100/start)
    return {"equity_eur":round(total,6),"cash_eur":cash,
            "daily_loss_pct":round(loss(days[day]["start_eur"]),5),
            "weekly_loss_pct":round(loss(weeks[week]["start_eur"]),5),
            "drawdown_pct":round(loss(history["peak_eur"]),5),
            "daily_halt":loss(days[day]["start_eur"])>=5,
            "weekly_halt":loss(weeks[week]["start_eur"])>=10}
def test():
    s={"mode":"PAPER","cash_eur":200,"positions":{}}
    a=metrics(s,datetime(2026,10,26,tzinfo=timezone.utc))
    assert a["daily_loss_pct"]==0 and a["weekly_loss_pct"]==0
    s["cash_eur"]=189
    b=metrics(s,datetime(2026,10,26,tzinfo=timezone.utc))
    assert b["daily_halt"] and not b["weekly_halt"]
    s["cash_eur"]=179
    c=metrics(s,datetime(2026,10,26,tzinfo=timezone.utc))
    assert c["weekly_halt"]
    s["positions"]={"0xabc":{"qty":1,"last_eur":1}}
    try:metrics(s)
    except ValueError:pass
    else:raise AssertionError("Missing quote certification must fail closed")
    print("V9 portfolio accounting PASS: daily 5%, weekly 10%, missing quotes blocked")
if __name__=="__main__":test()
