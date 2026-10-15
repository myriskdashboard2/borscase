"""Bolagsinformation, beständig journal och försiktig modellutvärdering.
Allt lagras lokalt. Oföränderliga observationer och separata användaranteckningar.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
import numpy as np

DB = Path(__file__).with_name('analysjournal.sqlite3')
VERSION = '2.0'
FEATURES = ['roic', 'rorelsemarginal', 'fcf_yield', 'nettoskuld_ebitda', 'soliditet', 'momentum_12_1']
METRICS = {'intakter': 'Intäkter', 'rorelseresultat': 'Rörelseresultat',
           'fritt_kassaflode': 'Fritt kassaflöde', 'total_skuld': 'Total skuld', 'kassa': 'Kassa'}


def now():
    return datetime.now(timezone.utc).isoformat()


def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


@contextmanager
def connect():
    db = sqlite3.connect(DB, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS snapshots (
      id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, observed TEXT NOT NULL,
      scan_time TEXT NOT NULL, version TEXT NOT NULL, payload TEXT NOT NULL,
      UNIQUE(symbol, scan_time));
    CREATE TABLE IF NOT EXISTS notes (
      id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, kind TEXT NOT NULL,
      created TEXT NOT NULL, payload TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS outcomes (
      snapshot_id INTEGER NOT NULL, horizon INTEGER NOT NULL, measured TEXT NOT NULL,
      payload TEXT NOT NULL, PRIMARY KEY(snapshot_id,horizon));
    CREATE TABLE IF NOT EXISTS models (
      id INTEGER PRIMARY KEY, created TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS snapshots_symbol ON snapshots(symbol,id);
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()


def promises(text, source):
    """Extract exact source sentences as candidates, never silently certify a promise."""
    pattern = re.compile(r'\b(expect|expects|guidance|outlook|target|targets|aim|forecast|förväntar|prognos|målsättning|räknar med|bedömer att)\b', re.I)
    result = []
    for match in re.finditer(r'[^.!?\n]{30,1200}[.!?]?', text or ''):
        sentence = match.group().strip()
        if pattern.search(sentence):
            result.append({'text': sentence, 'start': match.start(), 'slut': match.end(),
                           'kalla': source, 'typ': 'Rapporterat uttalande – kandidat',
                           'status': 'Behöver tolkas och kopplas till mätbart mål'})
        if len(result) == 15:
            break
    return result


def quality(c, scan_time):
    r = c.get('rapport') or {}
    m = c.get('matt') or {}
    hist = c.get('historik') or []
    last = hist[-1] if hist else {}
    issues = []
    if not r.get('tillganglig'):
        issues.append('Rapporttext saknas')
    if not (r.get('foregaende') or {}).get('datum'):
        issues.append('Jämförelserapport saknas')
    if (c.get('kalender') or {}).get('fel'):
        issues.append('Rapportkalender kunde inte hämtas')
    stamp = (r.get('senaste') or {}).get('datum')
    if stamp:
        try:
            if (date.today() - date.fromisoformat(stamp[:10])).days > 400:
                issues.append('Rapporten är äldre än 400 dagar')
        except ValueError:
            issues.append('Ogiltigt rapportdatum')
    if not hist:
        issues.append('Bokslutshistorik saknas i denna skanning; kör en ny skanning')
    conflicts = c.get('datakonflikter') or []
    issues.extend(conflicts)
    return {'status': 'Kontroll behövs' if issues else 'Underlag tillgängligt – ingen garanti för riktighet',
            'problem': issues, 'skanning': scan_time, 'rapportdatum': stamp,
            'kursdatum': c.get('kursdatum'), 'bokslut': last.get('slut'),
            'tackning': c.get('tackning'), 'saknade_matt': [f for f in FEATURES if not number(m.get(f))],
            'kallor': c.get('datakallor') or [], 'rapport': r.get('senaste')}


def changes(c):
    hist = c.get('historik') or []
    if len(hist) < 2:
        return []
    previous, current = hist[-2:]
    result = []
    for key, label in METRICS.items():
        a, b = previous.get(key), current.get(key)
        if number(a) and number(b):
            result.append({'matt': key, 'namn': label, 'fore': a, 'nu': b, 'skillnad': b-a,
                           'procent': (b-a)/abs(a) if a else None,
                           'period_fore': previous['slut'], 'period_nu': current['slut'],
                           'typ': 'Beräknat från rapporterade värden',
                           'kalla_fore': (previous.get('kallor') or {}).get(key),
                           'kalla_nu': (current.get('kallor') or {}).get(key)})
    for row in (previous, current):
        revenue, operating = row.get('intakter'), row.get('rorelseresultat')
        row['_margin'] = operating/revenue if number(revenue) and revenue and number(operating) else None
    if all(number(x.get('_margin')) for x in (previous, current)):
        result.append({'matt': 'rorelsemarginal', 'namn': 'Rörelsemarginal',
                       'fore': previous['_margin'], 'nu': current['_margin'],
                       'skillnad': current['_margin']-previous['_margin'], 'procent': None,
                       'period_fore': previous['slut'], 'period_nu': current['slut'],
                       'typ': 'Beräknat; skillnad i andel (0,01 = 1 procentenhet)'})
    return result


def snapshot(scan):
    """One immutable observation per symbol and source scan; no historical backfill labels."""
    predictions = {c['symbol']: predict(c) for c in scan.get('case', [])}
    with connect() as db:
        for c in scan.get('case', []):
            payload = dict(c)
            payload['datakvalitet'] = quality(c, scan.get('tid'))
            payload['forandringar'] = changes(c)
            payload['skuggprognos'] = predictions[c['symbol']]
            db.execute('INSERT OR IGNORE INTO snapshots(symbol,observed,scan_time,version,payload) VALUES(?,?,?,?,?)',
                       (c['symbol'], now(), scan['tid'], scan.get('analysversion', 'legacy'),
                        json.dumps(payload, ensure_ascii=False, allow_nan=False)))


def latest(symbol):
    with connect() as db:
        row = db.execute('SELECT * FROM snapshots WHERE symbol=? ORDER BY id DESC LIMIT 1', (symbol,)).fetchone()
    if not row:
        raise ValueError('Bolaget saknar sparad analys. Kör en skanning först.')
    return dict(row), json.loads(row['payload'])


def evaluate_note(note, c):
    p = dict(note)
    field = p.get('metric')
    history = c.get('historik') or []
    values = dict(c.get('matt') or {})
    if p.get('kind') == 'promise':
        matching = [h for h in history if h['slut'] == p.get('due')]
        if not matching:
            p['aktuellt_varde'] = None
            p['status'] = 'Väntar på bokslut för exakt målperiod'
            return p
        history = matching
        revenue = history[-1].get('intakter')
        operating = history[-1].get('rorelseresultat')
        values = {}
        if number(revenue) and revenue and number(operating):
            values['rorelsemarginal'] = operating / revenue
    if history:
        values.update({k: v for k, v in history[-1].items() if k in METRICS})
    value = values.get(field)
    p['aktuellt_varde'] = value
    if not number(value):
        p['status'] = 'Okänt – mått saknas'
    elif p.get('kind') == 'promise' and (not history or history[-1]['slut'] < p.get('due', '9999')):
        p['status'] = 'Väntar på bokslut som täcker målperioden'
    else:
        hit = value >= p['threshold'] if p['operator'] == '>=' else value <= p['threshold']
        p['status'] = ('Uppfyllt' if hit else 'Ej uppfyllt') if p.get('kind') == 'promise' else ('Villkor uppfyllt' if hit else 'BEVAKNING: villkor brutet')
    return p


def add_note(data):
    symbol = str(data.get('symbol', ''))
    _, c = latest(symbol)
    kind = data.get('kind')
    if kind not in ('thesis', 'promise'):
        raise ValueError('Välj tes eller ledningsmål')
    metric = data.get('metric')
    if metric not in FEATURES + list(METRICS):
        raise ValueError('Okänt mått')
    if kind == 'promise' and metric not in list(METRICS) + ['rorelsemarginal']:
        raise ValueError('Ledningsmål stöder bokslutsbelopp och rörelsemarginal; välj ett sådant mått')
    threshold = float(data.get('threshold'))
    if not number(threshold) or data.get('operator') not in ('>=', '<='):
        raise ValueError('Ogiltigt gränsvärde')
    text = str(data.get('text', '')).strip()
    if not 5 <= len(text) <= 4000:
        raise ValueError('Skriv en tes eller ett citerat mål (5–4000 tecken)')
    due = str(data.get('due', ''))
    if kind == 'promise':
        date.fromisoformat(due)
        if not data.get('source'):
            raise ValueError('Ledningsmål måste ha en källa')
    payload = {k: data.get(k) for k in ('text', 'source', 'metric', 'operator', 'due')}
    payload.update(threshold=threshold, kind=kind, baseline=(c.get('matt') or {}).get(metric))
    with connect() as db:
        cur = db.execute('INSERT INTO notes(symbol,kind,created,payload) VALUES(?,?,?,?)',
                         (symbol, kind, now(), json.dumps(payload, ensure_ascii=False)))
        return cur.lastrowid


def detail(symbol):
    row, c = latest(symbol)
    with connect() as db:
        rows = db.execute('SELECT * FROM snapshots WHERE symbol=? ORDER BY id DESC LIMIT 30', (symbol,)).fetchall()
        notes = db.execute('SELECT * FROM notes WHERE symbol=? AND active=1 ORDER BY id DESC', (symbol,)).fetchall()
    c['journal'] = [{'id': r['id'], 'tid': r['observed'], 'skanning': r['scan_time'], 'version': r['version']} for r in rows]
    c['bevakningar'] = [{**evaluate_note(json.loads(n['payload']), c), 'id': n['id']} for n in notes]
    c['datakvalitet'] = quality(c, row['scan_time'])
    c['forandringar'] = changes(c)
    c['sedan_sist'] = []
    if len(rows)>1:
        previous=json.loads(rows[1]['payload'])
        for key in FEATURES:
            a=(previous.get('matt') or {}).get(key); b=(c.get('matt') or {}).get(key)
            if number(a) and number(b) and abs(a-b)>1e-10:
                c['sedan_sist'].append({'matt':key,'fore':a,'nu':b,'skillnad':b-a,'fore_tid':rows[1]['scan_time']})
    c['snapshot_id'] = row['id']
    return c


def scenario(data):
    """Five-year FCFF DCF. Inputs explicitly in report currency; no auto-filled FCFE."""
    required = ('revenue', 'margin', 'growth', 'conversion', 'discount', 'terminal', 'net_debt', 'shares', 'market_cap')
    try:
        v = {k: float(data[k]) for k in required}
    except (KeyError, ValueError, TypeError):
        raise ValueError('Fyll i alla scenarioantaganden med tal')
    if not all(number(x) for x in v.values()):
        raise ValueError('Alla tal måste vara ändliga')
    if not (v['revenue'] > 0 and v['shares'] > 0 and v['market_cap'] > 0 and
            -.5 <= v['growth'] <= 1 and 0 <= v['margin'] <= 1 and 0 <= v['conversion'] <= 1 and
            0 <= v['terminal'] < v['discount'] <= .5 and v['discount'] >= .01):
        raise ValueError('Kontrollera intervallen; kapitalkostnaden måste överstiga terminaltillväxten')
    def value(growth, margin, discount):
        cash = [v['revenue'] * (1+growth)**t * margin * v['conversion'] for t in range(1, 6)]
        pv = sum(cf/(1+discount)**t for t, cf in enumerate(cash, 1))
        terminal = cash[-1]*(1+v['terminal'])/(discount-v['terminal'])/(1+discount)**5
        equity = pv+terminal-v['net_debt']
        return {'eget_kapital': equity, 'per_aktie': equity/v['shares'],
                'skillnad_mot_borsvarde': equity/v['market_cap']-1,
                'terminalandel': terminal/(pv+terminal) if pv+terminal else None}
    result = []
    for name, dg, dm in [('Pessimistiskt', -.03, -.02), ('Grundscenario', 0, 0), ('Optimistiskt', .03, .02)]:
        g, m = max(-.5, min(1, v['growth']+dg)), max(0, min(1, v['margin']+dm))
        result.append({'namn': name, 'tillvaxt': g, 'marginal': m, **value(g,m,v['discount'])})
    sensitivity = []
    for dr in (-.01, 0, .01):
        discount = v['discount']+dr
        if discount <= v['terminal']:
            continue
        for dm in (-.02, 0, .02):
            margin = max(0, min(1, v['margin']+dm))
            sensitivity.append({'kapitalkostnad': discount, 'marginal': margin, **value(v['growth'],margin,discount)})
    # Solve the growth assumption that matches market cap; report unbracketed honestly.
    low, high = -.5, 1.
    implied = None
    if value(low,v['margin'],v['discount'])['eget_kapital'] <= v['market_cap'] <= value(high,v['margin'],v['discount'])['eget_kapital']:
        for _ in range(70):
            mid = (low+high)/2
            if value(mid,v['margin'],v['discount'])['eget_kapital'] < v['market_cap']:
                low = mid
            else:
                high = mid
        implied = (low+high)/2
    return {'scenarier': result, 'kanslighet': sensitivity, 'implicit_tillvaxt': implied,
            'antaganden': v, 'typ': 'Scenario – ingen prognos',
            'metod': 'FCFF = omsättning × rörelsemarginal × kassakonvertering efter skatt och återinvestering. Fem år och terminalvärde. Samtliga belopp i samma rapportvaluta. Ej anpassad för banker.'}


def price_on(series, day, after=False):
    rows = sorted((str(k)[:10], float(v)) for k,v in series.items() if number(v) and v>0)
    candidates = [(d,p) for d,p in rows if (d >= day if after else d <= day)]
    if not candidates:
        return None
    result = candidates[0] if after else candidates[-1]
    if abs((date.fromisoformat(result[0])-date.fromisoformat(day)).days) > 7:
        return None
    return result


def evaluate(fetch=None):
    """Adjusted prices fetched together avoid mixing adjustment bases across snapshots."""
    if fetch is None:
        import datakallor as dk
        fetch = lambda sym: dk.yahoo_kurser(sym, period='max').to_dict()
    with connect() as db:
        rows = db.execute('SELECT * FROM snapshots WHERE version=? ORDER BY observed', (VERSION,)).fetchall()
    prices, errors, count = {}, [], 0
    today = date.today().isoformat()
    for row in rows:
        c = json.loads(row['payload'])
        start = row['observed'][:10]
        # Avoid excessive correlated samples: journal keeps all; learning is monthly below.
        for horizon in (30,90,365):
            due = (date.fromisoformat(start)+timedelta(days=horizon)).isoformat()
            if due >= today:
                continue
            with connect() as db:
                if db.execute('SELECT 1 FROM outcomes WHERE snapshot_id=? AND horizon=?',(row['id'],horizon)).fetchone():
                    continue
            benchmark = 'XACT-OMXS30.ST' if row['symbol'].endswith('.ST') else 'SPY'
            try:
                for sym in (row['symbol'], benchmark):
                    if sym not in prices:
                        prices[sym] = fetch(sym)
                entry_day = (date.fromisoformat(start)+timedelta(days=1)).isoformat()
                a,b = price_on(prices[row['symbol']],entry_day,True),price_on(prices[row['symbol']],due,True)
                if not a or not b or b[0] >= today:
                    continue
                x,y = price_on(prices[benchmark],a[0]),price_on(prices[benchmark],b[0])
                if not x or not y or x[0]!=a[0] or y[0]!=b[0]:
                    continue
                raw, base = b[1]/a[1]-1,y[1]/x[1]-1
                # Recorded estimate, not broker-specific realised costs.
                cost = .005
                outcome = {'avkastning': raw, 'benchmark': benchmark,'benchmark_avkastning':base,
                           'kostnad':cost,'overavkastning_netto':raw-base-cost,
                           'startdatum':a[0],'slutdatum':b[0],
                           'metod':'Nästa handelsdags stängning, justerade kurser, 0,5 % schablonkostnad; lokal valuta'}
                with connect() as db:
                    db.execute('INSERT OR IGNORE INTO outcomes VALUES(?,?,?,?)',(row['id'],horizon,now(),json.dumps(outcome)))
                count += 1
            except Exception as exc:
                errors.append(f'{row["symbol"]}: {exc}')
    return {'nya_utfall':count, 'fel': errors[:15], 'modell': train()}


def training_rows():
    with connect() as db:
        rows = db.execute('SELECT s.*,o.payload outcome FROM snapshots s JOIN outcomes o ON s.id=o.snapshot_id WHERE o.horizon=90 AND s.version=? ORDER BY s.observed,s.id',(VERSION,)).fetchall()
    unique, result = set(), []
    for row in rows:
        key = (row['symbol'],row['observed'][:7])
        c, o = json.loads(row['payload']),json.loads(row['outcome'])
        if key in unique:
            continue
        features = [(c.get('matt') or {}).get(f) for f in FEATURES]
        if not all(number(x) for x in features):
            continue
        unique.add(key)
        result.append({'date':row['observed'][:10], 'month':row['observed'][:7], 'end':o['slutdatum'],
                       'x':features,'y':o['overavkastning_netto'],'symbol':row['symbol'],
                       'prediction':c.get('skuggprognos')})
    return result


def fit(rows):
    x=np.array([r['x'] for r in rows]); y=np.array([r['y'] for r in rows])
    mean=x.mean(axis=0);std=x.std(axis=0);std[std<1e-9]=1
    z=np.column_stack([np.ones(len(x)),np.clip((x-mean)/std,-5,5)])
    penalty=np.eye(z.shape[1])*10;penalty[0,0]=0
    weights=np.linalg.solve(z.T@z+penalty,z.T@y)
    return {'mean':mean.tolist(),'std':std.tolist(),'weights':weights.tolist(),'features':FEATURES}


def apply_model(model, features):
    z=np.clip((np.array(features)-model['mean'])/model['std'],-5,5)
    return float(np.r_[1,z] @ model['weights'])


def train():
    rows=training_rows(); months=sorted(set(r['month'] for r in rows))
    if len(rows)<120 or len(months)<12:
        return {'status':'Väntar på facit', 'observationer':len(rows),'manader':len(months),
                'krav':'Minst 120 kompletta observationer, 12 startmånader och 90 dagars utfall. Inga syntetiska träningsdata.'}
    folds=[]
    for month in months[6:]:
        test=[r for r in rows if r['month']==month]
        start=min(r['date'] for r in test)
        train_rows=[r for r in rows if r['end']<start]
        if len(train_rows)<60:
            continue
        model=fit(train_rows)
        error=np.mean([(apply_model(model,r['x'])-r['y'])**2 for r in test])
        baseline=np.mean([r['y']**2 for r in test])
        folds.append({'manad':month,'n':len(test),'mse':float(error),'baslinje_mse':float(baseline),
                      'senaste_traningsutfall':max(r['end'] for r in train_rows),'teststart':start})
    if len(folds)<3:
        return {'status':'För få separata testperioder','tester':folds}
    model=fit(rows)
    model.update(status='Skuggmodell – påverkar inte råd',tester=folds,observationer=len(rows),
                 manader=len(months),skapad=now(),metod='Ridge, fasta variabler och straff 10; rullande tidstest, utfall avslutade före teststart',
                 mse=float(np.mean([f['mse'] for f in folds])),baslinje_mse=float(np.mean([f['baslinje_mse'] for f in folds])))
    deltas=np.array([f['baslinje_mse']-f['mse'] for f in folds])
    rng=np.random.default_rng(20260908)
    boot=rng.choice(deltas,size=(1000,len(deltas)),replace=True).mean(axis=1)
    model['forbattring_intervall_95']=np.quantile(boot,[.025,.975]).tolist()
    model['battre_an_baslinje']=model['mse']<model['baslinje_mse']
    fingerprint=hashlib.sha256(json.dumps([(r['symbol'],r['date'],r['y']) for r in rows]).encode()).hexdigest()
    model['datahash']=fingerprint
    with connect() as db:
        previous=db.execute('SELECT payload FROM models ORDER BY id DESC LIMIT 1').fetchone()
        if previous and json.loads(previous['payload']).get('datahash')==fingerprint:
            return json.loads(previous['payload'])
        cur=db.execute('INSERT INTO models(created,payload) VALUES(?,?)',(now(),json.dumps(model)))
        model['id']=cur.lastrowid
    return model


def predict(c):
    features=[(c.get('matt') or {}).get(f) for f in FEATURES]
    if not all(number(x) for x in features):
        return None
    with connect() as db:
        row=db.execute('SELECT * FROM models ORDER BY id DESC LIMIT 1').fetchone()
    if not row:
        return None
    model=json.loads(row['payload'])
    return {'modell_id':row['id'],'netto_90d':apply_model(model,features),'status':'Experimentell skuggprognos'}


def overview():
    with connect() as db:
        count=db.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0]
        outcomes=db.execute('SELECT s.symbol,s.observed,o.horizon,o.payload FROM outcomes o JOIN snapshots s ON s.id=o.snapshot_id ORDER BY o.measured DESC LIMIT 100').fetchall()
        symbols=db.execute('SELECT symbol,MAX(id) id FROM snapshots GROUP BY symbol ORDER BY symbol').fetchall()
        model=db.execute('SELECT * FROM models ORDER BY id DESC LIMIT 1').fetchone()
        notes=db.execute('SELECT * FROM notes WHERE active=1').fetchall()
    alerts=[]
    for n in notes:
        _,c=latest(n['symbol'])
        item=evaluate_note(json.loads(n['payload']),c)
        alerts.append({'symbol':n['symbol'],**item})
    return {'antal_analyser':count,'bolag':[r['symbol'] for r in symbols],
            'utfall':[{'symbol':r['symbol'],'tid':r['observed'],'horisont':r['horizon'],**json.loads(r['payload'])} for r in outcomes],
            'modell': {'id':model['id'],**json.loads(model['payload'])} if model else {'status':'Väntar på facit; inga tränade modeller'},
            'bevakningar':alerts,
            'metod':'Journalen börjar när data observeras här. Äldre skanningar arkiveras men används inte som nya prognoser. Modeller lär av mätbara utfall, inte klick.'}
