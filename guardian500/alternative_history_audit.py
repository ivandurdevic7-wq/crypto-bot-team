"""Independent source AUDIT only, Binance public hourly spot archives.
Not a substitute for Coinbase EUR prices. No orders or synthetic candles. Audit trigger.
"""
import csv,datetime as dt,io,json,urllib.request,zipfile
from collections import Counter
PAIRS=("BTCUSDT","ETHUSDT","SOLUSDT")
HOUR=3600
def archive(symbol,year,month):
    filename=f"{symbol}-1h-{year:04d}-{month:02d}.zip"
    url=f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{filename}"
    req=urllib.request.Request(url,headers={"User-Agent":"Cuvar500PAPERAlternativeAudit/1"})
    with urllib.request.urlopen(req,timeout=40) as r:
        raw=r.read(18_000_000+1)
    if len(raw)>18_000_000:raise ValueError("archive unexpectedly large")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=[name for name in z.namelist() if name.endswith(".csv")]
        if len(names)!=1:raise ValueError("unexpected CSV count")
        with z.open(names[0]) as stream:
            reader=csv.reader(io.TextIOWrapper(stream,encoding="utf-8"))
            out={}
            for row in reader:
                t=int(row[0])
                # Binance spot archive switched to microseconds from Jan 2025.
                if t>10**15:t//=1000000
                elif t>10**12:t//=1000
                if t%HOUR:raise ValueError("non-hour timestamp")
                t//=HOUR
                if t in out:raise ValueError("duplicate hour within archive")
                o,h,l,c,v=[float(row[i]) for i in [1,2,3,4,5]]
                if not (l<=min(o,c)<=max(o,c)<=h and v>=0):raise ValueError("bad OHLCV")
                out[t]=[o,h,l,c,v]
    return out
def months(start,end):
    y,m=start.year,start.month
    while (y,m)<=(end.year,end.month):
        yield y,m
        m+=1
        if m==13:y,m=y+1,1
def main():
    now=dt.datetime.now(dt.timezone.utc)
    # Last completed month only: avoid archive being unavailable in current month.
    end=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    start=end-dt.timedelta(days=180)
    start_hour=int(start.timestamp())//HOUR
    end_hour=int(end.timestamp())//HOUR
    out={}
    for symbol in PAIRS:
        data={}
        for year,month in months(start,end-dt.timedelta(days=1)):
            part=archive(symbol,year,month)
            overlap=set(data).intersection(part)
            if overlap:raise ValueError("duplicate hourly archive rows")
            data.update(part)
        expected=set(range(start_hour,end_hour))
        missing=sorted(expected-set(data))
        result={"source":"Binance public SPOT USDT archives, NOT Coinbase EUR",
                "start_utc":dt.datetime.fromtimestamp(start_hour*HOUR,dt.timezone.utc).isoformat(),
                "end_exclusive_utc":end.isoformat(),
                "expected_hours":len(expected),
                "received_hours":len(expected.intersection(data)),
                "missing_hours":len(missing),
                "first_missing_utc":dt.datetime.fromtimestamp(missing[0]*HOUR,dt.timezone.utc).isoformat() if missing else None,
                "valid":not missing}
        out[symbol]=result
        print("SOURCE_AUDIT",symbol,json.dumps(result),flush=True)
    print("ALT_HISTORICAL_AUDIT="+json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
