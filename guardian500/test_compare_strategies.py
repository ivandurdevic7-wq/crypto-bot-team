import unittest
from compare_strategies import simulate
class ComparisonTests(unittest.TestCase):
 def bars(self):
  return [dict(time=1735689600+i*3600,open=100+i*.08,high=101+i*.08,low=99+i*.08,close=100+i*.08,volume=200) for i in range(140)]
 def test_same_capital(self):
  for mode in ("baseline","retest"):
   r=simulate(self.bars(),mode)
   self.assertGreater(r["final_eur"],0)
   self.assertGreaterEqual(r["entries"],0)
 def test_no_volume_signal(self):
  b=self.bars()
  for row in b:row["volume"]=0
  self.assertEqual(simulate(b,"retest")["entries"],0)
if __name__=="__main__":unittest.main()
