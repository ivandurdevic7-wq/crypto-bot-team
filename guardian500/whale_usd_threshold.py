"""Conservative daily-range USD threshold classifier for research only.
No intraday execution price is inferred; unknown/straddling ranges never alert.
"""
from decimal import Decimal, InvalidOperation
from typing import Optional

THRESHOLD_USD=Decimal("10000")

def classify_wbnb_swap(wbnb_raw, usd_low, usd_high, threshold=THRESHOLD_USD):
    if any(v is None for v in (wbnb_raw, usd_low, usd_high)):
        return {"status":"UNKNOWN_NO_ALERT"}
    try:
        qty=Decimal(str(wbnb_raw))/Decimal(10)**18
        lo=Decimal(str(usd_low)); hi=Decimal(str(usd_high)); gate=Decimal(str(threshold))
    except (InvalidOperation, ValueError, TypeError):
        return {"status":"UNKNOWN_NO_ALERT"}
    if not all(x.is_finite() for x in (qty,lo,hi,gate)) or qty<=0 or lo<=0 or hi<lo or gate<=0:
        return {"status":"UNKNOWN_NO_ALERT"}
    min_usd=qty*lo;max_usd=qty*hi
    status=("LARGE_SWAP_RESEARCH_ALERT" if min_usd>=gate else
            "BELOW_THRESHOLD" if max_usd<gate else
            "UNCERTAIN_THRESHOLD_NO_ALERT")
    return {"status":status,"min_usd":float(round(min_usd,2)),
            "max_usd":float(round(max_usd,2)),"threshold_usd":float(gate),
            "price_method":"DAILY_LOW_HIGH_BOUNDS_NOT_TRANSACTION_PRICE"}

if __name__=="__main__":
    import json
    # Confirmed PancakeSwap receipt 2026-05-15: 0.868252655142649991 WBNB.
    # TEST-ONLY illustrative USD price range; no verified historical quote.
    output=classify_wbnb_swap("868252655142649991","670.20","689.12")
    output.update({"reference_date":"2026-05-15","reference_price_status":"ILLUSTRATIVE_UNVERIFIED",
      "price_source":"NONE_VERIFIED; example bounds only",
      "historical_tx":"0xabdef90a25f08bb5ae51c2803ed576c3c1162bc359aed15350aaffab4ae34772",
      "mode":"RESEARCH_ONLY","orders_enabled":False})
    print("WHALE_USD_RANGE_CHECK="+json.dumps(output,sort_keys=True))
