import unittest
from unittest.mock import patch
from whale_watch_monitor import observe
class Tests(unittest.TestCase):
 def test_bounds(self):
  with self.assertRaises(ValueError):observe(4,10)
 @patch("whale_watch_monitor.request")
 def test_empty(self,req):
  req.side_effect=["0x64",{"transactions":[]},{"transactions":[]},{"transactions":[]}]
  r=observe()
  self.assertEqual(r["alert_count"],0)
  self.assertEqual(r["status"],"SAMPLE_COMPLETE")
 @patch("whale_watch_monitor.request")
 def test_no_missing_block(self,req):
  req.side_effect=["0x64",None]
  with self.assertRaises(ValueError):observe()
if __name__=="__main__":unittest.main()
