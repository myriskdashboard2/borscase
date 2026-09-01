"""
app.py — webbservern. Allt kör lokalt på din dator; inget skickas någonstans.

Långa jobb (skanning, validering) körs i en bakgrundstråd med en enkel
statusflagga som gränssnittet pollar. Det räcker gott för en användare, och
slipper webbsockets.
"""

from __future__ import annotations

import json
import os
import threading
import traceback
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

import case as C
import ordlista as ol
import rad as rd
import rapportlasning as rl
import skanning as sk
import svenska_rapporter as svr
import universum as un
import version as ver
import validering as va

HAR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)

JOBB = {"kor": False, "vad": None, "meddelande": "", "klart": 0, "av": 0, "fel": None}
_LAS = threading.Lock()


def _satt(**kw):
    with _LAS:
        JOBB.update(kw)


# ------------------------------------------------------------- sidorna ----

@app.route("/")
def index():
    return send_from_directory(HAR, "dashboard.html")


@app.route("/api/version")
def version_info():
    """
    Vilken version av PROGRAMMET, och hur färsk DATAN är.

    Två skilda frågor som båda orsakar förvirring: "kör jag den nya appen?" och
    "är siffrorna från idag?". De besvaras tillsammans i sidhuvudet.
    """
    res = sk.las_sparat() or {}
    inst = sk.las_installningar()
    return jsonify({
        "version": ver.VERSION,
        "datum": ver.DATUM,
        "nyheter": [{"version": v, "datum": d, "text": t} for v, d, t in ver.NYHETER],
        "skanning_tid": res.get("tid"),
        "antal_bolag": len(res.get("case") or []),
        "mapp": HAR,
        "stod_bmac": inst.get("stod_bmac", ""),
        "stod_paypal": inst.get("stod_paypal", ""),
    })


@app.route("/presentation")
def presentation():
    """Presentationen, serverad av appen sa att den gar att oppna och filma."""
    return send_from_directory(HAR, "presentation.html")


@app.route("/api/status")
def status():
    with _LAS:
        return jsonify(dict(JOBB))


@app.route("/api/installningar", methods=["GET", "POST"])
def installningar():
    if request.method == "POST":
        inst = sk.las_installningar()
        inst.update(request.get_json(force=True) or {})
        sk.spara_installningar(inst)
        return jsonify(inst)
    return jsonify(sk.las_installningar())


@app.route("/api/universum")
def universum():
    inst = sk.las_installningar()
    U = un.bygg_universum(inst.get("egna_bolag"))
    return jsonify({"bolag": list(U.values()), "sarskilda": un.SARSKILDA,
                    "profiler": list(C.PROFILER)})


# ------------------------------------------------------------ skanning ----

@app.route("/api/skanning")
def skanning_las():
    res = sk.las_sparat()
    if not res:
        return jsonify({"finns": False})
    res["finns"] = True
    return jsonify(res)


def _kor_skanning(profil, las_rapporter, rapportdjup):
    try:
        _satt(kor=True, vad="skanning", meddelande="startar", klart=0, av=0, fel=None)

        def framsteg(n, av, sym):
            _satt(klart=n, av=av, meddelande=f"{sym}")

        res = sk.skanna(profil=profil, las_rapporter=las_rapporter,
                        rapportdjup=rapportdjup, framsteg=framsteg)
        sk.spara(res)
        _satt(meddelande=f"klart: {res['antal_bedomda']} bolag på {res['sekunder']} s")
    except Exception as e:
        _satt(fel=f"{type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        _satt(kor=False)


@app.route("/api/skanna", methods=["POST"])
def skanna():
    with _LAS:
        if JOBB["kor"]:
            return jsonify({"fel": "Ett jobb kör redan."}), 409
    d = request.get_json(force=True) or {}
    inst = sk.las_installningar()
    t = threading.Thread(target=_kor_skanning, daemon=True, args=(
        d.get("profil", inst.get("profil", "sammansatt")),
        bool(d.get("las_rapporter", inst.get("las_rapporter", True))),
        int(d.get("rapportdjup", inst.get("rapportdjup", 3))),
    ))
    t.start()
    return jsonify({"startad": True})


@app.route("/api/case/<path:sym>")
def case_detalj(sym):
    profil = request.args.get("profil", sk.las_installningar().get("profil", "sammansatt"))
    try:
        return jsonify(sk.detaljer(sym, profil=profil))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"fel": f"{type(e).__name__}: {e}"}), 500


