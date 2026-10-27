"""Out-of-sample Bitcoin strength filter study, research-only; no production edits.
The hypothesis 2% above BTC SMA200 was selected using earlier April-Sept 2026 data.
Evaluate Oct 2026 hourly Binance spot bars WITHOUT tuning the threshold.
"""
import datetime as dt,json,urllib.request,time
from alternative_history_audit import archive
from binance_180d_compare import bars
from market_regime_research import simulate,SYMBOLS

# This is explicitly a data coverage/forward-test feasibility audit, NOT a valid
# strategy profitability score until unseen hourly data has been independently obtained.
def main():
    print("OOS_PLAN="+json.dumps({"training_span":"2026-04-04 through 2026-09-30",
      "holdout_start":"2026-10-01","hypothesis_btc_sma200_min_distance_pct":2.0,
      "status":"UNTESTED_NEEDS_OCTOBER_HOURLY_BARS",
      "reason":"Existing verified Binance monthly archives end at September. Do not reuse training data or fabricate October."}))
if __name__=="__main__":main()
