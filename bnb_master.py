"""BNB MASTER Team 7: BSC/PancakeSwap paper trading. Never sends orders."""
import json, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
STATE = ROOT / 'bnb_status.json'
API = 'https://api.geckoterminal.com/api/v2'
SEC = 'https://api.gopluslabs.io/api/v1/token_security/56'
START = 160.0
MAX_BUY = 5.0
MAX_INVESTED = 48.0
MIN_LIQUIDITY_USD = 100000.0
MIN_VOLUME_USD = 50000.0
FEE_RATE = 0.003  # conservative illustrative fee + slippage on each side
STOP_LOSS = 0.03
TRAIL_START = 0.03
TRAIL_BACK = 0.015
BOT_NAMES = ['BNB trend','Momentum','Dip recovery','Breakout','Volume','Telegram (not connected)', 'New pools','Whale (not connected)','Risk guard','Portfolio']

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent':'BNB-Master-Paper-7/1.0','accept':'application/json'})
    with urllib.request.urlopen(req, timeout=18) as response: return json.load(response)
def fresh_state():
    return {'cash_eur':START,'initial_eur':START,'positions':{},'trades':[],'decisions':[],'last_success':None}
def load_state():
    if not STATE.exists(): return fresh_state()
    s=json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(s.get('positions'),dict) or not isinstance(s.get('trades'),list): raise ValueError('Nevaljano prethodno stanje')
    return s
def save(s):
    tmp=STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    os.replace(tmp,STATE)
def decide(s,token,result,reason):
    s['decisions'].append({'time':now(),'token':token,'decision':result,'reason':reason})
    s['decisions']=s['decisions'][-150:]
def num(v, default=0):
    try: return float(v)
    except (TypeError,ValueError):return default

def pools():
    # Public API has page/rate caps. The counter is factual, not a claim of 1000.
    records={}
    for page in (1,2,3):
        data=get_json(f'{API}/networks/bsc/pools?page={page}&include=base_token,quote_token,dex')
        included={i['id']:i for i in data.get('included',[])}
        for p in data.get('data',[]):
            a=p.get('attributes',{})
            dex=p.get('relationships',{}).get('dex',{}).get('data') or {}
            if 'pancake' not in str(dex.get('id','')).lower(): continue
            base=p.get('relationships',{}).get('base_token',{}).get('data') or {}
            tok=included.get(base.get('id'),{})
            addr=(tok.get('attributes') or {}).get('address')
            if not addr or not addr.startswith('0x'):continue
            price=num(a.get('base_token_price_usd'))
            liq=num(a.get('reserve_in_usd'))
            vol=num((a.get('volume_usd') or {}).get('h24'))
            change=num((a.get('price_change_percentage') or {}).get('h1'))
            if price<=0: continue
            item={'token':(tok.get('attributes') or {}).get('symbol') or addr[:10], 'address':addr.lower(), 'price_usd':price,'liquidity_usd':liq,'volume_24h_usd':vol,'change_1h_pct':change,'pool':p.get('id',''),'dex':dex.get('id','')}
            if addr.lower() not in records or liq>records[addr.lower()]['liquidity_usd']: records[addr.lower()]=item
        time.sleep(.35)
    return list(records.values())

def security(address):
    try:
        d=get_json(SEC+'?'+urllib.parse.urlencode({'contract_addresses':address}))
        r=(d.get('result') or {}).get(address.lower())
        if not isinstance(r,dict): return False,'Sigurnosni podaci nedostupni'
        # Fail closed: unknown fields and risk flags prohibit BUY.
        if r.get('is_honeypot')!='0':return False,'Honeypot nije isključen'
        if r.get('is_open_source')!='1':return False,'Ugovor nije potvrđeno otvoren'
        for flag in ('cannot_sell_all','is_blacklisted','hidden_owner','is_mintable'):
            if r.get(flag)!='0':return False,'Rizična ili nepoznata provjera: '+flag
        for tax in ('buy_tax','sell_tax'):
            v=num(r.get(tax),-1)
            if v<0 or v>0.05:return False,'Nepoznato ili visoko oporezivanje'
        return True,'Osnovni GoPlus filtri prolaze (nije jamstvo sigurnosti)'
    except Exception as e:return False,'GoPlus nije dostupan: '+str(e)[:70]

