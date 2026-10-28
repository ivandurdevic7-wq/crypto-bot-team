"""Research-only join of verified PancakeSwap V2 WBNB events and current quote.
Fail closed: a quote is valid only for recent observed swaps; no historical repricing.
"""
import json,datetime
from decimal import Decimal
from dex_swap_research import parse,SWAP_TOPIC
from current_whale_quote import assess_current

def evaluate_receipt(receipt,pairs,now_timestamp,max_age_seconds=120):
    if not receipt or receipt.get("status")!="0x1":
        return {"status":"UNVERIFIED_NO_ALERT","reason":"missing_or_failed_receipt"}
    age=int(now_timestamp)-int(receipt.get("block_timestamp",0))
    if age<0 or age>max_age_seconds:
        return {"status":"STALE_NO_ALERT","age_seconds":age}
    out=[]
    for log in receipt.get("logs",[]):
        if not log.get("topics") or log["topics"][0].lower()!=SWAP_TOPIC:continue
        try:
            event=parse(log)
            # NOTE: only a WBNB pair is eligible. Token0/1 identity MUST be
            # verified upstream by eth_call; never assume a Swap log is WBNB.
            if log.get("verified_wbnb_position") not in (0,1):
                out.append({"status":"UNVERIFIED_POOL_NO_ALERT"});continue
            side=log["verified_wbnb_position"]
            ins=int(event[f"amount{side}_in_raw"])
            outs=int(event[f"amount{side}_out_raw"])
            if bool(ins)==bool(outs):
                out.append({"status":"AMBIGUOUS_DIRECTION_NO_ALERT"});continue
            rating=assess_current(str(ins or outs),pairs)
            rating["side"]="TOKEN_BOUGHT_WITH_WBNB" if ins else "TOKEN_SOLD_FOR_WBNB"
            rating["tx_hash"]=event["tx_hash"]
            out.append(rating)
        except (ValueError,KeyError,TypeError) as exc:
            out.append({"status":"UNVERIFIED_NO_ALERT","reason":type(exc).__name__})
    return {"status":"RESEARCH_ONLY","events":out,"alerts":sum(x.get("status")=="LARGE_SWAP_RESEARCH_ALERT" for x in out)}
