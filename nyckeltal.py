"""Pedagogiska nyckeltal från journalens underlag; inga nätanrop eller prognoser."""
import math
from datetime import date

def finite(v):
    return isinstance(v, (int,float)) and not isinstance(v,bool) and math.isfinite(v)

def ratio(a,b):
    return a/b if finite(a) and finite(b) and b>0 else None

# name, unit, explanation, formula, source fields
DEFS = {
'intakter':('Omsättning','money','Bolagets försäljning före kostnader.','Rapporterade intäkter',['intakter']),
'rorelseresultat':('Rörelseresultat (EBIT)','money','Resultat från verksamheten före finansnetto och skatt.','Rapporterat rörelseresultat',['rorelseresultat']),
'ebitda':('EBITDA','money','Resultat före ränta, skatt och avskrivningar. Är inte kassaflöde; justerad EBITDA kan skilja.','Leverantörens EBITDA eller EBIT + avskrivningar',['ebitda','rorelseresultat','avskrivningar']),
'nettoresultat':('Vinst efter skatt','money','Redovisad vinst är inte samma sak som pengar som kommit in.','Rapporterat nettoresultat',['nettoresultat']),
'kfo':('Kassaflöde från rörelsen','money','Pengar från den löpande verksamheten, inklusive förändringar i rörelsekapital.','Rapporterat operativt kassaflöde',['kfo']),
'capex':('Investeringar (Capex)','money','Utbetalningar för anläggningstillgångar. Visas som positivt utflöde; företagsförvärv ingår normalt inte.','Absolutvärdet av Capex',['capex']),
'fritt_kassaflode':('Fritt kassaflöde','money','Kvar efter investeringar enligt definitionen här. Bolag kan använda andra definitioner.','Kassaflöde från rörelsen − Capex',['kfo','capex']),
'fcf_marginal':('Kassaflödesmarginal','percent','Hur stor del av omsättningen som blir fritt kassaflöde.','Fritt kassaflöde / omsättning',['kfo','capex','intakter']),
'kassagenerering':('Kassaflöde i förhållande till vinst','times','Jämför kassaflöde från rörelsen med redovisad vinst. Lager och kundbetalningar kan påverka ett enskilt år.','Kassaflöde från rörelsen / positiv nettovinst',['kfo','nettoresultat']),
'bruttomarginal':('Bruttomarginal','percent','Andelen som återstår efter direkta kostnader, före övriga rörelsekostnader.','Bruttovinst / omsättning',['bruttovinst','intakter']),
'rorelsemarginal':('Rörelsemarginal','percent','Hur mycket rörelsevinst bolaget tjänar på varje försäljningskrona.','EBIT / omsättning',['rorelseresultat','intakter']),
'vinstmarginal':('Nettovinstmarginal','percent','Andelen av omsättningen som återstår efter samtliga kostnader och skatt.','Nettovinst / omsättning',['nettoresultat','intakter']),
'eps':('Vinst per aktie, beräknad','per_share','Nettovinst fördelad på periodens genomsnittliga utspädda aktier. Kan avvika från bolagets officiella EPS.','Nettovinst / genomsnittligt utspätt aktieantal',['nettoresultat','aktier_utspadda']),
'kassa':('Kassa och likvida placeringar','money','Likvida medel enligt datakällans definition. Kan även omfatta kortfristiga placeringar.','Rapporterad kassa',['kassa']),
'total_skuld':('Räntebärande skuld','money','Lån och andra räntebärande skulder. Leasing kan ingå beroende på källa.','Total skuld enligt källa',['total_skuld']),
'nettoskuld':('Nettoskuld','money','Räntebärande skuld minus kassa. Ett negativt värde betyder nettokassa.','Total skuld − kassa',['total_skuld','kassa']),
'nettoskuld_ebitda':('Nettoskuld / EBITDA','times','Skuld relativt resultat före avskrivningar. Jämför med liknande bolag; inte en faktisk återbetalningstid.','Nettoskuld / positiv EBITDA',['total_skuld','kassa','ebitda']),
'soliditet':('Soliditet','percent','Hur stor del av tillgångarna som finansieras av eget kapital. Banker har en annan kapitalstruktur.','Eget kapital / tillgångar',['eget_kapital','tillgangar']),
'pe':('P/E, historisk vinst','times','Hur mycket börsen betalar för den valda periodens vinst. Visas inte vid förlust; detta är inte ett prognos-P/E.','Börsvärde / positiv nettovinst',['nettoresultat']),
'pb':('P/B','times','Börsvärdet relativt bokfört eget kapital. Bokfört värde är inte samma sak som marknadsvärde eller substansvärde.','Börsvärde / positivt eget kapital',['eget_kapital']),
'ps':('P/S','times','Börsvärdet i förhållande till försäljningen. Säger inget ensamt om lönsamhet.','Börsvärde / omsättning',['intakter']),
'ev_ebit':('EV / EBIT','times','Förenklat företagsvärde i förhållande till rörelseresultatet.','(Börsvärde + nettoskuld) / positiv EBIT',['total_skuld','kassa','rorelseresultat']),
'ev_ebitda':('EV / EBITDA','times','Förenklat företagsvärde relativt EBITDA. Tar inte hänsyn till investeringsbehov.','(Börsvärde + nettoskuld) / positiv EBITDA',['total_skuld','kassa','ebitda']),
'fcf_borsvarde':('Fritt kassaflöde / börsvärde','percent','Fritt kassaflöde enligt definitionen här i förhållande till börsvärdet. Inte samma mått som FCF/EV i den äldre vyn.','Fritt kassaflöde / börsvärde',['kfo','capex']),
'utdelning':('Utbetald utdelning','money','Kontantutdelning under perioden. Är inte förslag till nästa utdelning.','Utbetald utdelning i kassaflödesrapporten',['utdelning']),
'utdelningsandel':('Utdelning / nettovinst','percent','Hur mycket kontantutdelningen motsvarar av vinsten. Tidpunkterna kan avse olika vinstår.','Utbetald utdelning / positiv nettovinst',['utdelning','nettoresultat']),
'utdelning_fcf':('Utdelning / fritt kassaflöde','percent','Om utdelningen ryms inom periodens positiva fria kassaflöde.','Utbetald utdelning / positivt fritt kassaflöde',['utdelning','kfo','capex']),
}
GROUPS = {'Kassaflöde':['kfo','capex','fritt_kassaflode','fcf_marginal','kassagenerering'],
          'Försäljning och lönsamhet':['intakter','rorelseresultat','ebitda','nettoresultat','bruttomarginal','rorelsemarginal','vinstmarginal','eps'],
          'Skuld och finansiell styrka':['kassa','total_skuld','nettoskuld','nettoskuld_ebitda','soliditet'],
          'Värdering och utdelning':['pe','pb','ps','ev_ebit','ev_ebitda','fcf_borsvarde','utdelning','utdelningsandel','utdelning_fcf']}
