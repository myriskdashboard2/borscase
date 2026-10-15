import unittest
from unittest.mock import patch
import nyckeltal as n
import fundamenta as fu

class FiguresTests(unittest.TestCase):
    def sample(self):
        return {'symbol':'TEST','rapportvaluta':'SEK','borsvarde':1000,'historik':[
            {'slut':'2024-12-31','intakter':100,'nettoresultat':10,'kfo':20,'capex':-5},
            {'slut':'2025-12-31','intakter':120,'nettoresultat':12,'kfo':30,'capex':8,'ebitda':20,'rorelseresultat':15,'kassa':10,'total_skuld':40,'utdelning':6,'aktier_utspadda':10}]}
    def rows(self,c,period='annual'):
        return {r['id']:r for g in n.build(c,period)['grupper'] for r in g['rader']}
    def test_cash_and_ratios(self):
        rows=self.rows(self.sample())
        self.assertEqual(rows['fritt_kassaflode']['varde'],22)
        self.assertEqual(rows['fritt_kassaflode']['fore'],15)
        self.assertEqual(rows['nettoskuld']['varde'],30)
        self.assertEqual(rows['nettoskuld_ebitda']['varde'],1.5)
        self.assertEqual(rows['utdelningsandel']['varde'],.5)
        self.assertAlmostEqual(rows['pe']['varde'],1000/12)
        self.assertIsNone(rows['pe']['fore'])
    def test_loss_and_missing_are_not_zero(self):
        c=self.sample();c['historik'][-1]['nettoresultat']=-10;c['historik'][-1]['capex']=None
        r=self.rows(c)
        self.assertIsNone(r['pe']['varde'])
        self.assertIsNone(r['fritt_kassaflode']['varde'])
        self.assertIsNone(r['kassagenerering']['varde'])
    def test_ttm_no_annual_fallback(self):
        r=self.rows(self.sample(),'ttm')
        self.assertIsNone(r['intakter']['varde'])
        c=self.sample();c['ttm']={'slut':'2026-06-30','varden':{'intakter':150,'kfo':40,'capex':10,'nettoresultat':20,'aktier_utspadda':10}}
        r=self.rows(c,'ttm')
        self.assertEqual(r['fritt_kassaflode']['varde'],30)
        self.assertIsNone(r['eps']['varde'])
    def test_bank_suppression(self):
        import case
        c=self.sample();c['bransch']=next(iter(case.BANKBRANSCHER))
        self.assertIsNone(self.rows(c)['nettoskuld_ebitda']['varde'])
        self.assertIsNotNone(self.rows(c)['pe']['varde'])
    def test_ttm_quarter_gap_rejected(self):
        hist=[fu.Bokslut(x,varden={'intakter':10}) for x in ['2024-03-31','2024-06-30','2024-12-31','2025-03-31']]
        with patch.object(fu,'bokslut_yahoo',return_value=hist):self.assertIsNone(fu.ttm('X'))
        hist=[fu.Bokslut(x,varden={'intakter':10}) for x in ['2024-03-31','2024-06-30','2024-09-30','2024-12-31']]
        with patch.object(fu,'bokslut_yahoo',return_value=hist):self.assertEqual(fu.ttm('X')['varden']['intakter'],40)

if __name__=='__main__':unittest.main()