@app.route("/api/omrangordna", methods=["POST"])
def omrangordna():
    """
    Byter profil utan att hämta data på nytt. Percentilerna är redan uträknade;
    bara vikterna ändras, så det tar millisekunder i stället för minuter.
    """
    d = request.get_json(force=True) or {}
    profil = d.get("profil", "sammansatt")
    res = sk.las_sparat()
    if not res:
        return jsonify({"fel": "Ingen sparad skanning."}), 404
    for c in res["case"]:
        pel = c["pelare"]
        varn = c["varningar"]
        t = C.total(pel, varn, profil, har_rapport=c.get("har_rapport", False))
        c["poang"] = t["poang"]
        c["rapoang"] = t["rapoang"]
        c["tackning"] = t["tackning"]
        c["profil"] = profil
    res["case"].sort(key=lambda c: (c["poang"] is None, -(c["poang"] or 0)))
    res["profil"] = profil
    # Skriver AVSIKTLIGT inte tillbaka till skanning_resultat.json. Att byta
    # profil är att titta på samma data med andra vikter — ingen ny mätning.
    # En vy som skriver till datafilen kan skriva sönder den, t.ex. om en äldre
    # serverprocess ligger kvar med gammal kod i minnet.
    res["finns"] = True
    return jsonify(res)


# ---------------------------------------------------------- validering ----

@app.route("/api/validering")
def validering_las():
    f = va.las_sparat() or {"finns": False}
    f["tavla"] = va.las_tavla()
    return jsonify(f)


