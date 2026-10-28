"""Current WBNB quote research, no historical backfill or trading.
Quote checks fail closed. Research alerts are indicative, never trade signals.
"""
import json,urllib.request,datetime
from decimal import Decimal,InvalidOperation
from whale_usd_threshold import classify_wbnb_swap
WBNB="0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
PAIR_URL="https://api.dexscreener.com/token-pairs/v1/bsc/"+WBNB

def select_quote(pairs):
    candidates=[]
    for p in pairs if isinstance(pairs,list) else []:
        if p.get("chainId")!="bsc":continue
        base=p.get("baseToken") or {}
        if base.get("address","").lower()!=WBNB:continue
        try:
            price=Decimal(str(p.get("priceUsd")))
            liquidity=Decimal(str((p.get("liquidity") or {}).get("usd")))
        except (InvalidOperation,TypeError,ValueError):continue
        if not price.is_finite() or not liquidity.is_finite() or price<=0 or liquidity<1000000:continue
        # Wide indicative uncertainty margin; excludes quotes near threshold.
        candidates.append((liquidity,price,p.get("pairAddress")))
    if not candidates:raise ValueError("No verified sufficiently liquid WBNB quote")
    _,price,pair=max(candidates)
    return {"price_usd":price,"pair":pair}

def assess_current(wbnb_raw,pairs):
    quote=select_quote(pairs)
    price=quote["price_usd"]
    # +/- 5% uncertainty buffer is a research convention, not a confidence interval.
    result=classify_wbnb_swap(wbnb_raw,price*Decimal("0.95"),price*Decimal("1.05"))
    result.update({"quote_type":"CURRENT_INDICATIVE_ONLY","quote_pair":quote["pair"],
        "historical_valuation":"UNAVAILABLE","price_buffer":"PLUS_MINUS_5_PERCENT_NOT_STATISTICAL"})
    return result

def main():
    req=urllib.request.Request(PAIR_URL,headers={"User-Agent":"Cuvar500-Research/1"})
    with urllib.request.urlopen(req,timeout=15) as response:
        pairs=json.load(response)
    # Do not claim the historical 2026-05-15 swap has today's price.
    quote=select_quote(pairs)
    result={"mode":"RESEARCH_ONLY","orders_enabled":False,"historical_alerts_enabled":False,
      "chain":"bsc","symbol":"WBNB","usd_quote":str(quote["price_usd"]),
      "quote_pair":quote["pair"],"checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "source":"DexScreener public token-pairs API","classification":"QUOTE_ONLY_NO_SWAP_ALERT"}
    print("WHALE_MARKET_QUOTE="+json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
