import unittest
from dex import discovery_score

class DiscoveryPriorityTests(unittest.TestCase):
    def test_eligible_pool_ranks_higher(self):
        p={'liquidity':{'usd':120000},'volume':{'h24':150000},
           'pairCreatedAt':1000*100,'txns':{'m5':{'buys':3,'sells':4}}}
        self.assertEqual(discovery_score(p,100000),4)
        p['liquidity']['usd']=5000
        self.assertEqual(discovery_score(p,100000),3)

    def test_unknown_values_cannot_qualify(self):
        self.assertEqual(discovery_score({'pairAddress':'abc'},100000),0)
        self.assertEqual(discovery_score({'liquidity':{'usd':'nan'}},100000),0)
