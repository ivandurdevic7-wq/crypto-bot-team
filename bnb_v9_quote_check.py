"""Independent price/liquidity cross-check for BSC PAPER research. No trades."""
import json, math, urllib.request
def number(v):
    try:
        if isinstance(v,bool):return None
        x=float(v)
        return x if math.isfinite(x) and x>0 else None
    except (ValueError,TypeError,OverflowError):return None
def fetch(url):
    r=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"BNB-V9-Paper/1.0"})
    with urllib.request.urlopen(r,timeout=8) as x:return json.load(x)
def compare(address,gecko_price,gecko_liquidity,request=fetch,pool_address=None):
    result={"verified":False,"reasons":[],"dex_price_usd":None,"dex_liquidity_usd":None}
    if not isinstance(address,str) or len(address)!=42 or not address.startswith("0x"):
        result["reasons"].append("Invalid token address");return result
    if pool_address is not None and (not isinstance(pool_address,str) or len(pool_address)!=42 or not pool_address.startswith("0x")):
        result["reasons"].append("Missing verified pool address");return result
    gp=number(gecko_price);gl=number(gecko_liquidity)
    if gp is None or gl is None:
        result["reasons"].append("Gecko price or liquidity unavailable");return result
    try:
        pairs=request("https://api.dexscreener.com/token-pairs/v1/bsc/"+address)
        if not isinstance(pairs,list):raise ValueError("Missing pair list")
        eligible=[p for p in pairs if p.get("chainId")=="bsc" and
                  "pancake" in str(p.get("dexId","")).lower() and
                  str((p.get("baseToken") or {}).get("address","")).lower()==address.lower() and
                  number(p.get("priceUsd")) is not None and
                  number((p.get("liquidity") or {}).get("usd")) is not None]
        if pool_address:
            eligible=[p for p in eligible if str(p.get("pairAddress","")).lower()==pool_address.lower()]
        if not eligible and pool_address:
            # Ask DEX Screener for the exact pair, rather than relying on
            # its token-wide listing, which may omit an otherwise valid pool.
            exact=request("https://api.dexscreener.com/latest/dex/pairs/bsc/"+pool_address)
            exact_pairs=(exact.get("pairs") or []) if isinstance(exact,dict) else []
            eligible=[p for p in exact_pairs if p.get("chainId")=="bsc"
                      and "pancake" in str(p.get("dexId","")).lower()
                      and str(p.get("pairAddress","")).lower()==pool_address.lower()
                      and str((p.get("baseToken") or {}).get("address","")).lower()==address.lower()
                      and number(p.get("priceUsd")) is not None
                      and number((p.get("liquidity") or {}).get("usd")) is not None]
        if not eligible:raise ValueError("No matching PancakeSwap token pair")
        pair=max(eligible,key=lambda p:number((p.get("liquidity") or {}).get("usd")))
        price=number(pair["priceUsd"]);liq=number(pair["liquidity"]["usd"])
        result.update(dex_price_usd=price,dex_liquidity_usd=liq)
        # Transaction counts are observational evidence, not proof of organic flow.
        tx=(pair.get("txns") or {}).get("h1") or {}
        buys=number(tx.get("buys"));sells=number(tx.get("sells"))
        if buys is not None and sells is not None:
            result["buys_h1"]=int(buys)
            result["sells_h1"]=int(sells)
        if abs(price-gp)/gp>0.03:result["reasons"].append("Price differs >3% between feeds")
        if abs(liq-gl)/gl>0.35:result["reasons"].append("Liquidity differs >35% between feeds")
        result["verified"]=not result["reasons"]
    except Exception as e:result["reasons"].append("DEX feed unavailable: "+str(e)[:100])
    return result
def test():
    a="0x"+"a"*40
    def match(url):return [{"chainId":"bsc","dexId":"pancakeswap","baseToken":{"address":a},"priceUsd":"1.02","liquidity":{"usd":99500}}]
    assert compare(a,1,100000,match)["verified"] is True
    assert compare(a,1,100000,lambda u: [])["verified"] is False
    assert compare(a,1,100000,lambda u:[dict(match(u)[0],priceUsd="2")])["verified"] is False
    assert compare(a,None,100000,match)["verified"] is False
    assert compare(a,1,100000,match,pool_address="0x"+"b"*40)["verified"] is False
    assert compare(a,1,100000,match,pool_address="")["verified"] is False
    pair="0x"+"b"*40
    def exact_pair(url):
        entry=dict(match(url)[0],pairAddress=pair)
        return {"pairs":[entry]} if "/latest/dex/pairs/" in url else []
    assert compare(a,1,100000,exact_pair,pool_address=pair)["verified"] is True
    def wrong_exact(url):
        entry=dict(match(url)[0],pairAddress="0x"+"c"*40)
        return {"pairs":[entry]} if "/latest/dex/pairs/" in url else []
    assert compare(a,1,100000,wrong_exact,pool_address=pair)["verified"] is False
    print("PASS: independent BSC price/liquidity consistency checks, fail-closed")
if __name__=="__main__":test()
