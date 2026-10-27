"""V9 full PAPER lifecycle regression using synthetic quotes ONLY.
Never operates on real tokens or broadcasts transactions.
"""
from bnb_master_v9_policy import REQUIRED,WEIGHTS,decide,LIVE_ENABLED
from bnb_v9_paper_ledger import initial,buy
from bnb_v9_exits import paper_exit

def test():
    assert LIVE_ENABLED is False
    token={k:False for k in REQUIRED}
    token.update(address="0x"+"a"*40,symbol="TEST",price_usd=1,liquidity_usd=100000,
                 age_min=10000,verified_code=True,honeypot_sell_ok=True,
                 buy_tax_pct=0,sell_tax_pct=0,lp_locked_pct=100,lp_lock_days=365,
                 largest_holder_pct=2,creator_pct=1,top10_pct=15,holders=1000,
                 volume_24h_usd=40000,price_impact_pct=.2,slippage_pct=.3,
                 change_1h_pct=5,bnb_change_24h_pct=1,
                 security_sources_ok=True,security_rechecked=True,
                 fresh_quotes_ok=True,token_value_explained=True)
    portfolio={"equity_eur":200,"cash_eur":200,"open_positions":0,
               "daily_loss_pct":0,"weekly_loss_pct":0,"loss_streak":0}
    agents={k:.8 for k in WEIGHTS}
    decision=decide(token,agents,portfolio)
    assert decision["action"]=="PAPER_BUY_READY",decision
    state=initial()
    quote={"price_eur":1,"impact_pct":.2,"slippage_pct":.3,
           "buy_tax_pct":0,"gas_eur":.05}
    checks={k:True for k in ("fresh_quote","security_rechecked","sell_simulation_ok","liquidity_ok","bnb_market_ok")}
    blocked,status=buy(state,decision,quote,{})
    assert blocked==state and status.startswith("SKIP")
    state,status=buy(state,decision,quote,checks)
    assert status=="PAPER_BUY" and len(state["positions"])==1
    addr=token["address"]
    cost=state["positions"][addr]["cost_eur"]
    before=state.copy()
    blocked,status=paper_exit(state,addr,{"price_eur":1.26},{})
    assert status.startswith("SELL_BLOCKED") and blocked==state
    exit_quote={"price_eur":1.26,"sell_tax_pct":0,"impact_pct":.2,
                "slippage_pct":.3,"gas_eur":.05,
                "sell_simulation_ok":True,"fresh_quote":True}
    after,status=paper_exit(state,addr,{"price_eur":1.26},exit_quote)
    assert status=="PAPER_SELL" and after["positions"][addr]["tp1"] is True
    assert len(after["trades"])==2
    assert 0<after["positions"][addr]["qty"]<state["positions"][addr]["qty"]
    print("PASS: policy -> blocked/no quote -> PAPER buy -> blocked/no sell quote -> TP25 PAPER sell, synthetic only")
if __name__=="__main__":test()
