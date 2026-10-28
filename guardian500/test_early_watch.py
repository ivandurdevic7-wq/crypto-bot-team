"""Offline checks: no token feeds or trades."""
import unittest
from early_watch import compare
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
if __name__=="__main__":unittest.main()
