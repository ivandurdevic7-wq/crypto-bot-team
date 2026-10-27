"""Two independent BSC token security feeds. Read only, fail closed."""
import json, re, urllib.request
ADDRESS=re.compile(r"^0x[a-fA-F0-9]{40}$")
def get(url):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"BNB-V9-Paper/1.0"})
    with urllib.request.urlopen(req,timeout=9) as response:return json.load(response)
def flag(d,k):
    v=d.get(k)
    return True if v in ("1",1,True) else False if v in ("0",0,False) else None
def check(address,request=get):
    if not ADDRESS.fullmatch(address):return {"safe":False,"reasons":["Invalid address"],"data":{}}
    reasons=[];out={};hp_verified=False;gp_verified=False
    try:
        hp=request("https://api.honeypot.is/v2/IsHoneypot?address="+address+"&chainID=56")
        hr=hp.get("honeypotResult") or {}
        sr=hp.get("simulationResult") or {}
        out["honeypot_sell_ok"]=hp.get("simulationSuccess") is True and hr.get("isHoneypot") is False and sr.get("sellTax") is not None and sr.get("buyTax") is not None
        hp_verified=out["honeypot_sell_ok"]
        if not out["honeypot_sell_ok"]:reasons.append("Honeypot or sell simulation unavailable")
        for field,key in (("buy_tax_pct","buyTax"),("sell_tax_pct","sellTax")):
            try:out[field]=float(sr[key])
            except (KeyError,TypeError,ValueError):out[field]=None
        if out["buy_tax_pct"] is None or out["buy_tax_pct"]>8:reasons.append("Buy tax unsafe or missing")
        if out["sell_tax_pct"] is None or out["sell_tax_pct"]>8:reasons.append("Sell tax unsafe or missing")
    except Exception as e:reasons.append("Honeypot.is unavailable: "+str(e)[:70])
    try:
        gp=request("https://api.gopluslabs.io/api/v1/token_security/56?contract_addresses="+address.lower())
        data=(gp.get("result") or {}).get(address.lower()) or {}
        if str(gp.get("code"))!="1" or not data:raise ValueError("Missing GoPlus response")
        gp_verified=True
        out["verified_code"]=flag(data,"is_open_source") is True
        if not out["verified_code"]:reasons.append("Contract verification missing")
        fields={"mintable":"is_mintable","hidden_owner":"hidden_owner","owner_reclaim":"can_take_back_ownership",
                "transfer_pause":"transfer_pausable","blacklist":"is_blacklisted",
                "mutable_tax":"slippage_modifiable","selfdestruct":"selfdestruct"}
        for name,key in fields.items():
            out[name]=flag(data,key)
            if out[name] is not False:reasons.append("Unsafe or unknown "+name)
        out["holders"]=int(data["holder_count"]) if data.get("holder_count") else None
        if out["holders"] is None or out["holders"]<100:reasons.append("Holder count too low or unknown")
        # GoPlus holder shares are fractional; only use complete verifiable records.
        raw_holders=data.get("holders")
        if isinstance(raw_holders,list) and len(raw_holders)>=10:
            try:
                shares=[float(h["percent"])*100 for h in raw_holders if isinstance(h,dict)]
                if len(shares)==len(raw_holders) and all(0<=p<=100 for p in shares):
                    out["largest_holder_pct"]=max(shares)
                    out["top10_pct"]=sum(sorted(shares,reverse=True)[:10])
                    creator=str(data.get("creator_address") or "").lower()
                    creators=[float(h["percent"])*100 for h in raw_holders
                              if str(h.get("address") or "").lower()==creator]
                    if creator and creators:out["creator_pct"]=sum(creators)
            except (ValueError,TypeError,KeyError,OverflowError):
                pass
        # GoPlus returns creator_percent as a fraction of total supply, not 0-100.
        raw_creator=data.get("creator_percent")
        if raw_creator not in (None,""):
            try:
                creator_value=float(raw_creator)
                if __import__("math").isfinite(creator_value) and 0<=creator_value<=1:
                    out["creator_pct"]=creator_value*100
                else:
                    out["creator_pct"]=None
            except (TypeError,ValueError,OverflowError):out["creator_pct"]=None
        for key,limit in (("largest_holder_pct",10),("creator_pct",5),("top10_pct",40)):
            if out.get(key) is None:reasons.append("Unverified "+key)
            elif out[key]>limit:reasons.append("Unsafe "+key)
    except Exception as e:reasons.append("GoPlus unavailable: "+str(e)[:70])
    out["security_sources_ok"]=hp_verified and gp_verified
    # Additional independent requirements are deliberately not inferred from these feeds.
    for name in ("lp_locked_pct","lp_lock_days","bundled_snipers","wash_trading","price_impact_pct",
                 "slippage_pct","token_value_explained","fresh_quotes_ok"):
        out[name]=None
    return {"safe":not reasons and all(v is not None for v in out.values()),"reasons":reasons or ["Other required safety evidence unavailable"],"data":out}
def test():
    addr="0x"+"a"*40
    def fake(url):
        if "honeypot.is" in url:return {"simulationSuccess":True,"honeypotResult":{"isHoneypot":False},"simulationResult":{"buyTax":0,"sellTax":0}}
        return {"code":1,"result":{addr:{"is_open_source":"1","is_mintable":"0","hidden_owner":"0",
            "can_take_back_ownership":"0","transfer_pausable":"0","is_blacklisted":"0",
            "slippage_modifiable":"0","selfdestruct":"0","holder_count":"150"}}}
    result=check(addr,fake)
    assert result["data"]["honeypot_sell_ok"] is True
    assert result["data"]["security_sources_ok"] is True
    assert result["data"]["creator_pct"] is None
    assert result["safe"] is False and result["data"]["lp_locked_pct"] is None
    assert check(addr,lambda url: {})["safe"] is False
    print("V9 dual source fail-closed checks PASS")
if __name__=="__main__":test()
