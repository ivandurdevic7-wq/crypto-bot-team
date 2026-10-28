import unittest
from current_whale_quote import select_quote,assess_current
WBNB="0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
def pair(price="650",liquidity=2000000):
 return {"chainId":"bsc","baseToken":{"address":WBNB},"priceUsd":price,"liquidity":{"usd":liquidity},"pairAddress":"0xpair"}
class Test(unittest.TestCase):
 def test_valid(self):self.assertEqual(str(select_quote([pair()])["price_usd"]),"650")
 def test_reject_thin(self):
  with self.assertRaises(ValueError):select_quote([pair(liquidity=100)])
 def test_no_alert_uncertainty(self):
  self.assertEqual(assess_current(str(15*10**18),[pair()])["status"],"UNCERTAIN_THRESHOLD_NO_ALERT")
 def test_large_activity(self):
  self.assertEqual(assess_current(str(20*10**18),[pair()])["status"],"LARGE_SWAP_RESEARCH_ALERT")
 def test_invalid_price(self):
  with self.assertRaises(ValueError):select_quote([pair(price="nan")])
if __name__=="__main__":unittest.main()
