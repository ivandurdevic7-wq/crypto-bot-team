import json, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone

FILE = Path("status.json")
BOTS = ["BTC","ETH","SOL","PYTH","TIA","OP","BEAM","GEOD","PEAQ","AXIS"]
FEE = 0.001
CAPITAL = 160.0
LIMIT = 48.0

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"CryptoBotTeam/3.0"})
    with urllib.request.urlopen(req, timeout=18) as r:
        return json.load(r)

def save(state):
    FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def record(s, action, token, eur, note=""):
    s["trades"].append({"time":datetime.now(timezone.utc).isoformat(),
                        "action":action,"token":token,"eur":round(eur,4),"note":note})
    s["trades"] = s["trades"][-300:]

def check_book(symbol):
    if not symbol.isalnum():
        return False
    u = "https://api.binance.com/api/v3/depth?symbol=" + symbol.upper() + "USDT&limit=20"
    try:
        data = fetch(u)
        bids, asks = data["bids"], data["asks"]
        bid, ask = float(bids[0][0]), float(asks[0][0])
        if bid <= 0 or ask <= 0 or (ask-bid)/ask > 0.008:
            return False
        return sum(float(p)*float(q) for p,q in asks) >= 10000
    except Exception:
        return False

def main():
    if FILE.exists():
        s = json.loads(FILE.read_text())
    else:
        s = {"cash":CAPITAL,"positions":{},"trades":[]}
    s.setdefault("cash",CAPITAL)
    s.setdefault("positions",{})
    s.setdefault("trades",[])
    url = ("https://api.coingecko.com/api/v3/coins/markets?"
           "vs_currency=eur&order=market_cap_desc&per_page=250&page=1"
           "&sparkline=false&price_change_percentage=1h")
    try:
        coins = fetch(url)
        if not isinstance(coins,list):
            raise ValueError("API nije vratio popis tokena")
    except Exception as e:
        s["status"] = "Pogreska API-ja: " + str(e)[:100]
        save(s)
        print(s["status"])
        return
    prices = {c["id"]:c for c in coins}
    for token, pos in list(s["positions"].items()):
        c = prices.get(token)
        if not c or not c.get("current_price"):
            continue
        p = float(c["current_price"])
        if p <= 0:
            continue
        pos["last"] = p
        pos["peak"] = max(pos.get("peak",p),p)
        if p <= pos["buy_price"] * 0.97:
            gross = pos["qty"] * p
            net = gross * (1-FEE)
            s["cash"] += net
            record(s,"SELL",token,net,"Stop-loss 3% (provjera po rasporedu)")
            del s["positions"][token]
    exposure = sum(
        p["qty"]*p.get("last",p["buy_price"])
        for p in s["positions"].values()
    )
    candidates = sorted(
        [c for c in coins if isinstance(c.get("price_change_percentage_1h_in_currency"),(int,float))
         and c["price_change_percentage_1h_in_currency"] >= 4
         and (c.get("total_volume") or 0) >= 1000000
         and (c.get("market_cap") or 0) >= 10000000
         and (c.get("current_price") or 0) > 0],
        key=lambda c:c["price_change_percentage_1h_in_currency"],reverse=True
    )
    for i,c in enumerate(candidates[:20]):
        if s["cash"] < 5 or exposure + 5 > LIMIT:
            break
        token = c["id"]
        if token in s["positions"] or not check_book(c["symbol"]):
            continue
        price = float(c["current_price"])
        s["cash"] -= 5
        s["positions"][token] = {
            "symbol":c["symbol"].upper(),"buy_price":price,
            "last":price,"peak":price,"qty":5*(1-FEE)/price
        }
        exposure += 5*(1-FEE)
        record(s,"BUY",token,5,"Bot "+BOTS[i%10]+"; 1h rast >= 4%; naknada 0.1%")
    s["status"] = "Uspjesno skenirano "+str(len(coins))+" tokena"
    s["updated"] = datetime.now(timezone.utc).isoformat()
    s["value"] = round(s["cash"]+sum(
        p["qty"]*p.get("last",p["buy_price"])
        for p in s["positions"].values()),2)
    save(s)
    print(s["status"], "Virtualno EUR:",s["value"])

if __name__ == "__main__":
    main()
