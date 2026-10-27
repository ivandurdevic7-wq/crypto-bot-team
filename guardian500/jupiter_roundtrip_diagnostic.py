"""Manual read-only Jupiter V2 roundtrip diagnostic, never submits swaps."""
import json, os, urllib.parse, urllib.request, math
USDC="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOL="So11111111111111111111111111111111111111112"
def quote(a,b,amount,key):
    url="https://api.jup.ag/swap/v2/order?"+urllib.parse.urlencode({"inputMint":a,"outputMint":b,"amount":str(amount)})
    req=urllib.request.Request(url,headers={"x-api-key":key,"User-Agent":"Cuvar500-PAPER-Diagnostic"})
    with urllib.request.urlopen(req,timeout=12) as r:
        raw=r.read(131073)
    if len(raw)>131072: raise ValueError("response too large")
    d=json.loads(raw)
    if d.get("inputMint")!=a or d.get("outputMint")!=b or str(d.get("inAmount"))!=str(amount):
        raise ValueError("mint or amount mismatch")
    if d.get("transaction") is not None or d.get("errorCode") is not None:
        raise ValueError("not a clean quote-only response")
    out=d.get("outAmount")
    if not isinstance(out,str) or not out.isdigit() or int(out)<=0: raise ValueError("bad output")
    return int(out)
def main():
    key=os.environ.get("JUPITER_API_KEY","")
    if not key: raise ValueError("API key missing")
    received=quote(USDC,SOL,1_000_000,key)
    recovered=quote(SOL,USDC,received,key)
    loss=100*(1-recovered/1_000_000)
    print(json.dumps({"status":"QUOTE_ONLY_NOT_EXECUTION_SIMULATION","route":"USDC -> SOL -> USDC","model_roundtrip_loss_percent":round(loss,3),"entry_allowed":False,"trades_executed":0}))
    if recovered<950000: raise ValueError("roundtrip quote loss > 5%")
if __name__=="__main__":
    try: main()
    except Exception as e:
        print(json.dumps({"status":"FAIL_CLOSED","error_type":type(e).__name__,"entry_allowed":False}))
        raise SystemExit(1)
