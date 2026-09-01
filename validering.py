"""
validering.py — testet som avgör om resten av appen är värd något.

En rangordning som ingen prövat är bara en åsikt med decimaler. Det här
skriptet prövar den, och är byggt för att kunna underkänna sin egen app.

PROTOKOLLET

  * Varje 30 juni, år för år, ställs frågan: hur hade modellen rangordnat
    bolagen med ENBART den information som fanns publicerad då?
  * "Publicerad då" är bokstavligt. SEC:s XBRL innehåller `filed`-datum för
    varje siffra, och bara siffror med filed <= rangordningsdagen används.
    Ett bokslut för 2019 som lämnades in i februari 2020 finns alltså inte i
    universumet den 30 juni 2019.
  * Börsvärdet räknas med OJUSTERAD kurs den dagen gånger antalet aktier i den
    då senast inlämnade rapporten. Använder man justerade kurser blir gamla
    P/E-tal fel med splitfaktorn.
  * Avkastningen mäts på justerade kurser tolv månader framåt.
  * Bolagen delas i femtedelar efter poäng. Vi mäter om högsta femtedelen slog
    lägsta och slog snittet.

NOLLKONTROLLEN

  Samma sak görs med SLUMPMÄSSIGA poäng, 300 gånger. Om modellens resultat
  ryms inom vad slumpen producerar är modellen inte bättre än att singla slant,
  hur fin tabellen än ser ut. Det är exakt det testet som fällde den tidigare
  trendappen i mappen `boliden`, och det ska få fälla den här också om det ska.

BEGRÄNSNINGAR (läs dem, de är inte små)

  * Bara amerikanska bolag. Svenska bolag saknar öppna filing-datum.
  * Överlevnadsbias: universumet består av bolag som finns idag. Bolag som gick
    under finns inte med, vilket gör ALLA resultat glädjande.
  * Pelaren Rapportsignaler ingår bara om du kör med --rapporter (då laddas
    hundratals årsredovisningar ner; det tar tid men cachas).
  * Runt 80 bolag och ~12 år är ungefär 900 observationer med kraftig
    korrelation inom varje år. Det räcker inte för starka påståenden.
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import date, timedelta

import numpy as np

import case as C
import datakallor as dk
import fundamenta as fu
import matt as M
import rapportlasning as rl
import universum as un

HAR = os.path.dirname(os.path.abspath(__file__))
RESULTAT = os.path.join(HAR, "validering_resultat.json")


# ------------------------------------------------------- point-in-time ----

def bokslut_pit(alla, datum: str):
    """Bokslut som var publicerade senast `datum`. Utan detta filter är allt fusk."""
    return [b for b in alla if b.publicerad and b.publicerad <= datum]


def kurs_vid(serie, datum: str):
    if serie is None or not len(serie):
        return None
    fore = serie[serie.index <= datum]
    return float(fore.iloc[-1]) if len(fore) else None


def matt_pit(sym, meta, alla_bokslut, datum, just, ojust, rapportlikhet=None):
    """Nyckeltal som de sett ut den dagen, med den dagens kurs och då kända siffror."""
    hist = bokslut_pit(alla_bokslut, datum)
    if len(hist) < 2:
        return None
    b = hist[-1]
    aktier = b.v("aktier_utspadda") or b.v("aktier_ute")
    pris_ojust = kurs_vid(ojust, datum)
    if not aktier or not pris_ojust:
        return None
    borsvarde = aktier * pris_ojust

    kurser_da = just[just.index <= datum] if just is not None else None
    marknad = {"borsvarde": borsvarde, "kurser": kurser_da,
               "beta": None, "utdelning_procent": None,
               "rapportvaluta": "USD"}
    m = M.alla_matt(hist, marknad, meta["bransch"])
    platt = C.platta_matt(m, None)
    if rapportlikhet is not None:
        platt["rapport_likhet_risk"] = rapportlikhet.get("risk")
        platt["rapport_likhet_vd"] = rapportlikhet.get("vd")
        platt["rapport_negativitet"] = rapportlikhet.get("negativitet")
        platt["rapport_osakerhet"] = rapportlikhet.get("osakerhet")
        platt["rapport_flaggvikt"] = rapportlikhet.get("flaggvikt")
        platt["rapport_tillganglig"] = rapportlikhet.get("risk") is not None
    return platt


def rapportmatt_per_ar(sym: str, ar_lista: list[int]) -> dict:
    """
    Lazy Prices-måtten historiskt. Kräver att varje års 10-K laddas ner —
    därför frivilligt. Nycklas på det år rapporten lämnades in.
    """
    ut = {}
    try:
        rapporter = rl.hamta_rapporter(sym, "10-K", antal=max(len(ar_lista) + 2, 12))
    except Exception:
        return ut
    rapporter = sorted(rapporter, key=lambda r: r["datum"])
    for i, r in enumerate(rapporter):
        if i == 0:
            continue
        risk_nu = rl.hitta_avsnitt(r["text"], "riskfaktorer")
        risk_fo = rl.hitta_avsnitt(rapporter[i - 1]["text"], "riskfaktorer")
        mda_nu = rl.hitta_avsnitt(r["text"], "vd_analys")
        mda_fo = rl.hitta_avsnitt(rapporter[i - 1]["text"], "vd_analys")
        fr = rl.sprakforandring(risk_nu, risk_fo)
        fv = rl.sprakforandring(mda_nu, mda_fo)
        ton = rl.tonlage(risk_nu) if risk_nu else {}
        flaggor = rl.roda_flaggor(r["text"])
        ut[r["datum"]] = {
            "risk": fr and fr["cosinuslikhet"],
            "vd": fv and fv["cosinuslikhet"],
            "negativitet": ton.get("negativa_pct"),
            "osakerhet": ton.get("osakerhet_pct"),
            "flaggvikt": float(sum(f["vikt"] for f in flaggor)),
        }
    return ut


def senaste_rapport_fore(rapportdata: dict, datum: str):
    kandidater = [d for d in rapportdata if d <= datum]
    return rapportdata[max(kandidater)] if kandidater else None


# ------------------------------------------------------------- testet ----

def kor(ar_fran: int = 2013, ar_till: int | None = None, profil: str = "sammansatt_utan_rapport",
        las_rapporter: bool = False, antal_slump: int = 300, framsteg=None) -> dict:
    U = {s: m for s, m in un.bygg_universum().items() if m.get("edgar")}
    idag = date.today()
    ar_till = ar_till or (idag.year - 1)

    if framsteg:
        framsteg("hämtar bokslut och kurser för {} bolag".format(len(U)))

    data = {}
    for i, (sym, meta) in enumerate(U.items(), 1):
        try:
            bs = fu.bokslut_edgar(sym)
            if len(bs) < 4:
                continue
            just = dk.yahoo_kurser(sym, period="max")
            ojust = dk.yahoo_kurser(sym, period="max", justerade=False)
            if not len(just):
                continue
            rap = {}
            if las_rapporter:
                rap = rapportmatt_per_ar(sym, list(range(ar_fran, ar_till + 1)))
            data[sym] = {"meta": meta, "bokslut": bs, "just": just,
                         "ojust": ojust, "rapport": rap}
        except Exception:
            continue
        if framsteg and i % 10 == 0:
            framsteg(f"{i}/{len(U)} bolag inlästa")

    ar_rader = []
    alla_par = []          # (poäng, framtida avkastning, år)

    for ar in range(ar_fran, ar_till + 1):
        dagen = f"{ar}-06-30"
        slutdag = (date(ar, 6, 30) + timedelta(days=365)).isoformat()
        if slutdag > idag.isoformat():
            break

        platta = {}
        avkastning = {}
        for sym, d_ in data.items():
            rl_matt = senaste_rapport_fore(d_["rapport"], dagen) if las_rapporter else None
            p = matt_pit(sym, d_["meta"], d_["bokslut"], dagen,
                         d_["just"], d_["ojust"], rl_matt)
            if p is None:
                continue
            k0 = kurs_vid(d_["just"], dagen)
            k1 = kurs_vid(d_["just"], slutdag)
            if not k0 or not k1:
                continue
            platta[sym] = p
            avkastning[sym] = k1 / k0 - 1

        if len(platta) < 20:
            continue

        perc = C.rangordna(platta)
        poang = {}
        for sym, p in platta.items():
            pel = C.pelarpoang(perc[sym])
            varn = C.varningar_for(p, None)
            t = C.total(pel, varn, profil, har_rapport=bool(p.get("rapport_tillganglig")))
            if t["poang"] is not None and t["tackning"] >= 0.6:
                poang[sym] = t["poang"]

        if len(poang) < 20:
            continue

        rader = sorted(poang.items(), key=lambda x: -x[1])
        n = len(rader)
        femtedel = max(3, n // 5)
        topp = [avkastning[s] for s, _ in rader[:femtedel]]
        botten = [avkastning[s] for s, _ in rader[-femtedel:]]
        snitt = float(np.mean([avkastning[s] for s, _ in rader]))

        ar_rader.append({
            "ar": ar,
            "antal": n,
            "topp_femtedel": float(np.mean(topp)),
            "botten_femtedel": float(np.mean(botten)),
            "universum": snitt,
            "topp_minus_botten": float(np.mean(topp) - np.mean(botten)),
            "topp_minus_universum": float(np.mean(topp) - snitt),
            "spearman": _spearman([p for _, p in rader], [avkastning[s] for s, _ in rader]),
            "basta": rader[0][0], "samsta": rader[-1][0],
        })
        alla_par += [(poang[s], avkastning[s], ar) for s in poang]
        if framsteg:
            framsteg(f"{ar}: {n} bolag, topp {np.mean(topp)*100:.1f} % "
                     f"mot universum {snitt*100:.1f} %")

    if not ar_rader:
        return {"fel": "För lite data för att testa. Kör en skanning först."}

    facit = {
        "ar": ar_rader,
        "snitt_topp": float(np.mean([r["topp_femtedel"] for r in ar_rader])),
        "snitt_botten": float(np.mean([r["botten_femtedel"] for r in ar_rader])),
        "snitt_universum": float(np.mean([r["universum"] for r in ar_rader])),
        "snitt_overavkastning": float(np.mean([r["topp_minus_universum"] for r in ar_rader])),
        "andel_ar_over": float(np.mean([1.0 if r["topp_minus_universum"] > 0 else 0.0
                                        for r in ar_rader])),
        "snitt_spearman": float(np.mean([r["spearman"] for r in ar_rader
                                         if r["spearman"] is not None])),
        "antal_ar": len(ar_rader),
        "antal_observationer": len(alla_par),
        "profil": profil,
        "med_rapportsignaler": las_rapporter,
    }

    facit["nollkontroll"] = nollkontroll(alla_par, facit["snitt_overavkastning"],
                                         antal_slump, framsteg)
    facit["dom"] = fall_dom(facit)
    facit["tid"] = dk.nu_iso()
    return facit


def _spearman(a, b):
    if len(a) < 5:
        return None
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    if ra.std() == 0 or rb.std() == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def nollkontroll(par, verkligt, antal=300, framsteg=None) -> dict:
    """
    Samma protokoll, slumpmässiga poäng. Ger fördelningen av vad ren tur
    producerar med exakt samma antal bolag, år och avkastningar.
    """
    per_ar = {}
    for poang, avk, ar in par:
        per_ar.setdefault(ar, []).append(avk)

    slumputfall = []
    rng = random.Random(20260813)
    for i in range(antal):
        overavk = []
        for ar, avkastningar in per_ar.items():
            blandad = avkastningar[:]
            rng.shuffle(blandad)
            n = len(blandad)
            femtedel = max(3, n // 5)
            overavk.append(float(np.mean(blandad[:femtedel]) - np.mean(blandad)))
        slumputfall.append(float(np.mean(overavk)))
        if framsteg and i and i % 100 == 0:
            framsteg(f"nollkontroll {i}/{antal}")

    slumputfall = np.array(slumputfall)
    battre_an = float((slumputfall < verkligt).mean() * 100)
    return {
        "antal_omgangar": antal,
        "slump_snitt": float(slumputfall.mean()),
        "slump_std": float(slumputfall.std()),
        "slump_p95": float(np.percentile(slumputfall, 95)),
        "slump_p99": float(np.percentile(slumputfall, 99)),
        "verkligt": verkligt,
        "percentil": battre_an,
        "p_varde": float((slumputfall >= verkligt).mean()),
    }


def fall_dom(f: dict) -> dict:
    """
    Fyra krav. Alla måste uppfyllas för att modellen ska få kallas belagd.
    Kraven är satta i förväg, inte efter att jag sett resultatet.
    """
    n = f["nollkontroll"]
    krav = [
        {"krav": "Toppfemtedelen slog universumet i snitt",
         "uppfyllt": f["snitt_overavkastning"] > 0,
         "varde": f"{f['snitt_overavkastning'] * 100:+.1f} %-enheter/år"},
        {"krav": "Slog universumet fler år än inte",
         "uppfyllt": f["andel_ar_over"] > 0.5,
         "varde": f"{f['andel_ar_over'] * 100:.0f} % av {f['antal_ar']} år"},
        {"krav": "Toppfemtedelen slog bottenfemtedelen",
         "uppfyllt": f["snitt_topp"] > f["snitt_botten"],
         "varde": f"{f['snitt_topp'] * 100:.1f} % mot {f['snitt_botten'] * 100:.1f} %"},
        {"krav": "Positiv rangkorrelation mellan poäng och utfall",
         "uppfyllt": (f["snitt_spearman"] or 0) > 0.05,
         "varde": f"Spearman {f['snitt_spearman']:+.3f}"},
        {"krav": "Utanför vad slumpen ger (p < 0,05)",
         "uppfyllt": n["p_varde"] < 0.05,
         "varde": f"p = {n['p_varde']:.3f}, percentil {n['percentil']:.0f}"},
    ]
    godkand = all(k["uppfyllt"] for k in krav)

    # Det mest avslöjande enskilda utfallet: om botten också slår snittet är
    # sambandet inte monotont, och då mäter poängen något annat än "bättre".
    extra = ""
    if f["snitt_botten"] > f["snitt_universum"]:
        extra = (" OBS: bottenfemtedelen slog också universumet "
                 f"({f['snitt_botten'] * 100:.1f} % mot {f['snitt_universum'] * 100:.1f} %). "
                 "Både högt och lågt betyg gick bättre än mitten — det ser mer ut som "
                 "att modellen plockar ut bolag som RÖR SIG mycket än bolag som går bra.")

    if godkand:
        text = ("Modellen klarade alla fyra kraven på ur-provs-data. Det betyder "
                "att rangordningen haft ETT SAMBAND med efterföljande avkastning i "
                "det här universumet och den här perioden. Det är inte samma sak som "
                "att den kommer fortsätta ha det, och överlevnadsbias gör siffran "
                "för snäll." + extra)
    else:
        fallna = [k["krav"] for k in krav if not k["uppfyllt"]]
        text = ("Modellen föll på: " + "; ".join(fallna) + ". Poängen ska då läsas "
                "som en STRUKTURERAD SAMMANFATTNING av bolagens siffror, inte som "
                "en prognos. Den är fortfarande användbar för att hitta bolag att "
                "läsa på om — men den har inte visat att den kan rangordna framtida "
                "avkastning." + extra)
    return {"krav": krav, "godkand": godkand, "text": text}


HUVUDPROFIL = "sammansatt_utan_rapport"
TAVLAN = os.path.join(HAR, "valideringstavla.json")


def spara(f):
    """
    Varje testad profil sparas för sig, OCH som en rad på resultattavlan.

    Skälet: förut skrev varje ny körning över den förra, så testet av
    rapporttexten raderade testet av huvudmodellen. Då kan man inte se
    helheten — och helheten är själva poängen. En modell som testats sju gånger
    och fallit sju gånger säger något helt annat än en som testats en gång.
    """
    profil = f.get("profil", "okand")
    with open(os.path.join(HAR, f"validering_{profil}.json"), "w", encoding="utf-8") as fil:
        json.dump(f, fil, ensure_ascii=False, default=str)
    if profil == HUVUDPROFIL:
        with open(RESULTAT, "w", encoding="utf-8") as fil:
            json.dump(f, fil, ensure_ascii=False, default=str)

    tavla = las_tavla()
    tavla[profil] = {
        "profil": profil,
        "antal_ar": f["antal_ar"],
        "antal_observationer": f["antal_observationer"],
        "topp": f["snitt_topp"],
        "botten": f["snitt_botten"],
        "universum": f["snitt_universum"],
        "overavkastning": f["snitt_overavkastning"],
        "topp_minus_botten": f["snitt_topp"] - f["snitt_botten"],
        "spearman": f["snitt_spearman"],
        "p_varde": f["nollkontroll"]["p_varde"],
        "godkand": f["dom"]["godkand"],
        "med_rapportsignaler": f.get("med_rapportsignaler", False),
        "tid": f.get("tid"),
    }
    with open(TAVLAN, "w", encoding="utf-8") as fil:
        json.dump(tavla, fil, ensure_ascii=False, indent=1, default=str)


def las_tavla() -> dict:
    if not os.path.exists(TAVLAN):
        return {}
    try:
        with open(TAVLAN, "r", encoding="utf-8") as fil:
            return json.load(fil)
    except Exception:
        return {}


def las_sparat():
    if not os.path.exists(RESULTAT):
        return None
    try:
        with open(RESULTAT, "r", encoding="utf-8") as fil:
            return json.load(fil)
    except Exception:
        return None


def skriv_ut(f):
    if f.get("fel"):
        print("  " + f["fel"])
        return
    print()
    print(f"  VALIDERING — {f['antal_ar']} år, {f['antal_observationer']} observationer, "
          f"profil '{f['profil']}'"
          + (", rapportsignaler MED" if f["med_rapportsignaler"] else ""))
    print()
    print(f"  {'År':>5} {'Bolag':>6} {'Topp 20%':>10} {'Botten 20%':>11} "
          f"{'Universum':>10} {'Topp−Univ':>10} {'Spearman':>9}")
    print("  " + "-" * 68)
    for r in f["ar"]:
        print(f"  {r['ar']:>5} {r['antal']:>6} {r['topp_femtedel'] * 100:>9.1f}% "
              f"{r['botten_femtedel'] * 100:>10.1f}% {r['universum'] * 100:>9.1f}% "
              f"{r['topp_minus_universum'] * 100:>+9.1f}% "
              f"{(r['spearman'] if r['spearman'] is not None else float('nan')):>+9.3f}")
    print("  " + "-" * 68)
    print(f"  {'SNITT':>5} {'':>6} {f['snitt_topp'] * 100:>9.1f}% "
          f"{f['snitt_botten'] * 100:>10.1f}% {f['snitt_universum'] * 100:>9.1f}% "
          f"{f['snitt_overavkastning'] * 100:>+9.1f}% {f['snitt_spearman']:>+9.3f}")
    n = f["nollkontroll"]
    print()
    print(f"  NOLLKONTROLL ({n['antal_omgangar']} omgångar slumpmässiga poäng)")
    print(f"    Slumpens överavkastning:  {n['slump_snitt'] * 100:+.2f} %-enheter "
          f"(std {n['slump_std'] * 100:.2f}, 95:e percentilen {n['slump_p95'] * 100:+.2f})")
    print(f"    Modellens:                {n['verkligt'] * 100:+.2f} %-enheter")
    print(f"    Modellen slår {n['percentil']:.0f} % av slumpen. p = {n['p_varde']:.3f}")
    print()
    print("  DOM")
    for k in f["dom"]["krav"]:
        print(f"    [{'JA ' if k['uppfyllt'] else 'NEJ'}] {k['krav']:<48} {k['varde']}")
    print()
    for rad in _radbryt(f["dom"]["text"], 76):
        print("    " + rad)
    print()


def _radbryt(text, bredd):
    ord_, rad, ut = text.split(), "", []
    for o in ord_:
        if len(rad) + len(o) + 1 > bredd:
            ut.append(rad)
            rad = o
        else:
            rad = (rad + " " + o).strip()
    if rad:
        ut.append(rad)
    return ut


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    med_rapporter = "--rapporter" in sys.argv
    profil = "sammansatt" if med_rapporter else "sammansatt_utan_rapport"
    for a in sys.argv[1:]:
        if a in C.PROFILER:
            profil = a

    print("\n  Börscase — ärlig validering.")
    print("  Point-in-time via SEC:s filing-datum. Bara amerikanska bolag.")
    if med_rapporter:
        print("  MED rapportsignaler: laddar ner ~800 årsredovisningar första gången.")
    print()

    def visa(m):
        print(f"  ... {m}", flush=True)

    f = kor(profil=profil, las_rapporter=med_rapporter, framsteg=visa)
    if not f.get("fel"):
        spara(f)
    skriv_ut(f)
    print(f"  Sparat i {RESULTAT}\n" if not f.get("fel") else "")
