"""Research-only exact per-trade P&L audit for shared 500 USDT simulated portfolio."""
import json
from binance_180d_compare import bars
from market_regime_research import SYMBOLS

def evaluate(fee=.001,slip=.001):
 data={s:bars(s) for s in SYMBOLS};cash=500.;hold={};pending={};trades=[]
 for i in range(205,4320-1):
  for name in list(hold):
   b=data[name][i];n=data[name][i+1];pos=hold[name]
   ma20=sum(x["close"] for x in data[name][i-19:i+1])/20
   ma200=sum(x["close"] for x in data[name][i-199:i+1])/200
   entry=pos["price"]
   if b["close"]<=entry*.95 or b["close"]>=entry*1.10 or b["close"]<ma200:
    revenue=pos["qty"]*n["open"]*(1-slip)*(1-fee)
    cash+=revenue
    trades.append({"symbol":name,"net_pnl":revenue-pos["paid"],"gross_pnl":pos["qty"]*n["open"]-pos["paid"],"cost":pos["paid"]+pos["qty"]*n["open"]-revenue})
    del hold[name]
  for name in SYMBOLS:
   if name in hold or len(hold)>=2:continue
   h=data[name];b=h[i];n=h[i+1]
   ma20=sum(x["close"] for x in h[i-19:i+1])/20
   ma200=sum(x["close"] for x in h[i-199:i+1])/200
   ma200prior=sum(x["close"] for x in h[i-204:i-4])/200
   bv=data["BTCUSDT"]
   bma=sum(x["close"] for x in bv[i-199:i+1])/200
   bprior=sum(x["close"] for x in bv[i-204:i-4])/200
   vol=sum(x["volume"] for x in h[i-20:i])/20
   rising=b["close"]>ma200 and ma200>ma200prior
   buy=False
   if name in pending:
    age=i-pending[name]
    if not rising or age>4:del pending[name]
    elif age>0 and b["close"]>h[i-1]["high"] and vol>0 and b["volume"]>vol:
     buy=True;del pending[name]
   elif rising and b["low"]<=ma20*1.005 and b["close"]>=ma20*.995:pending[name]=i
   if buy and bv[i]["close"]>bma and bma>bprior:
    paid=min(125.,cash)
    if paid>=5:
     hold[name]={"price":n["open"]*(1+slip),"qty":paid*(1-fee)/(n["open"]*(1+slip)),"paid":paid}
     cash-=paid
 # Unclosed positions marked at final close with all hypothetical costs.
 for name,pos in hold.items():
  close=data[name][-1]["close"]
  revenue=pos["qty"]*close*(1-slip)*(1-fee)
  cash+=revenue
  trades.append({"symbol":name,"net_pnl":revenue-pos["paid"],"gross_pnl":pos["qty"]*close-pos["paid"],"cost":pos["paid"]+pos["qty"]*close-revenue})
 wins=[t for t in trades if t["net_pnl"]>0]
 losses=[t for t in trades if t["net_pnl"]<=0]
 return {"completed_trades":len(trades),"win_rate_pct":round(100*len(wins)/len(trades),2) if trades else 0,
 "average_net_trade_usdt":round(sum(t["net_pnl"] for t in trades)/len(trades),4) if trades else 0,
 "average_win_usdt":round(sum(t["net_pnl"] for t in wins)/len(wins),4) if wins else 0,
 "average_loss_usdt":round(sum(t["net_pnl"] for t in losses)/len(losses),4) if losses else 0,
 "total_net_usdt":round(cash-500,4),"final_usdt":round(cash,4),
 "break_even_average_trade_usdt":0,
 "note":"Approximate simulated realized P&L with next-open fills; gross and cost fields are not additive causal decomposition."}
if __name__=="__main__":
 print("TRADE_EDGE_AUDIT="+json.dumps({"fee_0_1pct":evaluate(.001,.001),"no_costs":evaluate(0.,0.)},sort_keys=True))
