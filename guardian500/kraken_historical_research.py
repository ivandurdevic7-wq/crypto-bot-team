"""Read-only historical research using Kraken public hourly OHLC.
The public endpoint gives limited recent history; this is NOT full strategy validation.
Never accesses keys, wallets, orders, or production ledger.
"""
import csv,datetime as dt,json, tempfile,urllib.parse,urllib.request
from pathlib import Path
from backtest_offline import load,test_strategy

PAIRS={"BTC":"XBTEUR","ETH":"ETHEUR","SOL":"SOLEUR"}

def candles(pair):
    url="https://api.kraken.com/0/public/OHLC?"+urllib.parse.urlencode({"pair":pair,"interval":60})
    req=urllib.request.Request(url,headers={"User-Agent":"Cuvar500-PAPER-Historical-Research/1"})
    with urllib.request.urlopen(req,timeout=15) as response:
        payload=json.load(response)
    if payload.get("error"): raise ValueError("Kraken API error")
    result=payload["result"]
    key=next(k for k in result if k!="last")
    rows=result[key][:-1] # remove potentially incomplete last candle
    if len(rows)<100: raise ValueError("Insufficient public OHLC candles")
    return rows

def run():
    results={}
    for symbol,pair in PAIRS.items():
        rows=candles(pair)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"ohlc.csv"
            with path.open("w",newline="") as handle:
                writer=csv.writer(handle)
                writer.writerow(["timestamp","open","high","low","close"])
                for r in rows:
                    stamp=dt.datetime.fromtimestamp(int(r[0]),dt.timezone.utc).isoformat()
                    writer.writerow([stamp,r[1],r[2],r[3],r[4]])
            output=test_strategy(load(path))
        results[symbol]={key:value for key,value in output.items() if key!="trades"}
        results[symbol]["closed_trades"]=sum(t["side"] in ("SELL","FINAL_MARK_EXIT") for t in output["trades"])
        results[symbol]["sample_start_utc"]=dt.datetime.fromtimestamp(int(rows[0][0]),dt.timezone.utc).isoformat()
        results[symbol]["sample_end_utc"]=dt.datetime.fromtimestamp(int(rows[-1][0]),dt.timezone.utc).isoformat()
    report={"note":"Research only, recent limited Kraken OHLC, no DEX, simplified trend strategy; no proof of future profit","results":results,"real_trades":0}
    Path("guardian500/historical_research_result.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))
if __name__=="__main__": run()
