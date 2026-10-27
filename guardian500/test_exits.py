import unittest
from bot import initial,cycle
class ExitTests(unittest.TestCase):
 def setup_state(self):
  s=initial();s['cash']=475;s['positions']={'bsc:a':dict(qty=25,entry=1,cost=25,high=1)}
  return s
 def q(self,bid,**kw):
  q=dict(bid=bid,ask=bid,candle=1,entry=False,exit=False,liquid=True,volume_eur=1e6,fee=.004,slip=.01,gas=.25);q.update(kw);return {'bsc:a':q}
 def test_half_once_then_trail_accounting(self):
  s=self.setup_state();cycle(s,self.q(1.11),10000)
  self.assertEqual(s['positions']['bsc:a']['qty'],12.5);self.assertGreater(s['trades'][0]['pnl'],0)
  cycle(s,self.q(1.12),10001);self.assertEqual(len(s['trades']),1)
  cycle(s,self.q(1.08),10002);self.assertFalse(s['positions'])
  self.assertAlmostEqual(s['cash']-500,sum(t['pnl'] for t in s['trades']))
 def test_stop_gap_actual_price(self):
  s=self.setup_state();cycle(s,self.q(.90),10000)
  self.assertFalse(s['positions']);self.assertEqual(s['trades'][0]['reason'],'stop loss 5%')
  self.assertAlmostEqual(s['trades'][0]['price'],.891)
 def test_no_early_trail(self):
  s=self.setup_state();s['positions']['bsc:a']['high']=1.08
  cycle(s,self.q(1.02),10000);self.assertFalse(s['trades'])
 def test_costs_veto_half(self):
  s=self.setup_state();cycle(s,self.q(1.1,gas=2),10000);self.assertFalse(s['trades'])
 def test_emergency_priority(self):
  s=self.setup_state();cycle(s,self.q(1.2,emergency_exit=True),10000)
  self.assertFalse(s['positions']);self.assertFalse(s['trades'][0]['partial'])
