"""
rad.py — appen säger vad den tycker att du ska göra.

Det här är en privat app. Den ska inte hänvisa till att "alla beslut är dina
egna" och lämna dig med en tabell. Den ska ge besked.

Men ett råd är bara värt något om det vilar på något appen FAKTISKT vet, och
efter åtta genomförda ur-provs-test vet den detta:

  DEN VET INTE       vilken aktie som går upp. Samtliga åtta rangordningar föll,
                     med negativ topp-minus-botten i varenda variant. Därför
                     finns här inga "köp"-råd baserade på poängen.

  DEN VET            vilka bolag som har akut överlevnadsrisk. Utspädning,
                     Altman i nödzonen, går-vidare-tvivel och svag Piotroski
                     mäter finansiell hälsa, inte kursriktning — och de
                     sambanden är väsentligt bättre belagda.

  DEN VET            hur mycket ett bolag brukar röra sig. 32 rapporter med
                     mätt reaktion är en observation, inte en prognos.

  DEN VET            vad det kostar att handla, och det är den enda posten med
                     garanterat negativ förväntan om man slarvar.

  DEN VET            vad bolaget själv skrivit om sedan i fjol.

  DEN VET            vad personer i insynsställning gjort med sina EGNA pengar.
                     Det är hård data och intressant att veta — men signalen
                     testades på 1342 observationer och föll (nettoköpare
                     −0,4 %-enheter, p = 0,75). Den redovisas därför som en
                     upplysning, inte som ett skäl att köpa.

Råden nedan använder bara de fyra sista. Storleken på en position är ett beslut
man kan fatta rationellt utan att veta något om framtiden — det är därför den
här filen handlar mest om kronor och gränser, och inte alls om riktning.
"""

from __future__ import annotations

# Courtageklasser på Avanza (2026). Används för att räkna vad en affär kostar
# tur och retur och var brytpunkten går.
COURTAGE = [
    {"namn": "Start / Mini", "procent": 0.0025, "minimum": 1},
    {"namn": "Small", "procent": 0.0015, "minimum": 39},
    {"namn": "Medium", "procent": 0.0009, "minimum": 69},
    {"namn": "Fast pris", "procent": 0.0, "minimum": 99},
]
VAXLINGSAVGIFT = 0.0025      # Avanzas växlingspåslag för utländsk handel
SPREAD_ANTAGANDE = 0.0010    # halva spreaden i ett storbolag, grov uppskattning


def billigaste_courtage(belopp: float) -> dict:
    """Vilken courtageklass som är billigast för ett givet ordervärde."""
    val = []
    for k in COURTAGE:
        val.append({**k, "kostnad": max(k["minimum"], belopp * k["procent"])})
    return min(val, key=lambda k: k["kostnad"])


def handelskostnad(belopp: float, utlandsk: bool) -> dict:
    """Vad en tur och retur kostar, i kronor och i procent."""
    k = billigaste_courtage(belopp)
    courtage = k["kostnad"] * 2
    vaxling = belopp * VAXLINGSAVGIFT * 2 if utlandsk else 0.0
    spread = belopp * SPREAD_ANTAGANDE * 2
    total = courtage + vaxling + spread
    return {"klass": k["namn"], "courtage": courtage, "vaxling": vaxling,
            "spread": spread, "total": total, "andel": total / belopp if belopp else None}


