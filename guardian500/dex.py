"""Bounded BNB/Solana discovery and fail-closed PAPER screening."""
import json, math, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
from safety import simulation_check, lp_check, liquidity_drop
DS='https://api.dexscreener.com'
ZERO_BSC=('is_proxy','is_mintable','can_take_back_ownership','owner_change_balance','hidden_owner','selfdestruct','external_call','cannot_buy','cannot_sell_all','slippage_modifiable','is_honeypot','transfer_pausable','is_blacklisted','is_whitelisted','trading_cooldown','personal_slippage_modifiable')
ZERO_SOL=('mintable','freezable','closable','transfer_fee_upgradable','default_account_state_upgradable','balance_mutable_authority','transfer_hook_upgradable')

def number(v):
    n=float(v)
    if not math.isfinite(n): raise ValueError('non-finite number')
    return n

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Cuvar500-PAPER/2','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=8) as r:
        date=r.headers.get('Date')
        if not date or abs(time.time()-parsedate_to_datetime(date).timestamp())>180:
            raise ValueError('HTTP timestamp missing/stale')
        if number(r.headers.get('Age','0'))>120: raise ValueError('cached response too old')
        return json.load(r)

def security(chain,address,pair,details=False):
    path='token_security/56' if chain=='bsc' else 'solana/token_security'
    data=get('https://api.gopluslabs.io/api/v1/'+path+'?contract_addresses='+urllib.parse.quote(address))
    if data.get('code')!=1: raise ValueError('GoPlus unavailable')
    result=data.get('result',{})
    d=result.get(address) or result.get(address.lower())
    if not d: raise ValueError('GoPlus token missing')
    fee=check_security(chain,d,pair)
    return (fee,d) if details else fee

def check_security(chain,d,pair):
    if chain=='bsc':
        if d.get('is_open_source')!='1': raise ValueError('contract not verified')
        for k in ZERO_BSC:
            if str(d.get(k))!='0': raise ValueError('risk/unknown: '+k)
        if number(d['buy_tax'])!=0 or number(d['sell_tax'])!=0: raise ValueError('nonzero token tax')
    else:
        if str(d.get('default_account_state'))!='1' or str(d.get('non_transferable'))!='0': raise ValueError('transfer state unknown/blocked')
        for k in ZERO_SOL:
            if str(d.get(k,{}).get('status'))!='0': raise ValueError('risk/unknown: '+k)
        if 'transfer_hook' not in d or d['transfer_hook']: raise ValueError('hook unknown/present')
        fee=d.get('transfer_fee')
        if not isinstance(fee,dict): raise ValueError('transfer fee unknown')
        for k in ('current_fee_rate','scheduled_fee_rate'):
            if number(fee[k]['fee_rate'])!=0: raise ValueError('transfer fee nonzero')
    holders=d.get('holders')
    if not isinstance(holders,list) or len(holders)<10: raise ValueError('top10 holders incomplete')
    shares=[number(h['percent']) for h in holders[:10]]
    if any(x<0 or x>1 for x in shares) or sum(shares)<=0 or max(shares)>.10 or sum(shares)>.35:
        raise ValueError('holder concentration/invalid fractions')
    # Count all holders conservatively, including pools; no guesses about exclusions.
    pools=[x for x in d.get('dex',[]) if str(x.get('pair',x.get('id',''))).lower()==pair.lower()]
    if not pools: raise ValueError('selected pool not verified by GoPlus')
    fee=number(pools[0].get('pool_fee') if chain=='bsc' else pools[0].get('fee_rate'))
    if not 0<=fee<=.01: raise ValueError('pool fee unknown/high')
    return max(.004,fee)

def basic(p,now):
    price=number(p['priceUsd']); liq=number(p['liquidity']['usd'])
    if price<=0 or liq<100000: raise ValueError('liquidity below $100k')
    if not 86400<=now-number(p['pairCreatedAt'])/1000: raise ValueError('pool younger than 24h')
    if number(p['volume']['h24'])<100000: raise ValueError('volume below $100k/day')
    tx=p['txns']['m5']
    if int(tx['buys'])<2 or int(tx['sells'])<2: raise ValueError('insufficient recent buys/sells')
    return price,liq

