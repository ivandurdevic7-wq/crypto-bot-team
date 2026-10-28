import unittest
from free_whale_watch import inspect
class WatchTest(unittest.TestCase):
 def test_threshold(self):
  block={"transactions":[{"value":hex(1001*10**18),"hash":"0x1","from":"0xa","to":"0xb"},{"value":hex(99*10**18),"hash":"0x2","from":"0xa","to":"0xc"}]}
  result=inspect(block)
  self.assertEqual(len(result),1)
  self.assertEqual(result[0]["category"],"NATIVE_BNB_TRANSFER_NOT_TRADE")
 def test_missing(self):
  with self.assertRaises(ValueError):inspect({})
if __name__=="__main__":unittest.main()