def positionsstorlek(kapital: float, matt: dict, kalender: dict) -> dict:
    """
    Hur stor position bolaget tål — räknat baklänges från vad du är beredd att
    förlora, inte framlänges från vad du hoppas tjäna.

    Tre tak sätts, och det lägsta gäller:

      1. Ett bolag får aldrig väga mer än 10 % av det du avsatt för enskilda
         aktier. Med tio bolag är du diversifierad; med tre är du inte det.
      2. Bolagets värsta historiska fall får inte kosta mer än 15 % av det
         avsatta kapitalet. Ett bolag som fallit 70 % en gång kan göra det igen.
      3. En typisk rapportdagsrörelse får inte kosta mer än 3 %.

    Talen är mina val, men de är i alla fall uttalade — och de går att ändra i
    installningar.json.
    """
    tak = {}
    tak["spridning"] = kapital * 0.10

    fall = matt.get("max_fall_10ar")
    if fall and fall < -0.05:
        tak["varsta_fall"] = kapital * 0.15 / abs(fall)

    stat = (kalender or {}).get("statistik") or {}
    rorelse = stat.get("median_rorelse")
    if rorelse and stat.get("antal", 0) >= 5:
        tak["rapportdag"] = kapital * 0.03 / rorelse

    vol = matt.get("volatilitet")
    if vol and vol > 0.05:
        tak["volatilitet"] = kapital * 0.25 / vol

    if not tak:
        return {}
    styrande = min(tak, key=tak.get)
    belopp = tak[styrande]
    kostnad = handelskostnad(belopp, bool(matt.get("rapportvaluta") not in (None, "SEK")))
    return {
        "belopp": belopp,
        "styrande": styrande,
        "tak": tak,
        "andel_av_kapital": belopp / kapital if kapital else None,
        "kostnad": kostnad,
        "vid_varsta_fall": belopp * fall if fall else None,
        "vid_rapportdag": belopp * rorelse if rorelse else None,
    }


# ----------------------------------------------------------------- läget ---

def lagesbedomning(m: dict) -> dict | None:
    """
    "Är det bra läge just nu?" — så långt frågan går att besvara.

    Två saker mäts, och båda är positionsangivelser, inte prognoser:

      VÄRDERING MOT SIG SJÄLV. Var dagens P/E ligger i bolagets egen historiska
      spann. Percentil 10 betyder att marknaden betalat mer för bolaget nästan
      varje annan dag de senaste åren. Det är en HELT annan fråga än den som
      föll i valideringen — där jämfördes bolag med varandra, här jämförs ett
      bolag med sig självt.

      KURSLÄGE. RSI och avståndet till egen årstopp. Säger vad som HÄNT.

    BEVISLÄGET, uttalat: det här sambandet har appen INTE testat. Det som
    testats och fallit är att rangordna bolag mot varandra. Att köpa ett bolag
    när det är billigt mot sin egen historia är en rimligare tanke — men rimlig
    är inte samma sak som belagd, och en aktie kan vara billig mot sin historia
    därför att bolaget blivit sämre. Läs rapporten innan du tolkar rabatten som
    en möjlighet.
    """
    ev = m.get("egen_vardering")
    rsi_ = m.get("rsi")
    topp = m.get("avstand_till_arstopp")
    if not ev and rsi_ is None:
        return None

    rader, niva = [], "normalt"
    if ev:
        p = ev["percentil"]
        if p <= 20:
            niva = "ovanligt billigt mot sin egen historia"
            rader.append(f"P/E {ev['nu']:.1f} — lägre än {100 - p:.0f} % av de "
                         f"{ev['antal_ar']} år appen kan mäta. Bolagets eget spann är "
                         f"{ev['lagsta']:.0f}–{ev['hogsta']:.0f}, median {ev['median']:.0f}. "
                         "Du betalar mindre för samma bolag än marknaden brukat göra.")
        elif p >= 80:
            niva = "dyrt mot sin egen historia"
            rader.append(f"P/E {ev['nu']:.1f} — högre än {p:.0f} % av bolagets egna år "
                         f"(spann {ev['lagsta']:.0f}–{ev['hogsta']:.0f}, median "
                         f"{ev['median']:.0f}). Marknaden har sällan betalat så mycket "
                         "för det här bolaget. Förväntningarna är höga, och då krävs "
                         "det mindre för att göra besvikelse.")
        else:
            rader.append(f"P/E {ev['nu']:.1f} ligger mitt i bolagets eget spann "
                         f"({ev['lagsta']:.0f}–{ev['hogsta']:.0f}). Varken rabatt "
                         "eller premie mot hur det brukar värderas.")

    if rsi_ is not None:
        if rsi_ >= 70:
            rader.append(f"RSI {rsi_:.0f} — tekniskt överköpt. Kursen har gått upp "
                         "snabbt den senaste tiden. Det säger inget om fortsättningen, "
                         "men du köper efter uppgången, inte före.")
        elif rsi_ <= 30:
            rader.append(f"RSI {rsi_:.0f} — tekniskt översåld. Säljtrycket har varit "
                         "stort. Ofta är det befogat; ibland inte.")
        else:
            rader.append(f"RSI {rsi_:.0f} — varken överköpt eller översåld.")

    if topp is not None:
        rader.append(f"Kursen står {abs(topp) * 100:.0f} % under sin egen årstopp."
                     if topp < -0.01 else "Kursen står på eller nära sin årstopp.")

    return {"niva": niva, "rader": rader,
            "percentil": (ev or {}).get("percentil"),
            "rsi": rsi_,
            "bevis": "OTESTAT. Appen har testat att rangordna bolag mot varandra — "
                     "det föll åtta gånger av åtta. Att jämföra ett bolag med sin egen "
                     "historia är en annan och rimligare fråga, men den är inte prövad "
                     "här. Läs den som en prisuppgift, inte som ett besked."}


