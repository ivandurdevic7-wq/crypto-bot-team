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
def compare(address,gecko_price,gecko_liquidity,request=fetch):
    result={"verified":False,"reasons":[],"dex_price_usd":None,"dex_liquidity_usd":None}
    if not isinstance(address,str) or len(address)!=42 or not address.startswith("0x"):
        result["reasons"].append("Invalid token address");return result
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
        if not eligible:raise ValueError("No matching PancakeSwap token pair")
        pair=max(eligible,key=lambda p:number((p.get("liquidity") or {}).get("usd")))
        price=number(pair["priceUsd"]);liq=number(pair["liquidity"]["usd"])
        result.update(dex_price_usd=price,dex_liquidity_usd=liq)
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
    print("PASS: independent BSC price/liquidity consistency checks, fail-closed")
if __name__=="__main__":test()
