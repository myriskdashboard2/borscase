"""
svenska_rapporter.py — samma rapportanalys för svenska bolag.

Sverige har ingen motsvarighet till SEC EDGAR: ingen myndighet publicerar
noterade bolags rapporter i strukturerad form som vem som helst kan hämta. Men
rapporterna GÅR att komma åt ändå, för de måste offentliggöras via en godkänd
distributör, och MFN.se publicerar dem med ett öppet JSON-flöde:

    https://mfn.se/all/a.json?author=<bolagsslug>&limit=<n>

Varje post innehåller pressmeddelandets text och — det viktiga — PDF-bilagan,
som är hela delårsrapporten eller årsredovisningen. Den läses med pypdf och
matas sedan in i exakt samma analys som de amerikanska 10-K:erna.

TRE SKILLNADER MOT DE AMERIKANSKA, SOM DU SKA KÄNNA TILL

1. En svensk delårsrapport är 20-50 sidor. En 10-K är 100-200 och har ett
   lagstadgat riskavsnitt (Item 1A). Språkförändringsmåttet blir därför
   trubbigare — det finns mindre text att ändra i.

2. Jämförelsen görs mot SAMMA KVARTAL föregående år, inte mot förra kvartalet.
   Q2 skrivs alltid annorlunda än Q4, så en kvartal-mot-kvartal-jämförelse
   skulle mäta säsong i stället för förändring.

3. De flesta storbolag publicerar en engelsk version, och den föredras eftersom
   Loughran-McDonalds lexikon är engelskt. Finns bara svenska används den
   svenska ordlistan i rapportlasning.py, som är kortare — jämför då bolaget
   med sig självt över tid, aldrig med ett annat bolag.

MFN:s flöde är öppet men det finns inget publicerat API-avtal. Verktyget hämtar
sparsamt (ett anrop per bolag, allt cachas) och identifierar sig i User-Agent.
Samma osäkerhet gäller här som för Yahoo: kontrollera alltid en siffra som ska
ligga till grund för ett beslut mot bolagets egen rapport.
"""

from __future__ import annotations

import io
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime

import datakallor as dk
import rapportlasning as rl

MFN_BAS = "https://mfn.se/all/a.json"

# Bolag där slugen inte går att gissa ur namnet.
MFN_SLUGGAR = {
    "NIBE-B.ST": "nibe-industrier",
    "HM-B.ST": "handm",
    "TELIA.ST": "telia-company",
}

# Rubriker som ÄR en rapport.
ARRAPPORT = re.compile(
    r"\b(interim report|year[- ]end report|annual report|half[- ]year report"
    r"|quarterly report|q[1-4]\b|first quarter|second quarter|third quarter"
    r"|fourth quarter|delårsrapport|bokslutskommuniké|årsredovisning"
    r"|kvartalsrapport|halvårsrapport|niomånadersrapport)", re.I)

# …och rubriker som bara HANDLAR om en rapport.
INTE_RAPPORT = re.compile(
    r"\b(invitation|inbjudan|presentation of|webcast|telefonkonferens|conference call"
    r"|kallelse|notice of|publicerar|publishes|kommer att publicera|will publish"
    r"|silent period|tyst period|datum för|financial calendar|finansiell kalender)", re.I)


