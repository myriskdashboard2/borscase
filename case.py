"""
case.py — från nyckeltal till ett case, och från ett case till dess motbevis.

Ett "case" här är inte en köprekommendation. Det är en påstådd anledning till
att ett bolag är intressant, tillsammans med de siffror påståendet vilar på och
— viktigast — de exakta villkor som skulle göra påståendet fel.

Modellen är avsiktligt tråkig:

  * Varje mått rangordnas mot de andra bolagen (percentil 0-100). Absoluta
    gränsvärden åldras, rangordningar gör det inte.
  * Måtten grupperas i pelare. Varje pelare får ett snitt av sina percentiler.
  * Totalpoängen är ett viktat snitt av pelarna, omnormerat efter hur stor del
    av modellen som faktiskt gick att beräkna. Ett bolag där halva modellen
    saknar data får inte låtsas ha samma säkerhet som ett där allt finns —
    därför redovisas `tackning` alltid bredvid poängen.
  * Varningsflaggor drar av poäng direkt, inte via percentil. En Beneish-flagga
    ska inte kunna vägas upp av en fin bruttomarginal.

Vikterna är MINA val, inte naturlagar. Därför finns validering.py, som testar
om rangordningen faktiskt haft något med framtida avkastning att göra.
"""

from __future__ import annotations

import numpy as np

import matt as M

# ---------------------------------------------------------------------------
# Pelare: (fältnamn, riktning, vikt inom pelaren, etikett, enhet)
# riktning +1 = högre är bättre, -1 = lägre är bättre
# ---------------------------------------------------------------------------
PELARE = {
    "Kvalitet": [
        ("bruttolonsamhet", +1, 1.0, "Bruttovinst / tillgångar", "kvot"),
        ("roic", +1, 1.5, "Avkastning på investerat kapital", "procent"),
        ("roic_5ar", +1, 1.0, "ROIC, snitt 5 år", "procent"),
        ("greenblatt_roc", +1, 1.0, "Avkastning på rörelsekapital", "procent"),
        ("kassagenerering", +1, 1.0, "Kassaflöde / vinst", "kvot"),
        ("rorelsemarginal", +1, 0.8, "Rörelsemarginal", "procent"),
        ("marginalstabilitet", -1, 0.7, "Marginalens svängning", "kvot"),
    ],
    "Värdering": [
        ("ebit_ev", +1, 1.5, "Rörelseresultat / företagsvärde", "procent"),
        ("fcf_yield", +1, 1.5, "Fritt kassaflöde / företagsvärde", "procent"),
        ("ev_ebitda", -1, 1.0, "Företagsvärde / EBITDA", "gånger"),
        ("pe", -1, 0.8, "P/E", "gånger"),
        ("pb", -1, 0.5, "P/B", "gånger"),
    ],
    "Finansiell styrka": [
        ("piotroski_poang", +1, 1.5, "Piotroski F-score", "poäng"),
        ("altman_z", +1, 1.2, "Altman Z''", "poäng"),
        ("soliditet", +1, 0.8, "Soliditet", "procent"),
        ("nettoskuld_ebitda", -1, 1.2, "Nettoskuld / EBITDA", "gånger"),
        ("rantetackning", +1, 0.8, "Räntetäckningsgrad", "gånger"),
    ],
    "Tillväxt": [
        ("tillvaxt_3ar", +1, 1.2, "Omsättningstillväxt 3 år", "procent"),
        ("vinsttillvaxt_3ar", +1, 1.0, "Vinsttillväxt 3 år", "procent"),
        ("fcf_tillvaxt_3ar", +1, 1.0, "Kassaflödestillväxt 3 år", "procent"),
        ("marginaltrend", +1, 0.8, "Marginaltrend", "kvot"),
    ],
    "Marknad": [
        ("momentum_12_1", +1, 1.2, "Momentum 12-1 månader", "procent"),
        ("avstand_till_arstopp", +1, 0.5, "Avstånd till årstopp", "procent"),
        ("volatilitet", -1, 0.5, "Volatilitet", "procent"),
    ],
    "Rapportsignaler": [
        ("rapport_likhet_risk", +1, 1.5, "Riskavsnittets likhet mot fjolåret", "kvot"),
        ("rapport_likhet_vd", +1, 0.8, "Vd-analysens likhet mot fjolåret", "kvot"),
        ("rapport_negativitet", -1, 1.0, "Negativa ord i riskavsnittet", "procent"),
        ("rapport_osakerhet", -1, 0.8, "Osäkerhetsord i riskavsnittet", "procent"),
        ("rapport_flaggvikt", -1, 1.5, "Röda flaggor, sammanlagd vikt", "poäng"),
    ],
}

