"""
insynshandel.py — vad de som vet mest gör med sina egna pengar.

Hård, officiell data om vad ledningen gör med sina egna pengar. Insynsköp har i
flera studier följts av bättre avkastning än marknaden (Lakonishok & Lee 2001;
Jeng, Metrick & Zeckhauser 2003; Cohen, Malloy & Pomorski 2012).

MEN VI TESTADE DET PÅ VÅR EGEN DATA, OCH DET HÖLL INTE.

    1342 observationer, 25 mättillfällen, svenska bolag 2020-2026
    Nettoköpare          +7,1 %    på sex månader
    Nettosäljare         +8,1 %
    Ingen insynshandel   +7,7 %
    Alla bolag           +7,5 %
    p mot slumpen         0,747

Nettoköparna gick alltså 0,4 procentenheter SÄMRE än snittet, och säljarna
bäst av alla. Kör om testet själv med `python testa_insyn.py`.

Att effekten finns i litteraturen men inte här kan bero på att studierna mätte
på hela marknader inklusive småbolag, där insynsinformation betyder mer, medan
våra 55 bolag är de mest genomlysta i Sverige. Det kan också bero på att sex
år och 1342 observationer är för lite. Vad det INTE betyder är att du kan
använda insynsköp som köpsignal här.

Insynsförsäljningar säger ännu mindre — en vd säljer för att köpa hus, betala
skatt eller sprida risk, och det är oftast allt.

TVÅ KÄLLOR, BÅDA OFFICIELLA OCH GRATIS

  SVERIGE   Finansinspektionens insynsregister. Hela marknaden i EN CSV-fil
            per datumintervall, vilket gör den här delen nästan gratis att
            hämta. Filen är UTF-16 med semikolon — inte UTF-8, vilket får de
            flesta parsers att ge upp direkt.

  USA       SEC Form 4, en fil per transaktion. Dyrare: varje bolag har
            hundratals. Vi hämtar därför bara de senaste månaderna och tar max
            ett tjugotal per bolag. Cachas för alltid — en inlämnad Form 4
            ändras aldrig.

DET SOM SKILJER SIGNAL FRÅN BRUS

Merparten av all insynsrapportering är LÖN, inte övertygelse: aktier som delas
ut i bonusprogram, optioner som löses in, och försäljningar för att betala
skatten på dem. De säger ingenting om vad personen tror.

  USA      Transaktionskod P = köp på öppna marknaden, S = försäljning.
           A (tilldelning) och M (optionslösen) räknas bort.
  SVERIGE  Kolumnen "Är kopplad till aktieprogram" flaggar samma sak.

Efter den filtreringen återstår det som faktiskt är intressant: någon som
lägger egna pengar på bordet, eller lämnar bordet.
"""

from __future__ import annotations

import csv
import io
import re
import urllib.request
from collections import defaultdict
from datetime import date, timedelta

import datakallor as dk

FI_BAS = ("https://marknadssok.fi.se/publiceringsklient/sv-SE/Search/Search"
          "?SearchFunctionType=Insyn&Transaktionsdatum.From={fran}"
          "&Transaktionsdatum.To={till}&button=export&navigation=")


# ------------------------------------------------------------- Sverige ----

