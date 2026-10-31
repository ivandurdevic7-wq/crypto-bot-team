"""EUROBOT 10 V3: optional LLM analysis, PAPER only.
LLM is advisory; missing key/network/invalid output => SKIP AI approval.
No wallets, live orders or secrets persisted.
"""
import json, os, urllib.request
STRATEGIES=("Cuvar","Trend","Momentum")
def evaluate(pair,bot_index):
    name=STRATEGIES[bot_index]
    result={"strategy":name,"decision":"UNAVAILABLE","reason":"AI API key nije postavljen","model":None}
    key=os.environ.get("OPENAI_API_KEY","").strip()
    if not key:return result
    model=os.environ.get("EUROBOT_AI_MODEL","gpt-4.1-mini")
    result["model"]=model
    try:
        price=float(pair["priceUsd"]);liq=float(pair["liquidity"]["usd"])
        volume=float(pair["volume"]["h24"]);hour=float(pair["priceChange"]["h1"])
        buys=int(pair.get("txns",{}).get("h1",{}).get("buys",0))
        payload={"strategy":name,"chain":pair.get("chainId"),
                 "dex":pair.get("dexId"),"symbol":pair.get("baseToken",{}).get("symbol"),
                 "price_usd":price,"liquidity_usd":liq,
                 "volume_24h_usd":volume,"price_change_1h_percent":hour,
                 "buys_1h":buys}
        instructions=("Procijeni PAPER trgovinu za strategiju "+name+
          ". Cuvar je konzervativan, Trend trazi umjereni uzlazni pomak, Momentum trazi potvrdu kupnji. "+
          "Vrati samo JSON s decision BUY ili SKIP i reason na hrvatskom (do 180 znakova). "+
          "Ako je informacija nedostatna, odaberi SKIP. Ne mijenjaj sigurnosna pravila.")
        body={"model":model,"instructions":instructions,
              "input":json.dumps(payload,ensure_ascii=False),"max_output_tokens":180}
        req=urllib.request.Request("https://api.openai.com/v1/responses",
          data=json.dumps(body).encode(),method="POST",
          headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=18) as r:response=json.load(r)
        chunks=[]
        for output in response.get("output",[]):
            if output.get("type")!="message":continue
            for item in output.get("content",[]):
                if item.get("type")=="output_text":chunks.append(item.get("text",""))
        parsed=json.loads("".join(chunks))
        decision=parsed.get("decision");reason=parsed.get("reason")
        if decision not in ("BUY","SKIP") or not isinstance(reason,str) or not reason.strip():
            raise ValueError("AI odgovor nije valjan")
        return {"strategy":name,"decision":decision,"reason":reason[:180],"model":model}
    except Exception as exc:
        return {"strategy":name,"decision":"ERROR","reason":"AI nedostupan: "+type(exc).__name__,"model":model}
