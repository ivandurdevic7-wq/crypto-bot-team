"""Independent, read-only PAPER pullback comparison, 90d public Coinbase OHLCV.
Not a replay of Čuvar 500. No keys, orders, leverage or production state.
"""
import json
from extended_history_research import history,PAIRS
from compare_strategies import simulate as original

def pullback(bars,initial=500.,fee=.004,slip=.001):
    cash=initial;qty=0.;paid=0.;entry=0.;peak=initial;dd=0.;entries=0
    pending=-1
    for i in range(200,len(bars)-1):
        b,n=bars[i],bars[i+1]
        closes=[x["close"] for x in bars[i-199:i+1]]
        ma200=sum(closes)/200
        ma200_old=sum(x["close"] for x in bars[i-204:i-4])/200 if i>=204 else ma200
        ma20=sum(closes[-20:])/20
        avgvol=sum(x["volume"] for x in bars[i-20:i])/20
        # Closed hourly candles only. Fills always on next opening candle.
        if qty:
            if b["close"]<=entry*.95 or b["close"]>=entry*1.10 or b["close"]<ma200:
                cash+=qty*n["open"]*(1-slip)*(1-fee);qty=0.
        else:
            trend=b["close"]>ma200 and ma200>ma200_old
            # Prior bar touched the 20h average: approximately a shallow pullback.
            if trend and b["low"]<=ma20*1.005 and b["close"]>=ma20*.995:
                pending=i
            elif pending>=0:
                # Confirm recovery within 1-4 bars, with >20-bar mean volume.
                if i-pending>4 or not trend: pending=-1
                elif i>pending and b["close"]>bars[i-1]["high"] and avgvol>0 and b["volume"]>avgvol:
                    budget=min(cash*.30,150.)
                    if budget>0:
                        qty=budget*(1-fee)/(n["open"]*(1+slip))
                        cash-=budget;entry=n["open"]*(1+slip);paid=budget;entries+=1
                    pending=-1
        mark=cash+qty*n["close"]*(1-slip)*(1-fee)
        peak=max(peak,mark);dd=max(dd,(peak-mark)/peak)
    if qty:cash+=qty*bars[-1]["close"]*(1-slip)*(1-fee)
    return {"initial_eur":initial,"final_eur":round(cash,3),"pnl_eur":round(cash-initial,3),
            "max_drawdown_pct":round(dd*100,3),"entries":entries,"real_trades":0}

def main():
    output={}
    for symbol,product in PAIRS.items():
        bars=history(product,90)
        output[symbol]={"candles":len(bars),
          "baseline":original(bars,"baseline"),
          "retest":original(bars,"retest"),
          "pullback":pullback(bars)}
    print("PULLBACK_PAPER_RESEARCH="+json.dumps(output,sort_keys=True))
if __name__=="__main__":main()
