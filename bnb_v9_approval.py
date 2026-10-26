"""V9 PAPER-only approval gate. Never executes trades or handles credentials."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

def utcnow(): return datetime.now(timezone.utc)
def create_request(decision, requested_at=None):
    if decision.get("action")!="PENDING_APPROVAL":raise ValueError("Not an eligible decision")
    start=requested_at or utcnow()
    if start.tzinfo is None:raise ValueError("Timezone required")
    return {"id":start.strftime("%Y%m%dT%H%M%S%fZ")+"-"+str(decision["address"])[-6:],
            "token":decision["token"],"address":decision["address"],
            "size_eur":decision["size_eur"],"status":"WAITING",
            "created_at":start.isoformat(),"expires_at":(start+timedelta(minutes=5)).isoformat(),
            "mode":"PAPER","decision":decision}
def process(request, response=None, received_at=None):
    now=received_at or utcnow()
    if request.get("status")!="WAITING":return request
    expiry=datetime.fromisoformat(request["expires_at"])
    if now.tzinfo is None:raise ValueError("Timezone required")
    result=dict(request)
    result["status"]=("EXPIRED" if now>expiry else
                      "APPROVED_PAPER" if response=="DA" else
                      "REJECTED" if response=="NE" else "WAITING")
    # APPROVED_PAPER is not a purchase. Market/security rechecks still mandatory.
    return result

if __name__=="__main__":
    t=datetime(2026,10,26,tzinfo=timezone.utc)
    sample={"action":"PENDING_APPROVAL","address":"0x"+"a"*40,"token":"TEST","size_eur":10}
    r=create_request(sample,t)
    assert process(r,received_at=t+timedelta(minutes=6))["status"]=="EXPIRED"
    assert process(r,response="NE",received_at=t)["status"]=="REJECTED"
    assert process(r,response="DA",received_at=t)["status"]=="APPROVED_PAPER"
    assert process(r,response="yes",received_at=t)["status"]=="WAITING"
    print(json.dumps({"approval_gate":"PASS","mode":"PAPER","trades_executed":0}))
