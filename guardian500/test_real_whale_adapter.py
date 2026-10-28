import unittest
from unittest.mock import patch
from real_whale_adapter import verify_wbnb_pair,inspect_one
from dex_swap_validation import WBNB
class GuardTests(unittest.TestCase):
 @patch("real_whale_adapter.call")
 def test_wbnb_pool(self,call):
  other="0x"+"1"*40
  call.side_effect=["0x"+"0"*24+WBNB[2:],"0x"+"0"*24+other[2:]]
  self.assertEqual(verify_wbnb_pair("0x"+"2"*40),0)
 @patch("real_whale_adapter.call")
 def test_non_wbnb_reject(self,call):
  call.return_value="0x"+"0"*24+"1"*40
  with self.assertRaises(ValueError):verify_wbnb_pair("0x"+"2"*40)
 @patch("real_whale_adapter.request")
 def test_stale_rejects_without_price_fetch(self,req):
  req.side_effect=[{"status":"0x1","blockHash":"0xabc","logs":[]},{"timestamp":hex(1000)}]
  self.assertEqual(inspect_one("0xabc",now_ts=5000)["status"],"STALE_NO_ALERT")
 @patch("real_whale_adapter.request")
 def test_failed_receipt(self,req):
  req.return_value={"status":"0x0"}
  self.assertEqual(inspect_one("0xabc")["alerts"],0)
if __name__=="__main__":unittest.main()