MARKET = {'pe','pb','ps','ev_ebit','ev_ebitda','fcf_borsvarde'}
BANK_UNSUITABLE = {'fcf_marginal','kassagenerering','ebitda','nettoskuld','nettoskuld_ebitda','ev_ebit','ev_ebitda','fcf_borsvarde','utdelning_fcf','bruttomarginal'}

def calculate(h, cap):
    v={k: h.get(k) if finite(h.get(k)) else None for k in DEFS}
    if finite(v['capex']):v['capex']=abs(v['capex'])
    if finite(v['kfo']) and finite(v['capex']):v['fritt_kassaflode']=v['kfo']-v['capex']
    else:v['fritt_kassaflode']=None
    if finite(v['total_skuld']) and finite(v['kassa']):v['nettoskuld']=v['total_skuld']-v['kassa']
    ev=cap+v['nettoskuld'] if finite(cap) and cap>0 and finite(v['nettoskuld']) else None
    if finite(v['utdelning']):v['utdelning']=abs(v['utdelning'])
    pairs={'fcf_marginal':(v['fritt_kassaflode'],v['intakter']), 'kassagenerering':(v['kfo'],v['nettoresultat']),
           'bruttomarginal':(h.get('bruttovinst'),v['intakter']), 'rorelsemarginal':(v['rorelseresultat'],v['intakter']),
           'vinstmarginal':(v['nettoresultat'],v['intakter']), 'eps':(v['nettoresultat'],h.get('aktier_utspadda')),
           'nettoskuld_ebitda':(v['nettoskuld'],v['ebitda']), 'soliditet':(h.get('eget_kapital'),h.get('tillgangar')),
           'pb':(cap,h.get('eget_kapital')), 'pe':(cap,v['nettoresultat']), 'ps':(cap,v['intakter']), 'ev_ebit':(ev,v['rorelseresultat']),
           'ev_ebitda':(ev,v['ebitda']), 'fcf_borsvarde':(v['fritt_kassaflode'],cap),
           'utdelningsandel':(v['utdelning'],v['nettoresultat']), 'utdelning_fcf':(v['utdelning'],v['fritt_kassaflode'])}
    v.update({k:ratio(*pair) for k,pair in pairs.items()})
    return v

