"""V9 integration guard: missing independent security evidence MUST veto a PAPER buy."""
from bnb_master_v9_policy import decide, WEIGHTS, START_EUR, LIVE_ENABLED
from bnb_v9_paper_ledger import initial, buy
def test():
    p={"equity_eur":START_EUR,"cash_eur":START_EUR,"open_positions":0,"daily_loss_pct":0,"weekly_loss_pct":0,"loss_streak":0}
    agents={k:1.0 for k in WEIGHTS}
    candidate={"address":"0x"+"a"*40,"symbol":"TEST","price_usd":1,"liquidity_usd":150000,
               "age_min":240,"volume_24h_usd":100000,"change_1h_pct":3}
    a=decide(candidate,agents,p)
    assert a["action"]=="SKIP" and a["data_gaps"]
    assert "honeypot_sell_ok" in a["data_gaps"]
    assert "lp_locked_pct" in a["data_gaps"]
    assert "verified_code" in a["data_gaps"]
    check=dict.fromkeys(("fresh_quote","security_rechecked","sell_simulation_ok","liquidity_ok","bnb_market_ok"),True)
    quote={"price_eur":1,"impact_pct":.5,"slippage_pct":.5,"buy_tax_pct":0,"gas_eur":.05}
    s,status=buy(initial(),a,quote,check)
    assert status.startswith("SKIP") and s["cash_eur"]==200 and not s["positions"]
    # No input can enable real transactions, regardless of a forged decision.
    s2,status2=buy(initial(),{"action":"PAPER_BUY_READY","vetoes":[],"data_gaps":[],
       "address":candidate["address"],"token":"TEST","size_eur":20},quote,{})
    assert status2.startswith("SKIP")
    assert LIVE_ENABLED is False
    print("PASS: missing honeypot, LP or code evidence => SKIP; 0 virtual buys; LIVE forbidden")
if __name__=="__main__":test()
