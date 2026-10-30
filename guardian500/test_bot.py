import unittest
from bot import initial, cycle

def quote(entry=True,bid=100,candle=3600):
    return dict(bid=bid,ask=bid*1.001,candle=candle,entry=entry,exit=False,liquid=True,volume_eur=2e6)
class Tests(unittest.TestCase):
    def test_buy_costs_and_duplicate(self):
        s=initial(); cycle(s,{'XBTEUR':quote()},10000)
        self.assertGreater(s['cash'],400); self.assertLess(s['equity_eur'],500)
        cycle(s,{'XBTEUR':quote()},10001); self.assertEqual(len(s['trades']),1)
    def test_stop_and_cooldown(self):
        s=initial(); cycle(s,{'XBTEUR':quote()},10000)
        cycle(s,{'XBTEUR':quote(bid=90,candle=7200)},14000)
        self.assertEqual(len(s['positions']),0); self.assertLess(s['trades'][-1]['pnl'],0)
        cycle(s,{'XBTEUR':quote(candle=10800)},15000); self.assertEqual(len(s['trades']),2)
    def test_halt(self):
        s=initial(); s['peak']=600
        cycle(s,{'XBTEUR':quote()},10000); self.assertTrue(s['halted']); self.assertFalse(s['positions'])
    def test_illiquid(self):
        s=initial(); q=quote(); q['liquid']=False
        cycle(s,{'XBTEUR':q},10000); self.assertEqual(s['cash'],500)
    def test_entry_diagnostics_wait(self):
        s=initial()
        cycle(s,{'XBTEUR':quote(entry=False)},10000)
        self.assertEqual(s['decisions'],['XBTEUR: WAIT'])
        self.assertFalse(s['entry_diagnostics']['XBTEUR']['checks']['entry_signal'])
        self.assertIn('entry_signal',s['entry_diagnostics']['XBTEUR']['blocked_by'])
        self.assertEqual(len(s['trades']),0)
    def test_entry_diagnostics_do_not_block_buy(self):
        s=initial()
        cycle(s,{'XBTEUR':quote(entry=True)},10000)
        self.assertEqual(s['decisions'],['XBTEUR: BUY'])
        self.assertTrue(s['entry_diagnostics']['XBTEUR']['checks']['entry_signal'])
if __name__=='__main__': unittest.main()
