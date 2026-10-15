"""
matt.py — nyckeltalen, och varifrån de kommer.

Varje mått här är publicerat och testat av någon annan än mig. Det är hela
poängen: jag hittar inte på egna formler som råkar se bra ut på just den här
datan. Referensen står i varje funktions docstring, och visas i appen.

Måtten grupperas i fem pelare:

  KVALITET      Tjänar bolaget riktiga pengar på riktigt kapital?
  VÄRDERING     Vad betalar du för de pengarna?
  FINANSIELL    Överlever bolaget en dålig treårsperiod?
  TILLVÄXT      Blir det större, och till vilket pris?
  VARNING       Ser bokföringen ut som hos bolag som senare fick problem?

Alla funktioner tål saknade siffror och returnerar None i stället för att smälla.
`None` betyder "vet ej" och ska aldrig tolkas som noll.
"""

from __future__ import annotations

import math

import numpy as np


# ------------------------------------------------------------- verktyg ----

def d(taljare, namnare):
    """Division som ger None i stället för att krascha eller ljuga."""
    try:
        if taljare is None or namnare in (None, 0):
            return None
        r = float(taljare) / float(namnare)
        return None if (math.isnan(r) or math.isinf(r)) else r
    except Exception:
        return None


def snitt(varden):
    v = [x for x in varden if x is not None]
    return sum(v) / len(v) if v else None


def lutning(varden):
    """Trend per år via minstakvadrat. Positiv = förbättring över tid."""
    v = [x for x in varden if x is not None]
    if len(v) < 3:
        return None
    x = np.arange(len(v), dtype=float)
    return float(np.polyfit(x, np.array(v, dtype=float), 1)[0])


def cagr(forst, sist, ar):
    if forst is None or sist is None or ar <= 0 or forst <= 0:
        return None
    if sist <= 0:
        return -1.0
    return (sist / forst) ** (1.0 / ar) - 1.0


def _v(b, f):
    return b.v(f) if b is not None else None


# ------------------------------------------------------------ KVALITET ----

def bruttolonsamhet(b):
    """
    Bruttovinst / totala tillgångar (Novy-Marx 2013, "The Other Side of Value").

    Novy-Marx visade att bruttovinst förutsäger avkastning bättre än nettovinst,
    just för att den ligger högst upp i resultaträkningen och därmed är minst
    påverkad av bokföringsval längre ner. Över ~0,33 är starkt.
    """
    return d(_v(b, "bruttovinst"), _v(b, "tillgangar"))


def roic(b, skattesats=0.22):
    """
    Avkastning på investerat kapital: NOPAT / (eget kapital + räntebärande skuld − kassa).

    Det ärligaste enskilda kvalitetsmåttet. Ett bolag som får ut 20 % på det
    kapital det binder kan återinvestera vinsten till 20 % — det är hela
    ränta-på-ränta-maskinen. Under ungefär 8 % förstör tillväxt värde i stället.
    """
    ebit = _v(b, "rorelseresultat")
    if ebit is None:
        return None
    ek = _v(b, "eget_kapital") or 0
    skuld = _v(b, "total_skuld") or 0
    kassa = _v(b, "kassa") or 0
    kapital = ek + skuld - kassa
    if kapital <= 0:
        return None
    return d(ebit * (1 - skattesats), kapital)


def roe(b):
    return d(_v(b, "nettoresultat"), _v(b, "eget_kapital"))


def roa(b):
    return d(_v(b, "nettoresultat"), _v(b, "tillgangar"))


def rorelsemarginal(b):
    return d(_v(b, "rorelseresultat"), _v(b, "intakter"))


def bruttomarginal(b):
    return d(_v(b, "bruttovinst"), _v(b, "intakter"))


def kassagenerering(b):
    """
    Kassaflöde från rörelsen / nettoresultat.

    Vinst är en åsikt, kassaflöde är ett faktum. Ligger kvoten uthålligt under 1
    finns vinsten på papperet men inte på kontot. Under 0,8 är en flagga.
    """
    return d(_v(b, "kfo"), _v(b, "nettoresultat"))


def fritt_kassaflode_marginal(b):
    return d(_v(b, "fritt_kassaflode"), _v(b, "intakter"))


def kapitalintensitet(b):
    return d(_v(b, "capex"), _v(b, "kfo"))


# ------------------------------------------------------------- VÄRDERING --

