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

EARLY_WATCH_VOLUME_USD = 10000
PAPER_ENTRY_VOLUME_USD = 20000

def early_watch_volume(p):
    """Research-only classification. No quotes or BUY signals for low volume."""
    vol=number(p['volume']['h24'])
    if vol < EARLY_WATCH_VOLUME_USD:
        return 'BELOW_WATCH'
    if vol < PAPER_ENTRY_VOLUME_USD:
        return 'EARLY_WATCH'
    return 'PAPER_VOLUME_ELIGIBLE'

def basic(p,now):
    price=number(p['priceUsd']); liq=number(p['liquidity']['usd'])
    if price<=0 or liq<30000: raise ValueError('liquidity below $30k')
    if not 43200<=now-number(p['pairCreatedAt'])/1000: raise ValueError('pool younger than 12h')
    if number(p['volume']['h24'])<PAPER_ENTRY_VOLUME_USD: raise ValueError('volume below $20k/day')
    tx=p['txns']['m5']
    if int(tx['buys'])<2 or int(tx['sells'])<2: raise ValueError('insufficient recent buys/sells')
    return price,liq

def candidate_quality(p, now):
    """Soft ranking of search candidates; never overrides safety gates."""
    if not isinstance(p,dict) or not p.get('pairAddress'):
        return 0
    try:
        liq=number(p['liquidity']['usd'])
        vol=number(p['volume']['h24'])
        age=now-number(p['pairCreatedAt'])/1000
        tx=p['txns']['m5']
        return (int(liq>=30000)+int(vol>=PAPER_ENTRY_VOLUME_USD)
                +int(age>=43200)+int(int(tx['buys'])>=2 and int(tx['sells'])>=2))
    except (KeyError,TypeError,ValueError,OverflowError):
        return 0


