"""
testa_insyn.py — håller insynssignalen i vår egen data?

Samma protokoll som de åtta tidigare testerna, för annars går resultaten inte
att jämföra:

  * Var tredje månad rangordnas bolagen efter NETTO PERSONLIGT INSYNSKÖP under
    de föregående sex månaderna — bara transaktioner som var publicerade då.
  * Avkastningen mäts sex månader framåt.
  * Tre grupper: nettoköpare, nettosäljare, och de utan insynshandel.
  * Nollkontroll: samma protokoll med slumpmässigt tilldelade grupper.

BEGRÄNSNINGAR SOM GÖR RESULTATET SVAGARE ÄN DET SER UT

  * Bara svenska bolag. FI:s register går att hämta historiskt; SEC Form 4
    hade krävt hundratusentals nedladdningar.
  * 62 bolag. Av dem har kanske 15-25 insynshandel i ett givet halvår, så varje
    mättillfälle vilar på få observationer.
  * FI:s export ger max 1000 rader per anrop, därför hämtas den i treveckors-
    fönster. Slår ett fönster i taket blir den perioden ofullständig, och det
    skrivs ut som en varning under körningen.

Med den urvalsstorleken kan testet upptäcka en STOR effekt men inte utesluta en
liten. Det ska stå i domen, och det gör det.
"""

from __future__ import annotations

import csv
import io
import random
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, timedelta

import numpy as np

import datakallor as dk
import insynshandel as ih
import universum as un

FI = ("https://marknadssok.fi.se/publiceringsklient/sv-SE/Search/Search"
      "?SearchFunctionType=Insyn&Transaktionsdatum.From={a}&Transaktionsdatum.To={b}"
      "&button=export&navigation=")


def hamta_fonster(a: date, b: date) -> list[dict]:
    """Ett treveckorsfönster ur FI:s register. Cachas för alltid — historik ändras inte."""
    nyckel = f"fi_hist_{a}_{b}"
    cachad = dk.cache_las(nyckel, 24 * 365 * 5)
    if cachad is not None:
        return cachad
    # Ett misslyckat anrop får ALDRIG cachas. Första versionen gjorde det, och
    # då låg 102 av 125 fönster kvar som permanent tomma — testet hade körts på
    # ett register med fyra års hål i, utan att något syntes.
    rader, lyckades = [], False
    for forsok in range(3):
        try:
            beg = urllib.request.Request(FI.format(a=a.isoformat(), b=b.isoformat()),
                                         headers={"User-Agent": dk.KONTAKT})
            rad = urllib.request.urlopen(beg, timeout=120).read()
            text = rad.decode("utf-16-le", errors="replace").lstrip("﻿")
            rader = list(csv.DictReader(io.StringIO(text, newline=""), delimiter=";"))
            lyckades = True
            break
        except Exception:
            time.sleep(2 + 3 * forsok)
    if not lyckades:
        return None                      # None = misslyckades, [] = tomt på riktigt
    time.sleep(0.5)                      # var snäll mot FI:s server
    ut = []
    for x in rader:
        ut.append({
            "datum": (x.get("Transaktionsdatum") or "")[:10],
            "bolag": (x.get("Emittent") or "").strip(),
            "person": (x.get("Person i ledande ställning") or "").strip(),
            "befattning": (x.get("Befattning") or "").strip(),
            "typ": (x.get("Karaktär") or "").strip(),
            "volym": ih._tal(x.get("Volym")), "pris": ih._tal(x.get("Pris")),
            "instrument": (x.get("Instrumenttyp") or "").strip(),
            "aktieprogram": (x.get("Är kopplad till aktieprogram") or "").strip().lower()
                            in ("ja", "true", "1"),
            "narstaende": (x.get("Närstående") or "").strip().lower() in ("ja", "true", "1"),
        })
    dk.cache_skriv(nyckel, ut)
    return ut