# ---------------------------------------------------------------- domen ----

def rekommendation(c: dict, kapital: float = 100000.0) -> dict:
    """
    Ett besked, inte en beskrivning.

    `niva` styr färgen: undvik / las_forst / ok / for_lite_data.
    `gor` är listan över vad du konkret ska göra.
    """
    m = c.get("matt") or {}
    r = c.get("rapport") or {}
    kal = c.get("kalender") or {}
    varn = {v["nyckel"] for v in (c.get("varningar") or [])}
    namn = c.get("namn", c.get("symbol", ""))

    gor, skal = [], []
    ins = c.get("insyn") or {}
    insyn_dom = ins.get("bedomning")

    # --- 1. Överlevnadsrisk. Det enda område där appen har starkt stöd. ---
    doden = varn & {"gaende_bolag", "altman_nod", "utspadning", "piotroski_svag"}
    if "gaende_bolag" in varn:
        skal.append("Revisorn har uttryckt tvivel om att bolaget överlever tolv "
                    "månader. Det är inte en varningsflagga, det är en brandvarnare.")
    if "altman_nod" in varn:
        skal.append(f"Altman Z'' ligger i nödzonen ({m.get('altman_z', 0):.2f}) — "
                    "statistiskt förhöjd konkursrisk.")
    if "utspadning" in varn:
        skal.append(f"Antalet aktier ökade {(m.get('nettoemission') or 0) * 100:.0f} % "
                    "på ett år. Din andel av bolaget krymper medan du äger det.")
    if "piotroski_svag" in varn:
        skal.append(f"Piotroski {m.get('piotroski_poang')} av 9 — bolaget faller på de "
                    "flesta grundläggande hälsokontrollerna.")

    if len(doden) >= 2 or "gaende_bolag" in varn:
        gor.append("Låt bli. Det finns 200 andra bolag i listan.")
        gor.append("Vill du ändå: läs varför de behöver pengar, och räkna med "
                   "utspädning som en kostnad du betalar varje år.")
        return _bygg("undvik", f"Undvik {namn}", skal, gor, c, kapital)

    # --- 2. För lite data för att uttala sig ---
    if (c.get("tackning") or 0) < 0.6:
        skal.append(f"Bara {(c.get('tackning') or 0) * 100:.0f} % av modellen gick att "
                    "räkna för det här bolaget — branschen gör de flesta måtten "
                    "meningslösa.")
        gor.append("Bedöm bolaget på egen hand. Appen tillför inget här.")
        return _bygg("for_lite_data", f"{namn} går inte att bedöma här", skal, gor, c, kapital)

    # --- 3. Något har hänt som du ska läsa FÖRE beslut ---
    las = []
    fr = r.get("forandring_risk") or r.get("forandring_hela") or {}
    lik = fr.get("cosinuslikhet")
    if lik is not None and lik < 0.90 and not (abs(fr.get("langdforandring") or 0) > 1.0):
        las.append(f"riskavsnittet är omskrivet till {lik:.2f} (normalt över 0,95)")
    trend = r.get("tonlagestrend") or []
    if len(trend) >= 2 and trend[-1]["negativa_pct"] - trend[-2]["negativa_pct"] > 1.5:
        las.append(f"tonläget mörknade från {trend[-2]['negativa_pct']:.1f} % till "
                   f"{trend[-1]['negativa_pct']:.1f} % negativa ord")
    tunga = [f for f in (r.get("roda_flaggor") or []) if f["vikt"] >= 3]
    if tunga:
        las.append(f"{len(tunga)} tung{'a' if len(tunga) > 1 else ''} formulering"
                   f"{'ar' if len(tunga) > 1 else ''} i rapporten "
                   f"({tunga[0]['flagga'].split(':')[0].lower()})")
    if varn & {"beneish_flagga", "accruals_hog"}:
        las.append("redovisningen har drag som brukar följas av besvikelser "
                   "(Beneish eller höga periodiseringar)")

    dagar = kal.get("dagar_kvar")
    if dagar is not None and 0 <= dagar <= 7:
        las.append(f"rapport om {dagar} dagar — vänta tills den kommit")

    if insyn_dom and insyn_dom["niva"] == "kop" and not las:
        skal.append(insyn_dom["text"])

    if las:
        skal += [x[0].upper() + x[1:] + "." for x in las]
        if insyn_dom and insyn_dom["niva"] == "kop":
            gor.append("INSYN: " + insyn_dom["text"])
        gor.append("Läs rapporten innan du gör något. Avsnittet \"Vad rapporten säger\" "
                   "högst upp visar var.")
        if dagar is not None and 0 <= dagar <= 7:
            gor.append(f"Köp inget före rapporten. Bolaget rör sig typiskt "
                       f"±{((kal.get('statistik') or {}).get('median_rorelse') or 0) * 100:.1f} % "
                       "den dagen, och riktningen går inte att förutsäga.")
        return _bygg("las_forst", f"Läs innan du agerar: {namn}", skal, gor, c, kapital)

    # --- 4. Inget hindrar. Då handlar rådet om storlek och kostnad. ---
    # Insynsköp nämns FÖRE storleken, eftersom det är den enda positiva signal
    # appen har något publicerat stöd för.
    skal.append("Inga överlevnadsvarningar, inget omskrivet i rapporten, ingen "
                "rapport inom en vecka.")
    pel = c.get("pelare") or {}
    starka = [n for n, p in pel.items() if (p or {}).get("poang") is not None
              and p["poang"] >= 70]
    svaga = [n for n, p in pel.items() if (p or {}).get("poang") is not None
             and p["poang"] <= 30]
    if starka:
        skal.append("Starkast: " + ", ".join(s.lower() for s in starka) + ".")
    if svaga:
        skal.append("Svagast: " + ", ".join(s.lower() for s in svaga) +
                    " — det är där caset spricker om det spricker.")
    if insyn_dom and insyn_dom["niva"] == "kop":
        gor.append("INSYN: " + insyn_dom["text"])
    gor.append("Om du vill äga bolaget: håll dig till beloppet nedan.")
    gor.append("Skriv av falsifieringslistan och gå igenom den vid varje kvartal.")
    return _bygg("ok", f"Inget hindrar {namn}", skal, gor, c, kapital)


