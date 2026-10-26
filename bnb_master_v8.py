"""BNB Master 8.0: research & PAPER trading ONLY. No wallets, keys or orders."""
import json, os, urllib.request, urllib.parse, urllib.error, time, socket
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'bnb_v8_status.json'
GECKO='https://api.geckoterminal.com/api/v2'
DEX='https://api.dexscreener.com'
GOPLUS='https://api.gopluslabs.io/api/v1/token_security/56'
FX='https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD'
START=160.0; BUY=5.0; MAX_INVESTED=48.0; FEE=0.003
MIN_LIQ=100000; MIN_VOL=50000; DAILY_LOSS_LIMIT=0.05
STOP=0.03; TRAIL_START=0.03; TRAIL_DROP=0.015
ROLES=['Trend','Momentum','Dip recovery','Breakout','Volume','Liquidity','New pools','DEX cross-check','Risk guard','Portfolio']

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def num(x,default=0):
    try:return float(x)
    except (TypeError,ValueError):return default

def request(url, retries=1):
    """Bounded retries; respect rate limits. Do not invent quotes."""
    last_error=None
    for attempt in range(retries+1):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'BNB-Master-V8-Paper/1.2','Accept':'application/json'})
            with urllib.request.urlopen(req,timeout=7) as r:return json.load(r)
        except urllib.error.HTTPError as e:
            last_error=e
            if e.code==429:
                if attempt<retries:
                    try:delay=min(max(float(e.headers.get('Retry-After','2')),1),4)
                    except (ValueError,TypeError):delay=2
                    time.sleep(delay)
                    continue
                raise RuntimeError('HTTP 429 rate limited by provider') from e
            if e.code<500 or attempt>=retries:raise RuntimeError('Market API HTTP '+str(e.code)) from e
        except (TimeoutError,socket.timeout,urllib.error.URLError,ConnectionError,OSError) as e:
            last_error=e
            if attempt>=retries:break
        if attempt<retries:time.sleep(1.2*(attempt+1))
    raise RuntimeError('Market API unavailable: '+str(last_error)[:100])


def initial():return {'cash_eur':START,'initial_eur':START,'positions':{},'trades':[], 'decisions':[],'daily':{},'status':'NEW'}
def load():
    if not STATE.exists():return initial()
    s=json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(s.get('positions'),dict) or not isinstance(s.get('trades'),list):raise ValueError('Invalid state')
    s.setdefault('decisions',[]);s.setdefault('daily',{});return s

def save(s):
    t=STATE.with_suffix('.tmp');t.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(t,STATE)

def note(s,symbol,result,reason):
    s['decisions'].append({'time':now(),'token':symbol,'decision':result,'reason':reason})
    s['decisions']=s['decisions'][-180:]

def fetch_pools():
    """Use available verified pools; stop provider requests when rate limited."""
    out={};errors=[];successful_pages=0
    for route in ('networks/bsc/pools','networks/bsc/trending_pools','networks/bsc/new_pools'):
        try:
            data=request(f'{GECKO}/{route}?page=1&include=base_token,dex')
            successful_pages+=1
        except Exception as e:
            errors.append(f'{route}: {str(e)[:75]}')
            if '429' in str(e):break
            continue
        incl={v['id']:v for v in data.get('included',[])}
        for p in data.get('data',[]):
            a=p.get('attributes') or {};rel=p.get('relationships') or {}
            dex=(rel.get('dex') or {}).get('data') or {}
            if 'pancake' not in str(dex.get('id','')).lower():continue
            token=(rel.get('base_token') or {}).get('data') or {}
            att=(incl.get(token.get('id')) or {}).get('attributes') or {}
            addr=str(att.get('address') or '').lower()
            if not(addr.startswith('0x') and len(addr)==42):continue
            price=num(a.get('base_token_price_usd'));liq=num(a.get('reserve_in_usd'))
            if price<=0:continue
            item={'address':addr,'symbol':att.get('symbol') or addr[:8],'price_usd':price,
                  'liquidity_usd':liq,'volume_h24':num((a.get('volume_usd') or {}).get('h24')),
                  'change_h1':num((a.get('price_change_percentage') or {}).get('h1')),
                  'change_h24':num((a.get('price_change_percentage') or {}).get('h24')),
                  'pool':p.get('id',''),'dex':str(dex.get('id','')),'source':route}
            if addr not in out or liq>out[addr]['liquidity_usd']:out[addr]=item
        time.sleep(1.2)
    return list(out.values()),successful_pages,errors


