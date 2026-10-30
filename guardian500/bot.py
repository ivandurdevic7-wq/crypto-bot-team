"""PAPER ONLY. Public GET requests; no keys or order execution code."""
import json, math, time, urllib.request, urllib.parse
import copy
from dex import scan
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parent
FEE, SLIP = .004, .001  # modelling assumptions, not a fee quote
PAIRS = ('XBTEUR', 'ETHEUR', 'SOLEUR')

def api(endpoint, **params):
    url = 'https://api.kraken.com/0/public/' + endpoint + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=8) as r:
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
    breakout=closes[-1]>max(float(r[2]) for r in rows[-21:-1])
    trend=sum(closes[-20:])/20>sum(closes[-50:])/50
    return dict(bid=bid, ask=ask, candle=int(rows[-1][0]),
                entry=breakout and trend, breakout=breakout, trend=trend,
                exit=closes[-1]<sum(closes[-20:])/20,
                liquid=min(buy_depth,sell_depth)>=5000 and (ask-bid)/bid<=.002,
                volume_eur=float(tick['v'][1])*float(tick['p'][1]))

def initial():
    return dict(mode='PAPER', initial_eur=500, cash=500., positions={}, trades=[], peak=500., halted=False, seen={}, cooldown={})

def equity(s, quotes):
    return s['cash'] + sum(max(0,p['qty']*quotes[k]['bid']*(1-quotes[k].get('slip',SLIP))*(1-quotes[k].get('fee',FEE))-quotes[k].get('gas',0)) for k,p in s['positions'].items())

def cycle(s, quotes, now):
    s['exit_rules']={'take_profit_pct':10,'sell_fraction':.5,'trailing_after_tp_pct':3,'stop_loss_pct':5,'check_interval_minutes':15,'execution':'next validated observation; not guaranteed stop price'}
    eq = equity(s,quotes)
    s['peak'] = max(s['peak'],eq)
    day = datetime.fromtimestamp(now,timezone.utc).date().isoformat()
    if s.get('day') != day: s.update(day=day, day_start=eq, day_paused=False)
    if eq <= s['peak']*.92: s['halted']=True
    if eq <= s['day_start']*.97: s['day_paused']=True
    decisions=[]
    entry_diagnostics={}
    for pair,q in quotes.items():
        fee,slip,gas=q.get('fee',FEE),q.get('slip',SLIP),q.get('gas',0)
        p=s['positions'].get(pair)
        if p:
            # Applies to existing positions as well; preserve cost basis and quantities.
            p['stop']=.05; p['trail']=.03
            p['high']=max(p['high'],q['bid'])
            reason = ('risk halt' if s['halted'] or s['day_paused'] else
                      'security/liquidity exit' if q.get('emergency_exit') else
                      'stop loss 5%' if q['bid']<=p['entry']*.95 else
                      'trailing 3% after profit taking' if p.get('tp_done') and q['bid']<=p['high']*.97 else
                      'trend exit' if q['exit'] else None)
            fraction=1.
            if not reason and not p.get('tp_done') and q['bid']>=p['entry']*1.10:
                half=p['qty']*.5*q['bid']*(1-slip)*(1-fee)-gas
                # Profit must exceed the proportional cost basis, including entry costs.
                if half>p['cost']*.5:
                    reason='take profit 10%: sell half'; fraction=.5
            if reason:
                qty=p['qty']*fraction; basis=p['cost']*fraction
                price=q['bid']*(1-slip); gross=qty*price; net=max(0,gross*(1-fee)-gas)
                s['cash']+=net
                s['trades'].append(dict(time=now,pair=pair,side='SELL',price=price,qty=qty,fee=gross*fee,gas=gas,pnl=net-basis,cost_basis=basis,partial=fraction<1,reason=reason))
                if fraction<1:
                    p['qty']-=qty; p['cost']-=basis; p['tp_done']=True
                else:
                    del s['positions'][pair]; s['cooldown'][pair]=now+21600
                decisions.append(pair+': SELL '+reason)
                continue
        fresh=q['candle']>s['seen'].get(pair,0)
        s['seen'][pair]=max(q['candle'],s['seen'].get(pair,0))
        if pair in PAIRS:
            # Diagnostic only: mirrors the existing entry gate; never authorizes orders.
            checks={
                'new_candle': bool(fresh),
                'entry_signal': q['entry'] is True,
                'liquidity': q['liquid'] is True,
                'volume': q['volume_eur']>=q.get('min_volume',1e6),
                'risk_not_halted': not s['halted'],
                'day_not_paused': not s['day_paused'],
                'cooldown_complete': now>=s['cooldown'].get(pair,0),
                'position_limit': len(s['positions'])<2,
                'not_already_held': pair not in s['positions'],
            }
            if 'breakout' in q: checks['breakout']=q['breakout'] is True
            if 'trend' in q: checks['trend']=q['trend'] is True
            entry_diagnostics[pair]={
                'checked_at':datetime.fromtimestamp(now,timezone.utc).isoformat(),
                'candle':q['candle'],
                'checks':checks,
                'blocked_by':[k for k,v in checks.items() if not v],
                'note':'Diagnostic only; not a trading instruction',
            }
        if pair not in s['positions'] and fresh and q['entry'] and q['liquid'] and q['volume_eur']>=q.get('min_volume',1e6) and not s['halted'] and not s['day_paused'] and now>=s['cooldown'].get(pair,0) and len(s['positions'])<2:
            # 0.75% equity risk budget including modelled round-trip costs.
            budget=min(max(0,eq*q.get('risk',.0075)-2*gas)/(.05+2*(fee+slip)),eq*.20,q.get('cap',eq*.20),max(0,s['cash']-eq*.40))
            if budget>=10:
                price=q['ask']*(1+slip); gross=(budget-gas)/(1+fee); qty=gross/price
                s['cash']-=budget
                s['positions'][pair]=dict(qty=qty,entry=price,cost=budget,high=q['bid'],stop=.05,trail=.03,tp_done=False,pair_address=q.get('pair_address'))
                s['trades'].append(dict(time=now,pair=pair,side='BUY',price=price,qty=qty,fee=gross*fee,gas=gas,reason=q.get('reason','hourly breakout + trend')))
                decisions.append(pair+': BUY'); continue
        decisions.append(pair+(': HOLD' if pair in s['positions'] else ': WAIT'))
    s['entry_diagnostics']=entry_diagnostics
    s.update(equity_eur=equity(s,quotes),updated_at=datetime.fromtimestamp(now,timezone.utc).isoformat(),status='OK',decisions=decisions,quotes=quotes)
    s['pnl_eur']=s['equity_eur']-500
    return s

