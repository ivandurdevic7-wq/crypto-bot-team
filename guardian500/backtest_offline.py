"""Offline PAPER research: hourly CSV backtest; never sends orders.
CSV: timestamp,open,high,low,close (UTC; hourly; oldest first).
Signals are computed from *closed* candles; fills use the NEXT candle open.
No claim of profitability, no exchange execution, no DEX token simulation.
"""
import argparse,csv,datetime as dt,json,math
from pathlib import Path

def load(path):
    out=[]
    with open(path,newline="") as stream:
        for row in csv.DictReader(stream):
            try:
                stamp=dt.datetime.fromisoformat(row["timestamp"].replace("Z","+00:00"))
                if stamp.tzinfo is None: raise ValueError("UTC timestamp required")
                o,h,l,c=(float(row[k]) for k in ("open","high","low","close"))
                if not all(math.isfinite(x) and x>0 for x in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:
                    raise ValueError("invalid OHLC")
                out.append((stamp,o,h,l,c))
            except (ValueError,KeyError,TypeError) as exc:
                raise ValueError("Invalid row in OHLC CSV") from exc
    if len(out)<100: raise ValueError("Need at least 100 hourly candles")
    for a,b in zip(out,out[1:]):
        if (b[0]-a[0]).total_seconds()!=3600: raise ValueError("Hourly gap, duplicate or unordered candles")
    return out

def test_strategy(rows,initial=500.,fee=.004,slip=.001):
    """Long-only single-position experiment, separate from the live PAPER ledger."""
    cash=initial; qty=0.; trades=[]; peak=initial; max_dd=0.; entry_cost=0.
    # Candle i closes, entry/exit at i+1 OPEN; never use unfinished/future candles for signals.
    for i in range(60,len(rows)-1):
        closes=[r[4] for r in rows[i-59:i+1]]
        signal=closes[-1]>max(rows[j][2] for j in range(i-20,i)) and sum(closes[-20:])/20>sum(closes[-50:])/50
        exit_signal=closes[-1]<sum(closes[-20:])/20
        fill=rows[i+1][1]
        if qty and exit_signal:
            gross=qty*fill*(1-slip)
            cash=gross*(1-fee)
            trades.append({"time":rows[i+1][0].isoformat(),"side":"SELL","net_eur":round(cash,4),"pnl_eur":round(cash-entry_cost,4)})
            qty=0.;entry_cost=0.
        elif not qty and signal:
            entry_cost=cash
            qty=(cash*(1-fee))/(fill*(1+slip))
            cash=0.
            trades.append({"time":rows[i+1][0].isoformat(),"side":"BUY","budget_eur":round(entry_cost,4)})
        mark=cash if not qty else qty*rows[i+1][4]*(1-slip)*(1-fee)
        peak=max(peak,mark)
        max_dd=max(max_dd,(peak-mark)/peak)
    if qty:
        gross=qty*rows[-1][4]*(1-slip)
        cash=gross*(1-fee)
        trades.append({"time":rows[-1][0].isoformat(),"side":"FINAL_MARK_EXIT","net_eur":round(cash,4),"pnl_eur":round(cash-entry_cost,4)})
    benchmark=initial*rows[-1][4]/rows[60][4]
    return {"status":"OFFLINE_RESEARCH_NOT_BOT_REPLAY","candles":len(rows),"initial_eur":initial,
            "final_eur":round(cash,4),"pnl_eur":round(cash-initial,4),
            "max_drawdown_pct":round(max_dd*100,3),"buy_and_hold_eur_before_fees":round(benchmark,4),
            "trades":trades,"real_trades":0}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("csv",type=Path,help="UTC hourly OHLC CSV")
    args=ap.parse_args()
    print(json.dumps(test_strategy(load(args.csv)),indent=2))
