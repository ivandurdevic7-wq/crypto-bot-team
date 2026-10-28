"""Read-only DEX swap activity scanner: BNB Chain PancakeSwap V2.
One recent block only; no API keys and no token trades.
Swap events show pool activity, NOT identified whale wallets or directional buys.
"""
import json,urllib.request,datetime
RPC="https://bsc-dataseed.binance.org/"
SWAP_TOPIC="0xd78ad95fa46c994b6551d0da85fc275fe613ce37657a1e88d2b7a3c2a3a6e6"
# ERC20 pair Swap(address,uint256,uint256,uint256,uint256,address)
def request(method,params):
 req=urllib.request.Request(RPC,data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=20) as resp:result=json.load(resp)
 if result.get("error") or "result" not in result:raise ValueError("RPC error")
 return result["result"]
def parse(log):
 if not log.get("topics") or log["topics"][0].lower()!=SWAP_TOPIC:raise ValueError("Not a matching swap")
 raw=log.get("data","")
 if not isinstance(raw,str) or len(raw)!=2+64*4 or not raw.startswith("0x"):raise ValueError("Invalid swap data")
 amounts=[int(raw[2+i*64:2+(i+1)*64],16) for i in range(4)]
 return {"pool":log["address"],"tx_hash":log["transactionHash"],"amount0_in_raw":str(amounts[0]),"amount1_in_raw":str(amounts[1]),"amount0_out_raw":str(amounts[2]),"amount1_out_raw":str(amounts[3]),"status":"UNPRICED_SWAP_NOT_WHALE_CLASSIFIED"}
def main():
 height=int(request("eth_blockNumber",[]),16)-2
 if height<1:raise ValueError("Bad height")
 h=hex(height)
 logs=request("eth_getLogs",[{"fromBlock":h,"toBlock":h,"topics":[SWAP_TOPIC]}])
 if not isinstance(logs,list):raise ValueError("logs missing")
 swaps=[]
 errors=0
 for log in logs[:250]:
  try:swaps.append(parse(log))
  except (KeyError,ValueError,TypeError):errors+=1
 result={"mode":"RESEARCH_ONLY","chain":"bsc","block":height,"swaps_sampled":len(swaps),"parse_errors":errors,
         "swaps":swaps[:10],"source":"public BNB RPC eth_getLogs",
         "limitation":"Single block; pool-specific token decimals, token prices, pool identity and wallet attribution NOT verified. No USD size or buy/sell labels."}
 print("WHALE_DEX_AUDIT="+json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