def dex_data(address):
    pairs=request(f'{DEX}/token-pairs/v1/bsc/{address}')
    if not isinstance(pairs,list):return None
    good=[p for p in pairs if p.get('chainId')=='bsc' and 'pancake' in str(p.get('dexId','')).lower() and
          str((p.get('baseToken') or {}).get('address','')).lower()==address]
    if not good:return None
    p=max(good,key=lambda x:num((x.get('liquidity') or {}).get('usd')))
    return {'price_usd':num(p.get('priceUsd')),'liquidity_usd':num((p.get('liquidity') or {}).get('usd')),
            'volume_h24':num((p.get('volume') or {}).get('h24')),
            'buys_h1':num(((p.get('txns') or {}).get('h1') or {}).get('buys')),
            'sells_h1':num(((p.get('txns') or {}).get('h1') or {}).get('sells')),
            'change_h1':num((p.get('priceChange') or {}).get('h1')),
            'pair_url':p.get('url','')}

def security(address):
    try:
        response=request(GOPLUS+'?'+urllib.parse.urlencode({'contract_addresses':address}))
        info=(response.get('result') or {}).get(address)
        if not isinstance(info,dict):return False,'No GoPlus report'
        for key,expected in [('is_honeypot','0'),('is_open_source','1'),('cannot_sell_all','0'),('is_blacklisted','0'),('hidden_owner','0'),('is_mintable','0')]:
            if str(info.get(key,''))!=expected:return False,'Security unknown/risk: '+key
        for key in ('buy_tax','sell_tax'):
            tax=num(info.get(key),-1)
            if tax<0 or tax>0.05:return False,'Tax unknown/high: '+key
        return True,'GoPlus baseline checks passed (not a safety guarantee)'
    except Exception as e:return False,'GoPlus unavailable: '+str(e)[:55]

def votes(g,d):
    """Ten roles with actual, inspectable scoring logic; conservative research indicators, not AI models."""
    return {'Trend':g['change_h24']>=0,
      'Momentum':1<=g['change_h1']<=8,
      'Dip recovery':-3<=g['change_h24']<=0 and g['change_h1']>0,
      'Breakout':g['change_h1']>=3 and d['buys_h1']>d['sells_h1'],
      'Volume':g['volume_h24']>=MIN_VOL,
      'Liquidity':min(g['liquidity_usd'],d['liquidity_usd'])>=MIN_LIQ,
      'New pools':g['source'].endswith('new_pools'),
      'DEX cross-check':g['price_usd']>0 and d['price_usd']>0 and abs(g['price_usd']/d['price_usd']-1)<=0.025,
      'Risk guard':d['liquidity_usd']>=MIN_LIQ and 0<=d['volume_h24'],
      'Portfolio':True}

def price_for_position(address, by_addr):
    # Never mark a disappeared position as zero, and try direct token lookup before skipping exits.
    p=by_addr.get(address)
    if p:return p['price_usd'],'GeckoTerminal'
    try:
        d=dex_data(address)
        if d and d['price_usd']>0:return d['price_usd'],'DEX Screener'
    except Exception:pass
    return None,'unavailable'

