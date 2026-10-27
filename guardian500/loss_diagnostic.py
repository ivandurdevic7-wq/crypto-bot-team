"""Independent cost sensitivity diagnosis, read-only historical data. Not profit proof."""
import json
from market_regime_research import simulate,SYMBOLS
from binance_180d_compare import bars
def main():
 data={s:bars(s) for s in SYMBOLS}
 costs=[("zero",0.,0.),("fee_only",.004,0.),("slippage_only",0.,.001),("modeled",.004,.001)]
 results={name:simulate(data,"pullback",fee=fee,slip=slip,regime=True) for name,fee,slip in costs}
 baseline=results["zero"]["pnl_usdt"]
 results["comparison"]={"gross_strategy_pnl_usdt":baseline,
  "cost_drag_total_usdt":round(results["modeled"]["pnl_usdt"]-baseline,3),
  "fee_only_drag_usdt":round(results["fee_only"]["pnl_usdt"]-baseline,3),
  "slippage_only_drag_usdt":round(results["slippage_only"]["pnl_usdt"]-baseline,3),
  "warning":"One-at-a-time sensitivity, not additive decomposition; signals unchanged, virtual fills only."}
 print("LOSS_DIAGNOSTIC="+json.dumps(results,sort_keys=True))
if __name__=="__main__":main()
