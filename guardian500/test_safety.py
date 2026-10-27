import unittest
from safety import lp_check,simulation_check,liquidity_drop
class SafetyTests(unittest.TestCase):
 def evidence(self):
  return dict(dex=[{'pair':'pool','liquidity_type':'UniV2'}],lp_holders=[dict(address='locker',percent='.95',balance='100',is_locked='1',locked_detail=[dict(amount='100',end_time=100+8*86400)])])
 def test_lock_expiry_partial(self):
  d=self.evidence();self.assertEqual(lp_check(d,'bsc','pool',100)['status'],'PASS')
  d['lp_holders'][0]['locked_detail'][0]['amount']='10'
  with self.assertRaises(ValueError):lp_check(d,'bsc','pool',100)
 def test_near_unlock(self):
  d=self.evidence();d['lp_holders'][0]['locked_detail'][0]['end_time']=101
  with self.assertRaises(ValueError):lp_check(d,'bsc','pool',100)
 def test_wrong_pool_and_multiple(self):
  d=self.evidence()
  with self.assertRaises(ValueError):lp_check(d,'bsc','other',100)
  d['dex'].append(d['dex'][0])
  with self.assertRaises(ValueError):lp_check(d,'bsc','pool',100)
 def test_simulation(self):
  d=dict(chain={'id':56},token={'address':'token'},pair={'pair':{'address':'pool'}},simulationSuccess=True,honeypotResult={'isHoneypot':False},summary={'riskLevel':1},simulationResult=dict(buyTax=0,sellTax=0,transferTax=0,buyGas=100,sellGas=100,maxSell={'token':30}))
  self.assertEqual(simulation_check(d,'token','pool',25)['status'],'PASS')
  with self.assertRaises(ValueError):simulation_check(d,'token','pool',31)
  d['simulationSuccess']=False
  with self.assertRaises(ValueError):simulation_check(d,'token','pool',25)
 def test_drop(self):
  p={'pool':'a','at':100,'usd':100}
  self.assertTrue(liquidity_drop(p,{'pool':'a','usd':70},200))
  self.assertFalse(liquidity_drop(p,{'pool':'b','usd':70},200))
  self.assertFalse(liquidity_drop(p,{'pool':'a','usd':70},10000))
