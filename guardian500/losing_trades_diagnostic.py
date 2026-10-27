"""Analyze entry characteristics of losing PAPER trades, without optimizing a filter. Research execution only."""
import json,statistics
from trade_edge_audit import evaluate
def summary(rows):
 if not rows:return {"count":0}
 def med(field):return round(statistics.median(x[field] for x in rows),3)
 return {"count":len(rows),"median_volume_ratio":med("entry_volume_ratio"),"median_btc_distance_pct":med("entry_btc_distance_pct"),"median_local_trend_distance_pct":med("entry_trend_distance_pct"),"median_duration_hours":med("duration_hours"),"pnl_usdt":round(sum(x["net_pnl"] for x in rows),3)}
trades=evaluate(details=True)
wins=[t for t in trades if t["net_pnl"]>0]
losses=[t for t in trades if t["net_pnl"]<=0]
out={"total_trades":len(trades),"wins":summary(wins),"losses":summary(losses),"losses_by_asset":{name:summary([t for t in losses if t["symbol"]==name]) for name in ("BTCUSDT","ETHUSDT","SOLUSDT")},"notice":"Descriptive in-sample comparisons only; patterns do not establish a profitable filter."}
print("LOSING_TRADES_DIAGNOSTIC="+json.dumps(out,sort_keys=True))
