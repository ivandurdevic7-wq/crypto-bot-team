"""Radar 105: read-only Wikipedia pageview research; not demand or profit proof; isolated prototype."""
import json,urllib.request,datetime,statistics
PAGES={"AI i tehnologija":"3D_printing","Proizvodnja":"Additive_manufacturing","Energija":"Solar_power","Trgovina":"Electronic_commerce","Usluge":"Right_to_repair","Financije":"Exchange-traded_fund"}
def fetch(page):
    end=datetime.datetime.now(datetime.timezone.utc).date()-datetime.timedelta(days=2)
    start=end-datetime.timedelta(days=62)
    u=f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{page}/daily/{start:%Y%m%d}/{end:%Y%m%d}"
    req=urllib.request.Request(u,headers={"User-Agent":"Radar105Research/0.1 (github research project; contact via GitHub)"})
    with urllib.request.urlopen(req,timeout=15) as resp:d=json.load(resp)
    rows=d.get("items",[])
    if len(rows)<50:raise ValueError("insufficient observations")
    values=[int(x["views"]) for x in rows]
    if min(values)<0:raise ValueError("negative views")
    return values,end
def evaluate(vals):
    prev=sum(vals[-28:-14]);recent=sum(vals[-14:])
    if prev<=0:return {"status":"INSUFFICIENT_DATA"}
    change=round(100*(recent/prev-1),2)
    return {"status":"POSSIBLE_INTEREST_CHANGE" if change>=20 else "NO_SIGNIFICANT_INCREASE",
       "previous_14d_views":prev,"recent_14d_views":recent,"change_percent":change}
def main():
    out={"app":"Radar105","mode":"RESEARCH_ONLY","source":"Wikimedia Pageviews API","generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"signals":[],"warnings":["Wikipedia pageviews do not prove market demand, purchases or profit.","Small predefined English-language page sample; not exhaustive market coverage."]}
    for cat,page in PAGES.items():
        try:
            vals,end=fetch(page)
            item={"category":cat,"topic":page.replace("_"," "),"reference_end_date":str(end),"source_url":"https://en.wikipedia.org/wiki/"+page,**evaluate(vals)}
        except Exception as e:item={"category":cat,"topic":page.replace("_"," "),"status":"UNAVAILABLE","reason":type(e).__name__}
        out["signals"].append(item)
    with open("radar105_public.json","w",encoding="utf-8") as f:json.dump(out,f,indent=2,ensure_ascii=False)
    print("RADAR105="+json.dumps({"topics":len(out["signals"]),"available":sum(s["status"]!="UNAVAILABLE" for s in out["signals"])},sort_keys=True))
if __name__=="__main__":main()
