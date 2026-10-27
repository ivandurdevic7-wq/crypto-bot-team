"""Additional fail-closed gates. No transactions or wallet keys."""
import math

def num(x):
    n=float(x)
    if not math.isfinite(n): raise ValueError('invalid numeric evidence')
    return n

def simulation_check(d,address,pair,qty):
    if str(d.get('chain',{}).get('id'))!='56': raise ValueError('simulation chain mismatch')
    if d.get('token',{}).get('address','').lower()!=address.lower(): raise ValueError('simulation token mismatch')
    if d.get('pair',{}).get('pair',{}).get('address','').lower()!=pair.lower(): raise ValueError('simulation pool mismatch')
    if d.get('simulationSuccess') is not True: raise ValueError('buy/sell simulation unavailable or failed')
    if d.get('honeypotResult',{}).get('isHoneypot') is not False: raise ValueError('honeypot status unknown/unsafe')
    r=d.get('simulationResult',{})
    for key in ('buyTax','sellTax','transferTax'):
        if num(r.get(key))!=0: raise ValueError('simulation tax nonzero')
    for key in ('buyGas','sellGas'):
        if num(r.get(key))<=0: raise ValueError('simulation gas missing')
    if not 0<=num(d.get('summary',{}).get('riskLevel'))<20: raise ValueError('simulation risk unknown/high')
    for key in ('maxBuy','maxSell'):
        if key in r and num(r[key]['token'])<qty: raise ValueError('simulation size limit')
    return {'status':'PASS','source':'Honeypot.is','scope':'provider buy/sell simulation, not wallet-specific','checked_token_qty':qty}

def lp_check(d,chain,pair,now):
    pools=d.get('dex',[])
    # Top-level LP holders are not unambiguously tied to a selected pool when
    # several pools exist. Never attach another pool's lock to this trade.
    if len(pools)!=1: raise ValueError('LP pool attribution unknown')
    p=pools[0]
    actual=p.get('pair',p.get('id',''))
    if (actual.lower()!=pair.lower() if chain=='bsc' else actual!=pair): raise ValueError('LP pool mismatch')
    kind=p.get('liquidity_type',p.get('type','')).lower()
    if kind not in ('univ2','standard'): raise ValueError('concentrated LP lock evidence unsupported')
    holders=d.get('lp_holders')
    if not holders: raise ValueError('LP holders missing')
    protected=0.; expiries=[]; seen=set(); total=0.
    for h in holders:
        addr=h.get('address',h.get('token_account'))
        if not addr or addr in seen: raise ValueError('LP holder identity missing/duplicate')
        seen.add(addr); share=num(h['percent']);total+=share
        if not 0<=share<=1: raise ValueError('LP percentage invalid')
        if chain=='bsc' and addr.lower() in ('0x0000000000000000000000000000000000000000','0x000000000000000000000000000000000000dead'):
            protected+=share;continue
        if str(h.get('is_locked'))!='1': continue
        balance=num(h['balance']); locked=0.
        if balance<=0: raise ValueError('LP lock balance invalid')
        for lock in h.get('locked_detail',[]):
            end=num(lock['end_time']); amount=num(lock['amount'])
            if amount<0: raise ValueError('LP lock amount invalid')
            if end>now: expiries.append(end)
            if end>=now+7*86400: locked+=amount
        if locked>balance*1.000001: raise ValueError('LP lock exceeds balance')
        protected+=share*min(1,locked/balance)
    if total>1.000001: raise ValueError('LP fractions exceed supply')
    if protected<.90: raise ValueError('less than 90% LP protected for next 7 days')
    return {'status':'PASS','protected_fraction':protected,'next_unlock':min(expiries) if expiries else None,'source':'GoPlus','pool':pair}

def liquidity_drop(previous,current,now):
    if not previous or previous.get('pool')!=current['pool']: return False
    return 0<now-previous['at']<=7200 and current['usd']<previous['usd']*.75
