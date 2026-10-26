"""Crypto Bot Team 4.0 -- hourly paper trading only; no API keys/orders."""
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

STATE = Path(__file__).with_name('status.json')
BASE = 'https://data-api.binance.vision'
START = 160.0
MAX_BUY = 5.0
MAX_EXPOSURE = 48.0
FEE = .001
SLIPPAGE = .001
STOP = .03
MIN_VOLUME = 2_000_000
MIN_DEPTH = 20_000
MAX_SPREAD = .005
BOTS = ['BTC', 'ETH', 'SOL', 'PYTH', 'TIA', 'OP', 'BEAM', 'GEOD', 'PEAQ', 'AXIS']

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def fetch(path):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': 'CryptoTeamPaper/4.0'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)

def state_load():
    if STATE.exists():
        state = json.loads(STATE.read_text(encoding='utf-8'))
        if 'cash' in state and 'positions' in state:
            state.setdefault('trades', [])
            state.setdefault('decisions', [])
            for pos in state['positions'].values():
                if 'entry' not in pos and 'buy_price' in pos:
                    pos['entry'] = pos['buy_price']
                if 'last' not in pos and 'entry' in pos:
                    pos['last'] = pos['entry']
            return state
    return {'cash': START, 'positions': {}, 'trades': [], 'decisions': [], 'start_eur': START}

def write(s):
    STATE.write_text(json.dumps(s, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def note(s, symbol, result, reason):
    s['decisions'].append({'time': now(), 'token': symbol, 'result': result, 'reason': reason})
    s['decisions'] = s['decisions'][-150:]

def execute_sell(s, symbol, bid, eurusdt, reason):
    pos = s['positions'].pop(symbol)
    proceeds = pos['qty'] * bid * (1 - SLIPPAGE) * (1 - FEE) / eurusdt
    s['cash'] += proceeds
    s['trades'].append({'time': now(), 'side': 'SELL', 'token': symbol, 'eur': round(proceeds, 4), 'reason': reason})

def depth_ok(symbol):
    book = fetch('/api/v3/depth?symbol=' + symbol + '&limit=20')
    def total(key):
        return sum(float(price) * float(qty) for price, qty in book[key])
    return total('bids') >= MIN_DEPTH and total('asks') >= MIN_DEPTH

def hour_signal(symbol):
    candles = fetch('/api/v3/klines?symbol=' + symbol + '&interval=1m&limit=65')
    if len(candles) < 62:
        return None
    closed = candles[:-1]
    close = [float(x[4]) for x in closed]
    vol = [float(x[7]) for x in closed]
    if close[-61] <= 0:
        return None
    growth = (close[-1] / close[-61] - 1) * 100
    recent = sum(close[-15:]) / 15
    previous = sum(close[-45:-30]) / 15
    return growth, recent > previous, sum(vol[-15:]) > sum(vol[-30:-15]) * .75

def scan():
    s = state_load()
    try:
        tickers = fetch('/api/v3/ticker/24hr')
        market = {x['symbol']: x for x in tickers if x.get('symbol', '').endswith('USDT')}
        fx = float(market['EURUSDT']['lastPrice'])
        if fx <= 0:
            raise ValueError('Invalid EURUSDT rate')
        for symbol, pos in list(s['positions'].items()):
            q = market.get(symbol)
            if not q or not float(q['bidPrice']):
                note(s, symbol, 'WAIT', 'Nema pouzdane cijene za provjeru izlaza')
                continue
            bid = float(q['bidPrice'])
            pos['last'] = bid
            if bid <= pos['entry'] * (1 - STOP):
                execute_sell(s, symbol, bid, fx, 'Stop-loss 3% na satnoj provjeri')
        exposure = sum(p['qty'] * p.get('last', p['entry']) / fx for p in s['positions'].values())
        btc = market.get('BTCUSDT', {})
        btc_positive = float(btc.get('priceChangePercent', 0)) >= 0
        candidates = sorted((q for sym, q in market.items()
                    if sym != 'EURUSDT' and sym[:-4].isalnum()
                    and float(q.get('quoteVolume', 0)) >= MIN_VOLUME
                    and float(q.get('priceChangePercent', 0)) >= 0),
                    key=lambda q: float(q['priceChangePercent']), reverse=True)[:25]
        for q in candidates:
            symbol = q['symbol']
            if symbol in s['positions'] or s['cash'] < MAX_BUY or exposure + MAX_BUY > MAX_EXPOSURE:
                continue
            ask, bid = float(q['askPrice']), float(q['bidPrice'])
            if ask <= 0 or bid <= 0:
                continue
            spread = (ask - bid) / ask
            try:
                signal = hour_signal(symbol)
                if signal is None:
                    note(s, symbol, 'REJECT', 'Nedovoljno podataka za 1h trend')
                    continue
                rise, trend, volume_ok = signal
                if not 4 <= rise <= 12:
                    continue
                votes = {'BTC_trend': btc_positive,
                         'trend_15m': trend,
                         'volume_15m': volume_ok,
                         'spread': spread <= MAX_SPREAD}
                if not all(votes.values()):
                    note(s, symbol, 'REJECT', 'Nema potvrde: ' + ', '.join(k for k, v in votes.items() if not v))
                    continue
                if not depth_ok(symbol):
                    note(s, symbol, 'REJECT', 'Premala dubina knjige naloga')
                    continue
                qty = MAX_BUY * fx * (1 - FEE) / (ask * (1 + SLIPPAGE))
                s['cash'] -= MAX_BUY
                s['positions'][symbol] = {'qty': qty, 'entry': ask * (1 + SLIPPAGE), 'last': bid,
                                          'opened': now(), 'cost_eur': MAX_BUY}
                s['trades'].append({'time': now(), 'side': 'BUY', 'token': symbol,
                                    'eur': MAX_BUY, 'rise_1h': round(rise, 2), 'confirmations': votes})
                exposure += MAX_BUY
                note(s, symbol, 'BUY', '4/4 potvrde, provjerena dubina, virtualna kupnja')
            except Exception as err:
                note(s, symbol, 'SKIP', 'Podaci nedostupni: ' + str(err)[:90])
        s['last_success'] = now()
        s['status'] = 'OK; stvarni podaci, virtualne transakcije'
        s['screened_market_count'] = len(market)
        s['scanned_candidates'] = len(candidates)
        s['estimated_eur'] = round(s['cash'] + sum(p['qty'] * p.get('last', p['entry']) / fx for p in s['positions'].values()), 2)
    except Exception as err:
        s['status'] = 'API ERROR: ' + str(err)[:120]
        s['last_attempt'] = now()
    s['trades'] = s['trades'][-300:]
    write(s)
    print(s['status'], 'cash=', round(s['cash'], 2), 'positions=', list(s['positions']))

if __name__ == '__main__':
    scan()
