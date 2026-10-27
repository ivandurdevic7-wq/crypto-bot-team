"""Manual PAPER-only research of at most two Solana candidates; no trades."""
import json, os, urllib.request, urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
USDC="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
def quote(a,b,amount,key):
    url="https://api.jup.ag/swap/v2/order?"+urllib.parse.urlencode({"inputMint":a,"outputMint":b,"amount":amount})
    req=urllib.request.Request(url,headers={"x-api-key":key,"User-Agent":"Cuvar500-Research-PAPER"})
    with urllib.request.urlopen(req,timeout=10) as r:
        raw=r.read(131073)
    if len(raw)>131072: raise ValueError("Oversized quote")
    d=json.loads(raw)
    if d.get("inputMint")!=a or d.get("outputMint")!=b or str(d.get("inAmount"))!=str(amount) or d.get("transaction") is not None or d.get("errorCode") is not None:
        raise ValueError("Invalid quote")
    out=d.get("outAmount")
    if not isinstance(out,str) or not out.isdecimal() or int(out)<=0: raise ValueError("Invalid output")
    return int(out)
def main():
    key=os.getenv("JUPITER_API_KEY","")
    if not key: raise ValueError("Jupiter key missing")
    state=json.loads((ROOT/"state.json").read_text())
    records=[r for r in state.get("dex_scan",{}).get("records",[]) if r.get("chain")=="solana" and r.get("address") and r.get("status")=="SKIP"]
    # Previously rejected tokens are diagnostics only, NEVER entry candidates.
    report=[]
    for r in records[:2]:
        address=r["address"]
        try:
            out=quote(USDC,address,1_000_000,key)
            back=quote(address,USDC,out,key)
            report.append({"token":address,"existing_screen":r.get("reason","unknown"),"roundtrip_quote_loss_pct":round(100*(1-back/1_000_000),3),"quote_status":"AVAILABLE","entry_allowed":False})
        except Exception as exc:
            report.append({"token":address,"existing_screen":r.get("reason","unknown"),"quote_status":"UNAVAILABLE","error_type":type(exc).__name__,"entry_allowed":False})
    print(json.dumps({"mode":"PAPER_RESEARCH","checked":len(report),"results":report,"transactions":0,"entry_allowed":False}))
if __name__=="__main__":
    main()