# Egen pelaruppsättning för banker. Samma fem rubriker, andra mått bakom dem —
# annars står Swedbank med 40 % täckning och nästan tomma kolumner, trots att
# det finns gott om siffror att bedöma en bank på.
PELARE_BANK = {
    "Kvalitet": [
        ("roe", +1, 1.5, "Avkastning på eget kapital", "procent"),
        ("ki_tal", -1, 1.5, "K/I-tal (kostnad delat med intäkt)", "kvot"),
        ("ki_trend", -1, 0.8, "K/I-talets trend", "kvot"),
        ("roa", +1, 1.0, "Avkastning på tillgångar", "procent"),
        ("rantenetto_marginal", +1, 0.8, "Räntenetto / tillgångar", "procent"),
        ("intaktsdiversifiering", +1, 0.6, "Andel intäkter utanför räntenettot", "procent"),
    ],
    "Värdering": [
        ("pb", -1, 1.5, "P/B", "gånger"),
        ("pe", -1, 1.2, "P/E", "gånger"),
        ("direktavkastning", +1, 0.8, "Direktavkastning", "procent"),
    ],
    "Finansiell styrka": [
        ("kapitalstyrka", +1, 1.5, "Eget kapital / tillgångar", "procent"),
        ("tillgangstillvaxt", -1, 0.8, "Balansräkningens tillväxt", "procent"),
    ],
    "Tillväxt": [
        ("tillvaxt_3ar", +1, 1.2, "Intäktstillväxt 3 år", "procent"),
        ("vinsttillvaxt_3ar", +1, 1.0, "Vinsttillväxt 3 år", "procent"),
    ],
    "Marknad": [
        ("momentum_12_1", +1, 1.2, "Momentum 12-1 månader", "procent"),
        ("avstand_till_arstopp", +1, 0.5, "Avstånd till årstopp", "procent"),
        ("volatilitet", -1, 0.5, "Volatilitet", "procent"),
    ],
    "Rapportsignaler": PELARE["Rapportsignaler"],
}

BANKBRANSCHER = {"Bank"}


def pelare_for(bransch: str) -> dict:
    return PELARE_BANK if bransch in BANKBRANSCHER else PELARE


PROFILER = {
    "sammansatt": {"Kvalitet": 1.0, "Värdering": 1.0, "Finansiell styrka": 1.0,
                   "Tillväxt": 0.7, "Marknad": 0.5, "Rapportsignaler": 0.8},
    "kvalitet": {"Kvalitet": 2.0, "Värdering": 0.6, "Finansiell styrka": 1.2,
                 "Tillväxt": 1.0, "Marknad": 0.4, "Rapportsignaler": 0.8},
    "varde": {"Kvalitet": 0.8, "Värdering": 2.0, "Finansiell styrka": 1.4,
              "Tillväxt": 0.3, "Marknad": 0.3, "Rapportsignaler": 0.8},
    "sammansatt_utan_rapport": {"Kvalitet": 1.0, "Värdering": 1.0,
                                "Finansiell styrka": 1.0, "Tillväxt": 0.7,
                                "Marknad": 0.5},
    # En pelare i taget. Finns det signal någonstans måste den synas här — och
    # om ingen enskild pelare bär något är sammanvägningen av dem bara ett
    # snyggare sätt att blanda brus.
    "bara_kvalitet": {"Kvalitet": 1.0},
    "bara_vardering": {"Värdering": 1.0},
    "bara_styrka": {"Finansiell styrka": 1.0},
    "bara_tillvaxt": {"Tillväxt": 1.0},
    "bara_marknad": {"Marknad": 1.0},
    # Rapporttexten helt för sig. Blandas den med de fem pelare som redan
    # underkänts går det inte att se om texten bär något eget.
    "bara_rapport": {"Rapportsignaler": 1.0},
}

