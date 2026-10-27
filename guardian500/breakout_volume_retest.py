"""Isolated read-only PAPER test: breakout, volume confirmation, then retest.
Research model, not production bot replay. No orders, keys or ledger writes.
"""
import datetime as dt,json,urllib.parse,urllib.request

PAIRS={"BTC":"XBTEUR","ETH":"ETHEUR","SOL":"SOLEUR"}
def get_bars(pair):
    u="https://api.kraken.com/0/public/OHLC?"+urllib.parse.urlencode({"pair":pair,"interval":60})
    with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Cuvar500-PAPER-Research"}),timeout=20) as response:
        data=json.load(response)
    if data.get("error"): raise ValueError("Kraken API error")
    k=next(k for k in data["result"] if k!="last")
    bars=[]
    for r in data["result"][k][:-1]:
        bars.append(dict(time=int(r[0]),open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4]),volume=float(r[6])))
    if len(bars)<100 or any(b["time"]-a["time"]!=3600 for a,b in zip(bars,bars[1:])):
        raise ValueError("insufficient or discontinuous hourly bars")
    return bars

def simulate(bars,capital=500.0,fee=.004,slip=.001):
    """Signal on closed bar i; fill at i+1 open. Max one position, max 30% allocation.
    Breakout: close > preceding 20 bar highs, volume >= 1.5x prior 20-bar mean.
    Retest: in next 1-6 complete bars, low touches old resistance within 1% and
    close returns above resistance, then fill next open. No future candle access.
    Exit on 5% stop, 10% target or close below SMA20, next open execution.
    Gap risk means realized loss can exceed stop. No intrabar fill assumption.
    """
    cash=capital;qty=0.0;entry=0.;pending=None;trades=[];peak=capital;maxdd=0.
    for i in range(60,len(bars)-1):
        b=bars[i];n=bars[i+1]
        sma=sum(x["close"] for x in bars[i-19:i+1])/20
        if qty:
            if b["close"]<=entry*.95 or b["close"]>=entry*1.10 or b["close"]<sma:
                received=qty*n["open"]*(1-slip)*(1-fee)
                pnl=received-entry_paid
                cash+=received
                trades.append(dict(side="SELL",time=n["time"],pnl_eur=round(pnl,3)))
                qty=0.
        else:
            if pending is not None:
                level,created=pending
                if i-created>6:
                    pending=None
                elif i>created and b["low"]<=level*1.01 and b["close"]>level:
                    budget=min(150.,cash*.30)
                    if budget>0:
                        qty=budget*(1-fee)/(n["open"]*(1+slip))
                        cash-=budget;entry=n["open"]*(1+slip);entry_paid=budget
                        trades.append(dict(side="BUY",time=n["time"],budget_eur=round(budget,3)))
                    pending=None
            if not qty and pending is None:
                resistance=max(x["high"] for x in bars[i-20:i])
                prev_vol=sum(x["volume"] for x in bars[i-20:i])/20
                if b["close"]>resistance and prev_vol>0 and b["volume"]>=1.5*prev_vol:
                    pending=(resistance,i)
        mark=cash+qty*n["close"]*(1-slip)*(1-fee)
        peak=max(peak,mark);maxdd=max(maxdd,(peak-mark)/peak)
    if qty:
        cash+=qty*bars[-1]["close"]*(1-slip)*(1-fee)
        trades.append(dict(side="FINAL_MARK_EXIT",time=bars[-1]["time"]))
    return dict(initial_eur=capital,final_eur=round(cash,3),pnl_eur=round(cash-capital,3),
                max_drawdown_pct=round(100*maxdd,3),entries=sum(t["side"]=="BUY" for t in trades),
                sample_start_utc=dt.datetime.fromtimestamp(bars[0]["time"],dt.timezone.utc).isoformat(),
                sample_end_utc=dt.datetime.fromtimestamp(bars[-1]["time"],dt.timezone.utc).isoformat(),
                real_trades=0)

def main():
    results={key:simulate(get_bars(pair)) for key,pair in PAIRS.items()}
    print("PAPER_RESEARCH_RESULT="+json.dumps(results,sort_keys=True))
if __name__=="__main__": main()
