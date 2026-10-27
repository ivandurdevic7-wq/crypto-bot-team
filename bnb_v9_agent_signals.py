"""V8-derived observed signals for V9, without fabricated evidence."""
import math
from bnb_master_v9_policy import WEIGHTS
def num(v):
    try:
        if isinstance(v,bool):return None
        x=float(v)
        return x if math.isfinite(x) else None
    except (ValueError,TypeError,OverflowError):return None
def evaluate(f):
    a=dict.fromkeys(WEIGHTS)
    checks={"momentum":("change_1h_pct",lambda x:1<=x<=8),
            "volume":("volume_24h_usd",lambda x:x>=50000),
            "liquidity":("liquidity_usd",lambda x:x>=100000),
            "age":("age_min",lambda x:x>=30),
            "market":("bnb_change_24h_pct",lambda x:x>-6)}
    for k,(field,predicate) in checks.items():
        x=num(f.get(field))
        if x is not None:a[k]=1.0 if predicate(x) else -1.0
    buys=num(f.get("buys_h1"));sells=num(f.get("sells_h1"))
    if buys is not None and sells is not None and buys>=0 and sells>=0 and buys+sells>=20:
        a["order_flow"]=1.0 if buys>sells else -1.0
    holders=num(f.get("holders"));lock=num(f.get("lp_locked_pct"))
    if holders is not None and lock is not None:
        a["holders_lp"]=1.0 if holders>=100 and lock>=80 else -1.0
    return a
def test():
    r=evaluate({"change_1h_pct":3,"volume_24h_usd":60000,"liquidity_usd":120000})
    assert r["momentum"]==r["volume"]==r["liquidity"]==1
    assert r["order_flow"] is None and r["social"] is None
    assert all(v is None for v in evaluate({}).values())
    assert evaluate({"buys_h1":30,"sells_h1":10})["order_flow"]==1
    assert evaluate({"buys_h1":5,"sells_h1":2})["order_flow"] is None
    print("PASS: real-data V8 rules; unknown V9 agents remain unknown")
if __name__=="__main__":test()