# Under den här andelen av modellen sätts ingen poäng alls. Se `total`.
MINSTA_TACKNING = 0.35

# Avdrag i poäng (0-100-skalan) när något ser direkt fel ut.
VARNINGAR = [
    ("beneish_flagga", 12, "Beneish M-score över tröskeln",
     "Redovisningen liknar statistiskt de bolag som manipulerat sina siffror. "
     "Det är inte ett bevis — snabbväxare med förvärv triggar modellen oskyldigt — "
     "men det betyder att noterna måste läsas."),
    ("accruals_hog", 8, "Höga periodiseringar",
     "Vinsten består till stor del av bokföringsposter i stället för kontanter "
     "(Sloan 1996). Historiskt sämre avkastning året efter."),
    ("tillgangstillvaxt_hog", 6, "Balansräkningen växer snabbt",
     "Över 30 % tillgångstillväxt på ett år. Cooper, Gulen & Schill (2008): "
     "expansion sker oftast när optimismen toppar."),
    ("utspadning", 6, "Utspädning pågår",
     "Antalet aktier har ökat mer än 3 % på ett år. Din andel av bolaget krymper."),
    ("altman_nod", 10, "Altman Z'' i nödzonen",
     "Under 1,1. Konkursrisken är statistiskt förhöjd."),
    ("piotroski_svag", 8, "Piotroski 3 eller lägre",
     "Bolaget misslyckas med de flesta av de nio grundläggande hälsokontrollerna."),
    ("rapport_omskriven", 8, "Riskavsnittet kraftigt omskrivet",
     "Cosinuslikheten mot fjolårets riskavsnitt är under 0,85. Enligt Lazy Prices "
     "(Cohen, Malloy & Nguyen 2020) har stora textändringar följts av svagare "
     "avkastning."),
    ("gaende_bolag", 25, "Går-vidare-tvivel i rapporten",
     "Revisorn har uttryckt betydande tvivel om bolagets fortlevnad. Det här är "
     "inte en flagga, det är en brandvarnare."),
]


def platta_matt(m: dict, rapport: dict | None) -> dict:
    """
    Gör om den nästlade måttdicten till platta tal som går att rangordna.
    Här — och bara här — översätts rapportanalysen till siffror.
    """
    p = dict(m)
    piot = m.get("piotroski") or {}
    p["piotroski_poang"] = piot.get("poang") if piot.get("bedomda", 0) >= 6 else None
    alt = m.get("altman") or {}
    p["altman_z"] = alt.get("z")
    ben = m.get("beneish") or {}
    p["beneish_m"] = ben.get("m")

    r = rapport or {}
    fr = r.get("forandring_risk") or {}
    fv = r.get("forandring_vd") or {}
    tr = r.get("tonlage_risk") or {}
    p["rapport_likhet_risk"] = fr.get("cosinuslikhet")
    p["rapport_likhet_vd"] = fv.get("cosinuslikhet")
    p["rapport_negativitet"] = tr.get("negativa_pct")
    p["rapport_osakerhet"] = tr.get("osakerhet_pct")
    flaggor = r.get("roda_flaggor") or []
    p["rapport_flaggvikt"] = float(sum(f["vikt"] for f in flaggor)) if r.get("tillganglig") else None
    p["rapport_antal_nya_risker"] = len(r.get("nya_risker") or []) if r.get("tillganglig") else None
    p["rapport_tillganglig"] = bool(r.get("tillganglig"))
    return p


def _percentil(varden: list, x, riktning: int):
    """Percentil 0-100 bland de bolag som har måttet. None om måttet saknas."""
    if x is None:
        return None
    giltiga = [v for v in varden if v is not None and np.isfinite(v)]
    if len(giltiga) < 5:
        return None
    andel = sum(1 for v in giltiga if v < x) / len(giltiga) * 100
    return andel if riktning > 0 else 100 - andel


# Minsta antal bolag för att en grupp ska rangordnas mot sig själv. Åtta är
# lågt men medvetet: universumet innehåller tio banker, och en percentil bland
# tio banker svarar på rätt fråga ("vilken av bankerna är starkast?") medan en
# percentil mot 200 verkstadsbolag svarar på fel fråga ("är en bank en bank?").
# Grovkornigt och relevant slår finkornigt och meningslöst.
MINSTA_GRUPP = 8


