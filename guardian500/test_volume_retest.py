import unittest
from breakout_volume_retest import simulate
class TestVolumeRetest(unittest.TestCase):
    def bars(self):
        rows=[]
        for i in range(130):
            v=100.
            if i==80:v=110.
            elif 81<=i<=83:v=110.5
            elif i>83:v=112.
            low=100.5 if i==82 else v-.5
            rows.append(dict(time=1735689600+i*3600,open=v,high=v+.5,low=low,close=v,volume=500. if i==80 else 100.))
        return rows
    def test_read_only(self):
        result=simulate(self.bars())
        self.assertEqual(result["real_trades"],0)
        self.assertGreaterEqual(result["entries"],1)
    def test_no_volume_no_trade(self):
        rows=self.bars()
        for row in rows:row["volume"]=100.
        self.assertEqual(simulate(rows)["entries"],0)
if __name__=="__main__":unittest.main()
