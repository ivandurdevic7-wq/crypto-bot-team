import unittest
from whale_swap_alert import evaluate_receipt
from dex_swap_research import SWAP_TOPIC
WBNB="0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
PAIRS=[{"chainId":"bsc","baseToken":{"address":WBNB},"priceUsd":"700","liquidity":{"usd":2000000},"pairAddress":"0xpair"}]
def receipt(qty=20,verified=0):
 raw=[qty*10**18,0,0,1000*10**18]
 event={"topics":[SWAP_TOPIC],"data":"0x"+"".join(format(x,"064x") for x in raw),
 "address":"0xpool","transactionHash":"0xhash"}
 if verified is not None:event["verified_wbnb_position"]=verified
 return {"status":"0x1","block_timestamp":1000,"logs":[event]}
class Test(unittest.TestCase):
 def test_large(self):
  r=evaluate_receipt(receipt(),PAIRS,1030)
  self.assertEqual(r["alerts"],1)
 def test_low(self):
  r=evaluate_receipt(receipt(2),PAIRS,1030)
  self.assertEqual(r["alerts"],0)
 def test_old_no_alert(self):
  self.assertEqual(evaluate_receipt(receipt(),PAIRS,1500)["status"],"STALE_NO_ALERT")
 def test_no_pool_verification(self):
  self.assertEqual(evaluate_receipt(receipt(verified=None),PAIRS,1030)["alerts"],0)
 def test_failed_receipt(self):
  self.assertEqual(evaluate_receipt({"status":"0x0"},PAIRS,1030)["status"],"UNVERIFIED_NO_ALERT")
if __name__=="__main__":unittest.main()
