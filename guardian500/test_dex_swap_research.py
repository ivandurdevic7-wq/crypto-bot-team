import unittest
from dex_swap_research import parse,SWAP_TOPIC
class SwapTests(unittest.TestCase):
 def test_raw_amounts(self):
  e={"topics":[SWAP_TOPIC],"data":"0x"+"".join(f"{i:064x}" for i in (10,0,0,7)),"address":"0xpool","transactionHash":"0xtx"}
  v=parse(e)
  self.assertEqual(v["amount0_in_raw"],"10")
  self.assertEqual(v["status"],"UNPRICED_SWAP_NOT_WHALE_CLASSIFIED")
 def test_reject_wrong_topic(self):
  with self.assertRaises(ValueError):parse({"topics":["0xab"],"data":"0x"+"0"*256})
if __name__=="__main__":unittest.main()