def _bygg(niva, rubrik, skal, gor, c, kapital):
    pos = positionsstorlek(kapital, c.get("matt") or {}, c.get("kalender") or {})
    lage = lagesbedomning(c.get("matt") or {})
    if niva in ("ok", "las_forst") and pos:
        k = pos["kostnad"]
        gor.append(f"Max {pos['belopp']:,.0f} kr i det här bolaget"
                   .replace(",", " ") +
                   f" ({pos['andel_av_kapital'] * 100:.0f} % av kapitalet). "
                   f"Begränsas av {_taktext(pos['styrande'])}.")
        if pos.get("vid_varsta_fall"):
            gor.append(f"Det beloppet förlorar {abs(pos['vid_varsta_fall']):,.0f} kr"
                       .replace(",", " ") +
                       f" om bolagets värsta historiska fall upprepas "
                       f"({(c.get('matt') or {}).get('max_fall_10ar', 0) * 100:.0f} %). "
                       "Klarar du att sitta still genom det? Om inte, halvera.")
        if pos.get("vid_rapportdag"):
            gor.append(f"En vanlig rapportdag rör sig positionen ±"
                       f"{abs(pos['vid_rapportdag']):,.0f} kr.".replace(",", " "))
        if k["andel"] and k["andel"] > 0.01:
            gor.append(f"Handla inte för mindre — en tur och retur kostar "
                       f"{k['total']:.0f} kr ({k['andel'] * 100:.2f} %) i "
                       f"{k['klass']}-klassen.")
    # Läget läggs till som ett eget råd när det är ovanligt åt något håll.
    if lage and niva in ("ok", "las_forst"):
        if (lage.get("percentil") is not None and lage["percentil"] <= 20):
            gor.insert(0, "LÄGE: bolaget är ovanligt billigt mot sin EGEN historia — "
                          + lage["rader"][0])
        elif (lage.get("percentil") is not None and lage["percentil"] >= 80):
            gor.insert(0, "LÄGE: bolaget är dyrt mot sin egen historia. "
                          "Vänta hellre, eller ta en mindre post. " + lage["rader"][0])
    return {"niva": niva, "rubrik": rubrik, "skal": skal, "gor": gor,
            "position": pos, "lage": lage,
            "insyn": (c.get("insyn") or {}).get("bedomning")}


