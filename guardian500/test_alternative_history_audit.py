import unittest
from alternative_history_audit import months
import datetime as dt
class TestArchives(unittest.TestCase):
 def test_months(self):
  a=list(months(dt.datetime(2026,4,20),dt.datetime(2026,6,30)))
  self.assertEqual(a,[(2026,4),(2026,5),(2026,6)])
if __name__=="__main__":unittest.main()
