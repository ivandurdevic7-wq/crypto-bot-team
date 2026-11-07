import csv,datetime as dt,tempfile,unittest
from pathlib import Path
from backtest_offline import load,test_strategy
class BacktestTests(unittest.TestCase):
    def create(self,n=120,gap=False):
        temp=tempfile.TemporaryDirectory()
        path=Path(temp.name)/"bars.csv"
        with path.open("w",newline="") as f:
            writer=csv.writer(f); writer.writerow(["timestamp","open","high","low","close"])
            for i in range(n):
                v=100+i*.1
                writer.writerow([(dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(hours=i+(1 if gap and i>=15 else 0))).isoformat(),v,v+1,v-1,v])
        self.addCleanup(temp.cleanup)
        return path
    def test_runs_without_market_orders(self):
        result=test_strategy(load(self.create()))
        self.assertEqual(result["real_trades"],0)
        self.assertEqual(result["candles"],120)
    def test_rejects_missing_hour(self):
        with self.assertRaisesRegex(ValueError,"Hourly gap"): load(self.create(gap=True))
    def test_requires_history(self):
        with self.assertRaisesRegex(ValueError,"100"): load(self.create(n=80))
if __name__=="__main__":unittest.main()
