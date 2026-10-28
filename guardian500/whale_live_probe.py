"""Bounded live research probe, never trades or runs periodically.
Observes first 25 tx in one recent BSC block; no exhaustive coverage.
"""
import json,datetime
from dex_swap_research import request,SWAP_TOPIC
from real_whale_adapter import inspect_one

def scan():
    head=int(request("eth_blockNumber",[]),16)
    height=head-2
    block=request("eth_getBlockByNumber",[hex(height),False])
    if not block or not isinstance(block.get("transactions"),list):
        raise ValueError("missing block")
    txs=block["transactions"][:25]
    alerts=[];events=[];failures=0
    now=int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    for tx in txs:
        rec=request("eth_getTransactionReceipt",[tx])
        if rec is None:failures+=1;continue
        if not any(l.get("topics") and l["topics"][0].lower()==SWAP_TOPIC for l in rec.get("logs",[])):
            continue
        try:
            outcome=inspect_one(tx,now_ts=now)
            events.append({"tx":tx,"status":outcome.get("status"),"alerts":outcome.get("alerts",0)})
            if outcome.get("alerts",0)>0:alerts.append({"tx":tx,"outcome":outcome})
        except Exception:
            failures+=1
    status="INCOMPLETE_NO_ALERT" if failures else "BOUNDED_RESEARCH"
    return {"status":status,"block":height,"transactions_sampled":len(txs),
            "matching_receipts":len(events),"failures":failures,
            "alerts":alerts if not failures else [],"events":events,
            "scope":"one block, first 25 tx only; no recurring monitoring or trade signal"}
if __name__=="__main__":
    print("WHALE_LIVE_PROBE="+json.dumps(scan(),sort_keys=True))
