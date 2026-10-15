"""
skanning.py — motorn som går igenom hela universumet och bygger caselistan.

Ordningen spelar roll:

  1. Hämta bokslut, kurser och marknadsdata för varje bolag (parallellt).
  2. Räkna alla nyckeltal.
  3. Läsa rapporterna för de amerikanska bolagen.
  4. FÖRST DÄREFTER rangordna — percentiler kräver att alla bolag finns med,
     annars jämförs bolag mot ett urval som råkar vara på plats.
  5. Bygga case av rangordningen.

Steg 4 är hela anledningen till att det här inte kan göras bolag för bolag.
"""

from __future__ import annotations

import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import case as C
import datakallor as dk
import fundamenta as fu
import insynshandel as ih
import matt as M
import rad as rd
import rapportkalender as rk
import rapportlasning as rl
import svenska_rapporter as sv
import universum as un
import intel

HAR = os.path.dirname(os.path.abspath(__file__))
RESULTATFIL = os.path.join(HAR, "skanning_resultat.json")


def las_installningar() -> dict:
    fil = os.path.join(HAR, "installningar.json")
    grund = {
        "profil": "sammansatt",
        "las_rapporter": True,
        "rapportdjup": 3,
        "kapital_kr": 100000,
        # Stödlänkar. Appen är gratis; det här är enda stället den ber om något.
        "stod_bmac": "https://buymeacoffee.com/myriskdashk",
        "stod_paypal": "https://paypal.me/myriskdashboard",
        "grupper": ["karna", "halvledare_ai", "smabolag_global"],
        "egna_bolag": {},
        "sec_kontakt": "",
    }
    if os.path.exists(fil):
        try:
            with open(fil, "r", encoding="utf-8") as f:
                grund.update(json.load(f))
        except Exception:
            pass
    else:
        # Skriv ut standardfilen vid första körningen. Utan det här finns det
        # ingen fil att öppna när man vill ändra något, och inställningarna blir
        # osynliga för den som inte läser källkoden.
        try:
            spara_installningar(grund)
        except Exception:
            pass
    if grund.get("sec_kontakt"):
        dk.KONTAKT = grund["sec_kontakt"]
    return grund