def foretagsvarde(b, borsvarde):
    """EV = börsvärde + räntebärande skuld − kassa. Priset på hela verksamheten."""
    if borsvarde is None:
        return None
    skuld = _v(b, "total_skuld") or 0
    kassa = _v(b, "kassa") or 0
    return borsvarde + skuld - kassa


def ebit_ev(b, borsvarde):
    """
    Rörelseresultat / EV — Greenblatts "earnings yield" (The Little Book That
    Still Beats the Market, 2005). Mer jämförbart mellan bolag än P/E eftersom
    det bortser från kapitalstruktur och skatt.
    """
    return d(_v(b, "rorelseresultat"), foretagsvarde(b, borsvarde))


def fcf_yield(b, borsvarde):
    """Fritt kassaflöde / EV. Vad du får i kontanter för priset."""
    return d(_v(b, "fritt_kassaflode"), foretagsvarde(b, borsvarde))


def pe(b, borsvarde):
    """
    P/E — men bara när det betyder något.

    Ett bolag som går med förlust får ett NEGATIVT P/E, och eftersom lägre P/E
    rankas som bättre skulle det förlustbolaget hamna överst bland de billigaste.
    Intel låg på P/E −1987 och Snowflake på −86. Ett negativt P/E är inte billigt,
    det är odefinierat. Samma sak för EV/EBITDA och P/B: är nämnaren negativ
    säger kvoten ingenting, och då ska måttet saknas i stället för att ljuga.
    """
    vinst = _v(b, "nettoresultat")
    if vinst is None or vinst <= 0:
        return None
    return d(borsvarde, vinst)


def ps(b, borsvarde):
    return d(borsvarde, _v(b, "intakter"))


def pb(b, borsvarde):
    ek = _v(b, "eget_kapital")
    if ek is None or ek <= 0:          # negativt eget kapital -> kvoten är nonsens
        return None
    return d(borsvarde, ek)


def ev_ebitda(b, borsvarde):
    ebitda = _v(b, "ebitda")
    if ebitda is None or ebitda <= 0:
        return None
    return d(foretagsvarde(b, borsvarde), ebitda)


def ev_sales(b, borsvarde):
    return d(foretagsvarde(b, borsvarde), _v(b, "intakter"))


def greenblatt_roc(b):
    """
    Greenblatts avkastning på kapital: EBIT / (rörelsekapital + materiella
    anläggningstillgångar). Mäter avkastning på det kapital verksamheten faktiskt
    kräver, utan goodwill från gamla förvärv.
    """
    oms = _v(b, "oms_tillgangar")
    kort = _v(b, "kort_skulder")
    ppe = _v(b, "materiella")
    if None in (oms, kort, ppe):
        return None
    kapital = (oms - kort) + ppe
    if kapital <= 0:
        return None
    return d(_v(b, "rorelseresultat"), kapital)


# ----------------------------------------------------- FINANSIELL STYRKA --

def nettoskuld_ebitda(b):
    ebitda = _v(b, "ebitda")
    if ebitda is None or ebitda <= 0:
        return None
    netto = (_v(b, "total_skuld") or 0) - (_v(b, "kassa") or 0)
    return netto / ebitda


def rantetackning(b):
    r = _v(b, "rantekostnad")
    if r is None or abs(r) < 1:
        return None
    return d(_v(b, "rorelseresultat"), abs(r))


def kassalikviditet(b):
    return d(_v(b, "oms_tillgangar"), _v(b, "kort_skulder"))


def soliditet(b):
    return d(_v(b, "eget_kapital"), _v(b, "tillgangar"))


def altman_z(b, borsvarde):
    """
    Altman Z''-score (1995, den variant som gäller även för icke-tillverkande
    bolag och används på tillväxtmarknader):

        Z'' = 6,56·A + 3,26·B + 6,72·C + 1,05·D

        A = rörelsekapital / tillgångar
        B = balanserat resultat / tillgångar
        C = EBIT / tillgångar
        D = eget kapital (bokfört) / totala skulder

    Över 2,6 = säker zon. Under 1,1 = nödzon. Måttet mäter konkursrisk, inte
    aktiepris — men bolag i nödzonen tenderar att göra nyemissioner till dig.
    Gäller INTE banker och fastighetsbolag; där returneras None.
    """
    till = _v(b, "tillgangar")
    if not till:
        return None
    oms, kort = _v(b, "oms_tillgangar"), _v(b, "kort_skulder")
    rorelsekapital = (oms - kort) if (oms is not None and kort is not None) else None
    A = d(rorelsekapital, till)
    B = d(_v(b, "balanserat_resultat"), till)
    C = d(_v(b, "rorelseresultat"), till)
    D = d(_v(b, "eget_kapital"), _v(b, "skulder"))
    delar = [A, B, C, D]
    if sum(x is not None for x in delar) < 3:
        return None
    A, B, C, D = [x if x is not None else 0.0 for x in delar]
    z = 6.56 * A + 3.26 * B + 6.72 * C + 1.05 * D
    return {"z": z, "A": A, "B": B, "C": C, "D": D,
            "zon": "säker" if z > 2.6 else ("grå" if z > 1.1 else "nöd")}


