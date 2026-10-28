import unittest
from dex import basic, check_security
NOW=1_800_000
def pair(liq=60000,vol=40000,age=50000,buys=2,sells=2):
    return {"priceUsd":"1.0","liquidity":{"usd":liq},"pairCreatedAt":(NOW-age)*1000,"volume":{"h24":vol},"txns":{"m5":{"buys":buys,"sells":sells}}}
class RelaxedPaperThresholdTests(unittest.TestCase):
    def test_relaxed_pass(self):
        self.assertEqual(basic(pair(),NOW),(1.0,60000.0))
    def test_liquidity_below_30k_blocked(self):
        with self.assertRaisesRegex(ValueError,"liquidity"): basic(pair(liq=29999),NOW)
    def test_liquidity_at_30k_allowed(self):
        self.assertEqual(basic(pair(liq=30000),NOW),(1.0,30000.0))
    def test_volume_below_20k_blocked(self):
        with self.assertRaisesRegex(ValueError,"volume"): basic(pair(vol=19999),NOW)
    def test_volume_at_20k_allowed(self):
        self.assertEqual(basic(pair(vol=20000),NOW),(1.0,60000.0))
    def test_age_below_12h_blocked(self):
        with self.assertRaisesRegex(ValueError,"younger"): basic(pair(age=43199),NOW)
    def test_missing_sell_activity_blocked(self):
        with self.assertRaisesRegex(ValueError,"buys/sells"): basic(pair(sells=1),NOW)
    def test_missing_security_still_fails_closed(self):
        with self.assertRaises(ValueError): check_security("bsc",{}, "pool")
if __name__=="__main__": unittest.main()