def choose_candidates(candidates, scores, watch, held, now, per_chain=20, retry_ready=None):
    selected={}
    retry_ready=retry_ready or {}
    for c in ('bsc','solana'):
        keys=sorted(k for k,v in candidates.items() if v[0]==c)
        if not keys:
            continue
        # Rotate ties to avoid starving candidates from repeat searches.
        offset=(int(now//900)*per_chain)%len(keys)
        keys=keys[offset:]+keys[:offset]
        keys.sort(key=lambda k:scores.get(k,0),reverse=True)
        priority=sorted(k for k in watch
                        if k.startswith(c+':') and k in candidates
                        and now-watch[k].get('last_seen',0)<=3600)[:4]
        # Guaranteed bounded second-chance capacity, without changing trade gates.
        due=sorted((k for k in retry_ready if k.startswith(c+':') and k in candidates),
                   key=lambda k:(retry_ready[k]['last_checked'],k))[:4]
        reserved=list(dict.fromkeys(priority+due))[:per_chain]
        chosen=reserved+[k for k in keys if k not in reserved][:max(0,per_chain-len(reserved))]
        for k in chosen:
            selected[k]=candidates[k]
    # Held positions are always inspected regardless of the sampling cap.
    selected.update({k:tuple(k.split(':',1)) for k in held})
    return selected


def scan(s,now,fx):
    errors=[]; candidates={}; scores={}; held={k:v for k,v in s['positions'].items() if ':' in k}
    # Search and latest profiles are samples, not an exhaustive chain index.
    urls=[DS+'/token-profiles/latest/v1']+[DS+'/latest/dex/search?q='+q for q in ('WBNB','SOL','USDC')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(get,u) for u in urls]):
            try:
                d=f.result()
                for p in (d if isinstance(d,list) else d.get('pairs',[])):
                    c=p.get('chainId'); a=p.get('tokenAddress') or p.get('baseToken',{}).get('address')
                    if c in ('bsc','solana') and a:
                        k=c+':'+(a.lower() if c=='bsc' else a)
                        candidates[k]=(c,a)
                        scores[k]=max(scores.get(k,0),candidate_quality(p,now))
            except Exception as e:
                errors.append(str(e))
    watch=s.setdefault('dex_watch',{})
    # Retry only temporary market-data/market-activity rejections.
    # This affects discovery priority, never entry or safety requirements.
    retry=s.setdefault('dex_retry',{})
    for k in list(retry):
        if now-retry[k].get('last_checked',0)>7200 or k in held:
            del retry[k]
    for k,v in retry.items():
        if now-v.get('last_checked',0)>=600:
            candidates.setdefault(k,tuple(k.split(':',1)))
    for k in list(watch):
        if now-watch[k]['last_seen']>86400 and k not in held:
            del watch[k]
    for k in watch:
        candidates.setdefault(k,tuple(k.split(':',1)))
    # Reserve up to four slots per chain for delayed second chances (10 minutes).
    eligible={k:v for k,v in retry.items() if k in candidates and now-v.get('last_checked',0)>=900}
    for k in eligible:
        scores[k]=max(scores.get(k,0),5)
    selected=choose_candidates(candidates,scores,watch,held,now,per_chain=20,retry_ready=eligible)
    quotes={}; records=[]
    def inspect(item):
        k,(c,a)=item; record=dict(key=k,chain=c,address=a,checked_at=now,sell_simulation={'status':'NOT_CHECKED'},lp_protection={'status':'NOT_CHECKED'})
        try:
            pools=get(DS+'/token-pairs/v1/'+c+'/'+urllib.parse.quote(a))
            pools=[p for p in pools if p.get('chainId')==c and p.get('baseToken',{}).get('address','').lower()==a.lower() and (c!='bsc' or p.get('dexId')=='pancakeswap')]
            if k in held: pools=[p for p in pools if p['pairAddress']==held[k]['pair_address']]
            if not pools: raise ValueError('no matching DEX pool')
            p=max(pools,key=lambda p:number((p.get('liquidity') or {}).get('usd',0)))
            # Research a lower-volume token, but NEVER pass it to trade screening.
            # Unknown/invalid volume remains fail-closed.
            volume_class=early_watch_volume(p)
            if volume_class=='EARLY_WATCH' and k not in held:
                record.update(status='EARLY_WATCH',reason='research only: 24h volume below $20k PAPER gate',
                              symbol=p.get('baseToken',{}).get('symbol','?'),
                              pool=p['pairAddress'],volume_usd_24h=number(p['volume']['h24']),
                              research_only=True,trade_eligible=False)
                return k,None,record,None
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
            emergency=bool(failures and k in held and record['sell_simulation']['status']=='PASS')
            if failures and not emergency: raise ValueError('; '.join(failures))
            if fx is None: raise ValueError('EUR/USD unavailable; no EUR trade')
            old=watch.get(k); momentum=number(p['priceChange']['h1']); h24=number(p['priceChange']['h24'])
            entry=bool(old and 600<=now-old['last_seen']<=3600 and old['pool']==p['pairAddress'] and 1.005<=price/old['price']<=1.08 and 0.5<=momentum<=15 and -5<=h24<=50)
            q=dict(bid=price/fx,ask=price/fx,candle=int(now//900),entry=entry and not emergency,emergency_exit=emergency,exit=momentum<-3,liquid=True,volume_eur=number(p['volume']['h24'])/fx,min_volume=0,fee=fee,slip=.01,gas=.25,cap=25.,stop=.08,trail=.10,risk=.005,pair_address=p['pairAddress'],chain=c,symbol=record['symbol'],reason='DEX momentum confirmed across observations')
            record.update(status='EXIT_SIGNAL' if emergency else 'SIGNAL' if entry else 'WAIT_CONFIRMATION',fee=fee)
            return k,q,record,dict(last_seen=now,price=price,pool=p['pairAddress'])
        except Exception as e:
            record.update(status='SKIP',reason=str(e)); return k,None,record,None
    with ThreadPoolExecutor(max_workers=2) as pool:
        for k,q,r,w in pool.map(inspect,selected.items()):
            records.append(r)
            if 'liquidity_observation' in r: s.setdefault('liquidity_history',{})[k]=r['liquidity_observation']
            if q: quotes[k]=q; watch[k]=w
    retry_reasons=('insufficient recent buys/sells','volume below $20k/day',
                   'liquidity below $30k','pool younger than 12h','no matching DEX pool')
    counts={}
    for r in records:
        label=r.get('reason',r.get('status','UNKNOWN'))
        counts[label]=counts.get(label,0)+1
        k=r['key']
        if r['status']=='SKIP' and any(x in r.get('reason','') for x in retry_reasons):
            retry[k]={'last_checked':now,'reason':r['reason']}
        else:
            retry.pop(k,None)
    # Bound retained state; keep only the most recently inspected candidates.
    if len(retry)>80:
        keep=dict(sorted(retry.items(),key=lambda item:item[1]['last_checked'],reverse=True)[:80])
        retry.clear(); retry.update(keep)
    s['dex_scan']=dict(checked_at=now,discovered=len(candidates),checked=len(records),by_chain={c:sum(r['chain']==c for r in records) for c in ('bsc','solana')},errors=errors,records=records,
        skip_reasons=counts,early_watch_count=sum(r['status']=='EARLY_WATCH' for r in records),early_watch_volume_usd=EARLY_WATCH_VOLUME_USD,paper_volume_usd=PAPER_ENTRY_VOLUME_USD,retry_queued=len(retry),retry_inspected=sum(k in eligible for k in selected),
        coverage='bounded sample; not all tokens',sell_check='BNB provider simulation required; Solana unintegrated => no new DEX entry')
    return quotes
