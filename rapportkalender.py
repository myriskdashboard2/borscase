"""
rapportkalender.py — när rapporten kommer, och vad som brukar hända då.

Två frågor besvaras här, och de är olika mycket besvarbara:

  1. NÄR kommer nästa rapport, och hur har aktien historiskt reagerat på
     rapporter? Det är ren bokföring och statistik. Svaret går att lita på.

  2. Kommer aktien STIGA eller SJUNKA på rapporten? Det är en prognos, och
     prognoser om enskilda kursrörelser är nära nog omöjliga. Modulen räknar
     ändå fram en sannolikhet — men den visas ALDRIG utan träffsäkerheten
     bredvid, mätt med samma metod på historisk data. Är träffsäkerheten 52 %
     ska talet läsas som 52 %, inte som en spådom.

REAKTIONSFÖNSTRET

Amerikanska bolag rapporterar efter stängning (16:20 New York-tid), svenska
före öppning (07:00-07:45 svensk tid). Reaktionen ligger därför på olika dagar:

    rapport före kl 12 lokalt  ->  samma dags stängning mot gårdagens
    rapport efter kl 12        ->  nästa dags stängning mot rapportdagens

Missar man det mäter man fel dag för halva universumet, och hela statistiken
blir brus. Klockslaget finns i tidsstämpeln från Yahoo, så det går att göra rätt.

MODELLEN

Avsiktligt en enda, vald i förväg — inte den bästa av tio testade, för då blir
domen cirkulär (samma fel som fälldes i I:/Claudecode/boliden/SLUTSATSER.md):

    sannolikhet = 0,5 + krympning * (bolagets historiska andel upp − 0,5)
    krympning   = n / (n + 10)

Krympningen finns för att åtta rapporter inte säger något; med 24 rapporter
väger historiken 70 %. Modellen valideras rullande framåt: för varje rapport
används ENBART tidigare rapporter för att förutsäga, och träffarna räknas.
"""

from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import datakallor as dk

HAR = os.path.dirname(os.path.abspath(__file__))
DOMFIL = os.path.join(HAR, "rapportmodell.json")
KRYMPNING_N = 10.0


def spara_dom(f: dict) -> None:
    """
    Domen sparas som en riktig fil, inte i cache/.

    Skälet är distributionen: cache/ ska inte med i en zip (den är hundratals
    megabyte och regenereras), men UTAN domen skulle appen visa sannolikheten
    för rapportriktning helt utan träffsäkerheten bredvid sig. Då blir det en
    spådom i stället för en statistik, vilket är precis vad den inte får bli.
    """
    import json as _json
    with open(DOMFIL, "w", encoding="utf-8") as fil:
        _json.dump(f, fil, ensure_ascii=False, indent=1)


def las_dom() -> dict | None:
    import json as _json
    if not os.path.exists(DOMFIL):
        return None
    try:
        with open(DOMFIL, "r", encoding="utf-8") as fil:
            return _json.load(fil)
    except Exception:
        return None


def _yf():
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf
    return yf


