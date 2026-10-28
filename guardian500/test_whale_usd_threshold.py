import unittest
from whale_usd_threshold import classify_wbnb_swap as check
class Tests(unittest.TestCase):
 def test_confirmed_small(self):
  self.assertEqual(check("868252655142649991","670.20","689.12")["status"],"BELOW_THRESHOLD")
 def test_large(self):
  self.assertEqual(check(str(20*10**18),"670","689")["status"],"LARGE_SWAP_RESEARCH_ALERT")
 def test_straddling_is_not_alert(self):
  self.assertEqual(check(str(15*10**18),"650","700")["status"],"UNCERTAIN_THRESHOLD_NO_ALERT")
 def test_missing_price(self):
  self.assertEqual(check(str(10**18),None,None)["status"],"UNKNOWN_NO_ALERT")
 def test_invalid(self):
  self.assertEqual(check(str(10**18),"-1","900")["status"],"UNKNOWN_NO_ALERT")
if __name__=="__main__":unittest.main()