def run():
    s=load_state(); s['last_attempt']=now()
    try:
        entries=pools()
        usd_per_eur=num(get_json('https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD').get('rates',{}).get('USD'))
        if usd_per_eur<=0:raise ValueError('Nema pouzdanog EUR/USD tečaja')
        by_address={p['address']:p for p in entries}
        # Sell conservatively: do not invent prices if pool is missing.
        for address, pos in list(s['positions'].items()):
            q=by_address.get(address)
            if not q: decide(s,pos['token'],'WAIT','Nema nove cijene; izlaz nije simuliran');continue
            price=q['price_usd'];pos['last_usd']=price;pos['peak_usd']=max(num(pos.get('peak_usd')),price)
            cost=num(pos['cost_eur'])
            pnl=price/num(pos['entry_usd'])-1 if num(pos['entry_usd']) else -1
            trailing=pos['peak_usd']>=pos['entry_usd']*(1+TRAIL_START) and price<=pos['peak_usd']*(1-TRAIL_BACK)
            if pnl<=-STOP_LOSS or trailing:
                gross=num(pos['qty'])*price/usd_per_eur
                received=gross*(1-FEE_RATE)
                s['cash_eur']+=received
                s['trades'].append({'time':now(),'side':'SELL','token':pos['token'],'address':address,'eur':round(received,4),'pnl_eur':round(received-cost,4),'reason':'trailing stop' if trailing else 'stop loss'})
                del s['positions'][address]
        invested=sum(num(p['cost_eur']) for p in s['positions'].values())
        eligible=sorted((p for p in entries if p['liquidity_usd']>=MIN_LIQUIDITY_USD and p['volume_24h_usd']>=MIN_VOLUME_USD and 1<=p['change_1h_pct']<=8),key=lambda p:p['volume_24h_usd'],reverse=True)
        # At most 3 GoPlus checks per run to be polite to the provider.
        for p in eligible[:3]:
            a=p['address']
            if a in s['positions'] or s['cash_eur']<MAX_BUY or invested+MAX_BUY>MAX_INVESTED:continue
            ok,reason=security(a)
            if not ok:decide(s,p['token'],'SKIP',reason);continue
            entry=p['price_usd']*(1+FEE_RATE)
            qty=(MAX_BUY*usd_per_eur*(1-FEE_RATE))/entry
            s['cash_eur']-=MAX_BUY
            s['positions'][a]={'token':p['token'],'qty':qty,'entry_usd':entry,'peak_usd':entry,'last_usd':p['price_usd'],'cost_eur':MAX_BUY,'opened':now()}
            s['trades'].append({'time':now(),'side':'BUY','token':p['token'],'address':a,'eur':MAX_BUY,'reason':'MASTER odobrio, osnovni filtri prošli'})
            decide(s,p['token'],'BUY','PancakeSwap + likvidnost + volumen + GoPlus')
            invested+=MAX_BUY
        s['screened_count']=len(entries);s['eligible_count']=len(eligible)
        s['estimated_eur']=round(s['cash_eur']+sum(num(pos['qty'])*num(pos['last_usd'])/usd_per_eur for pos in s['positions'].values()),2)
        s['market_source']='GeckoTerminal BSC PancakeSwap pools';s['security_source']='GoPlus (reject on missing/uncertain)';s['bot_names']=BOT_NAMES
        s['last_success']=now();s['status']='OK — papirnato trgovanje; stvarni tržišni podaci'
    except Exception as e:
        s['status']='ERROR: '+str(e)[:160]
        decide(s,'SYSTEM','ERROR',str(e)[:150])
    s['trades']=s['trades'][-300:]
    save(s)
    print(s['status'],'cash',round(s['cash_eur'],2),'positions',len(s['positions']))
    if s['status'].startswith('ERROR'):raise RuntimeError(s['status'])
if __name__=='__main__':run()