def fi_transaktioner(dagar: int = 180, max_alder_h: float = 24) -> list[dict]:
    """
    Hela svenska marknadens insynshandel för perioden, i ett anrop.

    FI:s export är UTF-16LE med semikolon som avgränsare. Läser man den som
    UTF-8 blir varje kolumnnamn fyllt med nolltecken och filen ser trasig ut
    fast den är helt korrekt.
    """
    till = date.today()
    fran = till - timedelta(days=dagar)
    nyckel = f"fi_insyn_{fran}_{till}"
    cachad = dk.cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad

    url = FI_BAS.format(fran=fran.isoformat(), till=till.isoformat())
    beg = urllib.request.Request(url, headers={"User-Agent": dk.KONTAKT})
    try:
        rad = urllib.request.urlopen(beg, timeout=90).read()
    except Exception:
        return []
    text = rad.decode("utf-16-le", errors="replace").lstrip("﻿")
    rader = list(csv.DictReader(io.StringIO(text, newline=""), delimiter=";"))

    ut = []
    for x in rader:
        ut.append({
            "datum": (x.get("Transaktionsdatum") or "")[:10],
            "bolag": (x.get("Emittent") or "").strip(),
            "person": (x.get("Person i ledande ställning") or "").strip(),
            "befattning": (x.get("Befattning") or "").strip(),
            "typ": (x.get("Karaktär") or "").strip(),
            "volym": _tal(x.get("Volym")),
            "pris": _tal(x.get("Pris")),
            "valuta": (x.get("Valuta") or "SEK").strip(),
            "instrument": (x.get("Instrumenttyp") or "").strip(),
            "aktieprogram": (x.get("Är kopplad till aktieprogram") or "").strip().lower()
                            in ("ja", "true", "1"),
            "narstaende": (x.get("Närstående") or "").strip().lower() in ("ja", "true", "1"),
        })
    dk.cache_skriv(nyckel, ut)
    return ut


