"""Read-only PancakeSwap V2 swap sampler, strict pool and quote verification.
No orders, no production state, no guaranteed coverage; branch-only research. Only WBNB quote pairs
can be priced; BNB/USD reference from public market feed is informational.
"""
import json,urllib.request,time,math
from dex_swap_research import request,parse,SWAP_TOPIC
WBNB="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c".lower()
def call(to,data):
    result=request("eth_call",[{"to":to,"data":data},"latest"])
    if not isinstance(result,str) or not result.startswith("0x"):raise ValueError("missing contract metadata")
    return result
def address(result):
    if len(result)!=66:raise ValueError("bad address data")
    return "0x"+result[-40:].lower()
def decimals(token):
    result=call(token,"0x313ce567")
    d=int(result,16)
    if d>24:raise ValueError("unsupported decimals")
    return d
def bnb_usd():
    req=urllib.request.Request("https://api.dexscreener.com/latest/dex/search?q=WBNB",headers={"User-Agent":"Cuvar500-research/1"})
    with urllib.request.urlopen(req,timeout=12) as response:data=json.load(response)
    matches=[p for p in data.get("pairs",[]) if p.get("chainId")=="bsc" and
       p.get("baseToken",{}).get("address","").lower()==WBNB and
       float((p.get("liquidity") or {}).get("usd") or 0)>=1_000_000]
    if not matches:raise ValueError("No liquid WBNB USD reference")
    p=max(matches,key=lambda x:float(x["liquidity"]["usd"]))
    value=float(p["priceUsd"])
    if not math.isfinite(value) or value<=0:raise ValueError("Invalid WBNB quote")
    return value
def assess(event,price):
    pool=event["pool"]
    token0=address(call(pool,"0x0dfe1681"))
    token1=address(call(pool,"0xd21220a7"))
    if (token0==WBNB)==(token1==WBNB):
        return {"status":"UNPRICED_NOT_SINGLE_WBNB_PAIR"}
    wbnb0=token0==WBNB
    amount_in=int(event["amount0_in_raw"] if wbnb0 else event["amount1_in_raw"])
    amount_out=int(event["amount0_out_raw"] if wbnb0 else event["amount1_out_raw"])
    if bool(amount_in)==bool(amount_out):
        return {"status":"AMBIGUOUS_WBNB_DIRECTION"}
    qty=(amount_in or amount_out)/1e18
    return {"status":"INDICATIVE_WBNB_SWAP_ONLY","bnb_amount":round(qty,6),
       "indicative_usd":round(qty*price,2),
       "direction":"TOKEN_SOLD_FOR_WBNB" if amount_out else "TOKEN_BOUGHT_WITH_WBNB",
       "quote":"PUBLIC_USD_REFERENCE_NOT_EXECUTION_PRICE"}
def main():
    height=int(request("eth_blockNumber",[]),16)-2
    block=request("eth_getBlockByNumber",[hex(height),False])
    if not block or not isinstance(block.get("transactions"),list):raise ValueError("missing block")
    txs=block["transactions"][:80]
    swaps=[]
    for h in txs:
        rec=request("eth_getTransactionReceipt",[h])
        if rec is None:raise ValueError("receipt missing")
        if rec.get("status")!="0x1":continue
        for log in rec.get("logs",[]):
            if log.get("topics") and log["topics"][0].lower()==SWAP_TOPIC:
                swaps.append(parse(log))
    priced=[]
    if swaps:
        quote=bnb_usd()
        for swap in swaps[:15]:
            try:assessment=assess(swap,quote)
            except Exception as e:assessment={"status":"UNVERIFIED","reason":str(e)}
            priced.append({"tx_hash":swap["tx_hash"],"pool":swap["pool"],**assessment})
    print("DEX_SWAP_VALIDATION="+json.dumps({"mode":"RESEARCH_ONLY","block":height,
        "transactions_sampled":len(txs),"swaps_seen":len(swaps),"assessed":priced,
        "scope":"80 transactions in one block; not comprehensive; estimates are not trade signals"},sort_keys=True))
if __name__=="__main__":main()
