"""Whale Watch: public BNB block native BNB transfers, research-only.
No keys, subscriptions, wallets, token trades, or production-state writes.
A single latest block snapshot is NOT full whale surveillance.
"""
import json,time,urllib.request,datetime
RPC="https://bsc-dataseed.binance.org/"
THRESHOLD_BNB=1000
def rpc(method,params):
    payload=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RPC,data=payload,headers={"Content-Type":"application/json","User-Agent":"Cuvar500-WhaleWatch/1"})
    with urllib.request.urlopen(req,timeout=15) as resp:
        data=json.load(resp)
    if "error" in data or "result" not in data:raise ValueError("RPC invalid response")
    return data["result"]
def inspect(block,threshold=THRESHOLD_BNB):
    if not isinstance(block,dict) or not isinstance(block.get("transactions"),list):raise ValueError("invalid block")
    found=[]
    for tx in block["transactions"]:
        amount=int(tx["value"],16)/1e18
        if amount>=threshold:
            found.append({"tx_hash":tx["hash"],"from":tx["from"],"to":tx.get("to"),
                          "bnb":round(amount,6),"category":"NATIVE_BNB_TRANSFER_NOT_TRADE"})
    return sorted(found,key=lambda x:-x["bnb"])
def main():
    block=rpc("eth_getBlockByNumber",["latest",True])
    if not block:raise ValueError("block missing")
    events=inspect(block)
    out={"mode":"RESEARCH_ONLY","source":"public BSC RPC","network":"BNB Smart Chain",
      "block_number":int(block["number"],16),"block_time_utc":datetime.datetime.fromtimestamp(int(block["timestamp"],16),datetime.timezone.utc).isoformat(),
      "checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "threshold_bnb":THRESHOLD_BNB,"large_native_transfers":events,
      "coverage":"one BNB Smart Chain block only; native BNB transfers, not BEP20 token transfers or Solana",
      "warning":"Large transfers are not necessarily whale buys/sells; destination classification unavailable."}
    print("FREE_WHALE_WATCH="+json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