def spara_installningar(d: dict) -> None:
    with open(os.path.join(HAR, "installningar.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------- per bolag --

def samla_bolag(sym: str, meta: dict, las_rapport: bool, rapportdjup: int) -> dict:
    """Allt som går att veta om ett bolag, utan att jämföra med andra."""
    ut = {"symbol": sym, "meta": meta, "fel": None}
    try:
        historik = fu.bokslut(sym, meta)
        if not historik:
            ut["fel"] = "Inga bokslut hittades."
            return ut
        marknad = fu.marknadsdata(sym, meta)
        matt_ = M.alla_matt(historik, marknad, meta["bransch"])
        matt_["ttm"] = fu.ttm(sym)

        rapport = None
        if las_rapport:
            try:
                if meta.get("edgar"):
                    rapport = rl.analysera_bolag(sym, "10-K", rapportdjup)
                    if not rapport.get("tillganglig"):
                        # Utländska bolag noterade i USA lämnar 20-F i stället.
                        rapport = rl.analysera_bolag(sym, "20-F", rapportdjup)
                elif meta.get("marknad") == "Sverige":
                    # Svenska bolag: rapporterna hämtas via MFN i stället, och
                    # jämförs mot samma period föregående år.
                    rapport = sv.analysera_svenskt_bolag(sym, meta["namn"], rapportdjup)
                else:
                    # Varken SEC eller MFN känner bolaget. MFN indexerar bara
                    # svenska emittenter, så att fråga den om ett norskt eller
                    # japanskt bolag ger alltid tomt — och ett tomt svar såg
                    # likadant ut som en rapport som inte gick att läsa.
                    rapport = {"tillganglig": False,
                               "skal": "Ingen rapportkälla för %s — appen läser "
                                       "fulltext bara från SEC (USA) och MFN "
                                       "(Sverige)." % meta.get("marknad", "marknaden")}
            except Exception as e:
                rapport = {"tillganglig": False, "skal": f"Rapportfel: {e}"}

        try:
            kalender = rk.bedomning(sym, marknad.get("kurser"))
        except Exception as e:
            kalender = {"fel": str(e)}

        # Amerikansk insynshandel hämtas per bolag (Form 4). Den svenska ligger
        # i en enda fil för hela marknaden och fylls på efter parallellsteget.
        insyn = None
        if meta.get("edgar"):
            try:
                rader = ih.sec_form4(sym)
                insyn = ih.sammanfatta(rader, "USA")
                insyn["bedomning"] = ih.bedomning(insyn)
            except Exception as e:
                insyn = {"fel": str(e)}

        ut.update({
            "datakonflikter": [f"{b.slut}: {x['matt']} skiljer mer än 5 % mellan SEC och Yahoo (SEC används)" for b in historik[-2:] for x in b.datakonflikter],
            "matt": matt_,
            "rapport": rapport,
            "kalender": kalender,
            "insyn": insyn,
            "historik": [{"slut": b.slut, "publicerad": b.publicerad, "kalla": b.kalla,
                          "valuta": b.valuta, "kallor": fu.kallor_for(b, sym),
                          **{k: b.v(k) for k in
                             fu.FALT}}
                         for b in historik],
            "marknad": {k: v for k, v in marknad.items() if k != "kurser"},
            "kurshistorik": {str(i): float(v) for i, v in
                             marknad["kurser"].iloc[-1300:].items()}
            if marknad.get("kurser") is not None and len(marknad["kurser"]) else {},
        })
    except Exception as e:
        ut["fel"] = f"{type(e).__name__}: {e}"
        ut["spar"] = traceback.format_exc()[-800:]
    return ut


def kompakt_rapport(r: dict | None) -> dict | None:
    """
    Det ur rapportanalysen som ska med i den sparade skanningen.

    Full analys per bolag är megabytes; träfflistan behöver bara slutsatserna.
    Utan det här visar Case-fliken "ingen rapport hittades" för bolag vars
    rapport faktiskt lästes, vilket är sämre än att inte visa något alls.
    """
    if not r or not r.get("tillganglig"):
        return r
    return {
        "tillganglig": True,
        "form": r.get("form"),
        "senaste": r.get("senaste"),
        "foregaende": r.get("foregaende"),
        "avsnitt_hittade": r.get("avsnitt_hittade"),
        "tonlage_hela": r.get("tonlage_hela"),
        "tonlage_risk": r.get("tonlage_risk"),
        "tonlage_vd": r.get("tonlage_vd"),
        "tonlagestrend": r.get("tonlagestrend"),
        "ledningsuttalanden": r.get("ledningsuttalanden", []),
        "forandring_hela": r.get("forandring_hela"),
        "forandring_risk": r.get("forandring_risk"),
        "forandring_vd": r.get("forandring_vd"),
        "roda_flaggor": (r.get("roda_flaggor") or [])[:6],
        "nya_risker": [{"likhet_mot_fjolaret": n["likhet_mot_fjolaret"],
                        "text": n["text"][:600]}
                       for n in (r.get("nya_risker") or [])[:4]],
        "tolkning": rl.tolkning(r),
    }


# --------------------------------------------------------------- helhet --

def skanna(profil: str = "sammansatt", symboler=None, las_rapporter: bool = True,
           rapportdjup: int = 3, framsteg=None, max_tradar: int = 6,
           grupper=None) -> dict:
    inst = las_installningar()
    grupper = grupper or inst.get("grupper") or list(un.GRUPPER)
    U = un.bygg_universum(inst.get("egna_bolag"), grupper=grupper)
    if symboler:
        U = {s: U[s] for s in symboler if s in U}

    t0 = time.time()
    ravaror = {}
    klara = 0
    with ThreadPoolExecutor(max_workers=max_tradar) as pool:
        jobb = {pool.submit(samla_bolag, s, m, las_rapporter, rapportdjup): s
                for s, m in U.items()}
        for f in as_completed(jobb):
            s = jobb[f]
            try:
                ravaror[s] = f.result()
            except Exception as e:
                ravaror[s] = {"symbol": s, "meta": U[s], "fel": str(e)}
            klara += 1
            if framsteg:
                framsteg(klara, len(U), s)

    # Svensk insynshandel: hela marknaden i ett anrop, sedan matchad mot våra
    # bolag. Att hämta den per bolag vore 62 anrop för samma fil.
    try:
        svensk_insyn = ih.matcha_svenska(ih.fi_transaktioner(180), U)
    except Exception:
        svensk_insyn = {}
    for sym, rader in svensk_insyn.items():
        if sym in ravaror and not ravaror[sym].get("fel"):
            sam = ih.sammanfatta(rader, "Sverige")
            sam["bedomning"] = ih.bedomning(sam)
            ravaror[sym]["insyn"] = sam

    # Steg 4: rangordningen kräver hela fältet på plats.
    platta = {}
    for s, r in ravaror.items():
        if r.get("fel") or not r.get("matt"):
            continue
        platta[s] = C.platta_matt(r["matt"], r.get("rapport"))

    # Rangordningen sker INOM gruppen. Se docstringen i case.rangordna.
    # Banker jämförs bara med banker. Deras mått ligger på helt andra nivåer —
    # 6 % eget kapital mot 40 % i verkstad — och blandade i samma rangordning
    # skulle varje bank få bottenbetyg för att den är en bank.
    grupp_av = {}
    for s in platta:
        m = U[s]
        grupp_av[s] = "bank" if m["bransch"] in C.BANKBRANSCHER else m.get("grupp", "karna")
    percentiler = C.rangordna(platta, grupp_av)

    case_lista = []
    for s, p in platta.items():
        r = ravaror[s]
        c = C.bygg_case(s, {**r["meta"], "namn": r["meta"]["namn"]},
                        r["matt"], r.get("rapport"), percentiler[s], profil)
        c["rapport"] = kompakt_rapport(r.get("rapport"))
        c["datakonflikter"] = r.get("datakonflikter", [])
        c["historik"] = r["historik"]
        c["kursdatum"] = max(r.get("kurshistorik") or {}, default=None)
        c["marknadsdata"] = r["marknad"]
        c["datakallor"] = [{"namn": "Yahoo Finance", "hamtad": dk.cache_tid("yf_info_" + s), "typ": "Marknadsdata"},
                              {"namn": "SEC EDGAR / Yahoo", "typ": "Bokslut; se källa per fält"}]
        c["insyn"] = r.get("insyn")
        kal = r.get("kalender") or {}
        # De åtta senaste reaktionerna följer med i den sparade skanningen. De
        # ströks förut för att spara plats, men det är precis den tabellen man
        # vill se när man klickar på ett bolag: gick aktien upp eller ner på
        # förra rapporten, och vad hände de tjugo dagarna efter.
        c["kalender"] = {k: v for k, v in kal.items() if k != "reaktioner"}
        c["kalender"]["reaktioner"] = (kal.get("reaktioner") or [])[-8:]
        c["dagar_till_rapport"] = kal.get("dagar_kvar")
        c["kurs"] = r["marknad"].get("pris")
        c["borsvarde"] = r["marknad"].get("borsvarde")
        c["rapportvaluta"] = r["marknad"].get("rapportvaluta")
        c["grupp"] = U[s].get("grupp", "karna")
        c["jamfordes_mot"] = percentiler[s].get("_jamfordes_mot")
        c["antal_i_jamforelsen"] = percentiler[s].get("_antal_i_jamforelsen")
        c["percentiler"] = percentiler[s]
        case_lista.append(c)

    # Rådet räknas när allt annat är på plats — det behöver varningar,
    # rapportanalys och kalender samtidigt.
    kapital = float(inst.get("kapital_kr") or 100000)
    for c in case_lista:
        c["rad"] = rd.rekommendation(c, kapital)

    case_lista.sort(key=lambda c: (c["poang"] is None, -(c["poang"] or 0)))

    fel = {s: r["fel"] for s, r in ravaror.items() if r.get("fel")}
    modelldom = rk.las_dom()
    resultat = {
        "analysversion": intel.VERSION,
        "tid": dk.nu_iso(),
        "sekunder": round(time.time() - t0, 1),
        "profil": profil,
        "grupper": grupper,
        "gruppnamn": un.GRUPPER,
        "antal_bolag": len(U),
        "antal_bedomda": len(case_lista),
        "antal_med_rapport": sum(1 for c in case_lista if c["har_rapport"]),
        "case": case_lista,
        "rapportmodell": modelldom,
        "fel": fel,
    }
    return resultat


def spara(resultat: dict) -> None:
    lattare = dict(resultat)
    lattare["case"] = [{k: v for k, v in c.items() if k != "percentiler"}
                       for c in resultat["case"]]
    import tempfile
    fd, temporary = tempfile.mkstemp(dir=HAR, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(lattare, f, ensure_ascii=False, default=str)
        os.replace(temporary, RESULTATFIL)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    intel.snapshot(lattare)
    intel.evaluate()


def las_sparat() -> dict | None:
    if not os.path.exists(RESULTATFIL):
        return None
    try:
        with open(RESULTATFIL, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def detaljer(sym: str, profil: str = "sammansatt", las_rapport: bool = True,
             rapportdjup: int = 3) -> dict:
    """
    Djupdykning i ett bolag. Percentilerna hämtas från den senaste skanningen
    så att bolaget jämförs mot samma fält som i träfflistan — annars skulle
    siffrorna i djupdykningen inte stämma med dem i listan.
    """
    inst = las_installningar()
    U = un.bygg_universum(inst.get("egna_bolag"))
    if sym not in U:
        return {"fel": f"{sym} finns inte i universumet."}
    r = samla_bolag(sym, U[sym], las_rapport, rapportdjup)
    if r.get("fel"):
        return {"fel": r["fel"]}

    platt = C.platta_matt(r["matt"], r.get("rapport"))
    sparat = las_sparat()
    if sparat:
        # Use exactly the same metric set and peer grouping as the full scan,
        # including bank-specific metrics. Replace this company's old numbers.
        comparison = {x["symbol"]: x.get("matt") or {} for x in sparat["case"]}
        comparison[sym] = platt
        groups = {x["symbol"]: "bank" if x.get("bransch") in C.BANKBRANSCHER
                  else x.get("grupp", "karna") for x in sparat["case"]}
        groups[sym] = "bank" if U[sym]["bransch"] in C.BANKBRANSCHER else U[sym].get("grupp", "karna")
        perc = C.rangordna(comparison, groups)[sym]
    else:
        perc = C.rangordna({sym: platt})[sym]

    c = C.bygg_case(sym, U[sym], r["matt"], r.get("rapport"), perc, profil)
    c["datakonflikter"] = r.get("datakonflikter", [])
    c["historik"] = r["historik"]
    c["kurshistorik"] = r["kurshistorik"]
    c["marknad"] = r["marknad"]
    c["marknadsdata"] = r["marknad"]
    c["kursdatum"] = max(r.get("kurshistorik") or {}, default=None)
    c["kurs"] = r["marknad"].get("pris")
    c["borsvarde"] = r["marknad"].get("borsvarde")
    c["rapportvaluta"] = r["marknad"].get("rapportvaluta")
    c["rapport"] = r.get("rapport")
    c["percentiler"] = perc
    c["ttm"] = (r["matt"] or {}).get("ttm")
    c["grupp"] = U[sym].get("grupp", "karna")
    c["kalender"] = r.get("kalender")
    c["insyn"] = r.get("insyn")
    return c


# ----------------------------------------------------------- terminalen --

def _skriv_ut(res: dict, antal: int = 25) -> None:
    print()
    print(f"  Skannade {res['antal_bolag']} bolag på {res['sekunder']} s. "
          f"{res['antal_bedomda']} kunde bedömas, {res['antal_med_rapport']} "
          f"med läst årsredovisning.")
    print(f"  Profil: {res['profil']}")
    print()
    print(f"  {'#':>3}  {'Bolag':<26} {'Poäng':>6} {'Täck':>5}  {'Kval':>5} "
          f"{'Värd':>5} {'Fin':>5} {'Tillv':>5} {'Rapp':>5}  Varningar")
    print("  " + "-" * 104)
    for i, c in enumerate(res["case"][:antal], 1):
        p = c["pelare"]

        def q(n):
            v = p.get(n, {}).get("poang")
            return f"{v:5.0f}" if v is not None else "    –"
        varn = ", ".join(v["rubrik"] for v in c["varningar"]) or "–"
        if c.get("otillracklig_tackning"):
            varn = "för lite av modellen går att räkna för branschen"
        poang = f"{c['poang']:6.1f}" if c["poang"] is not None else "     -"
        print(f"  {i:>3}  {c['namn'][:26]:<26} {poang} "
              f"{c['tackning'] * 100:4.0f}%  {q('Kvalitet')} {q('Värdering')} "
              f"{q('Finansiell styrka')} {q('Tillväxt')} {q('Rapportsignaler')}  {varn[:40]}")
    print()
    if res["fel"]:
        print(f"  {len(res['fel'])} bolag kunde inte hämtas: "
              f"{', '.join(list(res['fel'])[:8])}")
        print()


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    inst = las_installningar()
    argument = [a for a in sys.argv[1:] if not a.startswith("--")]
    profil = argument[0] if argument else inst.get("profil", "sammansatt")
    grupper = None
    if "--karna" in sys.argv:
        grupper = ["karna"]
    elif "--ai" in sys.argv:
        grupper = ["halvledare_ai"]
    print(f"\n  Börscase — skannar universumet med profilen '{profil}'.")
    print("  Första körningen tar några minuter (allt cachas sedan).\n")

    def visa(n, av, sym):
        print(f"\r  {n:>3}/{av}  {sym:<12}", end="", flush=True)

    res = skanna(profil=profil, framsteg=visa, grupper=grupper)
    spara(res)
    _skriv_ut(res)
    print(f"  Sparat i {RESULTATFIL}")
    print("  Öppna appen med STARTA_APP.bat för att gräva vidare.\n")
