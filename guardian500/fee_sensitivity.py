"""Read-only cost sensitivity for shared 500 USDT PAPER research.
Illustrative tariffs; no exchange account validation, no live trades. Branch-only execution.
"""
import json
from market_regime_research import simulate,SYMBOLS
from binance_180d_compare import bars
def run():
 data={sym:bars(sym) for sym in SYMBOLS}
 scenarios={"zero_fee_zero_slip":(0,0),"binance_0_10pct_taker":(.001,.001),
            "kraken_0_40pct_maker":(.004,.001),"kraken_0_80pct_taker":(.008,.001),
            "zero_fee_with_slippage":(0,.001)}
 out={name:simulate(data,"pullback",fee=fee,slip=slip,regime=True) for name,(fee,slip) in scenarios.items()}
 out["note"]="Hypothetical costs per side on Binance USDT spot historical bars; NOT actual EUR execution. Assumes 0.1% slippage each side except no-cost baseline."
 print("FEE_SENSITIVITY_PAPER="+json.dumps(out,sort_keys=True))
if __name__=="__main__":run()
