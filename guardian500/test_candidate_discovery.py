import unittest
from dex import candidate_quality, choose_candidates

NOW=2000000
class CandidateDiscoveryTests(unittest.TestCase):
    def test_quality_ranking(self):
        p={'pairAddress':'pool','liquidity':{'usd':60000},'volume':{'h24':40000},
           'pairCreatedAt':(NOW-50000)*1000,'txns':{'m5':{'buys':2,'sells':2}}}
        self.assertEqual(candidate_quality(p,NOW),4)
        self.assertEqual(candidate_quality({'pairAddress':'pool'},NOW),0)
    def test_select_20_and_prefer_good(self):
        candidates={'solana:t'+str(i):('solana','t'+str(i)) for i in range(30)}
        scores={'solana:t29':4}
        result=choose_candidates(candidates,scores,{}, {},NOW,20)
        self.assertEqual(len(result),20)
        self.assertIn('solana:t29',result)
    def test_retains_holdings_outside_cap(self):
        candidates={'bsc:t'+str(i):('bsc','t'+str(i)) for i in range(25)}
        result=choose_candidates(candidates,{}, {},{'bsc:held':{}},NOW,20)
        self.assertEqual(len(result),21)
        self.assertIn('bsc:held',result)
    def test_watch_priority(self):
        candidates={'solana:t'+str(i):('solana','t'+str(i)) for i in range(25)}
        result=choose_candidates(candidates,{}, {'solana:t24':{'last_seen':NOW-100}}, {}, NOW,20)
        self.assertIn('solana:t24',result)
if __name__=='__main__': unittest.main()