@app.route("/api/validering/<profil>")
def validering_profil(profil):
    """En enskild testkörning. Gör det möjligt att öppna vilket test som helst."""
    import os as _os
    fil = _os.path.join(HAR, f"validering_{profil}.json")
    if not _os.path.exists(fil):
        return jsonify({"fel": f"Ingen sparad körning för profilen {profil}."}), 404
    with open(fil, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


def _kor_validering(las_rapporter, profil):
    try:
        _satt(kor=True, vad="validering", meddelande="startar", klart=0, av=0, fel=None)

        def framsteg(m):
            _satt(meddelande=str(m))

        f = va.kor(profil=profil, las_rapporter=las_rapporter, framsteg=framsteg)
        if not f.get("fel"):
            va.spara(f)
            _satt(meddelande="validering klar")
        else:
            _satt(fel=f["fel"])
    except Exception as e:
        _satt(fel=f"{type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        _satt(kor=False)


@app.route("/api/validera", methods=["POST"])
def validera():
    with _LAS:
        if JOBB["kor"]:
            return jsonify({"fel": "Ett jobb kör redan."}), 409
    d = request.get_json(force=True) or {}
    med = bool(d.get("las_rapporter", False))
    profil = d.get("profil", "sammansatt" if med else "sammansatt_utan_rapport")
    threading.Thread(target=_kor_validering, daemon=True, args=(med, profil)).start()
    return jsonify({"startad": True})


# --------------------------------------------------------- rapportlasa ----

@app.route("/api/rapport/<path:sym>")
def rapport(sym):
    """
    Rapportanalys för ett bolag — från SEC om det är amerikanskt, från MFN om
    det är svenskt. Att låta gränssnittet välja källa vore fel ställe: det är
    bolaget som avgör var dess rapporter finns, inte fliken man står på.
    """
    djup = int(request.args.get("djup", 3))
    form = request.args.get("form", "10-K")
    inst = sk.las_installningar()
    U = un.bygg_universum(inst.get("egna_bolag"))
    meta = U.get(sym)
    try:
        if meta and not meta.get("edgar"):
            r = svr.analysera_svenskt_bolag(sym, meta["namn"], max(djup, 4))
        else:
            r = rl.analysera_bolag(sym, form, djup)
            if not r.get("tillganglig"):
                r = rl.analysera_bolag(sym, "20-F", djup)
        r["symbol"] = sym
        r["namn"] = (meta or {}).get("namn", sym)
        r["tolkning"] = rl.tolkning(r)
        return jsonify(r)
    except Exception as e:
        return jsonify({"tillganglig": False, "skal": f"{type(e).__name__}: {e}"})


@app.route("/api/egen_rapport", methods=["POST"])
def egen_rapport():
    """Analysera en rapport du pekar ut själv — URL, filsökväg eller inklistrad text."""
    d = request.get_json(force=True) or {}
    try:
        def hamta(kalla, text):
            if text and len(text.strip()) > 400:
                return text
            if not kalla:
                return ""
            if kalla.startswith("http"):
                return rl.las_url(kalla)
            if kalla.lower().endswith(".pdf"):
                return rl.las_pdf(kalla)
            with open(kalla, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        nu = hamta(d.get("kalla"), d.get("text"))
        fo = hamta(d.get("kalla_forra"), d.get("text_forra"))
        if len(nu) < 400:
            return jsonify({"fel": "Fick ingen läsbar text. Kontrollera URL, "
                                   "sökväg eller klistra in texten direkt."}), 400
        r = rl.analysera_rapporttext(nu, fo)
        r["tecken"] = len(nu)
        r["tecken_forra"] = len(fo)
        return jsonify(r)
    except Exception as e:
        return jsonify({"fel": f"{type(e).__name__}: {e}"}), 500


@app.route("/api/insyn")
def insyn_lista():
    """Alla bolag med personlig insynshandel, störst nettoköp först."""
    res = sk.las_sparat()
    if not res:
        return jsonify({"finns": False})
    rader = []
    for c in res["case"]:
        i = c.get("insyn") or {}
        if not i or i.get("fel"):
            continue
        if not (i.get("antal_kop") or i.get("antal_salj") or i.get("antal_storagare")):
            continue
        rader.append({
            "symbol": c["symbol"], "namn": c["namn"], "marknad": c.get("marknad"),
            "bransch": c.get("bransch"), "poang": c.get("poang"),
            "valuta": (c.get("matt") or {}).get("rapportvaluta"),
            **{k: i.get(k) for k in ("antal_kop", "antal_salj", "netto", "personer_kopt",
                                     "personer_salt", "tunga_kop", "tunga_namn", "senaste",
                                     "rader", "antal_storagare", "storagarbelopp",
                                     "storagare", "bedomning", "bortsorterade_program")},
        })
    rader.sort(key=lambda x: -(x["netto"] or 0))
    return jsonify({"finns": True, "rader": rader, "tid": res.get("tid")})


@app.route("/api/idag")
def idag():
    """Dagens tre högar: undvik, läs först, inget hindrar."""
    res = sk.las_sparat()
    if not res:
        return jsonify({"finns": False})
    inst = sk.las_installningar()
    kapital = float(inst.get("kapital_kr") or 100000)
    ut = rd.dagens_lista(res["case"], kapital)
    ut["finns"] = True
    ut["kapital"] = kapital
    ut["tid"] = res.get("tid")
    ut["antal_bolag"] = len(res["case"])
    return jsonify(ut)


@app.route("/api/rad/<path:sym>")
def rad_for(sym):
    res = sk.las_sparat()
    if not res:
        return jsonify({"fel": "Ingen skanning."}), 404
    c = next((x for x in res["case"] if x["symbol"] == sym), None)
    if not c:
        return jsonify({"fel": f"{sym} finns inte i skanningen."}), 404
    kapital = float(sk.las_installningar().get("kapital_kr") or 100000)
    return jsonify(rd.rekommendation(c, kapital))


@app.route("/api/omskrivet")
def omskrivet():
    """
    Alla bolag rangordnade efter hur mycket de skrivit om sin rapporttext.

    Räknas ur den sparade skanningen — ingen ny hämtning behövs, siffrorna finns
    redan. Tre saker görs här som inte får glömmas bort:

      * Texter som inte är jämförbara (cosinuslikhet under 0,30) sorteras UT ur
        rangordningen och redovisas separat. De är nästan alltid olika språk
        eller en PDF som inte gick att textextrahera — inte en omskrivning. Utan
        det filtret består toppen av listan av mätfel, och då är listan värdelös.
      * Riskavsnittet väger tyngst när det finns, annars hela rapporten. Det var
        i riskavsnittet Lazy Prices-studien fann effekten.
      * Tonlägesförändringen räknas som skillnaden mot föregående rapport i
        samma bolag — aldrig mot andra bolag.
    """
    res = sk.las_sparat()
    if not res:
        return jsonify({"finns": False})

    rader, ej_jamforbara = [], []
    for c in res["case"]:
        r = c.get("rapport") or {}
        if not r.get("tillganglig"):
            continue
        fr = r.get("forandring_risk") or {}
        fh = r.get("forandring_hela") or {}
        likhet = fr.get("cosinuslikhet")
        var = "riskavsnittet"
        if likhet is None:
            likhet, var = fh.get("cosinuslikhet"), "hela rapporten"
        if likhet is None:
            continue

        trend = r.get("tonlagestrend") or []
        ton_nu = trend[-1]["negativa_pct"] if trend else None
        ton_forra = trend[-2]["negativa_pct"] if len(trend) > 1 else None

        post = {
            "symbol": c["symbol"], "namn": c["namn"], "bransch": c.get("bransch"),
            "marknad": c.get("marknad"), "grupp": c.get("grupp"),
            "poang": c.get("poang"), "kalla": r.get("kalla", "SEC"),
            "rapportdatum": (r.get("senaste") or {}).get("datum"),
            "form": r.get("form"),
            "jamford_med": (r.get("foregaende") or {}).get("datum"),
            "likhet": likhet,
            "vad": var,
            "likhet_hela": fh.get("cosinuslikhet"),
            "likhet_risk": fr.get("cosinuslikhet"),
            "tolkning": (fr.get("tolkning") or fh.get("tolkning")),
            "langdforandring": (fr.get("langdforandring")
                                if fr.get("langdforandring") is not None
                                else fh.get("langdforandring")),
            "nya_risker": len(r.get("nya_risker") or []),
            "nya_risker_text": [n["text"][:400] for n in (r.get("nya_risker") or [])[:3]],
            "flaggvikt": sum(f["vikt"] for f in (r.get("roda_flaggor") or [])),
            "flaggor": [f["flagga"] for f in (r.get("roda_flaggor") or [])],
            "negativa_pct": ton_nu,
            "negativa_forandring": (None if (ton_nu is None or ton_forra is None)
                                    else ton_nu - ton_forra),
        }
        # OBS: `tolkning` är det korta ordet ("kraftigt omskriven") som visas i
        # tabellen. Meningarna heter `forklaring` — de skrev över varandra en
        # gång och kolumnen visade [object Object].
        post["forklaring"] = rl.tolkning(r)

        # En text som blivit dubbelt så lång får låg cosinuslikhet av ren
        # matematik, oavsett om innehållet skrivits om eller bara utökats med
        # ett nytt kapitel. Diodes låg överst i listan med +842 % längd — det
        # är inte en omskrivning, det är två olika mängder text. De märks ut
        # och sorteras sist i stället för att toppa listan som falsklarm.
        langd = post.get("langdforandring")
        post["langdvarning"] = langd is not None and abs(langd) > 1.0

        (ej_jamforbara if likhet < 0.30 else rader).append(post)

    # Rangordna INOM marknaden. En svensk delårsrapport är 20-50 sidor och
    # varierar naturligt mycket mellan kvartal; en amerikansk 10-K är 200 sidor
    # mall som ändras marginellt. Rått jämfört hamnar därför alla svenska bolag
    # överst utan att något hänt. Percentilen svarar på rätt fråga: har DET HÄR
    # bolaget skrivit om mer än andra bolag med samma sorts rapport?
    for marknad in {r["marknad"] for r in rader}:
        i_marknaden = sorted([r for r in rader if r["marknad"] == marknad],
                             key=lambda x: x["likhet"])
        n = len(i_marknaden)
        for i, r in enumerate(i_marknaden):
            r["percentil_marknad"] = (i / max(n - 1, 1)) * 100
            r["antal_i_marknaden"] = n
            r["median_marknad"] = i_marknaden[n // 2]["likhet"]

    # Längdartefakter sist, hur låg deras likhet än är.
    rader.sort(key=lambda x: (x["langdvarning"], x["percentil_marknad"]))
    return jsonify({"finns": True, "rader": rader, "ej_jamforbara": ej_jamforbara,
                    "tid": res.get("tid"), "antal": len(rader),
                    "textdom": (va.las_tavla() or {}).get("bara_rapport")})


@app.route("/api/hjalp")
def hjalp():
    """Arbetsgången och hela ordlistan. Hjälp-fliken byggs helt av det här."""
    return jsonify({"steg": ol.STEG, "ord": ol.ORD, "grupper": ol.grupper()})


# --------------------------------------------------------------- metod ----

@app.route("/api/metod")
def metod():
    """Allt som appen räknar, med källa. Gränssnittet bygger Metod-fliken av detta."""
    ut = []
    for pelare, matt_ in C.PELARE.items():
        for falt, riktning, vikt, etikett, enhet in matt_:
            ut.append({"pelare": pelare, "falt": falt, "etikett": etikett,
                       "riktning": riktning, "vikt": vikt, "enhet": enhet,
                       "text": C.BEVISTEXT.get(falt, "")})
    return jsonify({
        "matt": ut,
        "profiler": C.PROFILER,
        "varningar": [{"nyckel": n, "avdrag": a, "rubrik": r, "forklaring": f}
                      for n, a, r, f in C.VARNINGAR],
        "flaggor": [{"monster": p[0], "vikt": p[1], "forklaring": p[2],
                     "negation": p[3] if len(p) > 3 else None}
                    for p in rl.RODA_FLAGGOR],
    })


def _tyst_start(port: int) -> None:
    """
    Byter Flasks standardbanner mot ett begripligt startmeddelande.

    Flask skriver annars ut en röd varning om att det här är en
    "development server" som inte ska användas i produktion. Den varningen
    gäller servrar som ligger öppna på internet för många samtidiga besökare.
    Den här servern lyssnar bara på 127.0.0.1 — din egen dator — och har exakt
    en användare. Varningen är alltså korrekt men irrelevant, och röd text som
    inte betyder något lär bara ögat att ignorera röd text som gör det.

    Loggraden per anrop tystas också. Den sa bara "webbläsaren hämtade en sida,
    och det gick bra" femton gånger i rad.
    """
    import logging
    from flask import cli
    cli.show_server_banner = lambda *a, **k: None
    logging.getLogger("werkzeug").setLevel(logging.ERROR)


if __name__ == "__main__":
    port = 8810
    with open(os.path.join(HAR, "app.pid"), "w") as f:
        f.write(str(os.getpid()))
    _tyst_start(port)

    res = sk.las_sparat() or {}
    skannad = (res.get("tid") or "")[:16].replace("T", " ")
    print(flush=True)
    print(f"   Borscase v{ver.VERSION}  ({ver.DATUM})")
    print(f"   Adress:     http://127.0.0.1:{port}")
    print(f"   Data:       {skannad or 'ingen skanning gjord an'}"
          f"{f', {len(res.get(chr(99) + chr(97) + chr(115) + chr(101)) or [])} bolag' if res else ''}")
    print(f"   Mapp:       {HAR}")
    print()
    print("   Webblasaren oppnas av sig sjalv. Later den vanta - oppna adressen manuellt.")
    print("   Stang med STOPPA_APP.bat, eller Ctrl+C har i fonstret.")
    print("   Det har fonstret maste vara oppet sa lange du anvander appen.")
    print(flush=True)

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
