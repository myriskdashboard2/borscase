"""Offline regression and integration tests. No production journal or network."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import intel
import fundamenta as fu
import datakallor as dk
import validering as va
import rad
import app

class DataTests(unittest.TestCase):
    def test_quarter_and_year_survive(self):
        facts={'facts':{'us-gaap':{'Revenues':{'units':{'USD':[
            {'start':'2023-10-01','end':'2023-12-31','val':25,'filed':'2024-02-01','form':'10-K'},
            {'start':'2023-01-01','end':'2023-12-31','val':100,'filed':'2024-02-01','form':'10-K'}]}}}}}
        result=dk.xbrl_serie(facts,['Revenues'])
        self.assertEqual(len(result),2)
        with patch.object(dk,'sec_cik',return_value='1'),patch.object(dk,'sec_companyfacts',return_value=facts):
            self.assertEqual(fu.bokslut_edgar('TEST')[0].v('intakter'),100)

    def test_pit_per_field_and_restatement(self):
        obs={'intakter':[{'varde':100,'filed':'2024-02-01','enhet':'USD'},
                          {'varde':120,'filed':'2025-02-01','enhet':'USD'}],
             'kfo':[{'varde':20,'filed':'2024-08-01','enhet':'USD'}],
             'capex':[{'varde':5,'filed':'2024-02-01','enhet':'USD'}]}
        b=fu.Bokslut('2023-12-31',observationer=obs)
        early=fu.bokslut_vid([b],'2024-06-30')[0]
        self.assertEqual(early.v('intakter'),100)
        self.assertIsNone(early.v('kfo'))
        self.assertIsNone(early.v('fritt_kassaflode'))
        self.assertEqual(fu.bokslut_vid([b],'2025-06-30')[0].v('intakter'),120)
        self.assertEqual(fu.bokslut_vid([b],'2023-06-30'),[])

    def test_split_reconstruction(self):
        h=pd.DataFrame({'Close':[25.,26.,27.],'Stock Splits':[0.,4.,0.]})
        self.assertEqual(dk.aterstall_splittar(h).tolist(),[100.,26.,27.])

    def test_currency_failure_not_one(self):
        with patch.object(dk,'cache_las',return_value=None),patch.object(dk,'yahoo_kurser',return_value=pd.Series(dtype=float)):
            with self.assertRaises(ValueError):
                dk.valutakurs('USD','SEK')

    def test_spearman_ties(self):
        self.assertIsNone(va._spearman([1]*6,list(range(6))))
        self.assertAlmostEqual(va._spearman([1,1,2,3,4],[1,1,2,3,4]),1)

    def test_detail_preserves_bank_metrics(self):
        import skanning as sk
        import case as C
        bank=next(iter(C.BANKBRANSCHER))
        raw={'matt':{'ki_tal':.5},'historik':[],'kurshistorik':{},'marknad':{},'rapport':None}
        peers={'case':[{'symbol':'B'+str(i),'bransch':bank,'matt':{'ki_tal':.2+i*.05}} for i in range(20)]}
        with patch.object(sk,'las_installningar',return_value={}),patch.object(sk.un,'bygg_universum',return_value={'B0':{'bransch':bank}}),patch.object(sk,'samla_bolag',return_value=raw),patch.object(sk,'las_sparat',return_value=peers),patch.object(C,'bygg_case',return_value={}):
            result=sk.detaljer('B0')
        self.assertIsNotNone(result['percentiler']['ki_tal'])
        self.assertEqual(result['percentiler']['_jamfordes_mot'],'bank')

    def test_missing_report_is_unknown(self):
        c={'symbol':'X','tackning':1,'matt':{},'kalender':{},'rapport':None}
        self.assertEqual(rad.rekommendation(c)['niva'],'for_lite_data')

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=intel.DB;intel.DB=Path(self.tmp.name)/'test.sqlite3'
        self.c={'symbol':'TEST','namn':'Test','matt':{f:.1 for f in intel.FEATURES},'kalender':{},
                'historik':[{'slut':'2024-12-31','intakter':100,'rorelseresultat':10},
                            {'slut':'2025-12-31','intakter':120,'rorelseresultat':18}]}
        intel.snapshot({'tid':'2026-09-08T10:00:00+00:00','analysversion':'2.0','case':[self.c]})
    def tearDown(self):
        intel.DB=self.old
        self.tmp.cleanup()
    def test_immutable_and_idempotent(self):
        self.c['namn']='Changed'
        intel.snapshot({'tid':'2026-09-08T10:00:00+00:00','case':[self.c]})
        self.assertEqual(intel.overview()['antal_analyser'],1)
        self.assertEqual(intel.latest('TEST')[1]['namn'],'Test')
    def test_legacy_never_trained(self):
        self.assertEqual(intel.training_rows(),[])
        self.assertIn('Väntar',intel.train()['status'])
    def test_changes(self):
        changes=intel.changes(self.c)
        self.assertEqual(changes[0]['skillnad'],20)
        self.assertAlmostEqual(changes[-1]['skillnad'],.05)
    def test_note_persistence_and_outcome(self):
        id=intel.add_note({'symbol':'TEST','kind':'promise','metric':'intakter','operator':'>=',
                           'threshold':110,'text':'Revenue target','source':'Annual report','due':'2025-12-31'})
        result=intel.detail('TEST')['bevakningar'][0]
        self.assertEqual(result['id'],id)
        self.assertEqual(result['status'],'Uppfyllt')
        self.assertEqual(result['aktuellt_varde'],120)
    def test_promise_not_evaluated_on_wrong_period(self):
        n={'kind':'promise','metric':'intakter','threshold':110,'operator':'>=','due':'2024-06-30'}
        self.assertIn('Väntar',intel.evaluate_note(n,self.c)['status'])
    def test_scenario_math_and_invalid_inputs(self):
        d=dict(revenue=100,margin=.1,growth=0,conversion=1,discount=.1,terminal=0,net_debt=0,shares=10,market_cap=100)
        result=intel.scenario(d)
        self.assertAlmostEqual(result['scenarier'][1]['eget_kapital'],100)
        self.assertAlmostEqual(result['implicit_tillvaxt'],0)
        d['terminal']=.1
        with self.assertRaises(ValueError):intel.scenario(d)
    def test_prices_no_stale_or_future_endpoint(self):
        s={'2026-01-02':100.,'2026-01-05':110.}
        self.assertEqual(intel.price_on(s,'2026-01-03',True),('2026-01-05',110.))
        self.assertIsNone(intel.price_on(s,'2026-02-01'))
    def test_http_validation_and_pages(self):
        client=app.app.test_client()
        for url in ['/analys','/analys.js','/api/intel','/api/intel/TEST']:
            with client.get(url) as response:
                self.assertEqual(response.status_code,200)
        self.assertEqual(client.post('/api/intel/scenario',json={}).status_code,400)
        self.assertEqual(client.post('/api/intel/scenario',json={},headers={'Origin':'https://attacker.invalid'}).status_code,403)
        self.assertEqual(client.get('/api/intel',headers={'Host':'attacker.invalid'}).status_code,403)
        sid=intel.latest('TEST')[0]['id']
        self.assertEqual(client.get('/api/intel/snapshot/'+str(sid)).json['data']['namn'],'Test')
        self.assertEqual(client.post('/api/intel/note',json={'symbol':'TEST','kind':'invalid'}).status_code,400)
    def test_exact_quote(self):
        text='We expect revenue to increase by ten percent next year. Ordinary statement.'
        p=intel.promises(text,{'url':'https://example.com'})[0]
        self.assertEqual(p['text'],text[p['start']:p['slut']].strip())

    def test_outcome_uses_next_day_and_benchmark_cost(self):
        with patch.object(intel,'now',return_value='2024-01-01T23:00:00+00:00'):
            intel.snapshot({'tid':'2024-01-01T23:00:00+00:00','analysversion':'2.0','case':[self.c]})
        prices={'2024-01-01':50.,'2024-01-02':100.,'2024-01-31':110.,'2024-03-31':120.}
        benchmark={'2024-01-01':50.,'2024-01-02':100.,'2024-01-31':105.,'2024-03-31':110.}
        result=intel.evaluate(fetch=lambda sym: benchmark if sym=='SPY' else prices)
        self.assertEqual(result['nya_utfall'],2)
        with intel.connect() as db:
            import json
            outcome=json.loads(db.execute('SELECT payload FROM outcomes WHERE horizon=90').fetchone()[0])
        self.assertAlmostEqual(outcome['overavkastning_netto'],.095)
        self.assertEqual(outcome['startdatum'],'2024-01-02')
        self.assertEqual(intel.evaluate(fetch=lambda sym: prices)['nya_utfall'],0)

    def test_shadow_model_temporal_embargo(self):
        from datetime import date,timedelta
        rows=[]
        for month in range(24):
            start=date(2022+month//12,month%12+1,1)
            for i in range(12):
                rows.append({'date':str(start),'month':str(start)[:7],
                             'end':str(start+timedelta(days=90)),
                             'symbol':str(i),'x':[.01*(i+j) for j in range(6)],
                             'y':i*.002})
        with patch.object(intel,'training_rows',return_value=rows):
            model=intel.train()
        self.assertIn('Skuggmodell',model['status'])
        self.assertGreaterEqual(len(model['tester']),3)
        for fold in model['tester']:
            self.assertLess(fold['senaste_traningsutfall'],fold['teststart'])
        prediction=intel.predict(self.c)
        self.assertIsNotNone(prediction['modell_id'])
        self.assertTrue(intel.number(prediction['netto_90d']))

    def test_legacy_outcome_excluded(self):
        import json
        with intel.connect() as db:
            db.execute("UPDATE snapshots SET version='legacy'")
            sid=db.execute('SELECT id FROM snapshots').fetchone()[0]
            db.execute('INSERT INTO outcomes VALUES(?,?,?,?)',(sid,90,intel.now(),json.dumps({'slutdatum':'2026-12-08','overavkastning_netto':.1})))
        self.assertEqual(intel.training_rows(),[])

if __name__=='__main__':
    unittest.main()
