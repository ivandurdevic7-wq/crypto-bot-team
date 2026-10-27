import unittest
from pullback_research import pullback
class PullbackTests(unittest.TestCase):
 def bars(self,n=260):
  return [dict(time=1735689600+i*3600,open=100+i*.05,high=101+i*.05,low=99+i*.05,close=100+i*.05,volume=100) for i in range(n)]
 def test_read_only(self):
  self.assertEqual(pullback(self.bars())["real_trades"],0)
 def test_no_false_profit_on_flat_data(self):
  rows=self.bars()
  for r in rows:r.update(open=100,high=100.1,low=99.9,close=100,volume=100)
  result=pullback(rows)
  self.assertEqual(result["entries"],0)
  self.assertEqual(result["final_eur"],500)
if __name__=="__main__": unittest.main()