def _hamta_json(url: str):
    beg = urllib.request.Request(url, headers={"User-Agent": dk.KONTAKT,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(beg, timeout=40) as svar:
        return json.loads(svar.read())


def gissa_slug(namn: str) -> str:
    n = re.sub(r"\s+(A|B|C|SDB|AB|B SDB)$", "", namn).strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")


def mfn_slug(symbol: str, namn: str, max_alder_h: float = 24 * 30) -> str | None:
    """Hittar bolagets id hos MFN. Gissar först, söker sedan, cachar alltid."""
    if symbol in MFN_SLUGGAR:
        return MFN_SLUGGAR[symbol]
    nyckel = f"mfn_slug_{symbol}"
    cachad = dk.cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad.get("slug")

    slug = None
    gissning = gissa_slug(namn)
    try:
        d = _hamta_json(f"{MFN_BAS}?limit=2&author={gissning}")
        if d.get("items"):
            slug = gissning
    except Exception:
        pass

    if not slug:
        try:
            from difflib import SequenceMatcher
            d = _hamta_json(f"{MFN_BAS}?limit=10&query={urllib.parse.quote(namn)}")
            bast = None
            for x in d.get("items") or []:
                a = x["author"]
                p = SequenceMatcher(None, a["name"].lower(), namn.lower()).ratio()
                if not bast or p > bast[0]:
                    bast = (p, a["slug"])
            if bast and bast[0] > 0.6:
                slug = bast[1]
        except Exception:
            pass

    dk.cache_skriv(nyckel, {"slug": slug})
    return slug


def lista_rapporter(slug: str, sidor: int = 5, per_sida: int = 100,
                    max_alder_h: float = 12) -> list[dict]:
    """
    Bolagets rapporter, nyaste först, en per tillfälle och språk.

    Flödet innehåller ALLA pressmeddelanden, inte bara rapporter, och ett aktivt
    storbolag skickar flera i veckan. En enda sida räcker därför bara ett halvår
    bakåt — och då finns ingen rapport från samma period i fjol att jämföra med,
    vilket är hela poängen. Vi bläddrar tills det finns tillräckligt djup.
    """
    nyckel = f"mfn_lista_{slug}"
    cachad = dk.cache_las(nyckel, max_alder_h)
    if cachad is None:
        cachad = []
        for sida in range(sidor):
            try:
                d = _hamta_json(f"{MFN_BAS}?limit={per_sida}"
                                f"&offset={sida * per_sida}&author={slug}")
            except Exception:
                break
            poster = d.get("items") or []
            if not poster:
                break
            cachad += poster
            if _antal_rapporter(cachad) >= 10:
                break
        dk.cache_skriv(nyckel, cachad)

    ut = []
    for x in cachad:
        c = x.get("content") or {}
        titel = c.get("title") or ""
        if not ARRAPPORT.search(titel) or INTE_RAPPORT.search(titel):
            continue
        pdf = [a for a in (c.get("attachments") or [])
               if a.get("content_type") == "application/pdf"]
        if not pdf:
            continue
        ut.append({
            "datum": (c.get("publish_date") or "")[:10],
            "titel": titel,
            "sprak": (x.get("properties") or {}).get("lang", "sv"),
            "url": x.get("url"),
            "pdf": pdf[0]["url"],
            "pressmeddelande": c.get("text") or "",
            "grupp": x.get("group_id"),
        })
    ut.sort(key=lambda r: r["datum"], reverse=True)
    return ut


def _antal_rapporter(poster: list[dict]) -> int:
    n = 0
    for x in poster:
        titel = ((x.get("content") or {}).get("title")) or ""
        if ARRAPPORT.search(titel) and not INTE_RAPPORT.search(titel):
            n += 1
    return n


def valj_sprak(rapporter: list[dict]) -> list[dict]:
    """Engelska framför svenska när båda finns för samma tillfälle."""
    per_grupp = {}
    for r in rapporter:
        nyckel = r["grupp"] or r["datum"]
        if nyckel not in per_grupp or (r["sprak"] == "en" and per_grupp[nyckel]["sprak"] != "en"):
            per_grupp[nyckel] = r
    return sorted(per_grupp.values(), key=lambda r: r["datum"], reverse=True)


def pdf_text(url: str, max_alder_h: float = 24 * 365) -> str:
    """Laddar ner och textextraherar en rapport-PDF. Rapporter ändras aldrig."""
    nyckel = "mfn_pdf_" + re.sub(r"[^A-Za-z0-9]", "_", url)[-80:]
    cachad = dk.cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad.get("text", "")
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("Svensk rapportläsning kräver pypdf. Kör: pip install pypdf")
    beg = urllib.request.Request(url, headers={"User-Agent": dk.KONTAKT})
    rad = urllib.request.urlopen(beg, timeout=90).read()
    lasare = PdfReader(io.BytesIO(rad))
    text = "\n".join((s.extract_text() or "") for s in lasare.pages)
    text = re.sub(r"[ \t]+", " ", text)
    dk.cache_skriv(nyckel, {"url": url, "text": text})
    return text


def _manader_mellan(a: str, b: str) -> float:
    try:
        da = datetime.strptime(a, "%Y-%m-%d")
        db = datetime.strptime(b, "%Y-%m-%d")
        return abs((da - db).days) / 30.44
    except Exception:
        return 999


def parhitta(rapporter: list[dict]) -> tuple[dict, dict | None]:
    """
    Senaste rapporten, och motsvarande rapport för ett år sedan.

    Att jämföra Q2 mot Q1 vore att mäta säsong. Vi letar därför den rapport som
    ligger närmast tolv månader tillbaka, med tio till fjorton månader som
    tillåtet fönster.
    """
    if not rapporter:
        return None, None
    nu = rapporter[0]
    # Samma SPRÅK är ett absolut krav. Jämförs en engelsk Q2 mot fjolårets
    # svenska Q2 blir cosinuslikheten 0,06 och verktyget larmar "kraftigt
    # omskriven" — när ingenting alls har skrivits om. Ett mått som larmar som
    # värst just när det har fel är sämre än inget mått.
    kandidater = [(abs(_manader_mellan(nu["datum"], r["datum"]) - 12), r)
                  for r in rapporter[1:]
                  if r["sprak"] == nu["sprak"]
                  and 10 <= _manader_mellan(nu["datum"], r["datum"]) <= 14]
    if not kandidater:
        return nu, None
    return nu, min(kandidater, key=lambda x: x[0])[1]


def analysera_svenskt_bolag(symbol: str, namn: str, djup: int = 6) -> dict:
    """
    Samma returformat som rapportlasning.analysera_bolag, så att appen inte
    behöver veta vilket land bolaget kommer ifrån.
    """
    slug = mfn_slug(symbol, namn)
    if not slug:
        return {"tillganglig": False,
                "skal": f"Hittade inget bolag hos MFN som matchar {namn}."}

    alla = valj_sprak(lista_rapporter(slug))
    if not alla:
        return {"tillganglig": False,
                "skal": "Inga rapporter med PDF-bilaga hittades hos MFN."}

    nu, forra = parhitta(alla)
    try:
        text_nu = pdf_text(nu["pdf"])
    except Exception as e:
        return {"tillganglig": False, "skal": f"Kunde inte läsa PDF: {e}"}
    if len(text_nu) < 2000:
        return {"tillganglig": False,
                "skal": "Rapportens PDF gick inte att textextrahera (troligen inskannad)."}

    text_forra = ""
    if forra:
        try:
            text_forra = pdf_text(forra["pdf"])
        except Exception:
            text_forra = ""

    import intel
    sprak = nu["sprak"]
    ut = {
        "tillganglig": True,
        "ledningsuttalanden": intel.promises(text_nu, {"url": nu["pdf"], "datum": nu["datum"]}),
        "form": nu["titel"],
        "kalla": "MFN",
        "sprak": sprak,
        "senaste": {"datum": nu["datum"], "period": nu["titel"], "url": nu["url"],
                    "pdf": nu["pdf"]},
        "foregaende": ({"datum": forra["datum"], "url": forra["url"],
                        "titel": forra["titel"]} if forra else None),
        "avsnitt_hittade": {"riskfaktorer": False, "vd_analys": False},
        "tonlage_hela": rl.tonlage(text_nu, sprak),
        "tonlage_risk": {},
        "tonlage_vd": {},
        "roda_flaggor": rl.roda_flaggor(text_nu, sprak),
        "forandring_hela": rl.sprakforandring(text_nu, text_forra) if text_forra else None,
        "forandring_risk": None,
        "forandring_vd": None,
        "nya_risker": rl.nya_stycken(text_nu, text_forra) if text_forra else [],
        "jamforelse": ("samma period föregående år" if forra else "ingen jämförelse möjlig"),
    }

    # Riskavsnittet om det går att hitta — svenska rapporter har inget
    # lagstadgat sådant, men de flesta har en rubrik som "Risker och osäkerhet".
    risk_nu = svenskt_riskavsnitt(text_nu)
    risk_fo = svenskt_riskavsnitt(text_forra) if text_forra else ""
    if risk_nu:
        ut["avsnitt_hittade"]["riskfaktorer"] = True
        ut["tonlage_risk"] = rl.tonlage(risk_nu, sprak)
        ut["forandring_risk"] = rl.sprakforandring(risk_nu, risk_fo) if risk_fo else None

    trend = []
    for r in alla[:djup]:
        try:
            t = pdf_text(r["pdf"])
        except Exception:
            continue
        ton = rl.tonlage(svenskt_riskavsnitt(t) or t, r["sprak"])
        if ton:
            trend.append({"datum": r["datum"], "negativa_pct": ton["negativa_pct"],
                          "osakerhet_pct": ton["osakerhet_pct"],
                          "antal_ord": ton["antal_ord"], "titel": r["titel"][:60]})
    ut["tonlagestrend"] = list(reversed(trend))
    return ut


SVENSKT_RISKAVSNITT = re.compile(
    r"(risker och os[äa]kerhetsfaktorer|risker och riskhantering|risker och os[äa]kerhet"
    r"|v[äa]sentliga risker|risks and uncertaint|risk management and|principal risks)",
    re.I)
SVENSKT_RISKSLUT = re.compile(
    r"(redovisningsprinciper|accounting policies|noter\b|notes to the|"
    r"moderbolaget|parent company|finansiella rapporter i sammandrag|"
    r"styrelsens f[öo]rs[äa]kran|signatures?\b)", re.I)


def svenskt_riskavsnitt(text: str) -> str:
    """Klipper ut riskavsnittet om rapporten har ett. Många har det inte."""
    if not text:
        return ""
    basta = ""
    slut_pos = [m.start() for m in SVENSKT_RISKSLUT.finditer(text)]
    for m in SVENSKT_RISKAVSNITT.finditer(text):
        s = m.start()
        efter = [p for p in slut_pos if p > s + 600]
        bit = text[s:(efter[0] if efter else min(len(text), s + 20000))]
        if len(bit) > len(basta):
            basta = bit
    return basta if len(basta) > 800 else ""
