"""Historical known PancakeSwap swap: verify pool assets and decimals.
Read-only research. Token metadata is queried at latest state, not historic USD.
"""
import json
from dex_swap_research import request, parse, SWAP_TOPIC
from dex_swap_validation import call,address,WBNB,decimals
TX="0xabdef90a25f08bb5ae51c2803ed576c3c1162bc359aed15350aaffab4ae34772"
def inspect():
    receipt=request("eth_getTransactionReceipt",[TX])
    if not receipt or receipt.get("status")!="0x1":raise ValueError("missing or failed transaction")
    swaps=[parse(x) for x in receipt["logs"] if x.get("topics") and x["topics"][0].lower()==SWAP_TOPIC]
    if len(swaps)!=1:raise ValueError("expected one verified swap")
    event=swaps[0]
    pool=event["pool"]
    t0=address(call(pool,"0x0dfe1681"))
    t1=address(call(pool,"0xd21220a7"))
    d0=decimals(t0)
    d1=decimals(t1)
    a=[int(event[f"amount{i}_{side}_raw"])/10**d for i,d in ((0,d0),(1,d1)) for side in ("in","out")]
    result={"transaction":TX,"pool":pool,
      "token0":t0,"token1":t1,"decimals0":d0,"decimals1":d1,
      "amount0_in":a[0],"amount0_out":a[1],"amount1_in":a[2],"amount1_out":a[3],
      "wbnb_is_token0":t0==WBNB,"wbnb_is_token1":t1==WBNB,
      "historical_usd":"UNAVAILABLE_NOT_ESTIMATED",
      "method":"onchain receipt and latest token decimals; no pricing, no order"}
    if (t0==WBNB)==(t1==WBNB):raise ValueError("unknown WBNB position")
    return result
if __name__=="__main__":print("HISTORICAL_SWAP_ASSETS="+json.dumps(inspect(),sort_keys=True))