def scan(s,now,fx):
    errors=[]; candidates={}; held={k:v for k,v in s['positions'].items() if ':' in k}
    # Search plus latest profiles are samples, not an exhaustive chain index.
    urls=[DS+'/token-profiles/latest/v1']+[DS+'/latest/dex/search?q='+q for q in ('WBNB','SOL','USDC')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(get,u) for u in urls]):
            try:
                d=f.result()
                for p in (d if isinstance(d,list) else d.get('pairs',[])):
                    c=p.get('chainId'); a=p.get('tokenAddress') or p.get('baseToken',{}).get('address')
                    if c in ('bsc','solana') and a: candidates[c+':'+(a.lower() if c=='bsc' else a)]=(c,a)
            except Exception as e: errors.append(str(e))
    watch=s.setdefault('dex_watch',{})
    for k in list(watch):
        if now-watch[k]['last_seen']>86400 and k not in held: del watch[k]
    for k in watch: candidates.setdefault(k,tuple(k.split(':',1)))
    selected={}
    for c in ('bsc','solana'):
        keys=[k for k,v in candidates.items() if v[0]==c]
        # Rotate the bounded sample so a static list does not starve later candidates.
        keys.sort(); offset=(int(now//900)*8)%max(1,len(keys)); keys=keys[offset:]+keys[:offset]
        priority=sorted(k for k in watch if k.startswith(c+':') and now-watch[k]['last_seen']<=3600)[:4]
        chosen=priority+[k for k in keys if k not in priority][:8-len(priority)]
        for k in chosen: selected[k]=candidates[k]
    selected.update({k:tuple(k.split(':',1)) for k in held})
    quotes={}; records=[]
    def inspect(item):
        k,(c,a)=item; record=dict(key=k,chain=c,address=a,checked_at=now,sell_simulation={'status':'NOT_CHECKED'},lp_protection={'status':'NOT_CHECKED'})
        try:
            pools=get(DS+'/token-pairs/v1/'+c+'/'+urllib.parse.quote(a))
            pools=[p for p in pools if p.get('chainId')==c and p.get('baseToken',{}).get('address','').lower()==a.lower() and (c!='bsc' or p.get('dexId')=='pancakeswap')]
            if k in held: pools=[p for p in pools if p['pairAddress']==held[k]['pair_address']]
            if not pools: raise ValueError('no matching DEX pool')
            p=max(pools,key=lambda p:number((p.get('liquidity') or {}).get('usd',0)))
            price,liq=basic(p,now)
            record.update(symbol=p['baseToken'].get('symbol','?'),pool=p['pairAddress'],liquidity_usd=liq,price_usd=price)
            previous=s.get('liquidity_history',{}).get(k)
            observation={'pool':p['pairAddress'],'usd':liq,'at':now}
            record['liquidity_observation']=observation
            record['liquidity_drop_alert']=liquidity_drop(previous,observation,now)
            fee,security_data=security(c,a,p['pairAddress'],details=True)
            failures=[]
            try: record['lp_protection']=lp_check(security_data,c,p['pairAddress'],now)
            except Exception as e:
                record['lp_protection']={'status':'UNCONFIRMED','reason':str(e)}; failures.append(str(e))
            try:
                if c!='bsc': raise ValueError('Solana buy/sell simulation not integrated; entries blocked')
                if fx is None: raise ValueError('FX missing for simulation size')
                size=held[k]['qty'] if k in held else 25*fx/price
                data=get('https://api.honeypot.is/v2/IsHoneypot?'+urllib.parse.urlencode({'address':a,'chainID':56,'pair':p['pairAddress']}))
                record['sell_simulation']=simulation_check(data,a,p['pairAddress'],size)
            except Exception as e:
                record['sell_simulation']={'status':'UNCONFIRMED','reason':str(e)};failures.append(str(e))
            if record['liquidity_drop_alert']: failures.append('liquidity dropped over 25% within 2 hours')
            if failures: raise ValueError('; '.join(failures))
            if fx is None: raise ValueError('EUR/USD unavailable; no EUR trade')
            old=watch.get(k); momentum=number(p['priceChange']['h1']); h24=number(p['priceChange']['h24'])
            entry=bool(old and 600<=now-old['last_seen']<=3600 and old['pool']==p['pairAddress'] and 1.005<=price/old['price']<=1.08 and 1<=momentum<=15 and -5<=h24<=50)
            q=dict(bid=price/fx,ask=price/fx,candle=int(now//900),entry=entry,exit=momentum<-3,liquid=True,volume_eur=number(p['volume']['h24'])/fx,min_volume=0,fee=fee,slip=.01,gas=.25,cap=25.,stop=.08,trail=.10,risk=.005,pair_address=p['pairAddress'],chain=c,symbol=record['symbol'],reason='DEX momentum confirmed across observations')
            record.update(status='SIGNAL' if entry else 'WAIT_CONFIRMATION',fee=fee)
            return k,q,record,dict(last_seen=now,price=price,pool=p['pairAddress'])
        except Exception as e:
            record.update(status='SKIP',reason=str(e)); return k,None,record,None
    with ThreadPoolExecutor(max_workers=2) as pool:
        for k,q,r,w in pool.map(inspect,selected.items()):
            records.append(r)
            if 'liquidity_observation' in r: s.setdefault('liquidity_history',{})[k]=r['liquidity_observation']
            if q: quotes[k]=q; watch[k]=w
    s['dex_scan']=dict(checked_at=now,discovered=len(candidates),checked=len(records),by_chain={c:sum(r['chain']==c for r in records) for c in ('bsc','solana')},errors=errors,records=records,coverage='bounded sample; not all tokens',sell_check='BNB provider simulation required; Solana unintegrated => no new DEX entry')
    return quotes
