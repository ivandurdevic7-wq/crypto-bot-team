"""Offline checks: no token feeds or trades."""
import unittest
from early_watch import compare,risk_alerts
class TestCompare(unittest.TestCase):
 def test_valid(self):
  a={"pair":"pool","last_seen_utc":"2026-10-28T06:00:00+00:00","liquidity_usd":100,"txns_m5_buys":2,"txns_m5_sells":4}
  z={"pair":"pool","last_seen_utc":"2026-10-28T06:15:00+00:00","liquidity_usd":75,"txns_m5_buys":6,"txns_m5_sells":3}
  d=compare(a,z)
  self.assertEqual(d["liquidity_change_pct"],-25.)
  self.assertEqual(d["txns_m5_buys_change"],4)
  self.assertEqual(d["status"],"COMPARABLE")
 def test_mismatch(self):
  self.assertEqual(compare({"pair":"a"},{"pair":"b"})["status"],"NO_COMPARABLE_PREVIOUS_SAMPLE")
 def test_missing(self):
  a={"pair":"a","last_seen_utc":"2026-10-28T06:00:00+00:00"}
  b={"pair":"a","last_seen_utc":"2026-10-28T06:15:00+00:00"}
  self.assertIsNone(compare(a,b)["liquidity_change_pct"])
class TestAlerts(unittest.TestCase):
 def test_liquidity_drop_and_sell_pressure(self):
  c={"status":"COMPARABLE","elapsed_minutes":15,"liquidity_change_pct":-30}
  a=risk_alerts({},{"txns_m5_buys":5,"txns_m5_sells":22},c)
  self.assertEqual({x["kind"] for x in a},{"LIQUIDITY_DROP","SELL_HEAVY_ACTIVITY"})
 def test_unknown_never_buy(self):
  a=risk_alerts({}, {},{"status":"NO_COMPARABLE_PREVIOUS_SAMPLE"})
  self.assertEqual(a[0]["level"],"UNKNOWN")
 def test_stale(self):
  a=risk_alerts({}, {},{"status":"COMPARABLE","elapsed_minutes":90})
  self.assertEqual(a[0]["kind"],"STALE_COMPARISON")
if __name__=="__main__":unittest.main()