def build(c, period='annual'):
    if period not in ('annual','ttm'):raise ValueError('Okänd period')
    import case as C
    bank=c.get('bransch') in C.BANKBRANSCHER
    history=sorted(c.get('historik') or [],key=lambda h:h['slut'])
    market=c.get('marknadsdata') or {}
    cap=market.get('borsvarde',c.get('borsvarde'))
    if not finite(cap) or cap<=0:cap=None
    currency=c.get('rapportvaluta') or market.get('rapportvaluta') or (history[-1].get('valuta') if history else None)
    h=history[-1] if history else {}
    previous=history[-2] if len(history)>1 else {}
    ttm=c.get('ttm') or (c.get('matt') or {}).get('ttm') or {}
    if period=='ttm':
        h={**(ttm.get('varden') or {}),'slut':ttm.get('slut'),'valuta':currency}
        previous={}
        # Last-quarter weighted shares cannot be used for annual EPS.
        h['aktier_utspadda']=None
    values=calculate(h,cap); old=calculate(previous,None)
    result=[]
    for group, keys in GROUPS.items():
        rows=[]
        for key in keys:
            title,unit,explain,formula,fields=DEFS[key]
            value=values[key]
            reason=None
            if bank and key in BANK_UNSUITABLE:value=None;reason='Ej lämpligt för bankanalys'
            if value is None and not reason:reason='Underlag saknas eller kvoten har ingen positiv nämnare'
            if key=='eps' and period=='ttm':reason='Periodvägt årsaktieantal saknas för TTM'
            prev=old.get(key) if previous and key not in MARKET and not (bank and key in BANK_UNSUITABLE) else None
            delta=value-prev if finite(value) and finite(prev) else None
            growth=delta/prev if delta is not None and prev>0 else None
            source=[]
            for f in fields:
                src=(h.get('kallor') or {}).get(f)
                source.append({'falt':f,**(src or {'kalla':'Yahoo, fyra kvartal' if period=='ttm' else h.get('kalla','Källa saknas'),
                    'url':'https://finance.yahoo.com/quote/'+c.get('symbol','')+'/financials/','slut':h.get('slut')})})
            rows.append({'id':key,'namn':title,'enhet':unit,'varde':value,'fore':prev,'skillnad':delta,'tillvaxt':growth,
                         'forklaring':explain,'formel':formula,'kallor':source,'saknas':reason,
                         'period':h.get('slut'),'kursdatum':c.get('kursdatum') if key in MARKET else None})
        result.append({'namn':group,'rader':rows})
    warnings=[]
    if finite(h.get('ebitda')) and finite(h.get('rorelseresultat')) and h['ebitda']<h['rorelseresultat']:
        warnings.append('EBITDA är lägre än EBIT i underlaget. Definitioner eller engångsposter kan skilja; kontrollera rapporten innan EBITDA-multiplarna används.')
    if c.get('bransch') in ('Fastighet','Investmentbolag'):warnings.append('P/E bygger på redovisad vinst, som kan påverkas av värdeförändringar. Komplettera med förvaltningsresultat respektive substansvärde från bolagets rapport; dessa hämtas inte automatiskt här.')
    if bank:warnings.append('Bank: kassaflöde och skulder fungerar annorlunda. Använd även bankmåtten i den ordinarie analysen.')
    if period=='ttm' and not ttm:warnings.append('Fyra sammanhängande kvartal saknas. Hämta en ny analys; inget helår används som dold ersättning.')
    if not currency:warnings.append('Rapportvaluta saknas – kontrollera källan innan belopp jämförs.')
    if h.get('slut'):
        try:
            if (date.today()-date.fromisoformat(h['slut'])).days>450:warnings.append('Bokslutsperioden är äldre än 450 dagar.')
        except ValueError:pass
    return {'grupper':result,'period':period,'slut':h.get('slut'),'fore_slut':previous.get('slut'),
            'valuta':currency,'varningar':warnings,'ttm_tillganglig':bool(ttm),
            'ej_tillgangligt':['Organisk tillväxt','Orderingång och orderbok','Analytikerkonsensus och rapportöverraskning','Prognos-P/E och justerad EBITA'],
            'notering':'Ovanstående mått kräver bolagsspecifika rapportuppgifter eller prognosdata och beräknas inte ur total omsättning eller historisk vinst.'}