def run():
    s=load();s['last_attempt']=now();today=datetime.now(timezone.utc).date().isoformat()
    try:
        market,successful_pages,api_errors=fetch_pools()
        s['market_pages_ok']=successful_pages;s['market_api_errors']=api_errors[-8:]
        if not market:
            s['screened_count']=0;s['candidate_count']=0;s['reviewed']=[]
            s['status']='DEGRADED: No verifiable market quotes; no new trades'
            note(s,'SYSTEM','WAIT','Market source unavailable; positions unchanged')
            save(s);print(s['status']);return
        try:usd_per_eur=num((request(FX).get('rates') or {}).get('USD'))
        except Exception:usd_per_eur=0
        if usd_per_eur<=0:
            s['screened_count']=len(market);s['candidate_count']=0;s['reviewed']=[]
            s['status']='DEGRADED: EUR/USD unavailable; no trades'
            note(s,'SYSTEM','WAIT','Missing FX rate; trades skipped, positions preserved')
            save(s);print(s['status']);return
        by_addr={p['address']:p for p in market}
        for addr,pos in list(s['positions'].items()):
            price,source=price_for_position(addr,by_addr)
            if price is None:note(s,pos['token'],'WAIT','No current price: no fictitious sale');continue
            pos['last_usd']=price;pos['peak_usd']=max(num(pos.get('peak_usd')),price)
            entry=num(pos.get('entry_usd'))
            trailing=entry>0 and pos['peak_usd']>=entry*(1+TRAIL_START) and price<=pos['peak_usd']*(1-TRAIL_DROP)
            if entry>0 and (price<=entry*(1-STOP) or trailing):
                proceeds=num(pos['qty'])*price/usd_per_eur*(1-FEE)
                cost=num(pos['cost_eur']);s['cash_eur']+=proceeds
                s['trades'].append({'time':now(),'side':'SELL','token':pos['token'],'address':addr,'eur':round(proceeds,4),'pnl_eur':round(proceeds-cost,4),'reason':'TRAIL' if trailing else 'STOP','price_source':source})
                del s['positions'][addr]
        estimated=s['cash_eur']+sum(num(p['qty'])*num(p.get('last_usd',p['entry_usd']))/usd_per_eur for p in s['positions'].values())
        s['daily'].setdefault(today,{'start_eur':round(estimated,4)})
        daily_start=num(s['daily'][today]['start_eur'],START)
        halt=estimated<=daily_start*(1-DAILY_LOSS_LIMIT)
        invested=sum(num(p['cost_eur']) for p in s['positions'].values())
        candidates=sorted((p for p in market if p['liquidity_usd']>=MIN_LIQ and p['volume_h24']>=MIN_VOL and 1<=p['change_h1']<=8),key=lambda p:p['volume_h24'],reverse=True)
        reviewed=[]
        for p in candidates[:3]:
            if p['address'] in s['positions']:continue
            try:
                d=dex_data(p['address'])
                if not d:note(s,p['symbol'],'SKIP','DEX Screener pair unavailable');continue
                v=votes(p,d)
                reviewed.append({'token':p['symbol'],'address':p['address'],'votes':v,'score':sum(v.values()),'dex_url':d['pair_url']})
                required=['Momentum','Volume','Liquidity','DEX cross-check','Risk guard']
                if not all(v[k] for k in required):note(s,p['symbol'],'SKIP','Signal/DEX verification insufficient');continue
                if halt or s['cash_eur']<BUY or invested+BUY>MAX_INVESTED:
                    note(s,p['symbol'],'WAIT','Capital/risk limit');continue
                ok,why=security(p['address'])
                if not ok:note(s,p['symbol'],'SKIP',why);continue
                # Strictly simulated fill with example cost assumptions.
                entry=d['price_usd']*(1+FEE)
                qty=BUY*usd_per_eur*(1-FEE)/entry
                s['cash_eur']-=BUY;s['positions'][p['address']]={'token':p['symbol'],'qty':qty,'entry_usd':entry,'peak_usd':entry,'last_usd':d['price_usd'],'cost_eur':BUY,'opened':now()}
                s['trades'].append({'time':now(),'side':'BUY','token':p['symbol'],'address':p['address'],'eur':BUY,'reason':'MASTER: Gecko + DEX + GoPlus verified','votes':v})
                note(s,p['symbol'],'BUY','Virtual trade; verification passed');invested+=BUY
            except Exception as e:
                note(s,p['symbol'],'SKIP','API error: '+str(e)[:65])
                if '429' in str(e):
                    api_errors.append('DEX/GoPlus rate limited')
                    break
        s['reviewed']=reviewed;s['screened_count']=len(market);s['candidate_count']=len(candidates)
        s['estimated_eur']=round(s['cash_eur']+sum(num(p['qty'])*num(p.get('last_usd',p['entry_usd']))/usd_per_eur for p in s['positions'].values()),2)
        s['roles']=ROLES;s['daily_halt']=halt;s['last_success']=now();s['status']=('OK (partial API coverage)' if api_errors else 'OK')+' | BSC PancakeSwap | real quotes, PAPER ONLY'
    except Exception as e:
        s['status']='ERROR: '+str(e)[:160];note(s,'SYSTEM','ERROR',str(e)[:130])
    s['trades']=s['trades'][-400:];save(s)
    print(s['status'],'cash',round(s['cash_eur'],2),'positions',len(s['positions']),'screened',s.get('screened_count'))
    if s['status'].startswith('ERROR'):raise RuntimeError(s['status'])
if __name__=='__main__':run()
