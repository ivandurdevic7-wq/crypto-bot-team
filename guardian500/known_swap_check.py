"""Historical known-transaction receipt regression check; read-only and fail-closed."""
import json
from dex_swap_research import request,parse,SWAP_TOPIC
TX="0xabdef90a25f08bb5ae51c2803ed576c3c1162bc359aed15350aaffab4ae34772"
def main():
 rec=request("eth_getTransactionReceipt",[TX])
 if not rec or rec.get("status")!="0x1":raise ValueError("Historical receipt unavailable or failed")
 swaps=[parse(log) for log in rec.get("logs",[]) if log.get("topics") and log["topics"][0].lower()==SWAP_TOPIC]
 if not swaps:raise ValueError("No matching PancakeSwap V2 swap logs in this specific receipt")
 print("KNOWN_SWAP_CHECK="+json.dumps({"tx":TX,"swap_count":len(swaps),"events":swaps[:3],"claim":"decoded raw event only; no price or wallet attribution"},sort_keys=True))
if __name__=="__main__":main()
