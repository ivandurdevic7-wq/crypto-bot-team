"""Strict public Coinbase historical candle retrieval with retry of missing UTC hours.
Never fabricates candles: if a real gap remains, fail closed.
"""
import datetime as dt,json,time,urllib.parse,urllib.request
HOUR=3600
def fetch(product,first,last):
    url="https://api.exchange.coinbase.com/products/"+product+"/candles?"+urllib.parse.urlencode({
      "granularity":HOUR,"start":dt.datetime.fromtimestamp(first,dt.timezone.utc).isoformat(),
      "end":dt.datetime.fromtimestamp(last,dt.timezone.utc).isoformat()})
    req=urllib.request.Request(url,headers={"User-Agent":"Cuvar500PAPERHistoricalAudit/1","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=25) as response: data=json.load(response)
    if not isinstance(data,list):raise ValueError("Non-candle public API response")
    return {int(r[0]):dict(time=int(r[0]),open=float(r[3]),high=float(r[2]),low=float(r[1]),
                           close=float(r[4]),volume=float(r[5]))
            for r in data if first<=int(r[0])<last}
def history(product,days=180):
    end=(int(time.time())//HOUR-1)*HOUR
    start=end-days*24*HOUR
    # Pages <= 168 hours to stay below the public 300-candle limit.
    candles={}
    for t in range(start,end+HOUR,168*HOUR):
        candles.update(fetch(product,t,min(t+168*HOUR,end+HOUR)))
        time.sleep(.12)
    expected=set(range(start,end+HOUR,HOUR))
    missing=sorted(expected-set(candles))
    print("GAP_AUDIT",product,"initial_missing",len(missing),flush=True)
    # Re-request narrow windows so page boundaries or transient omissions recover.
    for attempt in range(2):
        if not missing:break
        for t in missing:
            candles.update(fetch(product,t,t+HOUR))
            time.sleep(.10)
        missing=sorted(expected-set(candles))
        print("GAP_AUDIT",product,"after_retry",attempt+1,"missing",len(missing),flush=True)
    if missing:
        print("GAP_AUDIT",product,"first_missing_utc",
              dt.datetime.fromtimestamp(missing[0],dt.timezone.utc).isoformat(),flush=True)
        raise ValueError("Unresolved historical candle gaps: "+str(len(missing))+"; fail closed")
    ordered=[candles[t] for t in sorted(expected)]
    if any(b["time"]-a["time"]!=HOUR for a,b in zip(ordered,ordered[1:])):
        raise ValueError("Non-contiguous history")
    return ordered
