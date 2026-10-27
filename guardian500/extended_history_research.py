"""Independent longer-history PAPER research, public Coinbase Exchange hourly candles.
Research only. No orders, keys, production state, or HTML modifications.
Two strategies are assessed identically using compare_strategies.simulate.
"""
import datetime as dt,json,time,urllib.parse,urllib.request
from compare_strategies import simulate

PAIRS={"BTC":"BTC-EUR","ETH":"ETH-EUR","SOL":"SOL-EUR"}
HOUR=3600
def history(product,days=90):
    end=(int(time.time())//HOUR-1)*HOUR
    start=end-days*24*HOUR
    candles={}
    for t in range(start,end+1,7*24*HOUR):
        u="https://api.exchange.coinbase.com/products/"+product+"/candles?"+urllib.parse.urlencode({
          "granularity":3600,
          "start":dt.datetime.fromtimestamp(t,dt.timezone.utc).isoformat(),
          "end":dt.datetime.fromtimestamp(min(t+7*24*HOUR,end+HOUR),dt.timezone.utc).isoformat()})
        req=urllib.request.Request(u,headers={"User-Agent":"Cuvar500ReadOnlyHistoricalStudy/1","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=25) as resp:
            rows=json.load(resp)
        if not isinstance(rows,list):raise ValueError("Coinbase response not candles")
        for row in rows:
            stamp,low,high,op,close,volume=row[:6]
            if start<=stamp<=end:
                candles[int(stamp)]=dict(time=int(stamp),open=float(op),high=float(high),low=float(low),close=float(close),volume=float(volume))
        time.sleep(.13)
    ordered=[candles[x] for x in sorted(candles)]
    if len(ordered)<days*24-12:raise ValueError("Missing too many candles: "+str(len(ordered)))
    if any(b["time"]-a["time"]!=HOUR for a,b in zip(ordered,ordered[1:])):
        raise ValueError("Historical candles have gaps; no simulation allowed")
    return ordered

def main():
    out={}
    for symbol,product in PAIRS.items():
        b=history(product,90)
        # out-of-sample evaluation uses last 30 days; 60 bars warm up from preceding days
        test=b[-(30*24+60):]
        out[symbol]={"history_days":90,"total_candles":len(b),
                     "full_period":{s:simulate(b,s) for s in ["baseline","retest"]},
                     "last_30_days_holdout":{s:simulate(test,s) for s in ["baseline","retest"]},
                     "first_timestamp_utc":dt.datetime.fromtimestamp(b[0]["time"],dt.timezone.utc).isoformat(),
                     "last_timestamp_utc":dt.datetime.fromtimestamp(b[-1]["time"],dt.timezone.utc).isoformat()}
    print("EXTENDED_PAPER_RESEARCH="+json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