def rapportdatum(symbol: str, max_alder_h: float = 24) -> dict:
    """
    Historiska rapporttillfällen och nästa kommande.

    Returnerar {'kommande': 'YYYY-MM-DD'|None, 'historik': [{datum, tid,
    fore_lunch, estimat, utfall, overraskning}]}
    """
    nyckel = f"kalender_{symbol}"
    cachad = dk.cache_las(nyckel, max_alder_h)
    if cachad is not None:
        return cachad

    yf = _yf()
    ut = {"kommande": None, "kommande_estimat": None, "historik": []}
    with dk._YF_LAS:
        t = yf.Ticker(symbol)
        try:
            kal = t.calendar or {}
        except Exception:
            kal = {}
        try:
            ed = t.get_earnings_dates(limit=32)
        except Exception:
            ed = None

    datum = kal.get("Earnings Date")
    if isinstance(datum, (list, tuple)) and datum:
        ut["kommande"] = str(datum[0])
    elif datum:
        ut["kommande"] = str(datum)
    ut["kommande_estimat"] = kal.get("Earnings Average")

    if ed is not None and not getattr(ed, "empty", True):
        nu = pd.Timestamp.now(tz="UTC")
        for tid, rad in ed.iterrows():
            stampel = pd.Timestamp(tid)
            lokal = stampel.tz_convert(stampel.tz) if stampel.tz else stampel
            post = {
                "datum": str(lokal.date()),
                "timme": int(lokal.hour),
                "fore_lunch": int(lokal.hour) < 12,
                "estimat": _tal(rad.get("EPS Estimate")),
                "utfall": _tal(rad.get("Reported EPS")),
                "overraskning": _tal(rad.get("Surprise(%)")),
            }
            if stampel.tz_localize(None) if stampel.tz is None else stampel > nu:
                if not ut["kommande"]:
                    ut["kommande"] = post["datum"]
                continue
            ut["historik"].append(post)
    ut["historik"].sort(key=lambda x: x["datum"])
    dk.cache_skriv(nyckel, ut)
    return ut


def _tal(x):
    try:
        v = float(x)
        return None if (math.isnan(v) or math.isinf(v)) else v
    except Exception:
        return None


def reaktioner(symbol: str, kurser: pd.Series | None = None) -> list[dict]:
    """
    Kursreaktionen på varje historisk rapport, mätt i rätt fönster.

    `reaktion` = procentuell förändring från stängningen INNAN marknaden fick
    veta, till nästa stängning efter. `drift_20d` = vad som hände de följande
    tjugo handelsdagarna (det är där post-earnings announcement drift bor,
    Ball & Brown 1968, Bernard & Thomas 1989).
    """
    kal = rapportdatum(symbol)
    if kurser is None:
        kurser = dk.yahoo_kurser(symbol, period="10y")
    if kurser is None or not len(kurser):
        return []

    historik = kal["historik"]
    if symbol.endswith(".ST"):
        historik = _fyll_pa_med_mfn(symbol, historik)
    else:
        historik = _fyll_pa_med_edgar(symbol, historik)

    index = list(kurser.index)
    ut = []
    for post in historik:
        d = post["datum"]
        # Index för första handelsdag >= rapportdatum
        i = next((k for k, dag in enumerate(index) if dag >= d), None)
        if i is None or i == 0 or i >= len(index) - 1:
            continue
        if post["fore_lunch"]:
            fore, efter = i - 1, i          # morgonrapport: reaktionen samma dag
        else:
            fore, efter = i, i + 1          # kvällsrapport: reaktionen nästa dag
        if efter >= len(index):
            continue
        try:
            k0, k1 = float(kurser.iloc[fore]), float(kurser.iloc[efter])
        except Exception:
            continue
        if not k0:
            continue
        reaktion = k1 / k0 - 1
        drift = None
        if efter + 20 < len(index):
            drift = float(kurser.iloc[efter + 20]) / k1 - 1
        ut.append({**post, "reaktion": reaktion, "upp": reaktion > 0,
                   "drift_20d": drift, "kursdatum": index[efter]})
    return ut


def _fyll_pa_med_mfn(symbol: str, historik: list[dict]) -> list[dict]:
    """
    Yahoos rapportdatumtabell slutar ofta ett år tillbaka i tiden för svenska
    bolag. MFN vet exakt när varje rapport publicerades, och de datumen har vi
    redan hämtat för rapportläsningen — så luckan går att täppa gratis.

    Svenska rapporter publiceras på morgonen, därav fore_lunch=True.
    """
    try:
        import svenska_rapporter as sv
        import universum as un
        meta = un.bygg_universum().get(symbol)
        if not meta:
            return historik
        slug = sv.mfn_slug(symbol, meta["namn"])
        if not slug:
            return historik
        kanda = {p["datum"] for p in historik}
        for r in sv.valj_sprak(sv.lista_rapporter(slug)):
            if r["datum"] and r["datum"] not in kanda:
                historik = historik + [{"datum": r["datum"], "timme": 7,
                                        "fore_lunch": True, "estimat": None,
                                        "utfall": None, "overraskning": None,
                                        "kalla": "MFN"}]
                kanda.add(r["datum"])
    except Exception:
        pass
    return sorted(historik, key=lambda x: x["datum"])