def ohlson_o(b, b_forra, borsvarde=None):
    """
    Ohlson O-score (1980) — logistisk konkurssannolikhet. Kompletterar Altman
    genom att väga in om bolaget går med förlust två år i rad och om det egna
    kapitalet är negativt. Returnerar sannolikhet 0-1.
    """
    till = _v(b, "tillgangar")
    if not till or till <= 0:
        return None
    skulder = _v(b, "skulder") or 0
    oms, kort = _v(b, "oms_tillgangar"), _v(b, "kort_skulder")
    ni, ni_f = _v(b, "nettoresultat"), _v(b_forra, "nettoresultat")
    kfo = _v(b, "kfo")
    TLTA = d(skulder, till) or 0
    WCTA = d((oms - kort) if (oms is not None and kort is not None) else None, till) or 0
    CLCA = d(kort, oms) or 0
    NITA = d(ni, till) or 0
    FUTL = d(kfo, skulder) or 0
    OENEG = 1.0 if skulder > till else 0.0
    INTWO = 1.0 if (ni is not None and ni_f is not None and ni < 0 and ni_f < 0) else 0.0
    CHIN = 0.0
    if ni is not None and ni_f is not None and (abs(ni) + abs(ni_f)) > 0:
        CHIN = (ni - ni_f) / (abs(ni) + abs(ni_f))
    o = (-1.32 - 0.407 * math.log(max(till, 1) / 1e6) + 6.03 * TLTA - 1.43 * WCTA
         + 0.0757 * CLCA - 1.72 * OENEG - 2.37 * NITA - 1.83 * FUTL
         + 0.285 * INTWO - 0.521 * CHIN)
    p = 1 / (1 + math.exp(-min(max(o, -30), 30)))
    return {"o": o, "sannolikhet": p}


def piotroski_f(b, b_forra):
    """
    Piotroski F-Score (2000, "Value Investing: The Use of Historical Financial
    Statement Information to Separate Winners from Losers"). Nio ja/nej-frågor
    om lönsamhet, finansiering och effektivitet. 8-9 = starkt, 0-2 = svagt.

    Piotroskis eget resultat: bland billiga bolag gav höga F-poäng klart bättre
    utfall än låga. Det är ett av få mått som replikerats brett.
    """
    if b is None or b_forra is None:
        return None
    p = []

    def fraga(text, villkor):
        ok = bool(villkor) if villkor is not None else False
        p.append({"fraga": text, "poang": 1 if ok else 0,
                  "kunde_bedomas": villkor is not None})

    ni, till = _v(b, "nettoresultat"), _v(b, "tillgangar")
    till_f = _v(b_forra, "tillgangar")
    kfo = _v(b, "kfo")
    roa_nu = d(ni, till)
    roa_fo = d(_v(b_forra, "nettoresultat"), till_f)

    fraga("Positivt resultat", None if ni is None else ni > 0)
    fraga("Positivt kassaflöde från rörelsen", None if kfo is None else kfo > 0)
    fraga("Stigande avkastning på tillgångar",
          None if (roa_nu is None or roa_fo is None) else roa_nu > roa_fo)
    fraga("Kassaflödet överstiger vinsten (ingen pappersvinst)",
          None if (kfo is None or ni is None or not till) else (kfo / till) > (ni / till))

    sk_nu = d(_v(b, "langfristig_skuld"), till)
    sk_fo = d(_v(b_forra, "langfristig_skuld"), till_f)
    fraga("Minskad långfristig skuldsättning",
          None if (sk_nu is None or sk_fo is None) else sk_nu <= sk_fo)

    lik_nu, lik_fo = kassalikviditet(b), kassalikviditet(b_forra)
    fraga("Förbättrad likviditet",
          None if (lik_nu is None or lik_fo is None) else lik_nu > lik_fo)

    ak_nu, ak_fo = _v(b, "aktier_utspadda"), _v(b_forra, "aktier_utspadda")
    fraga("Inga nya aktier (ingen utspädning)",
          None if (ak_nu is None or ak_fo is None) else ak_nu <= ak_fo * 1.01)

    bm_nu, bm_fo = bruttomarginal(b), bruttomarginal(b_forra)
    fraga("Stigande bruttomarginal",
          None if (bm_nu is None or bm_fo is None) else bm_nu > bm_fo)

    oms_nu = d(_v(b, "intakter"), till)
    oms_fo = d(_v(b_forra, "intakter"), till_f)
    fraga("Stigande kapitalomsättning",
          None if (oms_nu is None or oms_fo is None) else oms_nu > oms_fo)

    poang = sum(x["poang"] for x in p)
    bedomda = sum(1 for x in p if x["kunde_bedomas"])
    return {"poang": poang, "max": 9, "bedomda": bedomda, "delar": p}


