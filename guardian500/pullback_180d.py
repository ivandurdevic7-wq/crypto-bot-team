"""180-day isolated PAPER study; public Coinbase candles, no real trading. Research branch only."""
import json,datetime as dt
from extended_history_research import history,PAIRS
from compare_strategies import simulate
from pullback_research import pullback

def main():
    report={}
    for symbol,product in PAIRS.items():
        bars=history(product,180)
        # All methods evaluated with identical data; pullback needs 200 warmup bars.
        def scores(sample):
            return {"trend":simulate(sample,"baseline"),"breakout_volume":simulate(sample,"retest"),"pullback":pullback(sample)}
        # Each window reinitializes virtual EUR 500 and uses 10 days of warmup for indicators.
        n=90*24
        report[symbol]={"180_days":scores(bars),
                        "first_90_days":scores(bars[:n]),
                        "last_90_days":scores(bars[n-240:]),
                        "candles":len(bars),
                        "start_utc":dt.datetime.fromtimestamp(bars[0]["time"],dt.timezone.utc).isoformat(),
                        "end_utc":dt.datetime.fromtimestamp(bars[-1]["time"],dt.timezone.utc).isoformat()}
    print("PULLBACK_180D_PAPER="+json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