def _fyll_pa_med_edgar(symbol: str, historik: list[dict]) -> list[dict]:
    """
    Samma lucka som för svenska bolag, men värre: Yahoos rapportdatumtabell för
    amerikanska bolag kan ligga över ETT ÅR efter. Applied Materials slutade på
    2025-05-15 medan bolaget rapporterat fyra gånger sedan dess.

    SEC vet exakt när. Ett bolag lämnar in en 8-K samma dag som det släpper sin
    kvartalsrapport (Item 2.02, "Results of Operations"). Bolag lämnar 8-K:er av
    många andra skäl också, så vi kan inte ta alla — i stället följs bolagets
    egen rapportrytm: från senast kända rapportdatum letas den 8-K som ligger
    närmast ett kvartal framåt, och så vidare. Det plockar de fyra årliga
    rapporterna och hoppar över resten.

    Rapporten släpps efter börsstängning, därav fore_lunch=False.
    """
    try:
        cik = dk.sec_cik(symbol) or dk.sec_cik(symbol.replace("-", "."))
        if not cik:
            return historik
        sub = dk.sec_inlamningar(cik)
        if not sub:
            return historik
        attakan = sorted({f["datum"] for f in sub["inlamningar"] if f["form"] == "8-K"})
        if not attakan or not historik:
            return historik

        datum = [datetime.strptime(p["datum"], "%Y-%m-%d").date() for p in historik]
        if len(datum) >= 4:
            avstand = sorted((datum[i + 1] - datum[i]).days for i in range(len(datum) - 1))
            takt = avstand[len(avstand) // 2]
        else:
            takt = 91
        takt = min(max(takt, 80), 100)

        idag = datetime.now().date()
        senast = datum[-1]
        kanda = {p["datum"] for p in historik}
        tillagda = []
        while True:
            mal = senast + timedelta(days=takt)
            if mal > idag + timedelta(days=5):
                break
            kandidater = [d for d in attakan
                          if abs((datetime.strptime(d, "%Y-%m-%d").date() - mal).days) <= 25
                          and d not in kanda]
            if not kandidater:
                senast = mal          # inget hittat, hoppa ett kvartal och fortsätt
                continue
            bast = min(kandidater,
                       key=lambda d: abs((datetime.strptime(d, "%Y-%m-%d").date() - mal).days))
            tillagda.append({"datum": bast, "timme": 16, "fore_lunch": False,
                             "estimat": None, "utfall": None, "overraskning": None,
                             "kalla": "SEC 8-K"})
            kanda.add(bast)
            senast = datetime.strptime(bast, "%Y-%m-%d").date()
        return sorted(historik + tillagda, key=lambda x: x["datum"])
    except Exception:
        return historik


def statistik(rader: list[dict]) -> dict:
    """Faktabasen: hur aktien BRUKAR röra sig på rapport. Ingen prognos."""
    if not rader:
        return {}
    r = np.array([x["reaktion"] for x in rader], dtype=float)
    upp = np.array([1.0 if x["upp"] else 0.0 for x in rader])
    overr = [x["overraskning"] for x in rader if x["overraskning"] is not None]
    return {
        "antal": len(rader),
        "andel_upp": float(upp.mean()),
        "median_rorelse": float(np.median(np.abs(r))),
        "snitt_rorelse": float(np.abs(r).mean()),
        "storsta_upp": float(r.max()),
        "storsta_ner": float(r.min()),
        "senaste_reaktion": float(r[-1]),
        "andel_slog_estimat": (float(np.mean([1.0 if o > 0 else 0.0 for o in overr]))
                               if overr else None),
        "median_overraskning": float(np.median(overr)) if overr else None,
        "period": f"{rader[0]['datum']} – {rader[-1]['datum']}",
    }


def sannolikhet_upp(rader: list[dict]) -> dict:
    """
    Modellen, i sin helhet. Fyra rader kod, valda i förväg.

    Att den är så enkel är avsiktligt: varje extra term är en chans att
    överanpassa mot historiken, och valideringen nedan visar att inte ens den
    här enkla varianten tillför särskilt mycket.
    """
    if len(rader) < 4:
        return {"sannolikhet": None, "skal": "för få rapporter"}
    upp = sum(1 for x in rader if x["upp"])
    n = len(rader)
    bas = upp / n
    krympning = n / (n + KRYMPNING_N)
    p = 0.5 + krympning * (bas - 0.5)
    return {
        "sannolikhet": p,
        "bas": bas,
        "antal": n,
        "krympning": krympning,
        "riktning": "upp" if p > 0.5 else "ner",
        "styrka": abs(p - 0.5) * 2,
    }


# --------------------------------------------------------------- validering

def validera(symboler: list[str], minsta_historik: int = 8, framsteg=None) -> dict:
    """
    Rullande test: för varje rapport används ENBART tidigare rapporter för att
    gissa riktningen. Jämförs mot två referenspunkter:

      * slantsingling (50 %)
      * "gissa alltid upp", som är svårare att slå än man tror eftersom
        aktier stiger oftare än de faller
    """
    traffar = totalt = 0
    alltid_upp = 0
    per_bolag = []
    for i, sym in enumerate(symboler, 1):
        try:
            r = reaktioner(sym)
        except Exception:
            continue
        if len(r) < minsta_historik + 1:
            continue
        bolag_traff = bolag_n = 0
        for k in range(minsta_historik, len(r)):
            gissning = sannolikhet_upp(r[:k])
            if gissning.get("sannolikhet") is None:
                continue
            gissade_upp = gissning["sannolikhet"] > 0.5
            ratt = (gissade_upp == r[k]["upp"])
            traffar += int(ratt)
            bolag_traff += int(ratt)
            totalt += 1
            bolag_n += 1
            alltid_upp += int(r[k]["upp"])
        if bolag_n:
            per_bolag.append({"symbol": sym, "traffsakerhet": bolag_traff / bolag_n,
                              "antal": bolag_n})
        if framsteg and i % 20 == 0:
            framsteg(f"{i}/{len(symboler)} bolag, {totalt} rapporter testade")

    if not totalt:
        return {"fel": "Ingen historik att testa på."}

    traffsakerhet = traffar / totalt
    basandel = alltid_upp / totalt
    # Binomialtest mot 50 %: hur osannolikt är utfallet om metoden är värdelös?
    std = math.sqrt(0.25 / totalt)
    z = (traffsakerhet - 0.5) / std if std else 0.0
    p_varde = 0.5 * math.erfc(z / math.sqrt(2))
    return {
        "antal_rapporter": totalt,
        "antal_bolag": len(per_bolag),
        "traffsakerhet": traffsakerhet,
        "alltid_upp_traffsakerhet": basandel,
        "battre_an_alltid_upp": traffsakerhet > basandel,
        "z": z,
        "p_varde": p_varde,
        "slutsats": _slutsats(traffsakerhet, basandel, p_varde),
        "tid": dk.nu_iso(),
    }


def _slutsats(traff, bas, p):
    if p < 0.05 and traff > bas:
        return (f"Metoden träffade {traff*100:.1f} % av riktningarna, mot "
                f"{bas*100:.1f} % för att alltid gissa upp. Skillnaden mot "
                f"slantsingling är statistiskt säkerställd (p = {p:.3f}). "
                "Det betyder fortfarande inte att den är användbar att handla på "
                "— avgifter och spread äter små kanter.")
    return (f"Metoden träffade {traff*100:.1f} % av riktningarna. Att alltid "
            f"gissa upp hade gett {bas*100:.1f} %. p = {p:.3f} mot slantsingling. "
            "Sannolikheten som visas i appen ska därför läsas som vad den är: en "
            "historisk andel, inte en prognos. Det som ÄR användbart på den här "
            "fliken är hur STORT bolaget brukar röra sig — den siffran säger vad "
            "du riskerar över rapportdagen.")


def bedomning(symbol: str, kurser=None) -> dict:
    """Allt om ett bolags rapportsituation, i ett paket."""
    kal = rapportdatum(symbol)
    rad = reaktioner(symbol, kurser)
    stat = statistik(rad)
    gissning = sannolikhet_upp(rad)

    # Yahoos kalenderfält innehåller ibland det SENASTE rapportdatumet i stället
    # för nästa. Släpper man igenom det får man negativa "dagar kvar" och en
    # kalender som pekar bakåt. Ligger datumet i det förflutna kastas det, och
    # nästa datum uppskattas i stället ur bolagets egen rapportrytm — tydligt
    # märkt som uppskattat, för det är precis vad det är.
    idag = datetime.now().date()
    kommande, sakerhet = None, None
    try:
        if kal.get("kommande"):
            d = datetime.strptime(str(kal["kommande"])[:10], "%Y-%m-%d").date()
            if d >= idag:
                kommande, sakerhet = d, "bekräftat av bolaget"
    except Exception:
        pass

    if kommande is None and len(rad) >= 4:
        datum = [datetime.strptime(x["datum"], "%Y-%m-%d").date() for x in rad]
        mellanrum = sorted((datum[i + 1] - datum[i]).days for i in range(len(datum) - 1))
        typiskt = mellanrum[len(mellanrum) // 2]
        gissat = datum[-1] + timedelta(days=typiskt)
        while gissat < idag:
            gissat += timedelta(days=max(typiskt, 30))
        kommande, sakerhet = gissat, f"uppskattat ur rapportrytmen (~{typiskt} dagar)"

    dagar = (kommande - idag).days if kommande else None

    return {
        "kommande": kommande.isoformat() if kommande else None,
        "datumsakerhet": sakerhet,
        "dagar_kvar": dagar,
        "estimat_eps": kal.get("kommande_estimat"),
        "statistik": stat,
        "gissning": gissning,
        "reaktioner": [{"datum": x["datum"], "reaktion": x["reaktion"],
                        "overraskning": x["overraskning"], "drift_20d": x["drift_20d"]}
                       for x in rad[-12:]],
    }


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    import universum as un

    grupper = None
    if "--karna" in sys.argv:
        grupper = ["karna"]
    elif "--ai" in sys.argv:
        grupper = ["halvledare_ai"]
    U = un.bygg_universum(grupper=grupper)

    print("\n  Testar rapportriktnings-modellen rullande framåt.")
    print("  Varje rapport gissas med ENBART tidigare rapporter som underlag.\n")
    f = validera(list(U), framsteg=lambda m: print("  ...", m, flush=True))
    if f.get("fel"):
        print("  " + f["fel"])
    else:
        print(f"\n  {f['antal_rapporter']} rapporter, {f['antal_bolag']} bolag")
        print(f"  Modellens träffsäkerhet:     {f['traffsakerhet']*100:.1f} %")
        print(f"  Gissa alltid upp:            {f['alltid_upp_traffsakerhet']*100:.1f} %")
        print(f"  Slantsingling:               50,0 %")
        print(f"  p mot slantsingling:         {f['p_varde']:.3f}\n")
        rad = ""
        for o in f["slutsats"].split():
            if len(rad) + len(o) + 1 > 74:
                print("  " + rad)
                rad = o
            else:
                rad = (rad + " " + o).strip()
        if rad:
            print("  " + rad)
        spara_dom(f)
        print()