def rangordna(alla: dict[str, dict], grupp_av: dict | None = None) -> dict[str, dict]:
    """
    Räknar percentiler för varje mått.

    `grupp_av` = {symbol: gruppnamn}. Anges den jämförs varje bolag ENBART mot
    sin egen grupp. Det är inte en kosmetisk uppdelning: ett halvledarbolag i
    samma rangordning som dagligvaror får alltid usel värderingspercentil —
    inte för att det är dyrt för att vara halvledarbolag, utan för att cykliska
    tillväxtbolag alltid värderas högre än dagligvaror. Utan uppdelningen mäter
    poängen bransch i stället för bolag.

    Grupper med färre än MINSTA_GRUPP bolag rangordnas mot hela universumet i
    stället — en percentil bland åtta bolag är brus.
    """
    falt, riktningar = [], {}
    for uppsattning in (PELARE, PELARE_BANK):
        for pelare in uppsattning.values():
            for f, r, *_ in pelare:
                if f not in riktningar:
                    falt.append(f)
                    riktningar[f] = r

    if not grupp_av:
        grupp_av = {sym: "alla" for sym in alla}
    medlemmar = {}
    for sym in alla:
        medlemmar.setdefault(grupp_av.get(sym, "alla"), []).append(sym)

    alla_symboler = list(alla)
    ut = {}
    for grupp, symboler in medlemmar.items():
        jamforelse = symboler if len(symboler) >= MINSTA_GRUPP else alla_symboler
        kolumner = {f: [alla[s].get(f) for s in jamforelse] for f in falt}
        for sym in symboler:
            d = alla[sym]
            ut[sym] = {f: _percentil(kolumner[f], d.get(f), riktningar[f]) for f in falt}
            ut[sym]["_jamfordes_mot"] = grupp if len(symboler) >= MINSTA_GRUPP else "alla"
            ut[sym]["_antal_i_jamforelsen"] = len(jamforelse)
    return ut


def pelarpoang(percentiler: dict, bransch: str = "") -> dict:
    """Viktat snitt av percentilerna inom varje pelare, plus hur mycket som fanns."""
    ut = {}
    for namn, matt_ in pelare_for(bransch).items():
        summa = vikt = mojlig = 0.0
        for falt, _riktning, v, *_ in matt_:
            mojlig += v
            p = percentiler.get(falt)
            if p is not None:
                summa += p * v
                vikt += v
        ut[namn] = {
            "poang": (summa / vikt) if vikt else None,
            "tackning": vikt / mojlig if mojlig else 0.0,
        }
    return ut


def varningar_for(p: dict, rapport: dict | None) -> list[dict]:
    ut = []
    ben = p.get("beneish_m")
    alt = p.get("altman_z")
    flaggor = {
        "beneish_flagga": ben is not None and ben > -1.78,
        "accruals_hog": (p.get("accruals") or 0) > 0.10,
        "tillgangstillvaxt_hog": (p.get("tillgangstillvaxt") or 0) > 0.30,
        "utspadning": (p.get("nettoemission") or 0) > 0.03,
        "altman_nod": alt is not None and alt < 1.1,
        "piotroski_svag": (p.get("piotroski_poang") is not None
                           and p["piotroski_poang"] <= 3),
        "rapport_omskriven": (p.get("rapport_likhet_risk") is not None
                              and p["rapport_likhet_risk"] < 0.85),
        "gaende_bolag": any("Går-vidare" in f["flagga"]
                            for f in ((rapport or {}).get("roda_flaggor") or [])),
    }
    for nyckel, avdrag, rubrik, forklaring in VARNINGAR:
        if flaggor.get(nyckel):
            ut.append({"nyckel": nyckel, "avdrag": avdrag, "rubrik": rubrik,
                       "forklaring": forklaring})
    return ut


