"""
fundamenta.py — gör två olika rapportvärldar till en enda tabell.

Ett bokslut från SEC:s XBRL och ett bokslut från Yahoo har inget gemensamt i
form, men samma innehåll. Här normaliseras båda till ett `Bokslut` med samma
fältnamn, i bolagets rapportvaluta, så att resten av appen slipper veta var
siffrorna kom ifrån.

Två saker är värda att förstå:

1. `publicerad` sätts bara för EDGAR-data. Det är datumet då siffran blev
   offentlig. Utan det datumet går det inte att göra en ärlig historisk test —
   man råkar då "veta" bokslutet innan det fanns, vilket får vilken strategi som
   helst att se lysande ut. Yahoo saknar datumet, därför används svenska bolag
   aldrig i den historiska valideringen.

2. Där EDGAR och Yahoo överlappar vinner EDGAR (det är primärkällan), men
   saknade fält fylls från Yahoo. Det är skillnaden mellan 5 och 15 års historik
   för amerikanska bolag.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

import datakallor as dk

# ---------------------------------------------------------------------------
# Fältkarta Yahoo. Första träffen i listan vinner.
# ---------------------------------------------------------------------------
YAHOO_RESULTAT = {
    "intakter": ["Total Revenue", "Operating Revenue"],
    "ksv": ["Cost Of Revenue", "Reconciled Cost Of Revenue"],
    "bruttovinst": ["Gross Profit"],
    "rorelseresultat": ["Operating Income", "Total Operating Income As Reported", "EBIT"],
    "ebitda": ["EBITDA", "Normalized EBITDA"],
    "nettoresultat": ["Net Income Common Stockholders", "Net Income",
                      "Net Income From Continuing Operation Net Minority Interest"],
    "resultat_fore_skatt": ["Pretax Income"],
    "fou": ["Research And Development"],
    "sga": ["Selling General And Administration"],
    "avskrivningar": ["Reconciled Depreciation"],
    "rantekostnad": ["Interest Expense", "Interest Expense Non Operating"],
    "skatt": ["Tax Provision"],
    "aktier_utspadda": ["Diluted Average Shares", "Basic Average Shares"],
    # Bankposter. En bank har ingen bruttovinst och inget rörelseresultat i
    # vanlig mening, men räntenettot och rörelsekostnaderna finns — och det är
    # de två talen all bankanalys faktiskt bygger på.
    "rorelsekostnader": ["Operating Expense", "Total Expenses"],
    "rantenetto": ["Net Interest Income"],
    "ranteintakter": ["Interest Income"],
}

YAHOO_BALANS = {
    "tillgangar": ["Total Assets"],
    "oms_tillgangar": ["Current Assets"],
    "kort_skulder": ["Current Liabilities"],
    "skulder": ["Total Liabilities Net Minority Interest"],
    "eget_kapital": ["Stockholders Equity", "Common Stock Equity",
                     "Total Equity Gross Minority Interest"],
    "kassa": ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"],
    "kundfordringar": ["Accounts Receivable", "Receivables"],
    "lager": ["Inventory"],
    "materiella": ["Net PPE"],
    "goodwill": ["Goodwill", "Goodwill And Other Intangible Assets"],
    "total_skuld": ["Total Debt"],
    "langfristig_skuld": ["Long Term Debt And Capital Lease Obligation", "Long Term Debt"],
    "balanserat_resultat": ["Retained Earnings"],
    "aktier_ute": ["Ordinary Shares Number", "Share Issued"],
}

YAHOO_KASSA = {
    "kfo": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    "capex": ["Capital Expenditure", "Purchase Of PPE"],
    "fritt_kassaflode": ["Free Cash Flow"],
    "aterkop": ["Repurchase Of Capital Stock", "Common Stock Payments"],
    "utdelning": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
    "nyemission": ["Issuance Of Capital Stock", "Common Stock Issuance"],
    "sbc": ["Stock Based Compensation"],
    "avskr_kassaflode": ["Depreciation And Amortization", "Depreciation Amortization Depletion"],
}

# ---------------------------------------------------------------------------
# Fältkarta XBRL (SEC). Bolag taggar samma sak olika — listorna är fallbacks.
# ---------------------------------------------------------------------------
XBRL_FLODE = {
    "intakter": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                 "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "ksv": ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold", "CostOfServices"],
    "bruttovinst": ["GrossProfit"],
    "rorelseresultat": ["OperatingIncomeLoss"],
    "nettoresultat": ["NetIncomeLoss", "ProfitLoss"],
    "resultat_fore_skatt": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
    "fou": ["ResearchAndDevelopmentExpense"],
    "sga": ["SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense"],
    "avskrivningar": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
                      "DepreciationAmortizationAndAccretionNet", "Depreciation"],
    "rantekostnad": ["InterestExpense", "InterestExpenseDebt"],
    "skatt": ["IncomeTaxExpenseBenefit"],
    "kfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "aterkop": ["PaymentsForRepurchaseOfCommonStock"],
    "utdelning": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "nyemission": ["ProceedsFromIssuanceOfCommonStock"],
    "sbc": ["ShareBasedCompensation"],
    "aktier_utspadda": ["WeightedAverageNumberOfDilutedSharesOutstanding",
                        "WeightedAverageNumberOfSharesOutstandingBasic"],
}

XBRL_LAGE = {   # punktvärden (balansräkning)
    "tillgangar": ["Assets"],
    "oms_tillgangar": ["AssetsCurrent"],
    "kort_skulder": ["LiabilitiesCurrent"],
    "skulder": ["Liabilities"],
    "eget_kapital": ["StockholdersEquity",
                     "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "kassa": ["CashCashEquivalentsAndShortTermInvestments",
              "CashAndCashEquivalentsAtCarryingValue"],
    "kundfordringar": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"],
    "lager": ["InventoryNet"],
    "materiella": ["PropertyPlantAndEquipmentNet"],
    "goodwill": ["Goodwill"],
    "langfristig_skuld": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "kortfristig_skuld": ["DebtCurrent", "LongTermDebtCurrent", "ShortTermBorrowings"],
    "balanserat_resultat": ["RetainedEarningsAccumulatedDeficit"],
    "aktier_ute": ["CommonStockSharesOutstanding", "CommonStockSharesIssued"],
}

FALT = [
    "intakter", "ksv", "bruttovinst", "rorelseresultat", "ebitda", "nettoresultat",
    "resultat_fore_skatt", "fou", "sga", "avskrivningar", "rantekostnad", "skatt",
    "aktier_utspadda", "tillgangar", "oms_tillgangar", "kort_skulder", "skulder",
    "eget_kapital", "kassa", "kundfordringar", "lager", "materiella", "goodwill",
    "total_skuld", "langfristig_skuld", "kortfristig_skuld", "balanserat_resultat",
    "aktier_ute", "kfo", "capex", "fritt_kassaflode", "aterkop", "utdelning",
    "nyemission", "sbc", "rorelsekostnader", "rantenetto", "ranteintakter",
]


@dataclass
class Bokslut:
    """Ett räkenskapsår, normaliserat. Alla belopp i rapportvalutan."""
    slut: str                       # periodslut, YYYY-MM-DD
    publicerad: str | None = None   # när siffran blev offentlig (bara EDGAR)
    kalla: str = "yahoo"
    valuta: str | None = None
    varden: dict = field(default_factory=dict)

    observationer: dict = field(default_factory=dict)
    datakonflikter: list = field(default_factory=list)

    def v(self, namn):
        x = self.varden.get(namn)
        return None if x is None else float(x)

    def som_dict(self):
        d = asdict(self)
        return d


# ------------------------------------------------------------------ hjälp --

def _forst(rad: dict, kandidater):
    for k in kandidater:
        if k in rad and rad[k] is not None:
            return float(rad[k])
    return None


def _harleds(v: dict):
    """Fyller i det som går att räkna ut ur det som redan finns."""
    if v.get("bruttovinst") is None and v.get("intakter") is not None and v.get("ksv") is not None:
        v["bruttovinst"] = v["intakter"] - abs(v["ksv"])
    if v.get("total_skuld") is None:
        lang, kort = v.get("langfristig_skuld"), v.get("kortfristig_skuld")
        if lang is not None or kort is not None:
            v["total_skuld"] = (lang or 0) + (kort or 0)
    if v.get("skulder") is None and v.get("tillgangar") is not None and v.get("eget_kapital") is not None:
        v["skulder"] = v["tillgangar"] - v["eget_kapital"]
    if v.get("ebitda") is None and v.get("rorelseresultat") is not None and v.get("avskrivningar"):
        v["ebitda"] = v["rorelseresultat"] + abs(v["avskrivningar"])
    if v.get("fritt_kassaflode") is None and v.get("kfo") is not None and v.get("capex") is not None:
        v["fritt_kassaflode"] = v["kfo"] - abs(v["capex"])
    # capex och återköp lagras som positiva utflöden — Yahoo och SEC har olika tecken
    for f in ("capex", "aterkop", "utdelning"):
        if v.get(f) is not None:
            v[f] = abs(v[f])
    return v


def _ar_av(datum: str) -> int:
    try:
        return int(str(datum)[:4])
    except Exception:
        return 0


# --------------------------------------------------------------- Yahoo ----

def bokslut_yahoo(symbol: str, kvartal: bool = False) -> list[Bokslut]:
    rad = dk.yahoo_bokslut(symbol)
    suffix = "_q" if kvartal else ""
    res = rad.get("resultat" + suffix, {})
    bal = rad.get("balans" + suffix, {})
    kas = rad.get("kassaflode" + suffix, {})
    datum = sorted(set(res) | set(bal) | set(kas))
    ut = []
    for d in datum:
        v = {}
        for namn, kand in YAHOO_RESULTAT.items():
            v[namn] = _forst(res.get(d, {}), kand)
        for namn, kand in YAHOO_BALANS.items():
            v[namn] = _forst(bal.get(d, {}), kand)
        for namn, kand in YAHOO_KASSA.items():
            x = _forst(kas.get(d, {}), kand)
            if namn == "avskr_kassaflode":
                if v.get("avskrivningar") is None:
                    v["avskrivningar"] = x
                continue
            v[namn] = x
        if not any(v.get(f) is not None for f in ("intakter", "tillgangar", "nettoresultat")):
            continue
        ut.append(Bokslut(slut=d, kalla="yahoo", varden=_harleds(v)))
    return sorted(ut, key=lambda b: b.slut)


# --------------------------------------------------------------- EDGAR ----

def bokslut_edgar(symbol: str, form: str | None = None) -> list[Bokslut]:
    """
    Årsbokslut ur SEC:s XBRL.

    `form` avgör vilken blankett som räknas. Amerikanska bolag lämnar 10-K,
    men utländska bolag noterade i USA (ASML, TSMC, Arm, STM …) lämnar 20-F och
    kanadensiska 40-F. Utan den fallbacken får varje ADR noll års historik och
    faller tillbaka på Yahoos fyra år.
    """
    cik = dk.sec_cik(symbol.replace("-", "-"))
    if not cik:
        # BRK-B m.fl. skrivs med punkt hos SEC
        cik = dk.sec_cik(symbol.replace("-", "."))
    if not cik:
        return []
    facts = dk.sec_companyfacts(cik)
    if not facts:
        return []

    if form is None:
        for kandidat in ("10-K", "20-F", "40-F"):
            if dk.xbrl_serie(facts, XBRL_LAGE["tillgangar"], "USD", kandidat) or \
               dk.xbrl_serie(facts, XBRL_FLODE["intakter"], "USD", kandidat):
                form = kandidat
                break
        if form is None:
            form = "10-K"

    per_ar: dict[str, dict] = {}
    publicerad: dict[str, str] = {}
    enheter: dict[str, int] = {}
    observationer = {}

    def stoppa_in(namn, obs, langd_krav=None):
        for o in obs:
            slut = o.get("slut")
            if not slut:
                continue
            if langd_krav == "ar" and not o.get("start"):
                continue
            if langd_krav == "ar" and o.get("start"):
                dagar = (_datum(slut) - _datum(o["start"])).days
                if dagar < 300 or dagar > 400:      # bara helår
                    continue
            o = {**o, "cik": cik}
            observationer.setdefault(slut, {}).setdefault(namn, []).append(dict(o))
            per_ar.setdefault(slut, {})
            if per_ar[slut].get(namn) is None:
                per_ar[slut][namn] = o.get("varde")
            if o.get("filed"):
                tidigare = publicerad.get(slut)
                if not tidigare or o["filed"] < tidigare:
                    publicerad[slut] = o["filed"]
            e = o.get("enhet")
            if e and e != "shares":
                enheter[e] = enheter.get(e, 0) + 1

    for namn, kand in XBRL_FLODE.items():
        stoppa_in(namn, dk.xbrl_serie(facts, kand, "USD", form, alla_versioner=True), langd_krav="ar")
    for namn, kand in XBRL_LAGE.items():
        enhet = "shares" if namn == "aktier_ute" else "USD"
        stoppa_in(namn, dk.xbrl_serie(facts, kand, enhet, form, alla_versioner=True))
    for namn in ("aktier_utspadda",):
        stoppa_in(namn, dk.xbrl_serie(facts, XBRL_FLODE[namn], "shares", form, alla_versioner=True),
                  langd_krav="ar")

    valuta = max(enheter, key=enheter.get) if enheter else "USD"
    ut = []
    for slut, v in per_ar.items():
        if v.get("intakter") is None and v.get("nettoresultat") is None:
            continue
        ut.append(Bokslut(slut=slut, publicerad=publicerad.get(slut), kalla="edgar",
                          valuta=valuta, varden=_harleds(dict(v)),
                          observationer=observationer.get(slut, {})))
    return bokslut_vid(sorted(ut, key=lambda b: b.slut), "9999-12-31")


def bokslut_vid(alla, datum):
    """Build each field from its latest available filing; derive only afterwards."""
    ut = []
    for b in alla:
        if not b.observationer:
            if b.publicerad and b.publicerad <= datum:
                ut.append(b)
            continue
        v, dates, units = {}, [], []
        for namn, obs in b.observationer.items():
            eligible = [o for o in obs if o.get("filed") and o["filed"] <= datum]
            if not eligible:
                continue
            o = max(eligible, key=lambda o: (o["filed"], o.get("start") or ""))
            v[namn] = o["varde"]
            dates.append(o["filed"])
            if o.get("enhet") != "shares":
                units.append(o.get("enhet"))
        if not v or len(set(units)) > 1:
            continue
        ut.append(Bokslut(b.slut, max(dates), b.kalla, units[0] if units else b.valuta,
                         _harleds(v), b.observationer))
    return sorted(ut, key=lambda b: b.slut)


def _datum(s):
    from datetime import date
    return date(int(s[:4]), int(s[5:7]), int(s[8:10]))


# --------------------------------------------------------------- ihop ----

def bokslut(symbol: str, meta: dict) -> list[Bokslut]:
    """Bästa möjliga årshistorik: EDGAR i botten, Yahoo som utfyllnad."""
    y = bokslut_yahoo(symbol)
    if not meta.get("edgar"):
        return y

    try:
        e = bokslut_edgar(symbol)
    except Exception:
        e = []
    if not e:
        return y

    # Valutakontrollen. ASML rapporterar i euro, TSMC i taiwandollar, men Yahoo
    # anger börsvärdet i dollar. Slår man ihop EDGAR-siffror i en valuta med
    # Yahoo-siffror i en annan blir varje nyckeltal fel med exakt växelkursen —
    # och felet syns inte, det ser bara ut som att bolaget är extremt billigt.
    # Vid krock används enbart Yahoo, som åtminstone är internt konsekvent.
    rapportvaluta = (dk.yahoo_info(symbol) or {}).get("financialCurrency")
    edgarvaluta = e[-1].valuta
    if rapportvaluta and edgarvaluta and rapportvaluta != edgarvaluta:
        for b in y:
            b.varden["_valutakrock"] = None
        return y

    y_per_ar = {_ar_av(b.slut): b for b in y}
    sammanslaget = []
    for b in e:
        yb = y_per_ar.get(_ar_av(b.slut))
        if yb and yb.slut == b.slut:
            for f in FALT:
                ev, yv = b.varden.get(f), yb.varden.get(f)
                if ev is not None and yv is not None and abs(ev-yv) > max(abs(ev), abs(yv), 1) * 0.05:
                    b.datakonflikter.append({"matt": f, "sec": ev, "yahoo": yv, "period": b.slut, "vald": "SEC"})
                if b.varden.get(f) is None and yb.varden.get(f) is not None:
                    b.varden[f] = yb.varden[f]
            b.varden = _harleds(b.varden)
        sammanslaget.append(b)
    # år som bara Yahoo har (t.ex. allra senaste innan 10-K hunnit tuggas)
    e_ar = {_ar_av(b.slut) for b in e}
    for ar, yb in y_per_ar.items():
        if ar not in e_ar:
            sammanslaget.append(yb)
    return sorted(sammanslaget, key=lambda b: b.slut)


def ttm(symbol: str) -> dict | None:
    """Rullande tolv månader ur kvartalsrapporterna — nuläget, inte fjolåret."""
    kv = bokslut_yahoo(symbol, kvartal=True)
    if len(kv) < 4:
        return None
    fyra = kv[-4:]
    # Reject missing/duplicate quarters before summing annual cash flows.
    gaps = [(_datum(b.slut)-_datum(a.slut)).days for a,b in zip(fyra, fyra[1:])]
    if not all(70 <= gap <= 110 for gap in gaps):
        return None
    flode = ["intakter", "ksv", "bruttovinst", "rorelseresultat", "ebitda", "nettoresultat",
             "resultat_fore_skatt", "fou", "sga", "avskrivningar", "rantekostnad", "skatt",
             "kfo", "capex", "fritt_kassaflode", "aterkop", "utdelning", "nyemission", "sbc"]
    v = {}
    for f in flode:
        delar = [b.v(f) for b in fyra]
        v[f] = sum(delar) if all(d is not None for d in delar) else None
    senaste = fyra[-1]
    for f in ("tillgangar", "oms_tillgangar", "kort_skulder", "skulder", "eget_kapital",
              "kassa", "kundfordringar", "lager", "materiella", "goodwill", "total_skuld",
              "langfristig_skuld", "balanserat_resultat", "aktier_ute", "aktier_utspadda"):
        v[f] = senaste.v(f)
    v = _harleds(v)
    return {"slut": senaste.slut, "varden": v, "kvartal": [b.slut for b in fyra]}


def _andel(x):
    """
    Yahoos `dividendYield` kommer i PROCENT, inte som andel: 5,4 betyder 5,4 %
    och 0,36 betyder 0,36 %. Kontrollerat mot sju bolag i båda marknaderna
    (Swedbank 5,40 · Handelsbanken 5,44 · Telia 4,82 · Boliden 2,04 ·
    Coca-Cola 2,44 · Exxon 2,58 · Apple 0,36).

    Ett första försök tolkade allt under 1 som redan färdig andel — då blev
    Apples 0,36 % till 36 %. Storleken på talet går alltså inte att använda för
    att gissa enheten; enheten är alltid procent.
    """
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if v < 0 else v / 100.0


def marknadsdata(symbol: str, meta: dict) -> dict:
    """
    Pris, börsvärde och EV — allt uttryckt i RAPPORTVALUTAN.

    Fällan här är bolag som handlas i en valuta men rapporterar i en annan
    (t.ex. Autoliv, Nordea, AstraZeneca). Räknar man P/E med pris i SEK och
    vinst i USD blir talet fel med en faktor tio. Därför konverteras börsvärdet
    till rapportvalutan innan något nyckeltal beräknas.
    """
    info = dk.yahoo_info(symbol)
    kurs_valuta = info.get("currency") or meta.get("valuta")
    rapport_valuta = info.get("financialCurrency") or kurs_valuta
    kurser = dk.yahoo_kurser(symbol, period="10y")

    # Johannesburg noterar i cent och London i pence, men Yahoos marketCap
    # står ändå i hela rand respektive pund — kontrollräknat: för ARL.JO är
    # marketCap exakt pris × antal aktier × 0,01. Räknas börsvärdet om med
    # samma faktor som kursen blir varje nyckeltal hundra gånger fel. Därför
    # normaliseras KURSEN till hela enheter, och börsvärdet lämnas i fred.
    if kurs_valuta in dk.UNDERENHET:
        hel, faktor = dk.UNDERENHET[kurs_valuta]
        kurser = kurser * faktor
        kurs_valuta = hel

    pris = float(kurser.iloc[-1]) if len(kurser) else info.get("currentPrice")

    borsvarde = info.get("marketCap")
    fx = 1.0
    if borsvarde and kurs_valuta and rapport_valuta and kurs_valuta != rapport_valuta:
        fx = dk.valutakurs(kurs_valuta, rapport_valuta)
        borsvarde = borsvarde * fx

    return {
        "symbol": symbol,
        "pris": pris,
        "kursvaluta": kurs_valuta,
        "rapportvaluta": rapport_valuta,
        "fx_kurs_till_rapport": fx,
        "borsvarde": borsvarde,
        "aktier": info.get("sharesOutstanding"),
        "sektor": info.get("sector"),
        "industri": info.get("industry"),
        "namn": info.get("longName") or meta.get("namn"),
        "beta": info.get("beta"),
        # Yahoo har bytt enhet på det här fältet över tid: ibland 0,054 för
        # 5,4 %, ibland 5,4. Utan normaliseringen visade Swedbank
        # "direktavkastning 540 %". Allt över 1 tolkas som procent.
        "utdelning_procent": _andel(info.get("dividendYield")),
        "kurser": kurser,
    }


def kallor_for(b, symbol=None):
    """Source metadata for raw fields, including units and exact SEC accession."""
    result = {}
    for name in b.varden:
        observations = b.observationer.get(name) or []
        if observations:
            o = max(observations, key=lambda x: x.get("filed") or "")
            result[name] = {"kalla": "SEC EDGAR", "tagg": o.get("tagg"),
                            "publicerad": o.get("filed"), "start": o.get("start"),
                            "slut": o.get("slut"), "enhet": o.get("enhet"),
                            "accession": o.get("accession"),
                            "url": ("https://www.sec.gov/Archives/edgar/data/" + str(int(o["cik"])) + "/" + o["accession"].replace("-", "") + "/" + o["accession"] + "-index.html") if o.get("cik") and o.get("accession") else None}
        else:
            result[name] = {"kalla": "Härlett eller kompletterat från Yahoo", "slut": b.slut,
                            "enhet": b.valuta, "publicerad": None,
                            "url": "https://finance.yahoo.com/quote/" + symbol + "/financials/" if symbol else None}
    return result
