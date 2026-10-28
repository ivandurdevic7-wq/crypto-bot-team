"""Read-only real RPC adapter for Whale Watch alerts. Conservative, bounded and fail-closed."""
import datetime,json,urllib.request
from dex_swap_research import request,SWAP_TOPIC
from dex_swap_validation import call,address,WBNB
from whale_swap_alert import evaluate_receipt
from current_whale_quote import PAIR_URL

def verify_wbnb_pair(pool):
    if not isinstance(pool,str) or len(pool)!=42 or not pool.startswith("0x"):
        raise ValueError("Invalid pool")
    t0=address(call(pool,"0x0dfe1681"))
    t1=address(call(pool,"0xd21220a7"))
    if (t0==WBNB)==(t1==WBNB):raise ValueError("Not a single WBNB pool")
    return 0 if t0==WBNB else 1

def inspect_one(tx_hash,now_ts=None):
    receipt=request("eth_getTransactionReceipt",[tx_hash])
    if not receipt or receipt.get("status")!="0x1":
        return {"status":"UNVERIFIED_NO_ALERT","alerts":0}
    block=request("eth_getBlockByHash",[receipt["blockHash"],False])
    if not block or "timestamp" not in block:raise ValueError("Missing block timestamp")
    receipt["block_timestamp"]=int(block["timestamp"],16)
    now=int(datetime.datetime.now(datetime.timezone.utc).timestamp()) if now_ts is None else int(now_ts)
    if not 0<=now-receipt["block_timestamp"]<=120:
        return {"status":"STALE_NO_ALERT","alerts":0}
    logs=[log for log in receipt.get("logs",[]) if log.get("topics") and log["topics"][0].lower()==SWAP_TOPIC]
    if not logs:return {"status":"NO_SUPPORTED_SWAP","alerts":0}
    # No live alert is possible without on-chain token identity AND actual price feed.
    for log in logs:
        try:log["verified_wbnb_position"]=verify_wbnb_pair(log["address"])
        except (KeyError,ValueError,TypeError):pass
    req=urllib.request.Request(PAIR_URL,headers={"User-Agent":"Cuvar500-Research/1"})
    with urllib.request.urlopen(req,timeout=12) as resp:pairs=json.load(resp)
    return evaluate_receipt(receipt,pairs,now)

if __name__=="__main__":
    # Historical tx must be stale; diagnostic proof that latest prices are NOT applied.
    tx="0xabdef90a25f08bb5ae51c2803ed576c3c1162bc359aed15350aaffab4ae34772"
    outcome=inspect_one(tx)
    if outcome["status"]!="STALE_NO_ALERT":raise ValueError("Historical transaction was not rejected")
    print("REAL_RECEIPT_GUARD="+json.dumps(outcome,sort_keys=True))