def _tal(x):
    try:
        return float(str(x).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return None


def _normalisera(namn: str) -> str:
    n = (namn or "").lower()
    n = re.sub(r"\b(ab|publ|aktiebolag|holding|group|corp|inc|plc|asa|oyj|sa|nv)\b", " ", n)
    return re.sub(r"[^a-zåäö0-9]+", "", n)


def matcha_svenska(transaktioner: list[dict], universum: dict) -> dict:
    """Kopplar FI:s emittentnamn till våra symboler."""
    nycklar = {}
    for sym, m in universum.items():
        if m.get("marknad") != "Sverige":
            continue
        nycklar[_normalisera(m["namn"])] = sym

    per_bolag = defaultdict(list)
    for t in transaktioner:
        n = _normalisera(t["bolag"])
        if not n:
            continue
        traff = nycklar.get(n)
        if not traff:
            for k, sym in nycklar.items():
                if len(k) >= 4 and (k in n or n in k):
                    traff = sym
                    break
        if traff:
            per_bolag[traff].append(t)
    return dict(per_bolag)


# ----------------------------------------------------------------- USA ----

KOD = {"P": "köp", "S": "sälj", "A": "tilldelning", "M": "optionslösen",
       "F": "skatteavdrag", "G": "gåva"}


def sec_form4(symbol: str, dagar: int = 180, max_antal: int = 20,
              max_alder_h: float = 24) -> list[dict]:
    """Bolagets Form 4-transaktioner. Bara öppna marknaden räknas (kod P och S)."""
    nyckel = f"form4_{symbol}"
    cachad = dk.cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad

    cik = dk.sec_cik(symbol) or dk.sec_cik(symbol.replace("-", "."))
    if not cik:
        return []
    sub = dk.sec_inlamningar(cik)
    if not sub:
        return []
    grans = (date.today() - timedelta(days=dagar)).isoformat()
    fyror = [f for f in sub["inlamningar"]
             if f["form"] == "4" and f["datum"] >= grans and f.get("dokument")][:max_antal]

    ut = []
    for f in fyror:
        # Rå XML, inte SEC:s HTML-vy (xslF345X06/... renderar filen och tappar
        # taggarna vi behöver).
        dok = re.sub(r"^xsl[A-Za-z0-9]+/", "", f["dokument"])
        nyckel_xml = f"form4xml_{cik}_{f['accession']}"
        cachad_xml = dk.cache_las(nyckel_xml, 24 * 365)
        if cachad_xml is not None:
            xml = cachad_xml.get("text", "")
        else:
            # Tidigare byggdes URL:en av accession + "_x" som cachenyckel, vilket
            # gav en trasig adress, ett 404 med tre omförsök och ~7 sekunders
            # väntan PER inlämning. Adobe tog 143 sekunder i stället för fem.
            try:
                url = dk.sec_dokument_url(cik, f["accession"], dok)
                xml = dk._sec_hamta(url, som_json=False) or ""
            except Exception:
                continue
            dk.cache_skriv(nyckel_xml, {"text": xml})
        ut += _las_form4(xml, f["datum"])
    dk.cache_skriv(nyckel, ut)
    return ut


def _las_form4(xml: str, inlamnad: str) -> list[dict]:
    def ett(tagg, kropp=None):
        m = re.search(rf"<{tagg}>(.*?)</{tagg}>", kropp if kropp is not None else xml, re.S)
        if not m:
            return None
        v = re.sub(r"<[^>]+>", " ", m.group(1))
        return re.sub(r"\s+", " ", v).strip()

    person = ett("rptOwnerName") or ""
    titel = ett("officerTitle") or ""
    styrelse = (ett("isDirector") or "0") in ("1", "true")

    ut = []
    for block in re.findall(r"<nonDerivativeTransaction>(.*?)</nonDerivativeTransaction>",
                            xml, re.S):
        kod = ett("transactionCode", block)
        if kod not in ("P", "S"):        # allt annat är lön, inte övertygelse
            continue
        antal = _tal(ett("transactionShares", block))
        pris = _tal(ett("transactionPricePerShare", block))
        ut.append({
            "datum": ett("transactionDate", block) or inlamnad,
            "person": person, "befattning": titel or ("Styrelseledamot" if styrelse else ""),
            "typ": KOD.get(kod, kod), "kod": kod,
            "volym": antal, "pris": pris,
            "belopp": (antal * pris) if (antal and pris) else None,
            "aktieprogram": False,
        })
    return ut


# ------------------------------------------------------- sammanfattning ----

TUNGA_BEFATTNINGAR = ("vd", "verkställande", "chief executive", "ceo", "cfo",
                      "finansdirektör", "finanschef", "chief financial",
                      "styrelseordförande", "chairman")


def sammanfatta(transaktioner: list[dict], marknad: str = "Sverige") -> dict:
    """
    Nettobilden för ett bolag: vem köpte, vem sålde, för hur mycket.

    Transaktioner kopplade till aktieprogram räknas bort — de är ersättning och
    säger inget om vad personen tror om bolaget.
    """
    # Bara aktier. Registret innehåller även teckningsoptioner, swappar och
    # obligationer, och där betyder kolumnerna Volym och Pris något helt annat.
    # En Swedbank-post låg på "volym 200 000 000 à 200 000 000" — det är ett
    # obligationslån, inte ett insynsköp för 200 miljoner.
    akta = [t for t in transaktioner
            if not t.get("aktieprogram")
            and (not t.get("instrument") or "aktie" in t["instrument"].lower())
            and not (t.get("instrument") or "").upper().startswith("BT")]
    if marknad == "Sverige":
        kop = [t for t in akta if t["typ"] == "Förvärv"]
        salj = [t for t in akta if t["typ"] == "Avyttring"]
    else:
        kop = [t for t in akta if t.get("kod") == "P"]
        salj = [t for t in akta if t.get("kod") == "S"]

    def belopp(rader):
        s = 0.0
        for t in rader:
            b = t.get("belopp")
            if b is None and t.get("volym") and t.get("pris"):
                b = t["volym"] * t["pris"]
            s += b or 0
        return s

    # En transaktion på hundratals miljoner är inte en chef som köper med lönen —
    # det är en storägare som ökar. Tele2 låg på 5,4 miljarder från EN post, och
    # det var Iliad, inte vd:ns privatekonomi. Båda är information, men bara den
    # första är den signal litteraturen handlar om, så de redovisas var för sig.
    STORAGARGRANS = 50e6

    def personlig(t):
        b = t.get("belopp") or ((t.get("volym") or 0) * (t.get("pris") or 0))
        return b < STORAGARGRANS and not t.get("narstaende")

    kop_person = [t for t in kop if personlig(t)]
    salj_person = [t for t in salj if personlig(t)]
    storagare = [t for t in kop + salj if not personlig(t)]

    kopbelopp, saljbelopp = belopp(kop_person), belopp(salj_person)
    tunga_kop = [t for t in kop_person
                 if any(x in (t.get("befattning") or "").lower() for x in TUNGA_BEFATTNINGAR)]

    return {
        "antal_kop": len(kop_person), "antal_salj": len(salj_person),
        "storagare": [{"datum": t["datum"], "person": t["person"],
                       "typ": t["typ"],
                       "belopp": t.get("belopp") or ((t.get("volym") or 0) * (t.get("pris") or 0))}
                      for t in sorted(storagare, key=lambda x: x["datum"], reverse=True)[:4]],
        "antal_storagare": len(storagare),
        "kopbelopp": kopbelopp, "saljbelopp": saljbelopp,
        "netto": kopbelopp - saljbelopp,
        "personer_kopt": len({t["person"] for t in kop_person}),
        "personer_salt": len({t["person"] for t in salj_person}),
        "tunga_kop": len(tunga_kop),
        "tunga_namn": sorted({t["person"] for t in tunga_kop})[:3],
        "senaste": max([t["datum"] for t in akta], default=None),
        "storagarbelopp": sum((t.get("belopp") or ((t.get("volym") or 0) * (t.get("pris") or 0)))
                              * (1 if t["typ"] in ("Förvärv", "köp") else -1)
                              for t in storagare),
        "rader": sorted(akta, key=lambda t: t["datum"], reverse=True)[:10],
        "antal_totalt": len(transaktioner),
        "bortsorterade_program": len(transaktioner) - len(akta),
    }


def bedomning(s: dict) -> dict | None:
    """
    Vad insynshandeln säger, i klartext.

    Asymmetrin är viktig och står i litteraturen: köp betyder mer än
    försäljningar. Någon säljer för att köpa hus; ingen köper för att köpa hus.
    """
    if not s:
        return None
    if s["antal_kop"] == 0 and s["antal_salj"] == 0:
        if s.get("antal_storagare"):
            netto = s.get("storagarbelopp") or 0
            return {"niva": "storagare", "vikt": 1,
                    "text": f"Ingen personlig insynshandel, men {s['antal_storagare']} "
                            f"storägartransaktion{'er' if s['antal_storagare'] > 1 else ''} "
                            f"på netto {netto / 1e6:+.0f} mn. Det är en ägare som ändrar "
                            "sin position, inte en chef som satsar sin lön — informativt, "
                            "men inte samma signal."}
        return None

    if s["tunga_kop"] and s["netto"] > 0:
        return {"niva": "kop", "vikt": 3,
                "text": f"Insynsköp av ledningen: {s['tunga_kop']} köp av vd, finanschef "
                        f"eller ordförande ({', '.join(s['tunga_namn'])}), netto "
                        f"{s['netto'] / 1e6:.1f} mn i egna pengar de senaste sex "
                        "månaderna. I forskningen har insynsköp följts av bättre "
                        "avkastning — men i VÅR data gav nettoköpare −0,4 %-enheter mot "
                        "snittet (p = 0,75, 1342 observationer). Läs det som en upplysning "
                        "om vad ledningen gör, inte som ett besked om kursen."}
    if s["personer_kopt"] >= 2 and s["netto"] > 0:
        return {"niva": "kop", "vikt": 2,
                "text": f"{s['personer_kopt']} personer i insynsställning har köpt för "
                        f"netto {s['netto'] / 1e6:.1f} mn de senaste sex månaderna. "
                        "Flera oberoende köpare väger tyngre än en."}
    if s["antal_salj"] and s["netto"] < 0 and s["personer_salt"] >= 3:
        return {"niva": "salj", "vikt": 1,
                "text": f"{s['personer_salt']} personer har sålt, netto "
                        f"{abs(s['netto']) / 1e6:.1f} mn. Försäljningar säger betydligt "
                        "mindre än köp — folk säljer för att köpa hus, betala skatt och "
                        "sprida risk. Notera det, dra inga slutsatser."}
    return {"niva": "neutral", "vikt": 0,
            "text": f"{s['antal_kop']} köp och {s['antal_salj']} försäljningar bland "
                    "insynspersoner. Inget tydligt mönster."}
