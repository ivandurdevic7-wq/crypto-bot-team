import unittest
from dex import check_security, ZERO_BSC, ZERO_SOL, number, choose_candidates
from bot import initial,cycle
class DexTests(unittest.TestCase):
    def bsc(self):
        d={k:'0' for k in ZERO_BSC}
        d.update(is_open_source='1',buy_tax='0',sell_tax='0',holders=[{'percent':'.01'}]*10,dex=[{'pair':'abc','pool_fee':'.0025'}])
        return d
    def test_missing_honeypot_blocks(self):
        d=self.bsc(); del d['is_honeypot']
        with self.assertRaises(ValueError): check_security('bsc',d,'abc')
    def test_pool_identity(self):
        with self.assertRaises(ValueError): check_security('bsc',self.bsc(),'other')
    def test_safe_bsc_and_concentration(self):
        d=self.bsc(); self.assertEqual(check_security('bsc',d,'abc'),.004)
        d['holders'][0]={'percent':'.4'}
        with self.assertRaises(ValueError): check_security('bsc',d,'abc')
    def test_solana_freeze_and_hook(self):
        d={k:{'status':'0'} for k in ZERO_SOL}
        d.update(default_account_state='1',non_transferable='0',transfer_hook=[],transfer_fee={k:{'fee_rate':'0'} for k in ('current_fee_rate','scheduled_fee_rate')},holders=[{'percent':'.01'}]*10,dex=[{'id':'abc','fee_rate':'.003'}])
        self.assertEqual(check_security('solana',d,'abc'),.004)
        d['freezable']['status']='1'
        with self.assertRaises(ValueError): check_security('solana',d,'abc')
    def test_shared_cash_and_costs(self):
        s=initial(); q=dict(bid=1,ask=1,candle=100,entry=True,exit=False,liquid=True,volume_eur=2e6,cap=25,fee=.004,slip=.01,gas=.25,stop=.08,trail=.10,risk=.005,pair_address='pool')
        cycle(s,{'bsc:abc':q,'solana:def':q,'ETHEUR':q},10000)
        self.assertEqual(len(s['positions']),2)
        self.assertEqual(len(s['trades']),2)
        self.assertGreaterEqual(s['cash'],450)
        self.assertTrue(all(p['cost']<=25 for p in s['positions'].values()))
        self.assertLess(s['equity_eur'],500)
        q=dict(q,bid=.8,entry=False)
        cycle(s,{'bsc:abc':q,'solana:def':q},11000)
        self.assertFalse(s['positions']); self.assertLess(s['cash'],500)
        self.assertAlmostEqual(s['cash']-500,sum(t.get('pnl',0) for t in s['trades']))
    def test_second_chance_reserved(self):
        now=10000
        candidates={'bsc:retry':('bsc','retry')}
        candidates.update({'bsc:new'+str(i):('bsc','new'+str(i)) for i in range(30)})
        scores={k:4 for k in candidates}
        picked=choose_candidates(candidates,scores,{}, {},now,per_chain=5,
            retry_ready={'bsc:retry':{'last_checked':now-650}})
        self.assertIn('bsc:retry',picked)
        self.assertLessEqual(len(picked),5)
    def test_no_retry_without_eligibility(self):
        now=10000
        candidates={'bsc:retry':('bsc','retry')}
        candidates.update({'bsc:new'+str(i):('bsc','new'+str(i)) for i in range(30)})
        scores={k:(0 if k=='bsc:retry' else 4) for k in candidates}
        picked=choose_candidates(candidates,scores,{}, {},now,per_chain=5,retry_ready={})
        self.assertNotIn('bsc:retry',picked)
    def test_nan(self):
        with self.assertRaises(ValueError): number('nan')