def hela_historiken(fran: date, till: date, framsteg=None) -> list[dict]:
    alla, a, n, tak, miss = [], fran, 0, 0, 0
    while a < till:
        b = min(a + timedelta(days=20), till)
        bit = hamta_fonster(a, b)
        if bit is None:
            miss += 1
            if framsteg:
                framsteg(f"MISSLYCKADES: {a} .. {b} — perioden saknas i testet")
            bit = []
        alla += bit
        n += 1
        if len(bit) >= 1000:
            tak += 1
        if framsteg and n % 15 == 0:
            framsteg(f"{a} .. {b}: {len(alla)} transaktioner hittills")
        a = b + timedelta(days=1)
    if miss and framsteg:
        framsteg(f"VARNING: {miss} av {n} fönster gick inte att hämta")
    if tak and framsteg:
        framsteg(f"VARNING: {tak} fönster slog i takgränsen 1000 rader — "
                 "de perioderna är ofullständiga")
    return alla


def kor(ar_fran=2020, hall_dagar=182, framsteg=None, antal_slump=300):
    U = {s: m for s, m in un.bygg_universum().items() if m["marknad"] == "Sverige"}
    idag = date.today()

    if framsteg:
        framsteg(f"hämtar FI-registret från {ar_fran - 1}-07-01 i treveckorsfönster")
    alla = hela_historiken(date(ar_fran - 1, 7, 1), idag, framsteg)
    if framsteg:
        framsteg(f"{len(alla)} transaktioner totalt i registret")

    per_bolag = ih.matcha_svenska(alla, U)
    if framsteg:
        framsteg(f"matchade till {len(per_bolag)} av {len(U)} bolag i universumet")

    kurser = {}
    for sym in U:
        k = dk.yahoo_kurser(sym, period="max")
        if len(k):
            kurser[sym] = k

    rader = []
    d = date(ar_fran, 1, 1)
    while d + timedelta(days=hall_dagar) < idag:
        start = (d - timedelta(days=182)).isoformat()
        dagen = d.isoformat()
        slut = (d + timedelta(days=hall_dagar)).isoformat()

        for sym, tr in per_bolag.items():
            if sym not in kurser:
                continue
            fonster = [t for t in tr if start <= t["datum"] < dagen]
            s = ih.sammanfatta(fonster, "Sverige")
            k = kurser[sym]
            k0 = k[k.index <= dagen]
            k1 = k[k.index <= slut]
            if not len(k0) or not len(k1) or k1.index[-1] <= k0.index[-1]:
                continue
            avk = float(k1.iloc[-1]) / float(k0.iloc[-1]) - 1
            netto = s["netto"] if (s["antal_kop"] or s["antal_salj"]) else 0.0
            rader.append({"datum": dagen, "symbol": sym, "netto": netto,
                          "kop": s["antal_kop"], "salj": s["antal_salj"],
                          "tunga": s["tunga_kop"], "avk": avk})
        d = d + timedelta(days=91)

    return analysera(rader, antal_slump, framsteg)