# -------------------------------------------------------------- VARNING --

def accruals(b, b_forra):
    """
    Sloan (1996): periodiseringar = (nettoresultat − kassaflöde) / tillgångar.

    Bolag vars vinst till stor del består av bokföringsposter i stället för
    kontanter har systematiskt gett sämre avkastning året efter. Över +0,10 är
    en tydlig flagga; kraftigt negativt är bra.
    """
    ni, kfo = _v(b, "nettoresultat"), _v(b, "kfo")
    till, till_f = _v(b, "tillgangar"), _v(b_forra, "tillgangar")
    if None in (ni, kfo, till):
        return None
    snitt_till = (till + till_f) / 2 if till_f else till
    return d(ni - kfo, snitt_till)


def tillgangstillvaxt(b, b_forra):
    """
    Cooper, Gulen & Schill (2008): bolag som blåser upp balansräkningen snabbt
    har gett sämre avkastning de följande åren — förvärv och investeringar görs
    oftast som mest när optimismen är som störst. Över 30 %/år är en flagga.
    """
    # Kvoten plockas ut först. Saknas ÅRETS tillgångar ger d() None, och
    # "None - 1" sänkte hela bolagets post: täckning 0, ingen poäng och
    # ingenting som sa varför. Toyo Tire föll på precis det.
    kvot = d(_v(b, "tillgangar"), _v(b_forra, "tillgangar"))
    return None if kvot is None else kvot - 1


def nettoemission(b, b_forra):
    """
    Förändring i antal aktier (Daniel & Titman 2006, Pontiff & Woodgate 2008).
    Bolag som ger ut aktier underpresterar; bolag som återköper överpresterar.
    Positivt tal = utspädning = dåligt för dig som redan äger.
    """
    nu, fo = _v(b, "aktier_utspadda"), _v(b_forra, "aktier_utspadda")
    if not nu or not fo:
        nu, fo = _v(b, "aktier_ute"), _v(b_forra, "aktier_ute")
    if not nu or not fo:
        return None
    return nu / fo - 1


def beneish_m(b, b_forra):
    """
    Beneish M-Score (1999) — åtta index som tillsammans skiljer bolag som
    manipulerat sin redovisning från dem som inte gjort det. Modellen flaggade
    Enron ett år innan kollapsen.

        M > −1,78  =>  statistiskt likt ett manipulerande bolag

    Viktigt: det är inte en anklagelse. Snabbväxande bolag med förvärv triggar
    modellen ofta och helt oskyldigt. Det är en uppmaning att läsa noterna.
    """
    if b is None or b_forra is None:
        return None
    n = lambda f: _v(b, f)
    f = lambda x: _v(b_forra, x)

    intakt, intakt_f = n("intakter"), f("intakter")
    if not intakt or not intakt_f:
        return None
    till, till_f = n("tillgangar"), f("tillgangar")

    DSRI = d(d(n("kundfordringar"), intakt), d(f("kundfordringar"), intakt_f))
    bm_nu, bm_f = bruttomarginal(b), bruttomarginal(b_forra)
    GMI = d(bm_f, bm_nu)

    def kvalitet(bb):
        t = _v(bb, "tillgangar")
        if not t:
            return None
        oms = _v(bb, "oms_tillgangar") or 0
        ppe = _v(bb, "materiella") or 0
        return 1 - (oms + ppe) / t
    AQI = d(kvalitet(b), kvalitet(b_forra))
    SGI = d(intakt, intakt_f)

    def avskr_takt(bb):
        av = _v(bb, "avskrivningar")
        ppe = _v(bb, "materiella")
        return None if (av is None or not ppe) else av / (av + ppe)
    DEPI = d(avskr_takt(b_forra), avskr_takt(b))
    SGAI = d(d(n("sga"), intakt), d(f("sga"), intakt_f))
    LVGI = d(d(n("skulder"), till), d(f("skulder"), till_f))
    TATA = accruals(b, b_forra)

    delar = {"DSRI": DSRI, "GMI": GMI, "AQI": AQI, "SGI": SGI,
             "DEPI": DEPI, "SGAI": SGAI, "LVGI": LVGI, "TATA": TATA}
    if sum(v is not None for v in delar.values()) < 6:
        return None
    x = {k: (1.0 if v is None else v) for k, v in delar.items()}
    x["TATA"] = 0.0 if delar["TATA"] is None else delar["TATA"]
    m = (-4.84 + 0.920 * x["DSRI"] + 0.528 * x["GMI"] + 0.404 * x["AQI"]
         + 0.892 * x["SGI"] + 0.115 * x["DEPI"] - 0.172 * x["SGAI"]
         + 4.679 * x["TATA"] - 0.327 * x["LVGI"])
    return {"m": m, "flagga": m > -1.78, "delar": delar}


