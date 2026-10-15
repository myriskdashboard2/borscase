"""
datakallor.py — allt som hämtas utifrån, och cachen som gör det uthärdligt.

Två källor, båda gratis och utan API-nyckel:

  1. SEC EDGAR (amerikanska bolag)
     - XBRL "companyfacts": varje siffra som bolaget rapporterat, MED det datum
       då den blev offentlig (`filed`). Det är guld: det gör det möjligt att
       bygga en point-in-time-vy och slippa look-ahead-bias, vilket i princip
       varenda gratis screener fuskar med.
     - Själva rapportdokumenten (10-K, 10-Q, 8-K) i fulltext.
     SEC kräver en User-Agent med kontaktuppgift och max 10 anrop/sekund.

  2. Yahoo Finance via yfinance (svenska + amerikanska)
     - Kurser, marknadsvärde, sektor, och 4-5 år av bokslut.
     - Ingen filing-datum-information -> kan INTE användas point-in-time.
       Därför används Yahoo till nuläget och EDGAR till historiken.

Allt cachas på disk i cache/. Nätet anlitas bara när cachen är för gammal.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pandas as pd

HAR = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HAR, "cache")
os.makedirs(CACHE, exist_ok=True)

# SEC vill ha en identifierbar avsändare. Byt i installningar.json om du vill.
KONTAKT = "Borscase Research (privat verktyg) kontakt@example.com"

_SEC_LAS = threading.Lock()
_SEC_SENAST = [0.0]
# yfinance tål viss parallellitet men Yahoo strypar hårt vid för många samtidiga
# anrop. Tre i taget är den nivå som fungerat stabilt utan 429-svar.
_YF_LAS = threading.Semaphore(3)


# ---------------------------------------------------------------- cache ----

def _cachefil(nyckel: str) -> str:
    trygg = re.sub(r"[^A-Za-z0-9_.-]", "_", nyckel)
    return os.path.join(CACHE, trygg + ".json")


def cache_las(nyckel: str, max_alder_h: float):
    """Returnerar cachat värde om det finns och är färskt nog, annars None."""
    fil = _cachefil(nyckel)
    if not os.path.exists(fil):
        return None
    alder_h = (time.time() - os.path.getmtime(fil)) / 3600.0
    if alder_h > max_alder_h:
        return None
    try:
        with open(fil, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def cache_skriv(nyckel: str, varde) -> None:
    import tempfile
    fd, temporary = tempfile.mkstemp(dir=CACHE, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(varde, f, ensure_ascii=False)
        os.replace(temporary, _cachefil(nyckel))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def cache_alder_h(nyckel: str):
    fil = _cachefil(nyckel)
    if not os.path.exists(fil):
        return None
    return (time.time() - os.path.getmtime(fil)) / 3600.0


# ------------------------------------------------------------ SEC EDGAR ----

def _sec_hamta(url: str, som_json: bool = True, forsok: int = 3):
    """Ett anrop mot SEC, strypt till max 10/sekund enligt deras krav."""
    huvuden = {
        "User-Agent": KONTAKT,
        "Accept-Encoding": "gzip, deflate",
        "Host": url.split("/")[2],
    }
    sista_fel = None
    for n in range(forsok):
        with _SEC_LAS:
            vantan = 0.12 - (time.time() - _SEC_SENAST[0])
            if vantan > 0:
                time.sleep(vantan)
            _SEC_SENAST[0] = time.time()
        try:
            beg = urllib.request.Request(url, headers=huvuden)
            with urllib.request.urlopen(beg, timeout=45) as svar:
                rad = svar.read()
                if svar.info().get("Content-Encoding") == "gzip":
                    import gzip
                    rad = gzip.decompress(rad)
            if som_json:
                return json.loads(rad)
            return rad.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            sista_fel = e
            if e.code == 404:
                return None
            time.sleep(1.0 + n)
        except Exception as e:
            sista_fel = e
            time.sleep(1.0 + n)
    raise RuntimeError(f"SEC-anrop misslyckades: {url} ({sista_fel})")


def sec_tickerkarta(max_alder_h: float = 168) -> dict:
    """{TICKER: {'cik': '0000320193', 'namn': 'Apple Inc.'}} för alla SEC-bolag."""
    cachad = cache_las("sec_tickers", max_alder_h)
    if cachad:
        return cachad
    rad = _sec_hamta("https://www.sec.gov/files/company_tickers.json")
    karta = {}
    for post in (rad or {}).values():
        karta[post["ticker"].upper()] = {
            "cik": str(post["cik_str"]).zfill(10),
            "namn": post["title"],
        }
    cache_skriv("sec_tickers", karta)
    return karta


def sec_cik(ticker: str):
    return (sec_tickerkarta().get(ticker.upper()) or {}).get("cik")


def sec_companyfacts(cik: str, max_alder_h: float = 24):
    """Rå XBRL-dump: varje rapporterad siffra med start, slut och filing-datum."""
    nyckel = f"sec_facts_{cik}"
    cachad = cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad
    rad = _sec_hamta(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
    if rad is None:
        return None
    # Full dump är 5-20 MB. Vi sparar bara de taggar vi faktiskt använder.
    bantad = {"cik": cik, "entityName": rad.get("entityName"), "facts": {}}
    for rymd, taggar in (rad.get("facts") or {}).items():
        if rymd not in ("us-gaap", "ifrs-full", "dei"):
            continue
        behall = {}
        for tagg, kropp in taggar.items():
            if tagg in INTRESSANTA_TAGGAR or rymd == "dei":
                behall[tagg] = kropp
        if behall:
            bantad["facts"][rymd] = behall
    cache_skriv(nyckel, bantad)
    return bantad


def sec_inlamningar(cik: str, max_alder_h: float = 12):
    """Lista över bolagets inlämnade rapporter, nyaste först."""
    nyckel = f"sec_sub_{cik}"
    cachad = cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad
    rad = _sec_hamta(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if rad is None:
        return None
    senaste = (rad.get("filings") or {}).get("recent") or {}
    rader = []
    for i in range(len(senaste.get("accessionNumber", []))):
        rader.append({
            "form": senaste["form"][i],
            "datum": senaste["filingDate"][i],
            "rapportdatum": senaste.get("reportDate", [None] * (i + 1))[i],
            "accession": senaste["accessionNumber"][i],
            "dokument": senaste.get("primaryDocument", [None] * (i + 1))[i],
        })
    ut = {"cik": cik, "namn": rad.get("name"), "sic": rad.get("sicDescription"),
          "inlamningar": rader}
    cache_skriv(nyckel, ut)
    return ut


def sec_dokument_url(cik: str, accession: str, dokument: str) -> str:
    ren = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{ren}/{dokument}"


def sec_dokumenttext(cik: str, accession: str, dokument: str,
                     max_alder_h: float = 24 * 365) -> str:
    """Hämtar en rapport och skalar bort HTML. Rapporter ändras aldrig -> cache för evigt."""
    nyckel = f"sec_txt_{cik}_{accession}"
    cachad = cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad.get("text", "")
    url = sec_dokument_url(cik, accession, dokument)
    rad = _sec_hamta(url, som_json=False)
    text = html_till_text(rad or "")
    cache_skriv(nyckel, {"url": url, "text": text})
    return text


ENTITETER = {
    "&nbsp;": " ", "&amp;": "&", "&quot;": '"', "&lt;": "<", "&gt;": ">",
    "&#39;": "'", "&#8217;": "'", "&#8216;": "'", "&#146;": "'", "&#145;": "'",
    "&#8220;": '"', "&#8221;": '"', "&#147;": '"', "&#148;": '"',
    "&#8212;": "-", "&#8211;": "-", "&#151;": "-", "&#150;": "-",
    "&#160;": " ", "&#38;": "&", "&#8226;": "*", "&#149;": "*",
    "&rsquo;": "'", "&lsquo;": "'", "&ldquo;": '"', "&rdquo;": '"',
    "&mdash;": "-", "&ndash;": "-", "&bull;": "*",
}


def html_till_text(html: str) -> str:
    """Enkel men robust HTML-avskalning. Rapporter är tabelltunga; vi vill åt prosan."""
    t = re.sub(r"(?is)<(script|style|title)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?is)<!--.*?-->", " ", t)
    t = re.sub(r"(?i)<(br|/p|/div|/tr|/h[1-6])[^>]*>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
          .replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
          .replace(" ", " ").replace("’", "'").replace("“", '"')
          .replace("”", '"').replace("—", "-").replace("–", "-"))
    # HTML-entiteterna måste översättas INNAN resten städas bort. Missar man det
    # blir "Management&#8217;s Discussion" till "Management s Discussion" — och då
    # hittar avsnittssökningen i rapportlasning.py ingenting alls.
    for fran, till in ENTITETER.items():
        t = t.replace(fran, till)
    t = re.sub(r"&#\d+;|&[a-zA-Z]{2,8};", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)
    return t.strip()


# XBRL-taggar vi bryr oss om. Bolag använder olika taggar för samma sak, så varje
# post i fundamenta.py får en lista av kandidater i prioritetsordning.
INTRESSANTA_TAGGAR = {
    # Resultat
    "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet",
    "SalesRevenueGoodsNet", "SalesRevenueServicesNet",
    "CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold",
    "CostOfServices",
    "GrossProfit",
    "OperatingIncomeLoss",
    "ResearchAndDevelopmentExpense",
    "SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense",
    "SellingAndMarketingExpense",
    "OperatingExpenses", "CostsAndExpenses",
    "NetIncomeLoss", "ProfitLoss",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeTaxExpenseBenefit",
    "InterestExpense", "InterestExpenseDebt", "InterestIncomeExpenseNet",
    "DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
    "DepreciationAndAmortization", "Depreciation",
    "EarningsPerShareDiluted", "EarningsPerShareBasic",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "ShareBasedCompensation",
    # Balans
    "Assets", "AssetsCurrent", "AssetsNoncurrent",
    "Liabilities", "LiabilitiesCurrent", "LiabilitiesAndStockholdersEquity",
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsAndShortTermInvestments",
    "ShortTermInvestments", "MarketableSecuritiesCurrent",
    "AccountsReceivableNetCurrent", "ReceivablesNetCurrent",
    "InventoryNet",
    "PropertyPlantAndEquipmentNet",
    "Goodwill", "IntangibleAssetsNetExcludingGoodwill", "FiniteLivedIntangibleAssetsNet",
    "LongTermDebtNoncurrent", "LongTermDebtCurrent", "LongTermDebt",
    "DebtCurrent", "ShortTermBorrowings", "OperatingLeaseLiabilityNoncurrent",
    "OperatingLeaseLiabilityCurrent",
    "RetainedEarningsAccumulatedDeficit",
    "CommonStockSharesOutstanding", "CommonStockSharesIssued",
    # Kassaflöde
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "PaymentsForRepurchaseOfCommonStock",
    "PaymentsOfDividendsCommonStock", "PaymentsOfDividends",
    "ProceedsFromIssuanceOfCommonStock",
    "IncreaseDecreaseInAccountsReceivable", "IncreaseDecreaseInInventories",
}


def xbrl_serie(facts: dict, kandidater, enhet: str = "USD", form: str = "10-K", alla_versioner: bool = False):
    """
    Plockar ut en tidsserie ur companyfacts.

    Returnerar en lista dictar sorterade på periodslut:
      {slut, start, varde, filed, form, fy, fp}
    `filed` är det som gör point-in-time möjligt: siffran fanns inte i världen
    innan dess.
    """
    if not facts:
        return []
    rymder = (facts.get("facts") or {})
    for tagg in kandidater:
        for rymd in ("us-gaap", "ifrs-full"):
            kropp = (rymder.get(rymd) or {}).get(tagg)
            if not kropp:
                continue
            enheter = kropp.get("units") or {}
            nyckel = enhet if enhet in enheter else next(iter(enheter), None)
            if not nyckel:
                continue
            rader = []
            for obs in enheter[nyckel]:
                if form and obs.get("form") not in (form, form + "/A"):
                    continue
                rader.append({
                    "slut": obs.get("end"), "start": obs.get("start"),
                    "varde": obs.get("val"), "filed": obs.get("filed"),
                    "form": obs.get("form"), "fy": obs.get("fy"), "fp": obs.get("fp"),
                    "tagg": tagg, "enhet": nyckel, "accession": obs.get("accn"),
                })
            if rader:
                if alla_versioner:
                    return sorted(rader, key=lambda x: (x["slut"] or "", x["filed"] or ""))
                # Samma period kan rapporteras flera gånger (omräkningar). Behåll den
                # FÖRSTA publicerade — det är den investeraren faktiskt såg då.
                per_period = {}
                for r in sorted(rader, key=lambda x: (x["slut"] or "", x["filed"] or "")):
                    key = (r["start"], r["slut"], r["enhet"])
                    if key not in per_period:
                        per_period[key] = r
                return sorted(per_period.values(), key=lambda x: x["slut"] or "")
    return []


# --------------------------------------------------------------- Yahoo ----

def _yf():
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf
    return yf


def yahoo_info(symbol: str, max_alder_h: float = 12) -> dict:
    nyckel = f"yf_info_{symbol}"
    cachad = cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad
    yf = _yf()
    with _YF_LAS:
        try:
            info = dict(yf.Ticker(symbol).info or {})
        except Exception:
            info = {}
    behall = {k: v for k, v in info.items() if isinstance(v, (str, int, float, bool, type(None)))}
    # yfinance svarar {"trailingPegRatio": null} när hämtningen misslyckas — en
    # dict som är sann men tom på innehåll. Cachades den slogs bolaget ut ur
    # skanningen i tolv timmar utan att något sa varför. Samma fälla som sänkte
    # insynstestet: ett misslyckat anrop får aldrig se ut som data.
    riktigt = any(behall.get(f) is not None for f in
                  ("longName", "shortName", "marketCap", "currency",
                   "regularMarketPrice", "financialCurrency"))
    if riktigt:
        cache_skriv(nyckel, behall)
    return behall


def yahoo_kurser(symbol: str, period: str = "10y", max_alder_h: float = 12,
                 justerade: bool = True):
    """
    Stängningskurser som {datum: kurs}.

    `justerade=True` ger split- och utdelningsjusterade kurser — det man ska
    räkna AVKASTNING på. `justerade=False` ger den kurs som faktiskt stod på
    skärmen den dagen — det man måste använda för att räkna BÖRSVÄRDE bakåt i
    tiden, eftersom antalet aktier i en gammal rapport är det verkliga antalet,
    inte ett justerat. Blandar man ihop dem blir historiska P/E-tal fel med
    exakt splitfaktorn, och en validering byggd på dem är värdelös.
    """
    nyckel = f"yf_kurs_{symbol}_{period}" + ("" if justerade else "_noterad_v2")
    cachad = cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return pd.Series(cachad, dtype=float) if cachad else pd.Series(dtype=float)
    yf = _yf()
    with _YF_LAS:
        try:
            h = yf.Ticker(symbol).history(period=period, auto_adjust=justerade)
        except Exception:
            h = None
    if h is None or h.empty:
        return pd.Series(dtype=float)
    s = h["Close"].dropna()
    if not justerade:
        s = aterstall_splittar(h).dropna()
    d = {str(i.date()): float(v) for i, v in s.items()}
    cache_skriv(nyckel, d)
    return pd.Series(d, dtype=float)


def yahoo_bokslut(symbol: str, max_alder_h: float = 24 * 7) -> dict:
    """Årsbokslut från Yahoo som {'YYYY-MM-DD': {radnamn: värde}} per rapport."""
    nyckel = f"yf_fin_{symbol}"
    cachad = cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad
    yf = _yf()
    ut = {"resultat": {}, "balans": {}, "kassaflode": {},
          "resultat_q": {}, "balans_q": {}, "kassaflode_q": {}}
    with _YF_LAS:
        try:
            t = yf.Ticker(symbol)
            par = [("resultat", t.income_stmt), ("balans", t.balance_sheet),
                   ("kassaflode", t.cashflow),
                   ("resultat_q", t.quarterly_income_stmt),
                   ("balans_q", t.quarterly_balance_sheet),
                   ("kassaflode_q", t.quarterly_cashflow)]
        except Exception:
            par = []
        for namn, df in par:
            if df is None or getattr(df, "empty", True):
                continue
            for kol in df.columns:
                d = str(pd.Timestamp(kol).date())
                ut[namn][d] = {str(i): (None if pd.isna(v) else float(v))
                               for i, v in df[kol].items()}
    cache_skriv(nyckel, ut)
    return ut


# Några börser noterar i valutans HUNDRADEL medan boksluten står i hela
# enheter: London i pence (GBp), Johannesburg i cent (ZAc), Tel Aviv i
# agorot (ILA). Det är ingen växelkurs utan en enhet — hundra pence ÄR ett
# pund — men Yahoo har ingen "GBpGBP=X" att hämta, så utan den här tabellen
# föll bolagen ur skanningen med "växelkurs saknas". Alternativet, att låta
# kursen bli 1,0, hade gjort varje nyckeltal hundra gånger fel utan att
# synas.
UNDERENHET = {"GBp": ("GBP", 0.01), "GBX": ("GBP", 0.01),
              "ZAc": ("ZAR", 0.01), "ZAC": ("ZAR", 0.01),
              "ILA": ("ILS", 0.01)}


def valutakurs(fran: str, till: str, max_alder_h: float = 12) -> float:
    """Växelkurs via Yahoo, t.ex. USD->SEK. 1.0 om samma valuta."""
    if not fran or not till or fran == till:
        return 1.0
    for liten, (hel, faktor) in UNDERENHET.items():
        if fran == liten:
            return faktor * valutakurs(hel, till, max_alder_h)
        if till == liten:
            return valutakurs(fran, hel, max_alder_h) / faktor
    nyckel = f"fx_{fran}_{till}"
    cachad = cache_las(nyckel, max_alder_h)
    if cachad:
        return float(cachad["kurs"])
    s = yahoo_kurser(f"{fran}{till}=X", period="1mo", max_alder_h=max_alder_h)
    if not len(s):
        raise ValueError(f"Växelkurs saknas för {fran}/{till}; räknar inte med påhittad kurs 1,0")
    kurs = float(s.iloc[-1])
    cache_skriv(nyckel, {"kurs": kurs})
    return kurs


def nu_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def cache_tid(nyckel):
    path = _cachefil(nyckel)
    return datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).isoformat() if os.path.exists(path) else None


def aterstall_splittar(history):
    """Yahoo Close is split-adjusted even with auto_adjust=False.
    Undo later split factors, excluding the split on the price date itself.
    """
    splits = history.get("Stock Splits")
    if splits is None:
        raise ValueError("Splitdata saknas; historiskt börsvärde kan inte beräknas")
    factors = splits.replace(0, 1).iloc[::-1].cumprod().iloc[::-1] / splits.replace(0, 1)
    return history["Close"] * factors
