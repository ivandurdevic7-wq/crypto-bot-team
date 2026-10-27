"""PAPER ONLY. Public GET requests; no keys or order execution code."""
import json, math, time, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parent
FEE, SLIP = .004, .001  # modelling assumptions, not a fee quote
PAIRS = ('XBTEUR', 'ETHEUR', 'SOLEUR')

def api(endpoint, **params):
    url = 'https://api.kraken.com/0/public/' + endpoint + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.load(r)
    if data['error']: raise ValueError(str(data['error']))
    return data['result']

def market(pair, now):
    rows = next(v for k,v in api('OHLC', pair=pair, interval=60).items() if k != 'last')[:-1]
    if len(rows) < 60 or not 3600 <= now-int(rows[-1][0]) < 7500:
        raise ValueError('OHLC stale or insufficient')
    rows = rows[-60:]
    if any(int(b[0])-int(a[0]) != 3600 for a,b in zip(rows,rows[1:])):
        raise ValueError('OHLC gaps')
    closes = [float(r[4]) for r in rows]
    if not all(math.isfinite(x) and x > 0 for x in closes): raise ValueError('invalid price')
    tick = next(iter(api('Ticker', pair=pair).values()))
    bid, ask = float(tick['b'][0]), float(tick['a'][0])
    trades = next(v for k,v in api('Trades', pair=pair, count=1).items() if k != 'last')
    if not -30 <= now-float(trades[-1][2]) <= 300: raise ValueError('stale trades')
    if not 0 < bid <= ask or not math.isfinite(ask): raise ValueError('invalid quote')
    depth = next(iter(api('Depth', pair=pair, count=25).values()))
    buy_depth = sum(float(p)*float(q) for p,q,*_ in depth['asks'] if float(p)<=ask*1.002)
    sell_depth = sum(float(p)*float(q) for p,q,*_ in depth['bids'] if float(p)>=bid*.998)
    return dict(bid=bid, ask=ask, candle=int(rows[-1][0]),
                entry=closes[-1]>max(float(r[2]) for r in rows[-21:-1]) and sum(closes[-20:])/20>sum(closes[-50:])/50,
                exit=closes[-1]<sum(closes[-20:])/20,
                liquid=min(buy_depth,sell_depth)>=5000 and (ask-bid)/bid<=.002,
                volume_eur=float(tick['v'][1])*float(tick['p'][1]))

def initial():
    return dict(mode='PAPER', initial_eur=500, cash=500., positions={}, trades=[], peak=500., halted=False, seen={}, cooldown={})

def equity(s, quotes):
    return s['cash'] + sum(p['qty']*quotes[k]['bid']*(1-SLIP)*(1-FEE) for k,p in s['positions'].items())

def cycle(s, quotes, now):
    eq = equity(s,quotes)
    s['peak'] = max(s['peak'],eq)
    day = datetime.fromtimestamp(now,timezone.utc).date().isoformat()
    if s.get('day') != day: s.update(day=day, day_start=eq, day_paused=False)
    if eq <= s['peak']*.92: s['halted']=True
    if eq <= s['day_start']*.97: s['day_paused']=True
    decisions=[]
    for pair,q in quotes.items():
        p=s['positions'].get(pair)
        if p:
            p['high']=max(p['high'],q['bid'])
            reason = 'risk halt' if s['halted'] or s['day_paused'] else 'stop/trailing' if q['bid']<=max(p['entry']*.96,p['high']*.95) else 'trend exit' if q['exit'] else None
            if reason:
                price=q['bid']*(1-SLIP); gross=p['qty']*price; net=gross*(1-FEE)
                s['cash']+=net
                s['trades'].append(dict(time=now,pair=pair,side='SELL',price=price,qty=p['qty'],fee=gross*FEE,pnl=net-p['cost'],reason=reason))
                del s['positions'][pair]; s['cooldown'][pair]=now+21600
                decisions.append(pair+': SELL '+reason)
                continue
        fresh=q['candle']>s['seen'].get(pair,0)
        s['seen'][pair]=max(q['candle'],s['seen'].get(pair,0))
        if pair not in s['positions'] and fresh and q['entry'] and q['liquid'] and q['volume_eur']>=1e6 and not s['halted'] and not s['day_paused'] and now>=s['cooldown'].get(pair,0) and len(s['positions'])<2:
            # 0.75% equity risk budget including modelled round-trip costs.
            budget=min(eq*.0075/(.04+2*(FEE+SLIP)),eq*.20,max(0,s['cash']-eq*.40))
            if budget>=10:
                price=q['ask']*(1+SLIP); gross=budget/(1+FEE); qty=gross/price
                s['cash']-=budget
                s['positions'][pair]=dict(qty=qty,entry=price,cost=budget,high=q['bid'])
                s['trades'].append(dict(time=now,pair=pair,side='BUY',price=price,qty=qty,fee=gross*FEE,reason='hourly breakout + trend'))
                decisions.append(pair+': BUY'); continue
        decisions.append(pair+(': HOLD' if pair in s['positions'] else ': WAIT'))
    s.update(equity_eur=equity(s,quotes),updated_at=datetime.fromtimestamp(now,timezone.utc).isoformat(),status='OK',decisions=decisions,quotes=quotes)
    s['pnl_eur']=s['equity_eur']-500
    return s

def save(s):
    target=ROOT/'state.json'; temp=ROOT/'state.tmp'
    temp.write_text(json.dumps(s,indent=2,allow_nan=False)+'\n'); temp.replace(target)
    report = '# Čuvar 500 — PAPER\n\n' + '\n'.join(f'- {k}: {s.get(k)}' for k in ['updated_at','status','cash','equity_eur','pnl_eur','halted','decisions'])
    report+='\n\nVirtualni rezultat; nije stvarna zarada. Naknada modela 0,4% po strani + 0,1% slippage i bid/ask spread. Stop se provjerava samo pri pokretanju, pa gubitak može prijeći limit.\n'
    (ROOT/'STATUS.md').write_text(report)

def main():
    path=ROOT/'state.json'
    s=json.loads(path.read_text()) if path.exists() else initial()
    if s.get('mode')!='PAPER' or s.get('initial_eur')!=500: raise ValueError('Wrong ledger')
    try:
        now=time.time(); server=api('Time')['unixtime']
        if abs(now-server)>120: raise ValueError('server clock mismatch')
        if api('SystemStatus')['status']!='online': raise ValueError('exchange offline')
        quotes={p:market(p,now) for p in PAIRS}
        if time.time()-now>120: raise ValueError('snapshot too slow')
        cycle(s,quotes,now)
    except Exception as exc:
        s.update(status='SKIP_DATA_ERROR',error=str(exc),last_attempt=datetime.now(timezone.utc).isoformat())
        # Last valuation stays explicitly timestamped; never invent fills or prices.
        save(s); print(json.dumps({'status':s['status'],'error':s['error']})); return
    s.pop('error',None); save(s)
    print(json.dumps({k:s[k] for k in ['status','equity_eur','pnl_eur','decisions']}))
if __name__=='__main__': main()
