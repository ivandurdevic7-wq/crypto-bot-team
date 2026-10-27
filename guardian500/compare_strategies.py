"""Fair same-candle PAPER comparison of two research signal strategies.
Both are long only, 30% position size, same 0.4% per-side fee, 0.1% slippage.
No orders, production ledger, API keys or live trading.
"""
import json
from breakout_volume_retest import get_bars,PAIRS

def baseline_signal(bars,i):
    closes=[x["close"] for x in bars[i-59:i+1]]
    return closes[-1]>max(x["high"] for x in bars[i-20:i]) and sum(closes[-20:])/20>sum(closes[-50:])/50

def simulate(bars,strategy,capital=500.,fee=.004,slip=.001):
    cash=capital;qty=0.;entry=0.;cost=0.;pending=None;peak=capital;dd=0.;entries=0
    for i in range(60,len(bars)-1):
        b=bars[i];n=bars[i+1]
        sma=sum(x["close"] for x in bars[i-19:i+1])/20
        if qty:
            leave=(b["close"]<sma if strategy=="baseline" else (b["close"]<=entry*.95 or b["close"]>=entry*1.10 or b["close"]<sma))
            if leave:
                cash+=qty*n["open"]*(1-slip)*(1-fee)
                qty=0.
        else:
            do_buy=False
            if strategy=="baseline":
                do_buy=baseline_signal(bars,i)
            elif strategy=="retest":
                if pending:
                    level,created=pending
                    if i-created>6: pending=None
                    elif i>created and b["low"]<=level*1.01 and b["close"]>level:
                        do_buy=True;pending=None
                if not do_buy and pending is None:
                    resistance=max(x["high"] for x in bars[i-20:i])
                    avgvol=sum(x["volume"] for x in bars[i-20:i])/20
                    if b["close"]>resistance and avgvol>0 and b["volume"]>=1.5*avgvol:
                        pending=(resistance,i)
            else: raise ValueError("unknown strategy")
            if do_buy:
                cost=min(150.,cash*.30)
                if cost>0:
                    qty=cost*(1-fee)/(n["open"]*(1+slip))
                    cash-=cost;entry=n["open"]*(1+slip);entries+=1
        mark=cash+qty*n["close"]*(1-slip)*(1-fee)
        peak=max(peak,mark);dd=max(dd,(peak-mark)/peak)
    if qty:cash+=qty*bars[-1]["close"]*(1-slip)*(1-fee)
    return {"final_eur":round(cash,3),"pnl_eur":round(cash-capital,3),"max_drawdown_pct":round(dd*100,3),"entries":entries}

def main():
    report={}
    for symbol,pair in PAIRS.items():
        rows=get_bars(pair)
        report[symbol]={"candles":len(rows),"baseline":simulate(rows,"baseline"),"retest":simulate(rows,"retest"),
                        "retest_minus_baseline_eur":round(simulate(rows,"retest")["final_eur"]-simulate(rows,"baseline")["final_eur"],3)}
    print("FAIR_PAPER_COMPARISON="+json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
