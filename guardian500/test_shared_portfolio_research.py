import unittest
from shared_portfolio_research import simulate
class SharedTests(unittest.TestCase):
 def test_flat_market_no_orders(self):
  data={sym:[dict(time=i*3600,open=100.,high=100.1,low=99.9,close=100.,volume=10.) for i in range(270)] for sym in ("BTCUSDT","ETHUSDT","SOLUSDT")}
  for mode in ("trend","retest","pullback"):
   r=simulate(data,mode)
   self.assertEqual(r["real_trades"],0)
   self.assertEqual(r["entries"],0)
   self.assertEqual(r["final_usdt"],500.)
if __name__=="__main__":unittest.main()
