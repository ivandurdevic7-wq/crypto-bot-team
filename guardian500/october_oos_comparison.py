"""Strict unseen October 2026 backtest (branch-only execution); prior 2% threshold fixed before October fetch.
Binance spot USDT archives; no orders, writes to production, or synthetic candles.
"""
import datetime as dt,io,csv,urllib.request,zipfile,json,time
from alternative_history_audit import archive
SYMBOLS=("BTCUSDT","ETHUSDT","SOLUSDT")
def simulate(data,method,initial=500.,fee=.001,slip=.001,regime=False,min_distance=0.,start_index=205):
    capital=initial;cash=capital;hold={};pending={};peak=capital;maxdd=0.;entries=0;exits=0
    end=min(len(v) for v in data.values())
    for i in range(max(205,start_index),end-1):
        # Exit before entering, one common account, at most 2 active positions
        for name in list(hold):
            b=data[name][i];n=data[name][i+1];entry,qty=hold[name]
            ma20=sum(x["close"] for x in data[name][i-19:i+1])/20
            ma200=sum(x["close"] for x in data[name][i-199:i+1])/200
            leave=b["close"]<ma20 if method=="trend" else (b["close"]<=entry*.95 or b["close"]>=entry*1.10 or b["close"]<(ma200 if method=="pullback" else ma20))
            if leave:
                cash+=qty*n["open"]*(1-slip)*(1-fee)
                del hold[name];exits+=1
        for name in SYMBOLS:
            if name in hold or len(hold)>=2:continue
            hist=data[name];b=hist[i];n=hist[i+1]
            ma20=sum(x["close"] for x in hist[i-19:i+1])/20
            ma50=sum(x["close"] for x in hist[i-49:i+1])/50
            ma200=sum(x["close"] for x in hist[i-199:i+1])/200
            old200=sum(x["close"] for x in hist[i-204:i-4])/200
            avgvol=sum(x["volume"] for x in hist[i-20:i])/20
            priorhigh=max(x["high"] for x in hist[i-20:i])
            buy=False
            if method=="trend":
                buy=b["close"]>priorhigh and ma20>ma50
            elif method=="retest":
                if name in pending:
                    level,created=pending[name]
                    if i-created>6:del pending[name]
                    elif i>created and b["low"]<=level*1.01 and b["close"]>level:
                        buy=True;del pending[name]
                if not buy and name not in pending and b["close"]>priorhigh and avgvol>0 and b["volume"]>=1.5*avgvol:
                    pending[name]=(priorhigh,i)
            elif method=="pullback":
                rising=b["close"]>ma200 and ma200>old200
                if name in pending:
                    created=pending[name]
                    if not rising or i-created>4:del pending[name]
                    elif i>created and b["close"]>hist[i-1]["high"] and avgvol>0 and b["volume"]>avgvol:
                        buy=True;del pending[name]
                elif rising and b["low"]<=ma20*1.005 and b["close"]>=ma20*.995:
                    pending[name]=i
            else:raise ValueError("unknown method")
            if buy and regime:
                # Filter on CLOSED market-wide BTC bars; no forward-looking data.
                btc=data["BTCUSDT"]
                btc_ma200=sum(row["close"] for row in btc[i-199:i+1])/200
                prior_ma200=sum(row["close"] for row in btc[i-204:i-4])/200
                buy=(btc[i]["close"]>btc_ma200*(1+min_distance) and btc_ma200>prior_ma200)
            if buy:
                budget=min(125.,cash)  # fixed max 25% initial capital
                if budget>=5.:
                    qty=budget*(1-fee)/(n["open"]*(1+slip))
                    hold[name]=(n["open"]*(1+slip),qty);cash-=budget;entries+=1
        mark=cash+sum(qty*data[name][i+1]["close"]*(1-slip)*(1-fee) for name,(_,qty) in hold.items())
        peak=max(peak,mark);maxdd=max(maxdd,(peak-mark)/peak)
    for name,(_,qty) in hold.items():
        cash+=qty*data[name][-1]["close"]*(1-slip)*(1-fee)
    return {"initial_usdt":initial,"final_usdt":round(cash,3),"pnl_usdt":round(cash-initial,3),
            "max_drawdown_pct":round(maxdd*100,3),"entries":entries,"exits":exits,"real_trades":0}

def october_daily(symbol,date):
    name=f"{symbol}-1h-{date}.zip"
    u=f"https://data.binance.vision/data/spot/daily/klines/{symbol}/1h/{name}"
    with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Cuvar500UnseenOctResearch/1"}),timeout=30) as response:
        raw=response.read(3_000_001)
    if len(raw)>3_000_000:raise ValueError("unexpected archive size")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=[n for n in z.namelist() if n.endswith(".csv")]
        if len(names)!=1:raise ValueError("bad daily archive")
        result={}
        with z.open(names[0]) as f:
            for r in csv.reader(io.TextIOWrapper(f,encoding="utf-8")):
                stamp=int(r[0])
                if stamp>10**15:stamp//=1_000_000
                elif stamp>10**12:stamp//=1000
                if stamp%3600:raise ValueError("non-hour timestamp")
                t=stamp//3600
                if t in result:raise ValueError("duplicate")
                result[t]=[float(r[k]) for k in [1,2,3,4,5]]
        return result
def load(symbol):
    # September only used for warmup, NEVER simulated for score.
    full=archive(symbol,2026,9)
    for day in range(1,27):
        date=f"2026-10-{day:02d}"
        d=october_daily(symbol,date)
        if len(d)!=24:raise ValueError("incomplete daily archive "+date)
        if set(d)&set(full):raise ValueError("overlap")
        full.update(d)
        time.sleep(.06)
    beginning=int(dt.datetime(2026,9,1,tzinfo=dt.timezone.utc).timestamp())//3600
    end=int(dt.datetime(2026,10,27,tzinfo=dt.timezone.utc).timestamp())//3600
    missing=[h for h in range(beginning,end) if h not in full]
    if missing:raise ValueError(f"missing {len(missing)} actual hourly bars")
    return [dict(time=h*3600,open=full[h][0],high=full[h][1],low=full[h][2],close=full[h][3],volume=full[h][4]) for h in range(beginning,end)]
def main():
    d={sym:load(sym) for sym in SYMBOLS}
    n=len(d[SYMBOLS[0]])
    if any(len(rows)!=n or any(b["time"]!=d[SYMBOLS[0]][i]["time"] for i,b in enumerate(rows)) for rows in d.values()):
        raise ValueError("unaligned spot candles")
    start=30*24
    result={"unseen_period":"2026-10-01 to 2026-10-26 UTC","prior_training_period":"2026-04-04 to 2026-09-30",
       "fee_per_side":.001,"slippage_per_side":.001,"simulated_unit":"USDT",
       "old_btc_filter":simulate(d,"pullback",regime=True,min_distance=0.,start_index=start),
       "btc_filter_2percent":simulate(d,"pullback",regime=True,min_distance=.02,start_index=start)}
    print("UNSEEN_OCTOBER_RESULT="+json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