def total(pelare: dict, varningar: list, profil: str = "sammansatt",
          har_rapport: bool = True) -> dict:
    vikter = dict(PROFILER.get(profil, PROFILER["sammansatt"]))
    if not har_rapport:
        vikter.pop("Rapportsignaler", None)

    summa = vikt = mojlig = 0.0
    for namn, v in vikter.items():
        mojlig += v
        p = pelare.get(namn, {})
        if p.get("poang") is not None and p.get("tackning", 0) >= 0.4:
            summa += p["poang"] * v
            vikt += v
    ravarde = (summa / vikt) if vikt else None
    avdrag = sum(v["avdrag"] for v in varningar)
    tackning = vikt / mojlig if mojlig else 0.0

    # Ett betyg satt på en åttondel av modellen är inte jämförbart med ett satt
    # på hela. Investmentbolag hamnade annars överst i listan på ett P/B och ett
    # momentum, medan bolag som faktiskt granskats av alla fem pelarna trängdes
    # undan. Under gränsen får bolaget ingen poäng alls — bara en förklaring.
    otillrackligt = tackning < MINSTA_TACKNING
    return {
        "rapoang": ravarde,
        "avdrag": avdrag,
        "poang": None if (ravarde is None or otillrackligt) else max(0.0, ravarde - avdrag),
        "tackning": tackning,
        "otillracklig_tackning": otillrackligt,
        "profil": profil,
    }


# ------------------------------------------------------------ berättelsen --

def _fmt(varde, enhet):
    if varde is None:
        return "–"
    if enhet == "procent":
        return f"{varde * 100:.1f} %"
    if enhet == "gånger":
        return f"{varde:.1f}x"
    if enhet == "poäng":
        return f"{varde:.1f}"
    return f"{varde:.2f}"


BEVISTEXT = {
    "ki_tal": "K/I-talet är {v} — så många kronor i kostnad per intjänad krona. "
              "Det enskilt viktigaste effektivitetsmåttet för en bank.",
    "ki_trend": "K/I-talet trendar nedåt ({v} per år), alltså blir banken effektivare.",
    "rantenetto_marginal": "Räntenettot motsvarar {v} av balansräkningen.",
    "kapitalstyrka": "Eget kapital utgör {v} av tillgångarna — bankens buffert mot "
                     "kreditförluster.",
    "intaktsdiversifiering": "{v} av intäkterna kommer från annat än räntenettot, "
                             "vilket gör banken mindre räntekänslig.",
    "bruttolonsamhet": "Bruttovinsten motsvarar {v} av tillgångarna (Novy-Marx 2013: "
                       "det måttet har förutsagt avkastning bättre än nettovinst).",
    "roic": "Avkastningen på investerat kapital är {v}. Det är takten bolaget kan "
            "återinvestera i sig självt till.",
    "roic_5ar": "Femårssnittet för ROIC är {v} — nivån är alltså inte ett enskilt bra år.",
    "greenblatt_roc": "Avkastningen på det kapital verksamheten faktiskt binder är {v}.",
    "kassagenerering": "Kassaflödet är {v} gånger den redovisade vinsten — vinsten finns "
                       "på kontot, inte bara på papperet.",
    "rorelsemarginal": "Rörelsemarginalen är {v}.",
    "marginalstabilitet": "Marginalen svänger lite ({v} i standardavvikelse) — resultatet "
                          "är förutsägbart.",
    "ebit_ev": "Rörelseresultatet motsvarar {v} av företagsvärdet (Greenblatts earnings "
               "yield — jämförbar mellan bolag oavsett skuldsättning).",
    "fcf_yield": "Det fria kassaflödet motsvarar {v} av företagsvärdet.",
    "ev_ebitda": "Företagsvärdet är {v} rörelseresultatet före avskrivningar.",
    "pe": "P/E-talet är {v}.",
    "pb": "Börsvärdet är {v} det bokförda egna kapitalet.",
    "piotroski_poang": "Piotroski F-score är {v} av 9 — bolaget klarar de flesta "
                       "grundläggande hälsokontrollerna.",
    "altman_z": "Altman Z'' är {v}; över 2,6 räknas som säker zon.",
    "soliditet": "Soliditeten är {v}.",
    "nettoskuld_ebitda": "Nettoskulden motsvarar {v} årsresultat före avskrivningar.",
    "rantetackning": "Rörelseresultatet täcker räntekostnaden {v}.",
    "tillvaxt_3ar": "Omsättningen har vuxit {v} per år i tre år.",
    "vinsttillvaxt_3ar": "Vinsten har vuxit {v} per år i tre år.",
    "fcf_tillvaxt_3ar": "Det fria kassaflödet har vuxit {v} per år i tre år.",
    "marginaltrend": "Marginalen har trendat uppåt ({v} per år).",
    "momentum_12_1": "Kursen är {v} högre än för ett år sedan (exklusive senaste "
                     "månaden — Jegadeesh & Titman 1993).",
    "avstand_till_arstopp": "Kursen står {v} från sin egen årstopp.",
    "volatilitet": "Volatiliteten är {v} per år.",
    "rapport_likhet_risk": "Riskavsnittet i senaste årsredovisningen är {v} likt "
                           "fjolårets — bolaget har inte behövt skriva om sin riskbild.",
    "rapport_likhet_vd": "Vd-analysen är {v} lik fjolårets.",
    "rapport_negativitet": "Andelen negativa ord i riskavsnittet är {v}.",
    "rapport_osakerhet": "Andelen osäkerhetsord i riskavsnittet är {v}.",
    "rapport_flaggvikt": "Röda flaggor i rapporten väger {v} sammanlagt.",
}


