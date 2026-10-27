"""Shared-capital, read-only PAPER comparison: BTC/ETH/SOL USDT spot.
Experimental simplified backtest, NOT the deployed Čuvar 500 strategy.
Signals on closed 1h candles, fills at next hour open; no exchange orders.
"""
import json
from binance_180d_compare import bars

SYMBOLS=("BTCUSDT","ETHUSDT","SOLUSDT")
def simulate(data,method,initial=500.,fee=.004,slip=.001):
    capital=initial;cash=capital;hold={};pending={};peak=capital;maxdd=0.;entries=0;exits=0
    end=min(len(v) for v in data.values())
    for i in range(205,end-1):
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
def main():
    dataset={name:bars(name) for name in SYMBOLS}
    if len({len(x) for x in dataset.values()})!=1:raise ValueError("Different history length")
    if any(any(x["time"]!=dataset[SYMBOLS[0]][i]["time"] for i,x in enumerate(rows)) for rows in dataset.values()):
        raise ValueError("Histories not aligned")
    scores={mode:simulate(dataset,mode) for mode in ("trend","retest","pullback")}
    print("SHARED_PORTFOLIO_PAPER="+json.dumps({"quote_currency":"USDT","history_hours":len(dataset[SYMBOLS[0]]),"strategies":scores},sort_keys=True))
if __name__=="__main__":main()