def analysera(rader, antal_slump, framsteg=None):
    if len(rader) < 50:
        return {"fel": f"Bara {len(rader)} observationer — för lite för att testa."}

    per_datum = defaultdict(list)
    for r in rader:
        per_datum[r["datum"]].append(r)

    kop_avk, salj_avk, ingen_avk, alla_avk, tunga_avk = [], [], [], [], []
    per_period = []
    for datum, grupp in sorted(per_datum.items()):
        if len(grupp) < 8:
            continue
        k = [g["avk"] for g in grupp if g["netto"] > 0]
        s = [g["avk"] for g in grupp if g["netto"] < 0]
        i = [g["avk"] for g in grupp if g["netto"] == 0]
        t = [g["avk"] for g in grupp if g["tunga"] > 0]
        a = [g["avk"] for g in grupp]
        kop_avk += k
        salj_avk += s
        ingen_avk += i
        alla_avk += a
        tunga_avk += t
        per_period.append({
            "datum": datum, "antal": len(grupp),
            "kop": float(np.mean(k)) if k else None, "antal_kop": len(k),
            "salj": float(np.mean(s)) if s else None, "antal_salj": len(s),
            "alla": float(np.mean(a)),
        })

    def t_test(a, b):
        if len(a) < 5 or len(b) < 5:
            return None
        s = np.sqrt(np.var(a) / len(a) + np.var(b) / len(b))
        return float((np.mean(a) - np.mean(b)) / s) if s else None

    # Nollkontroll: slumpa vem som "köpte" inom varje period, med samma antal
    # köpare som i verkligheten. Då mäts exakt samma sak, bara utan signal.
    rng = random.Random(20260817)
    slump = []
    for varv in range(antal_slump):
        diffar = []
        for datum, grupp in per_datum.items():
            n_kop = sum(1 for g in grupp if g["netto"] > 0)
            if n_kop < 2 or len(grupp) - n_kop < 2:
                continue
            avk = [g["avk"] for g in grupp]
            rng.shuffle(avk)
            diffar.append(np.mean(avk[:n_kop]) - np.mean(avk))
        if diffar:
            slump.append(float(np.mean(diffar)))
        if framsteg and varv and varv % 100 == 0:
            framsteg(f"nollkontroll {varv}/{antal_slump}")

    verklig = float(np.mean(kop_avk) - np.mean(alla_avk)) if kop_avk else 0.0
    slump = np.array(slump) if len(slump) else np.array([0.0])
    return {
        "observationer": len(rader), "perioder": len(per_period),
        "kop": {"n": len(kop_avk), "snitt": float(np.mean(kop_avk)) if kop_avk else None},
        "salj": {"n": len(salj_avk), "snitt": float(np.mean(salj_avk)) if salj_avk else None},
        "ingen": {"n": len(ingen_avk), "snitt": float(np.mean(ingen_avk)) if ingen_avk else None},
        "tunga": {"n": len(tunga_avk), "snitt": float(np.mean(tunga_avk)) if tunga_avk else None},
        "alla": {"n": len(alla_avk), "snitt": float(np.mean(alla_avk))},
        "overavkastning_kop": verklig,
        "t_kop_mot_salj": t_test(kop_avk, salj_avk),
        "t_kop_mot_ingen": t_test(kop_avk, ingen_avk),
        "nollkontroll": {
            "snitt": float(slump.mean()), "std": float(slump.std()),
            "p95": float(np.percentile(slump, 95)),
            "p_varde": float((slump >= verklig).mean()),
        },
        "per_period": per_period,
        "tid": dk.nu_iso(),
    }


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("\n  Testar insynssignalen mot vår egen data.")
    print("  Svenska bolag, sex månaders hållperiod, nollkontroll mot slumpen.\n")
    f = kor(framsteg=lambda m: print("  ...", m, flush=True))
    if f.get("fel"):
        print("  " + f["fel"])
        sys.exit(0)

    print(f"\n  {f['observationer']} observationer i {f['perioder']} mättillfällen\n")
    print(f"  {'Grupp':30s} {'Antal':>6} {'Avkastning 6 mån':>18}")
    print("  " + "-" * 58)
    for namn, nyckel in [("Nettoköpare", "kop"), ("— varav ledningen köpt", "tunga"),
                         ("Nettosäljare", "salj"), ("Ingen insynshandel", "ingen"),
                         ("Alla bolag", "alla")]:
        g = f[nyckel]
        v = f"{g['snitt'] * 100:+.1f} %" if g["snitt"] is not None else "–"
        print(f"  {namn:30s} {g['n']:>6} {v:>18}")
    print()
    print(f"  Köpare mot alla bolag:  {f['overavkastning_kop'] * 100:+.1f} %-enheter")
    if f["t_kop_mot_salj"] is not None:
        print(f"  t mot säljare:          {f['t_kop_mot_salj']:.2f}")
    if f["t_kop_mot_ingen"] is not None:
        print(f"  t mot ingen handel:     {f['t_kop_mot_ingen']:.2f}")
    n = f["nollkontroll"]
    print(f"  Slumpen ger i snitt:    {n['snitt'] * 100:+.2f} %-enheter "
          f"(95:e percentilen {n['p95'] * 100:+.2f})")
    print(f"  p mot slumpen:          {n['p_varde']:.3f}")
    print()
    dk.cache_skriv("insyn_validering", f)
    print("  Sparat i cache/insyn_validering.json\n")
