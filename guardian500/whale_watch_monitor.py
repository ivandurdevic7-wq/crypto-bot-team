"""Bounded Whale Watch observer (research only; no trading).
Samples up to three confirmed BSC blocks with max 35 tx each, writes JSON.
Do not interpret incomplete samples as full chain coverage.
"""
import json,datetime,os
from dex_swap_research import request,SWAP_TOPIC
from real_whale_adapter import inspect_one

def observe(block_count=3,tx_limit=35):
    if not (1<=block_count<=3 and 1<=tx_limit<=35):
        raise ValueError("invalid bounds")
    head=int(request("eth_blockNumber",[]),16)
    now=int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    records=[];failures=0;checked=0
    for height in range(head-2,head-2-block_count,-1):
        block=request("eth_getBlockByNumber",[hex(height),False])
        if not block or not isinstance(block.get("transactions"),list):
            raise ValueError("missing block; fail closed")
        for txhash in block["transactions"][:tx_limit]:
            checked+=1
            try:
                receipt=request("eth_getTransactionReceipt",[txhash])
                if receipt is None:raise ValueError("missing receipt")
                if not any(log.get("topics") and log["topics"][0].lower()==SWAP_TOPIC for log in receipt.get("logs",[])):
                    continue
                result=inspect_one(txhash,now_ts=now)
                records.append({"tx":txhash,"block":height,"status":result.get("status"),
                                "alerts":result.get("alerts",0),"events":result.get("events",[])})
            except Exception:
                failures+=1
    complete=failures==0
    # Explicit no alerts when any required receipt failed.
    result={"mode":"RESEARCH_ONLY","coverage":"sampled first 35 transactions of up to 3 recent blocks",
            "blocks_checked":block_count,"transactions_checked":checked,
            "matching_swap_receipts":len(records),"failures":failures,
            "status":"SAMPLE_COMPLETE" if complete else "INCOMPLETE_NO_ALERT",
            "observations":records,"alert_count":sum(x["alerts"] for x in records) if complete else 0,
            "generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "orders_enabled":False,"warning":"Not comprehensive chain monitoring; USD values indicative and unfit for trade execution."}
    return result

if __name__=="__main__":
    out=observe()
    path="guardian500/whale_watch_snapshot.json"
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:json.dump(out,f,indent=2)
    print("WHALE_MONITOR="+json.dumps({k:v for k,v in out.items() if k!="observations"},sort_keys=True))