def save(s):
    target=ROOT/'state.json'; temp=ROOT/'state.tmp'
    temp.write_text(json.dumps(s,indent=2,allow_nan=False)+'\n'); temp.replace(target)
    report = '# Čuvar 500 — PAPER\n\n' + '\n'.join(f'- {k}: {s.get(k)}' for k in ['updated_at','status','cash','equity_eur','pnl_eur','halted','decisions'])
    scan_data=s.get('dex_scan',{})
    report+='\n\n## BNB Chain i Solana\n\n'+str(scan_data.get('by_chain',{}))+'\n\n'
    report+='| Token / adresa | Mreža | Odluka | Razlog |\n|---|---|---|---|\n'
    for r in scan_data.get('records',[]):
        clean=lambda v: str(v).replace('|','/').replace('\n',' ')
        report+='| '+' | '.join(clean(v) for v in [r.get('symbol',r['address']),r['chain'],r['status'],r.get('reason','čekanje potvrde signala')])+' |\n'
    report+='\nDEX: model naknade najmanje 0,4%, slippage 1% i mrežni trošak 0,25 EUR po strani. Nije izvediva swap ponuda. Uzorak tokena, ne cijela mreža. Nedostajući podaci = SKIP.\n'
    report+='\n\nVirtualni rezultat; nije stvarna zarada. Naknada modela 0,4% po strani + 0,1% slippage i bid/ask spread. Stop se provjerava samo pri pokretanju, pa gubitak može prijeći limit.\n'
    (ROOT/'STATUS.md').write_text(report)

def main():
    path=ROOT/'state.json'
    s=json.loads(path.read_text()) if path.exists() else initial()
    if s.get('mode')!='PAPER' or s.get('initial_eur')!=500: raise ValueError('Wrong ledger')
    now=time.time()
    s['last_attempt']=datetime.fromtimestamp(now,timezone.utc).isoformat()
    s['safety_version']=3
    quotes={}; errors=[]
    # Discovery runs independently of the exchange feeds.
    fx=None
    try:
        fxq=market('EURUSD',now)
        fx=(fxq['bid']+fxq['ask'])/2
    except Exception as e:
        errors.append('FX: '+str(e))
    try:
        quotes.update(scan(s,now,fx))
    except Exception as e:
        errors.append('DEX: '+str(e))
        s['dex_scan']=dict(checked_at=now,errors=[str(e)],records=[],by_chain={})
    for pair in PAIRS:
        try: quotes[pair]=market(pair,time.time())
        except Exception as e: errors.append(pair+': '+str(e))
    try:
        if time.time()-now>240: raise ValueError('snapshot too slow')
        missing=set(s['positions'])-set(quotes)
        s['pending_exit_checks']=sorted(missing)
        if missing: raise ValueError('held asset data unavailable; no fills: '+','.join(sorted(missing)))
        if not quotes: raise ValueError('no valid quotes')
        # Transactional ledger: a failed cycle must not leave partially executed fills.
        work=copy.deepcopy(s)
        cycle(work,quotes,now)
        s=work
        s['source_errors']=errors
        if errors: s['status']='PARTIAL_DATA'
    except Exception as exc:
        s.update(status='SKIP_DATA_ERROR',error=str(exc),last_attempt=datetime.now(timezone.utc).isoformat(),source_errors=errors)
        save(s); print(json.dumps({'status':s['status'],'error':s['error']})); return
    s['last_cycle_completed_at']=datetime.now(timezone.utc).isoformat()
    s.pop('error',None); save(s)
    print(json.dumps({k:s[k] for k in ['status','equity_eur','pnl_eur','decisions']}))
if __name__=='__main__': main()