# ------------------------------------------------------------- TILLVÄXT --

def tillvaxt(historik, falt, ar=3):
    """CAGR för valfritt fält över N år, om det finns N+1 bokslut."""
    v = [b.v(falt) for b in historik]
    v = [x for x in v if x is not None]
    if len(v) < ar + 1:
        return None
    return cagr(v[-(ar + 1)], v[-1], ar)


def regel_40(b, historik):
    """
    Rule of 40 (Brad Feld, riskkapitalvärlden): tillväxt% + rörelsemarginal% ≥ 40
    är tumregeln för att ett mjukvarubolag växer sunt. Bara meningsfullt för
    bolag med hög bruttomarginal — appen visar det inte för verkstad.
    """
    g = tillvaxt(historik, "intakter", 1)
    m = rorelsemarginal(b)
    if g is None or m is None:
        return None
    return (g + m) * 100


def marginaltrend(historik, n=5):
    return lutning([rorelsemarginal(b) for b in historik[-n:]])


def marginalstabilitet(historik, n=5):
    v = [rorelsemarginal(b) for b in historik[-n:]]
    v = [x for x in v if x is not None]
    return float(np.std(v)) if len(v) >= 3 else None


# ------------------------------------------------------------- MOMENTUM --

def momentum(kurser, manader=12, hoppa=1):
    """
    Jegadeesh & Titman (1993): 12 månaders avkastning EXKLUSIVE den senaste
    månaden. Den senaste månaden hoppas över eftersom den kortsiktigt tenderar
    att vända — det är två olika effekter som annars tar ut varandra.
    """
    if kurser is None or len(kurser) < 260:
        return None
    slut = -21 * hoppa if hoppa else -1
    start = -21 * manader
    if abs(start) >= len(kurser):
        return None
    a, b = float(kurser.iloc[start]), float(kurser.iloc[slut])
    return None if a <= 0 else b / a - 1


def vandning_1m(kurser):
    if kurser is None or len(kurser) < 25:
        return None
    return float(kurser.iloc[-1]) / float(kurser.iloc[-21]) - 1


def volatilitet(kurser, dagar=252):
    if kurser is None or len(kurser) < 60:
        return None
    r = kurser.pct_change().dropna().iloc[-dagar:]
    return float(r.std() * math.sqrt(252)) if len(r) > 20 else None


def max_fall(kurser):
    if kurser is None or len(kurser) < 60:
        return None
    topp = kurser.cummax()
    return float((kurser / topp - 1).min())


def avstand_till_topp(kurser, dagar=252):
    if kurser is None or len(kurser) < 30:
        return None
    fonster = kurser.iloc[-dagar:]
    return float(kurser.iloc[-1] / fonster.max() - 1)


# ---------------------------------------------------- sammanställningen --



# ------------------------------------------------------------------ LÄGE ---
# "Är det bra läge NU?" är en annan fråga än "är det ett bra bolag?", och den
# har ett ärligare svar: var står kursen och värderingen mot bolagets EGEN
# historia? Det är inte en prognos — det är en positionsangivelse. Att en aktie
# står lågt mot sin egen historia betyder inte att den ska upp; det betyder att
# du betalar mindre än du hade gjort de flesta andra dagar de senaste åren.

