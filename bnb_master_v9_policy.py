"""BNB MASTER 9.0: fail-closed PAPER policy prototype. No wallet or LIVE execution."""
import json
from datetime import datetime, timezone, timedelta

START_EUR = 200.0
WEIGHTS = {"momentum":1.2,"order_flow":1.2,"volume":1.0,"liquidity":1.0,
           "holders_lp":1.0,"age":0.6,"social":1.0,"whales_trending":0.8,"market":0.8}
REQUIRED = ("address","symbol","price_usd","liquidity_usd","age_min","verified_code",
            "honeypot_sell_ok","buy_tax_pct","sell_tax_pct","mintable","hidden_owner",
            "owner_reclaim","transfer_pause","blacklist","mutable_tax","selfdestruct",
            "lp_locked_pct","lp_lock_days","largest_holder_pct","creator_pct",
            "top10_pct","holders","volume_24h_usd","wash_trading","bundled_snipers",
            "community_scam_warnings","price_impact_pct","slippage_pct",
            "change_1h_pct","bnb_change_24h_pct","security_sources_ok",
            "security_rechecked","fresh_quotes_ok","token_value_explained")
def safe_number(value):
    """Convert API numeric strings; invalid values remain missing (fail closed)."""
    try:
        if isinstance(value, bool): return None
        number=float(value)
        return number if __import__("math").isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None

NUMERIC_FIELDS = ("price_usd","liquidity_usd","age_min","buy_tax_pct",
    "sell_tax_pct","lp_locked_pct","lp_lock_days","largest_holder_pct",
    "creator_pct","top10_pct","holders","volume_24h_usd",
    "price_impact_pct","slippage_pct","change_1h_pct","bnb_change_24h_pct")

SECURITY_BAD = ("mintable","hidden_owner","owner_reclaim","transfer_pause",
                "blacklist","mutable_tax","selfdestruct","wash_trading",
                "bundled_snipers","community_scam_warnings")

def decide(token, agents, portfolio, now=None):
    now = now or datetime.now(timezone.utc)
    token=dict(token)
    for field in NUMERIC_FIELDS:
        if field in token: token[field]=safe_number(token[field])
    missing = [k for k in REQUIRED if token.get(k) is None]
    missing += [f"agent:{k}" for k in WEIGHTS if agents.get(k) is None]
    veto = []
    if missing: veto.append("Nedostaju sigurnosni podaci ili signali")
    if token.get("honeypot_sell_ok") is not True: veto.append("Prodaja nije potvrđena")
    if token.get("verified_code") is not True: veto.append("Kod nije verificiran")
    if token.get("token_value_explained") is not True: veto.append("Vrijednost tokena nije objašnjena")
    if token.get("security_sources_ok") is not True: veto.append("Neovisni sigurnosni izvori nisu dostupni")
    if token.get("security_rechecked") is not True or token.get("fresh_quotes_ok") is not True:
        veto.append("Završna provjera nije potvrđena")
    for field in SECURITY_BAD:
        if token.get(field) is not False: veto.append(field)
    limits = {"buy_tax_pct":8,"sell_tax_pct":8,"price_impact_pct":1.5,
              "slippage_pct":3,"change_1h_pct":100}
    for name, lim in limits.items():
        if token.get(name) is not None and token[name]>lim: veto.append(f"{name} > {lim}")
    floors = {"liquidity_usd":30000,"age_min":30,"lp_locked_pct":80,
              "lp_lock_days":30,"holders":100}
    for name, lim in floors.items():
        if token.get(name) is not None and token[name]<lim: veto.append(f"{name} < {lim}")
    for name, lim in {"largest_holder_pct":10,"creator_pct":5,"top10_pct":40}.items():
        if token.get(name) is not None and token[name]>lim:veto.append(f"{name} > {lim}")
    liq=token.get("liquidity_usd")
    if liq and token.get("volume_24h_usd") is not None and token["volume_24h_usd"]>30*liq:
        veto.append("Neprirodan promet")
    if token.get("bnb_change_24h_pct") is not None and token["bnb_change_24h_pct"]<=-6:
        veto.append("BNB tržišni režim: pad")
    if portfolio.get("halted") or safe_number(portfolio.get("daily_loss_pct")) is None or safe_number(portfolio.get("weekly_loss_pct")) is None or portfolio.get("daily_loss_pct",100)>5 or portfolio.get("weekly_loss_pct",100)>10:
        veto.append("Prekidač gubitaka")
    if portfolio.get("loss_streak",3)>=3: veto.append("Tri uzastopna gubitka")
    positions=portfolio.get("open_positions",3)
    if positions>=3:veto.append("Najviše tri pozicije")
    for k,v in agents.items():
        if k in WEIGHTS and v is not None and not(-1<=v<=1):veto.append(f"Agent {k}: nevaljana ocjena")
    score=None
    if not missing and all(-1<=agents[k]<=1 for k in WEIGHTS):
        weighted=dict(agents)
        # Social influence <=10% of total possible weight.
        weighted["social"]=max(-0.1,min(0.1,weighted["social"]))
        score=round(sum(weighted[k]*w for k,w in WEIGHTS.items())/sum(WEIGHTS.values()),4)
        if score<0.35:veto.append("Ocjena ispod 0.35")
        if sum(agents[k]<-0.2 for k in WEIGHTS)>2:veto.append("Više od dva negativna agenta")
    equity=portfolio.get("equity_eur",0)
    cash=portfolio.get("cash_eur",0)
    risk_budget=max(0,equity*0.02/0.15)
    size=round(max(0,min(equity*0.20,risk_budget,cash-equity*0.4)),2)
    if size<=0:veto.append("Nema slobodnog kapitala uz rezervu od 40%")
    base={"action":"SKIP","token":token.get("symbol","?"),"address":token.get("address"),
          "score":score,"vetoes":list(dict.fromkeys(veto)),
          "price_usd":token.get("price_usd"),"liquidity_usd":liq,
          "age_min":token.get("age_min"),"size_eur":0,
          "max_slippage_pct":3,"stop_loss_pct":-15,
          "take_profit":[{"at_pct":25,"sell_pct":30},{"at_pct":50,"sell_pct":30}],
          "trailing_pct":12,"reasons":[],"risks":[],
          "data_gaps":missing,"confidence":"niska"}
    if not veto:
        base.update(action="PENDING_APPROVAL",size_eur=size,
                    reasons=["Svi tvrdi filteri prošli; čeka DA/NE"],
                    risks=["PAPER simulacija ne obuhvaća sve MEV i izvršne rizike"],
                    confidence="srednja")
        base["approval_expires_at"]=(now+timedelta(minutes=5)).isoformat()
    else:base["reasons"]=["SKIP: "+", ".join(base["vetoes"][:5])]
    return base

def approve(request, answer, received_at=None):
    """No order execution: approval is a state transition, not a transaction."""
    received_at=received_at or datetime.now(timezone.utc)
    if request.get("action")!="PENDING_APPROVAL":return "REJECTED"
    try:expiry=datetime.fromisoformat(request["approval_expires_at"])
    except (KeyError,ValueError,TypeError):return "REJECTED"
    return "APPROVED_PAPER" if answer=="DA" and received_at<=expiry else "REJECTED"

if __name__=="__main__":
    result=decide({}, {}, {"equity_eur":START_EUR,"cash_eur":START_EUR,
        "open_positions":0,"daily_loss_pct":0,"weekly_loss_pct":0,"loss_streak":0})
    assert result["action"]=="SKIP" and result["data_gaps"]
    print(json.dumps(result,ensure_ascii=False,indent=2))