def bygg_bevis(platt: dict, percentiler: dict, hog: bool = True, antal: int = 6,
               bransch: str = ""):
    """De starkaste (eller svagaste) enskilda måtten, med siffra och tolkning."""
    rader = []
    for pelare, matt_ in pelare_for(bransch).items():
        for falt, _r, vikt, etikett, enhet in matt_:
            p = percentiler.get(falt)
            if p is None:
                continue
            if hog and p < 70:
                continue
            if not hog and p > 30:
                continue
            varde = platt.get(falt)
            mall = BEVISTEXT.get(falt, etikett + ": {v}")
            rader.append({
                "pelare": pelare, "matt": falt, "etikett": etikett,
                "varde": varde, "formaterat": _fmt(varde, enhet),
                "percentil": p, "vikt": vikt,
                "text": mall.format(v=_fmt(varde, enhet)),
            })
    rader.sort(key=lambda x: (-(x["percentil"] * x["vikt"]) if hog
                              else (x["percentil"] * x["vikt"])))
    return rader[:antal]


def falsifiering(platt: dict, bevis: list) -> list[dict]:
    """
    Vad skulle göra caset fel? Konkreta, mätbara villkor — inte "om marknaden
    vänder". Det här är den viktigaste listan i hela appen: den gör caset
    möjligt att motbevisa, och därmed värt att ha en åsikt om.
    """
    ut = []
    anvanda = {b["matt"] for b in bevis}

    def lagg(villkor, varfor):
        ut.append({"villkor": villkor, "varfor": varfor})

    if "roic" in anvanda and platt.get("roic"):
        # Taket på 30 % finns för att bolag med kraftiga återköp får en pytteliten
        # nämnare och därmed ROIC på 100 %+. Det är inte fel räknat, men "ROIC
        # faller under 95 %" vore en meningslös larmgräns.
        gräns = min(max(0.08, platt["roic"] * 0.7), 0.30)
        lagg(f"ROIC faller under {gräns * 100:.0f} % två år i rad",
             "Hela kvalitetsargumentet bygger på att kapitalet förräntas högt. "
             "Faller det bort är bolaget ett vanligt bolag till ett högt pris.")
    if "kassagenerering" in anvanda:
        lagg("Kassaflöde/vinst går under 0,8 två år i rad",
             "Då börjar vinsten vara bokföring snarare än pengar.")
    if platt.get("nettoskuld_ebitda") is not None:
        gräns = max(2.5, (platt["nettoskuld_ebitda"] or 0) + 1.0)
        lagg(f"Nettoskuld/EBITDA passerar {gräns:.1f}x",
             "Skuldsättning är det som gör en dålig period till en existentiell period.")
    if "ebit_ev" in anvanda and platt.get("ebit_ev"):
        lagg(f"EBIT/EV sjunker under {platt['ebit_ev'] * 0.6 * 100:.1f} % utan att "
             "vinsten stigit",
             "Då har du betalat upp värderingen och rabatten som var själva caset är borta.")
    if "tillvaxt_3ar" in anvanda:
        lagg("Två kvartal i rad med fallande omsättning jämfört med året innan",
             "Tillväxtcaset förutsätter att tillväxten finns kvar.")
    if platt.get("rapport_tillganglig"):
        lagg("Nästa 10-K har under 0,90 cosinuslikhet i riskavsnittet",
             "Enligt Lazy Prices-studien är stora omskrivningar av risktexten "
             "en signal om att något faktiskt hänt.")
        lagg("Formuleringen 'material weakness' eller 'going concern' dyker upp",
             "Två uttryck som aldrig står i en rapport av misstag.")
    if platt.get("piotroski_poang") is not None:
        lagg(f"Piotroski F-score faller under {max(4, int(platt['piotroski_poang']) - 3)}",
             "Poängen mäter om det underliggande blir bättre eller sämre, inte hur fint "
             "det ser ut just nu.")
    lagg("Antalet aktier ökar mer än 5 % utan ett förvärv som motiverar det",
         "Utspädning är den tystaste formen av förlust.")
    return ut