def rsi(kurser, dagar=14):
    """
    Relativt styrkeindex. Över 70 brukar kallas överköpt, under 30 översåld.

    Måttet säger hur mycket av den senaste tidens rörelse som varit uppåt. Det
    är en beskrivning av vad som HÄNT, inget annat — RSI-baserade regler föll
    i den tidigare trendappen (se I:/Claudecode/boliden/SLUTSATSER.md).
    """
    if kurser is None or len(kurser) < dagar + 5:
        return None
    f = kurser.diff().dropna().iloc[-(dagar * 3):]
    upp = f.clip(lower=0).ewm(alpha=1 / dagar, adjust=False).mean()
    ner = (-f.clip(upper=0)).ewm(alpha=1 / dagar, adjust=False).mean()
    if float(ner.iloc[-1]) == 0:
        return 100.0
    rs = float(upp.iloc[-1]) / float(ner.iloc[-1])
    return 100 - 100 / (1 + rs)


def egen_varderingshistorik(historik, kurser, aktuellt_pe):
    """
    Var dagens P/E ligger i bolagets EGET historiska spann.

    För varje räkenskapsår räknas P/E som kursen vid periodens slut delat med
    årets vinst per aktie. Det ger en serie som säger vad marknaden brukat
    betala för just det här bolaget — vilket är en helt annan och betydligt
    mer relevant referens än vad den betalar för andra bolag.

    Returnerar percentilen (0 = billigast bolaget varit, 100 = dyrast) plus
    spannet, så att talet går att kontrollera.
    """
    if aktuellt_pe is None or kurser is None or len(kurser) < 200:
        return None
    serie = []
    for b in historik:
        vinst = b.v("nettoresultat")
        aktier = b.v("aktier_utspadda") or b.v("aktier_ute")
        if not vinst or not aktier or vinst <= 0:
            continue
        fore = kurser[kurser.index <= b.slut]
        if not len(fore):
            continue
        pe = float(fore.iloc[-1]) / (vinst / aktier)
        if 0 < pe < 200:
            serie.append({"ar": b.slut[:4], "pe": pe})
    if len(serie) < 4:
        return None
    varden = sorted(x["pe"] for x in serie)
    lagre = sum(1 for v in varden if v < aktuellt_pe)
    return {
        "percentil": lagre / len(varden) * 100,
        "lagsta": varden[0], "hogsta": varden[-1],
        "median": varden[len(varden) // 2],
        "antal_ar": len(varden), "nu": aktuellt_pe,
        "serie": serie[-10:],
    }


# ------------------------------------------------------------------ BANK ---
# En bank har ingen bruttovinst, inget rörelsekapital och ingen nettoskuld —
# därför stängs de vanliga måtten av. Men det betyder inte att en bank inte går
# att bedöma. Den bedöms bara på andra tal, och de här är de fyra som varje
# bankanalytiker börjar med.

def ki_tal(b):
    """
    Kostnad/intäkt-relationen, "K/I-talet".

    Rörelsekostnader delat med totala intäkter. Det enskilt mest använda måttet
    på hur effektivt en bank drivs. En svensk storbank ligger typiskt på
    0,40-0,50; Handelsbanken byggde hela sitt rykte på att ligga lägst i
    branschen. Lägre är bättre.
    """
    kostn = _v(b, "rorelsekostnader")
    if kostn is None:
        return None
    return d(abs(kostn), _v(b, "intakter"))


def rantenetto_marginal(b):
    """
    Räntenettot i förhållande till balansomslutningen.

    Räntenettot är skillnaden mellan vad banken får betalt för att låna ut och
    vad den betalar för att låna in — bankens grundaffär. Delat med tillgångarna
    blir det ett mått på hur mycket banken tjänar per utlånad krona. Stiger när
    räntorna stiger, faller när de faller.
    """
    return d(_v(b, "rantenetto"), _v(b, "tillgangar"))


def kapitalstyrka(b):
    """
    Eget kapital delat med tillgångar.

    För ett industribolag heter det soliditet och 40 % är bra. För en bank är
    5-8 % normalt — den lånar in för att låna ut, det ÄR affären. Talet ska
    därför bara jämföras mot andra banker, aldrig mot verkstad. Ju högre, desto
    mer tål banken av kreditförluster innan det egna kapitalet är borta.
    """
    return d(_v(b, "eget_kapital"), _v(b, "tillgangar"))


def intaktsdiversifiering(b):
    """
    Hur stor del av intäkterna som INTE är räntenetto.

    Provisioner, courtage och kapitalförvaltning svänger mindre med räntan än
    utlåningen gör. En bank med hög andel andra intäkter är mindre utsatt när
    räntan vänder.
    """
    netto, intakt = _v(b, "rantenetto"), _v(b, "intakter")
    if netto is None or not intakt:
        return None
    return max(0.0, min(1.0, 1 - netto / intakt))


# ---------------------------------------------------------------------------
# Mått som inte betyder vad de ser ut att betyda i vissa branscher.
#
# Det här är den enskilt viktigaste tabellen i filen. Utan den toppas varje
# lista av investmentbolag med "P/E 8" — deras redovisade vinst är i huvudsak
# orealiserade värdeförändringar på innehaven, alltså börsens rörelse bokförd
# som resultat. Ett P/E på det talet mäter ingenting. Samma sak med banker och
# soliditet: en bank MÅSTE ha låg soliditet, det är affärsmodellen, inte en
# svaghet. Och ett fastighetsbolags fria kassaflöde är negativt per konstruktion
# eftersom fastighetsköp bokförs som investering.
#
# Appen stänger av måtten i stället för att räkna fel på dem. Priset är att
# bolaget får lägre "täckning" — vilket är precis rätt signal: modellen kan
# helt enkelt mindre om det här bolaget.
# ---------------------------------------------------------------------------

RESULTATBASERADE = [
    "bruttolonsamhet", "roic", "roic_5ar", "roic_trend", "greenblatt_roc",
    "rorelsemarginal", "bruttomarginal", "marginaltrend", "marginalstabilitet",
]
EV_BASERADE = ["ev", "ebit_ev", "fcf_yield", "ev_ebitda", "ev_sales",
               "nettoskuld_ebitda", "rantetackning"]
KASSAFLODESBASERADE = ["kassagenerering", "fcf_marginal", "fcf_tillvaxt_3ar"]

AVSTANGDA = {
    "Bank": (RESULTATBASERADE + EV_BASERADE + KASSAFLODESBASERADE
             + ["soliditet", "kassalikviditet", "altman", "ohlson", "piotroski",
                "accruals", "beneish"]),
    "Investmentbolag": (RESULTATBASERADE + EV_BASERADE + KASSAFLODESBASERADE
                        + ["pe", "roe", "roa", "altman", "ohlson", "piotroski",
                           "accruals", "beneish", "tillvaxt_1ar", "tillvaxt_3ar",
                           "tillvaxt_5ar", "vinsttillvaxt_3ar", "tillgangstillvaxt"]),
    "Fastighet": (KASSAFLODESBASERADE
                  + ["bruttolonsamhet", "greenblatt_roc", "pe", "roe", "roa",
                     "vinsttillvaxt_3ar", "altman", "accruals", "beneish",
                     "marginaltrend", "marginalstabilitet", "rorelsemarginal",
                     "bruttomarginal"]),
}

VARFOR_AVSTANGT = {
    "Bank": "En bank har låg soliditet, ingen bruttovinst och inget rörelsekapital "
            "— det är affärsmodellen, inte en svaghet. Företagsvärde och nettoskuld "
            "saknar mening när skulder ÄR råvaran. Piotroski och Altman är dessutom "
            "framtagna för icke-finansiella bolag och exkluderade banker uttryckligen.",
    "Investmentbolag": "Ett investmentbolags redovisade vinst är till största delen "
                       "orealiserade värdeförändringar på innehaven — alltså börsens "
                       "rörelse bokförd som resultat. P/E, marginaler, tillväxt och "
                       "kassaflödesmått mäter därför ingenting här. Det som betyder "
                       "något är priset mot substansvärdet (P/B) och avgifterna.",
    "Fastighet": "Resultatet domineras av orealiserade värdeförändringar på "
                 "fastigheterna, och kassaflödet efter investeringar är negativt per "
                 "konstruktion eftersom fastighetsköp bokförs som investering. "
                 "Skuldsättning, räntetäckning och pris mot substans är det som säger "
                 "något.",
}


def avstangda_for(bransch: str) -> set:
    return set(AVSTANGDA.get(bransch, ()))


def alla_matt(historik, marknad, bransch) -> dict:
    """
    Räknar allt som går att räkna för ett bolag och returnerar en platt dict.
    Fält som inte är meningsfulla för branschen sätts till None med en not.
    """
    if not historik:
        return {}
    b = historik[-1]
    bf = historik[-2] if len(historik) >= 2 else None
    borsvarde = marknad.get("borsvarde")
    kurser = marknad.get("kurser")
    av = avstangda_for(bransch)
    banklikt = bool(av)

    m = {
        "ar": b.slut,
        "kalla": b.kalla,
        "publicerad": b.publicerad,
        "antal_ar": len(historik),

        # kvalitet
        "bruttolonsamhet": bruttolonsamhet(b),
        "roic": roic(b),
        "roe": roe(b),
        "roa": roa(b),
        "rorelsemarginal": rorelsemarginal(b),
        "bruttomarginal": bruttomarginal(b),
        "kassagenerering": kassagenerering(b),
        "fcf_marginal": fritt_kassaflode_marginal(b),
        "greenblatt_roc": greenblatt_roc(b),
        "roic_5ar": snitt([roic(x) for x in historik[-5:]]),
        "roic_trend": lutning([roic(x) for x in historik[-5:]]),

        # värdering
        "ev": foretagsvarde(b, borsvarde),
        "ebit_ev": ebit_ev(b, borsvarde),
        "fcf_yield": fcf_yield(b, borsvarde),
        "pe": pe(b, borsvarde),
        "ps": ps(b, borsvarde),
        "pb": pb(b, borsvarde),
        "ev_ebitda": ev_ebitda(b, borsvarde),
        "ev_sales": ev_sales(b, borsvarde),
        "direktavkastning": marknad.get("utdelning_procent"),

        # finansiell styrka
        "nettoskuld_ebitda": nettoskuld_ebitda(b),
        "rantetackning": rantetackning(b),
        "kassalikviditet": kassalikviditet(b),
        "soliditet": soliditet(b),
        "altman": altman_z(b, borsvarde),
        "ohlson": ohlson_o(b, bf),
        "piotroski": piotroski_f(b, bf),

        # tillväxt
        "tillvaxt_1ar": tillvaxt(historik, "intakter", 1),
        "tillvaxt_3ar": tillvaxt(historik, "intakter", 3),
        "tillvaxt_5ar": tillvaxt(historik, "intakter", 5),
        "vinsttillvaxt_3ar": tillvaxt(historik, "nettoresultat", 3),
        "fcf_tillvaxt_3ar": tillvaxt(historik, "fritt_kassaflode", 3),
        "marginaltrend": marginaltrend(historik),
        "marginalstabilitet": marginalstabilitet(historik),
        "regel_40": regel_40(b, historik) if (bruttomarginal(b) or 0) > 0.6 else None,

        # varningar
        "accruals": accruals(b, bf) if bf else None,
        "tillgangstillvaxt": tillgangstillvaxt(b, bf) if bf else None,
        "nettoemission": nettoemission(b, bf) if bf else None,
        "beneish": beneish_m(b, bf) if bf else None,

        # marknad
        "momentum_12_1": momentum(kurser),
        "vandning_1m": vandning_1m(kurser),
        "volatilitet": volatilitet(kurser),
        "max_fall_10ar": max_fall(kurser),
        "avstand_till_arstopp": avstand_till_topp(kurser),
        "beta": marknad.get("beta"),

        # bank — beräknas alltid, men är bara meningsfulla för banker och
        # rangordnas därför enbart mot andra banker (se case.rangordna)
        "ki_tal": ki_tal(b),
        "rantenetto_marginal": rantenetto_marginal(b),
        "kapitalstyrka": kapitalstyrka(b),
        "intaktsdiversifiering": intaktsdiversifiering(b),
        "ki_trend": lutning([ki_tal(x) for x in historik[-5:]]),

        # läge just nu
        "rsi": rsi(kurser),
        "egen_vardering": egen_varderingshistorik(historik, kurser, pe(b, borsvarde)),

        # storlek
        "borsvarde": borsvarde,
        "intakter": b.v("intakter"),
        "rapportvaluta": marknad.get("rapportvaluta"),
        "banklikt": banklikt,
    }

    # Stäng av det som inte betyder något i den här branschen. Måtten räknades
    # ovan för att koden ska vara enkel att läsa; de nollställs här, på ett
    # ställe, så att det aldrig kan glömmas bort på något enskilt mått.
    BANKMATT = {"ki_tal", "rantenetto_marginal", "kapitalstyrka",
                "intaktsdiversifiering", "ki_trend"}
    for falt in av:
        if falt in m and falt not in BANKMATT:
            m[falt] = None
    m["avstangda"] = sorted(av)
    m["avstangt_varfor"] = VARFOR_AVSTANGT.get(bransch)
    return m