def _taktext(nyckel):
    return {
        "spridning": "spridningsregeln (max 10 % i ett bolag)",
        "varsta_fall": "bolagets värsta historiska fall",
        "rapportdag": "hur mycket det svänger på rapportdagen",
        "volatilitet": "bolagets volatilitet",
    }.get(nyckel, nyckel)


def dagens_lista(case_lista: list, kapital: float = 100000.0,
                 antal: int = 8) -> dict:
    """
    Vad du bör göra idag, i prioritetsordning. Tre högar, inget mer.
    """
    undvik, las, ok = [], [], []
    for c in case_lista:
        r = rekommendation(c, kapital)
        post = {"symbol": c["symbol"], "namn": c["namn"], "niva": r["niva"],
                "rubrik": r["rubrik"], "skal": r["skal"][:2], "gor": r["gor"][:2],
                "poang": c.get("poang"),
                "dagar_kvar": (c.get("kalender") or {}).get("dagar_kvar"),
                "position": (r.get("position") or {}).get("belopp")}
        if r["niva"] == "undvik":
            undvik.append(post)
        elif r["niva"] == "las_forst":
            las.append(post)
        elif r["niva"] == "ok":
            ok.append(post)

    las.sort(key=lambda x: (x["dagar_kvar"] if x["dagar_kvar"] is not None else 999))
    ok.sort(key=lambda x: -(x["poang"] or 0))
    undvik.sort(key=lambda x: (x["poang"] or 0))
    return {"undvik": undvik[:antal], "las_forst": las[:antal], "ok": ok[:antal],
            "antal_totalt": {"undvik": len(undvik), "las_forst": len(las), "ok": len(ok)}}