def rubrik_och_tes(namn: str, pelare: dict, bevis: list, varningar: list,
                   platt: dict) -> tuple[str, str]:
    starkast = sorted(
        [(n, v["poang"]) for n, v in pelare.items() if v["poang"] is not None],
        key=lambda x: -x[1])
    if not starkast:
        return f"{namn}: för lite data", "Det går inte att bedöma bolaget med den data som finns."

    topp = [n for n, p in starkast[:2] if p >= 60]
    botten = [n for n, p in starkast[-2:] if p is not None and p < 40]

    if not topp:
        rubrik = f"{namn} — inget som sticker ut"
    elif set(topp) >= {"Kvalitet", "Värdering"}:
        rubrik = f"{namn} — bra bolag till ovanligt lågt pris"
    elif "Kvalitet" in topp:
        rubrik = f"{namn} — kvalitetsbolag, priset är frågan"
    elif "Värdering" in topp:
        rubrik = f"{namn} — billigt, men varför?"
    elif "Tillväxt" in topp:
        rubrik = f"{namn} — växer snabbt"
    else:
        rubrik = f"{namn} — styrka i {topp[0].lower()}"

    delar = []
    if bevis:
        delar.append("Det som talar för: " + " ".join(b["text"] for b in bevis[:3]))
    if botten:
        delar.append("Svagast pelare är " + " och ".join(b.lower() for b in botten) + ".")
    if varningar:
        delar.append("Varningar: " + "; ".join(v["rubrik"].lower() for v in varningar) + ".")
    if platt.get("avstangt_varfor"):
        delar.append("Obs om branschen: " + platt["avstangt_varfor"])
    if not platt.get("rapport_tillganglig"):
        delar.append("Rapporttexten har inte lästs (finns bara för amerikanska bolag "
                     "via SEC) — pelaren Rapportsignaler saknas i poängen.")
    return rubrik, " ".join(delar)


def bygg_case(sym: str, meta: dict, matt_: dict, rapport: dict | None,
              percentiler: dict, profil: str = "sammansatt") -> dict:
    bransch = meta.get("bransch", "")
    platt = platta_matt(matt_, rapport)
    pel = pelarpoang(percentiler, bransch)
    varn = varningar_for(platt, rapport)
    tot = total(pel, varn, profil, har_rapport=bool(platt.get("rapport_tillganglig")))
    for_ = bygg_bevis(platt, percentiler, hog=True, bransch=bransch)
    mot = bygg_bevis(platt, percentiler, hog=False, bransch=bransch)
    rubrik, tes = rubrik_och_tes(meta.get("namn", sym), pel, for_, varn, platt)
    return {
        "symbol": sym,
        "namn": meta.get("namn", sym),
        "bransch": meta.get("bransch"),
        "marknad": meta.get("marknad"),
        "rubrik": rubrik,
        "tes": tes,
        "poang": tot["poang"],
        "rapoang": tot["rapoang"],
        "avdrag": tot["avdrag"],
        "tackning": tot["tackning"],
        "otillracklig_tackning": tot.get("otillracklig_tackning", False),
        "profil": profil,
        "pelare": pel,
        "for": for_,
        "mot": mot,
        "varningar": varn,
        "falsifiering": falsifiering(platt, for_),
        "matt": platt,
        "har_rapport": bool(platt.get("rapport_tillganglig")),
    }
