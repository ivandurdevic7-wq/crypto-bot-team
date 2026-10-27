"""Read-only 180d Binance USDT study. NEVER mix EUR and USDT, no trades. Branch experiment."""
import datetime as dt,json
from alternative_history_audit import archive
from compare_strategies import simulate
from pullback_research import pullback

def bars(symbol):
    start=dt.datetime(2026,4,4,tzinfo=dt.timezone.utc)
    end=dt.datetime(2026,10,1,tzinfo=dt.timezone.utc)
    data={}
    for m in range(4,10):
        part=archive(symbol,2026,m)
        if set(part)&set(data):raise ValueError("Duplicate archive candle")
        data.update(part)
    lo=int(start.timestamp())//3600;hi=int(end.timestamp())//3600
    if any(t not in data for t in range(lo,hi)):raise ValueError("Missing real hourly bars")
    return [dict(time=t*3600,open=data[t][0],high=data[t][1],low=data[t][2],close=data[t][3],volume=data[t][4]) for t in range(lo,hi)]
def scores(data):
    return {"trend":simulate(data,"baseline"),"breakout_volume":simulate(data,"retest"),"pullback":pullback(data)}
def main():
    report={}
    for symbol in ("BTCUSDT","ETHUSDT","SOLUSDT"):
        b=bars(symbol)
        report[symbol]={"quote_currency":"USDT","history_hours":len(b),"full_180d":scores(b),
                        "first_90d":scores(b[:2160]),"second_90d":scores(b[2160-240:]),
                        "note":"Each scenario uses independent 500 units of USDT virtual starting capital; second window includes 240h indicator warm-up."}
        print("SYMBOL_180D",symbol,json.dumps(report[symbol],sort_keys=True),flush=True)
    print("BINANCE_180D_COMPARISON="+json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
