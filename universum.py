"""
universum.py — vilka bolag som jagas, och varför just de.

Urvalskriteriet är banalt men viktigt: bolag du faktiskt kan köpa på Avanza till
rimlig spread, och som har tillräckligt lång rapporthistorik för att gå att
bedöma. Storbolag på Stockholmsbörsen + amerikanska large/mid cap.

Amerikanska bolag får dessutom `edgar: True` — för dem finns hela rapport-
historiken i SEC:s XBRL-API med publiceringsdatum, vilket är det enda sättet att
göra en ärlig historisk test utan look-ahead-bias.

Lägg gärna till egna bolag i `EGNA` (installningar.json -> "egna_bolag").
"""

SVERIGE = {
    # Verkstad & industri
    "ATCO-A.ST": ("Atlas Copco A", "Industri"),
    "SAND.ST": ("Sandvik", "Industri"),
    "ALFA.ST": ("Alfa Laval", "Industri"),
    "EPI-A.ST": ("Epiroc A", "Industri"),
    "VOLV-B.ST": ("Volvo B", "Industri"),
    "SKF-B.ST": ("SKF B", "Industri"),
    "ASSA-B.ST": ("Assa Abloy B", "Industri"),
    "HEXA-B.ST": ("Hexagon B", "Teknik"),
    "TREL-B.ST": ("Trelleborg B", "Industri"),
    "INDT.ST": ("Indutrade", "Industri"),
    "ADDT-B.ST": ("Addtech B", "Industri"),
    "LIFCO-B.ST": ("Lifco B", "Industri"),
    "NIBE-B.ST": ("Nibe B", "Industri"),
    "SAAB-B.ST": ("Saab B", "Försvar"),
    "MTRS.ST": ("Munters", "Industri"),
    "BEIJ-B.ST": ("Beijer Ref B", "Industri"),
    "AQ.ST": ("AQ Group", "Industri"),
    "VOLCAR-B.ST": ("Volvo Car B", "Fordon"),
    "AUTO.ST": ("Autoliv SDB", "Fordon"),
    "HUSQ-B.ST": ("Husqvarna B", "Industri"),
    "ELUX-B.ST": ("Electrolux B", "Sällanköp"),
    "GETI-B.ST": ("Getinge B", "Hälsovård"),
    "ERIC-B.ST": ("Ericsson B", "Teknik"),
    "SECU-B.ST": ("Securitas B", "Tjänster"),
    "SWEC-B.ST": ("Sweco B", "Tjänster"),
    "AFRY.ST": ("AFRY", "Tjänster"),
    # Råvaror & skog
    "BOL.ST": ("Boliden", "Råvaror"),
    "SSAB-B.ST": ("SSAB B", "Råvaror"),
    "HOLM-B.ST": ("Holmen B", "Skog"),
    "SCA-B.ST": ("SCA B", "Skog"),
    "BILL.ST": ("Billerud", "Skog"),
    "LUMI.ST": ("Lundin Mining", "Råvaror"),
    # Bank & finans
    "SEB-A.ST": ("SEB A", "Bank"),
    "SHB-A.ST": ("Handelsbanken A", "Bank"),
    "SWED-A.ST": ("Swedbank A", "Bank"),
    "NDA-SE.ST": ("Nordea", "Bank"),
    "INVE-B.ST": ("Investor B", "Investmentbolag"),
    "INDU-C.ST": ("Industrivärden C", "Investmentbolag"),
    "LATO-B.ST": ("Latour B", "Investmentbolag"),
    "KINV-B.ST": ("Kinnevik B", "Investmentbolag"),
    "EQT.ST": ("EQT", "Finans"),
    # Fastigheter
    "BALD-B.ST": ("Balder B", "Fastighet"),
    "CAST.ST": ("Castellum", "Fastighet"),
    "FABG.ST": ("Fabege", "Fastighet"),
    "WALL-B.ST": ("Wallenstam B", "Fastighet"),
    "SAGA-B.ST": ("Sagax B", "Fastighet"),
    # Konsument, hälsa, telekom, bygg
    "AZN.ST": ("AstraZeneca", "Hälsovård"),
    "HM-B.ST": ("H&M B", "Sällanköp"),
    "EVO.ST": ("Evolution", "Spel"),
    "TELIA.ST": ("Telia", "Telekom"),
    "TEL2-B.ST": ("Tele2 B", "Telekom"),
    "AXFO.ST": ("Axfood", "Dagligvaror"),
    "SKA-B.ST": ("Skanska B", "Bygg"),
    "PEAB-B.ST": ("Peab B", "Bygg"),
    "NCC-B.ST": ("NCC B", "Bygg"),
    "ABB.ST": ("ABB", "Industri"),
    "ATCO-B.ST": ("Atlas Copco B", "Industri"),
    "TIETOS.ST": ("Tietoevry", "Teknik"),
    "SINCH.ST": ("Sinch", "Teknik"),
    "VITR.ST": ("Vitrolife", "Hälsovård"),
    "THULE.ST": ("Thule Group", "Sällanköp"),
    "DOM.ST": ("Dometic", "Sällanköp"),
}

USA = {
    # Teknik
    "AAPL": ("Apple", "Teknik"),
    "MSFT": ("Microsoft", "Teknik"),
    "GOOGL": ("Alphabet", "Teknik"),
    "META": ("Meta Platforms", "Teknik"),
    "NVDA": ("Nvidia", "Halvledare"),
    "AVGO": ("Broadcom", "Halvledare"),
    "AMD": ("AMD", "Halvledare"),
    "TXN": ("Texas Instruments", "Halvledare"),
    "QCOM": ("Qualcomm", "Halvledare"),
    "MU": ("Micron", "Halvledare"),
    "INTC": ("Intel", "Halvledare"),
    "AMAT": ("Applied Materials", "Halvledare"),
    "LRCX": ("Lam Research", "Halvledare"),
    "KLAC": ("KLA", "Halvledare"),
    "ADI": ("Analog Devices", "Halvledare"),
    "ORCL": ("Oracle", "Teknik"),
    "CRM": ("Salesforce", "Teknik"),
    "ADBE": ("Adobe", "Teknik"),
    "NOW": ("ServiceNow", "Teknik"),
    "INTU": ("Intuit", "Teknik"),
    "IBM": ("IBM", "Teknik"),
    "CSCO": ("Cisco", "Teknik"),
    "ACN": ("Accenture", "Tjänster"),
    "PANW": ("Palo Alto Networks", "Teknik"),
    "SNPS": ("Synopsys", "Teknik"),
    "CDNS": ("Cadence", "Teknik"),
    # Konsument
    "AMZN": ("Amazon", "Sällanköp"),
    "TSLA": ("Tesla", "Fordon"),
    "HD": ("Home Depot", "Sällanköp"),
    "MCD": ("McDonald's", "Sällanköp"),
    "NKE": ("Nike", "Sällanköp"),
    "SBUX": ("Starbucks", "Sällanköp"),
    "LOW": ("Lowe's", "Sällanköp"),
    "TJX": ("TJX", "Sällanköp"),
    "COST": ("Costco", "Dagligvaror"),
    "WMT": ("Walmart", "Dagligvaror"),
    "PG": ("Procter & Gamble", "Dagligvaror"),
    "KO": ("Coca-Cola", "Dagligvaror"),
    "PEP": ("PepsiCo", "Dagligvaror"),
    "MDLZ": ("Mondelez", "Dagligvaror"),
    "CL": ("Colgate-Palmolive", "Dagligvaror"),
    "NFLX": ("Netflix", "Media"),
    "DIS": ("Disney", "Media"),
    # Hälsovård
    "LLY": ("Eli Lilly", "Hälsovård"),
    "JNJ": ("Johnson & Johnson", "Hälsovård"),
    "UNH": ("UnitedHealth", "Hälsovård"),
    "MRK": ("Merck", "Hälsovård"),
    "ABBV": ("AbbVie", "Hälsovård"),
    "PFE": ("Pfizer", "Hälsovård"),
    "TMO": ("Thermo Fisher", "Hälsovård"),
    "ABT": ("Abbott", "Hälsovård"),
    "DHR": ("Danaher", "Hälsovård"),
    "AMGN": ("Amgen", "Hälsovård"),
    "GILD": ("Gilead", "Hälsovård"),
    "ISRG": ("Intuitive Surgical", "Hälsovård"),
    "VRTX": ("Vertex", "Hälsovård"),
    # Finans
    "BRK-B": ("Berkshire Hathaway B", "Investmentbolag"),
    "JPM": ("JPMorgan Chase", "Bank"),
    "BAC": ("Bank of America", "Bank"),
    "WFC": ("Wells Fargo", "Bank"),
    "GS": ("Goldman Sachs", "Bank"),
    "MS": ("Morgan Stanley", "Bank"),
    "V": ("Visa", "Finans"),
    "MA": ("Mastercard", "Finans"),
    "AXP": ("American Express", "Bank"),
    "BLK": ("BlackRock", "Finans"),
    # Industri, energi, övrigt
    "CAT": ("Caterpillar", "Industri"),
    "DE": ("Deere", "Industri"),
    "HON": ("Honeywell", "Industri"),
    "GE": ("GE Aerospace", "Industri"),
    "BA": ("Boeing", "Försvar"),
    "LMT": ("Lockheed Martin", "Försvar"),
    "RTX": ("RTX", "Försvar"),
    "NOC": ("Northrop Grumman", "Försvar"),
    "UPS": ("UPS", "Transport"),
    "UNP": ("Union Pacific", "Transport"),
    "XOM": ("Exxon Mobil", "Energi"),
    "CVX": ("Chevron", "Energi"),
    "COP": ("ConocoPhillips", "Energi"),
    "LIN": ("Linde", "Kemi"),
    "SHW": ("Sherwin-Williams", "Kemi"),
    "NEM": ("Newmont", "Råvaror"),
    "FCX": ("Freeport-McMoRan", "Råvaror"),
}


# ---------------------------------------------------------------------------
# Halvledare och AI, brett. Ungefär SOXX-korgen (iShares Semiconductor) plus de
# bolag som tjänar pengar på AI-utbyggnaden utan att själva rita kretsar:
# nätverk, kylning, servrar, lagring, datacenter och mjukvaran ovanpå.
#
# Två saker att veta om den här gruppen:
#
#   * ADR:er (ASML, TSMC, Arm, STM, UMC, ASE, Nova, Camtek, Nebius) lämnar 20-F
#     i stället för 10-K. fundamenta.bokslut_edgar hittar rätt blankett själv.
#   * Flera av dem redovisar i annan valuta än de handlas i. TSMC och UMC
#     rapporterar i taiwandollar men taggar USD i XBRL — där kopplas EDGAR bort
#     automatiskt och Yahoo används i stället, annars blir varje nyckeltal fel
#     med växelkursen.
#
# Sektorn är dessutom den mest cykliska som finns. Ett halvledarbolag på
# toppvinst ser billigt ut i exakt fel ögonblick — läs bruttomarginalen över
# tio år, inte P/E-talet för i år.
# ---------------------------------------------------------------------------
HALVLEDARE_AI = {
    # Kretsdesign och analog
    "MRVL": ("Marvell Technology", "Halvledare"),
    "NXPI": ("NXP Semiconductors", "Halvledare"),
    "MCHP": ("Microchip Technology", "Halvledare"),
    "ON": ("ON Semiconductor", "Halvledare"),
    "MPWR": ("Monolithic Power Systems", "Halvledare"),
    "SWKS": ("Skyworks Solutions", "Halvledare"),
    "QRVO": ("Qorvo", "Halvledare"),
    "LSCC": ("Lattice Semiconductor", "Halvledare"),
    "RMBS": ("Rambus", "Halvledare"),
    "CRUS": ("Cirrus Logic", "Halvledare"),
    "SLAB": ("Silicon Labs", "Halvledare"),
    "SYNA": ("Synaptics", "Halvledare"),
    "MTSI": ("MACOM Technology", "Halvledare"),
    "SITM": ("SiTime", "Halvledare"),
    "ALGM": ("Allegro MicroSystems", "Halvledare"),
    "POWI": ("Power Integrations", "Halvledare"),
    "DIOD": ("Diodes Incorporated", "Halvledare"),
    "AOSL": ("Alpha & Omega Semiconductor", "Halvledare"),
    "AMBA": ("Ambarella", "Halvledare"),
    "INDI": ("indie Semiconductor", "Halvledare"),
    "SMTC": ("Semtech", "Halvledare"),
    "VSH": ("Vishay Intertechnology", "Halvledare"),
    "CRDO": ("Credo Technology", "Halvledare"),
    "ALAB": ("Astera Labs", "Halvledare"),
    "ARM": ("Arm Holdings", "Halvledare"),
    "STM": ("STMicroelectronics", "Halvledare"),
    "WOLF": ("Wolfspeed", "Halvledare"),
    "OLED": ("Universal Display", "Halvledare"),
    # Tillverkning och kapsling
    "TSM": ("TSMC", "Halvledare"),
    "UMC": ("United Microelectronics", "Halvledare"),
    "GFS": ("GlobalFoundries", "Halvledare"),
    "AMKR": ("Amkor Technology", "Halvledare"),
    "ASX": ("ASE Technology", "Halvledare"),
    # Utrustning, mätning och material
    "ASML": ("ASML Holding", "Halvledarutrustning"),
    "TER": ("Teradyne", "Halvledarutrustning"),
    "ENTG": ("Entegris", "Halvledarutrustning"),
    "KLIC": ("Kulicke & Soffa", "Halvledarutrustning"),
    "ACLS": ("Axcelis Technologies", "Halvledarutrustning"),
    "FORM": ("FormFactor", "Halvledarutrustning"),
    "ONTO": ("Onto Innovation", "Halvledarutrustning"),
    "NVMI": ("Nova Ltd", "Halvledarutrustning"),
    "CAMT": ("Camtek", "Halvledarutrustning"),
    "IPGP": ("IPG Photonics", "Halvledarutrustning"),
    # AI-infrastruktur: nätverk, servrar, kyla, lagring, datacenter
    "ANET": ("Arista Networks", "AI-infrastruktur"),
    "VRT": ("Vertiv Holdings", "AI-infrastruktur"),
    "SMCI": ("Super Micro Computer", "AI-infrastruktur"),
    "DELL": ("Dell Technologies", "AI-infrastruktur"),
    "HPE": ("Hewlett Packard Enterprise", "AI-infrastruktur"),
    "WDC": ("Western Digital", "AI-infrastruktur"),
    "STX": ("Seagate Technology", "AI-infrastruktur"),
    "NTAP": ("NetApp", "AI-infrastruktur"),
    "CIEN": ("Ciena", "AI-infrastruktur"),
    "LITE": ("Lumentum", "AI-infrastruktur"),
    "COHR": ("Coherent", "AI-infrastruktur"),
    "NBIS": ("Nebius Group", "AI-infrastruktur"),
    "CRWV": ("CoreWeave", "AI-infrastruktur"),
    "EQIX": ("Equinix", "AI-infrastruktur"),
    "DLR": ("Digital Realty", "AI-infrastruktur"),
    # AI-mjukvara och data
    "PLTR": ("Palantir Technologies", "AI-mjukvara"),
    "SNOW": ("Snowflake", "AI-mjukvara"),
    "MDB": ("MongoDB", "AI-mjukvara"),
    "DDOG": ("Datadog", "AI-mjukvara"),
    "NET": ("Cloudflare", "AI-mjukvara"),
    "CRWD": ("CrowdStrike", "AI-mjukvara"),
    "ESTC": ("Elastic", "AI-mjukvara"),
    "GTLB": ("GitLab", "AI-mjukvara"),
    "S": ("SentinelOne", "AI-mjukvara"),
    "APP": ("AppLovin", "AI-mjukvara"),
    "TWLO": ("Twilio", "AI-mjukvara"),
    "PATH": ("UiPath", "AI-mjukvara"),
    "AI": ("C3.ai", "AI-mjukvara"),
    "TEM": ("Tempus AI", "AI-mjukvara"),
}

USA.update(HALVLEDARE_AI)


# Grupperna är åtskilda av en anledning som är statistisk, inte kosmetisk.
# Percentilerna räknas INOM gruppen. Ett halvledarbolag jämfört med Axfood får
# alltid usel värderingspercentil — inte för att det är dyrt för att vara
# halvledarbolag, utan för att cykliska tillväxtbolag alltid är dyrare än
# dagligvaror. Blandas de i samma rangordning mäter man bransch, inte bolag.
GRUPPER = {
    "karna": "Kärna — svenska storbolag och amerikanska large cap",
    "halvledare_ai": "Halvledare & AI — SOXX-korgen plus AI-infrastruktur och mjukvara",
}


def bygg_universum(extra: dict | None = None, grupper: list | None = None) -> dict:
    """
    {symbol: {namn, bransch, marknad, valuta, edgar, grupp}}

    `grupper` begränsar urvalet, t.ex. ["karna"] för att helt utesluta
    halvledar- och AI-bolagen.
    """
    ut = {}
    for sym, (namn, bransch) in SVERIGE.items():
        ut[sym] = {"symbol": sym, "namn": namn, "bransch": bransch,
                   "marknad": "Sverige", "valuta": "SEK", "edgar": False,
                   "grupp": "karna"}
    for sym, (namn, bransch) in USA.items():
        ut[sym] = {"symbol": sym, "namn": namn, "bransch": bransch,
                   "marknad": "USA", "valuta": "USD", "edgar": True,
                   "grupp": "halvledare_ai" if sym in HALVLEDARE_AI else "karna"}
    for sym, meta in (extra or {}).items():
        ut[sym] = {
            "symbol": sym,
            "namn": meta.get("namn", sym),
            "bransch": meta.get("bransch", "Övrigt"),
            "marknad": meta.get("marknad", "Sverige" if sym.endswith(".ST") else "USA"),
            "valuta": meta.get("valuta", "SEK" if sym.endswith(".ST") else "USD"),
            "edgar": bool(meta.get("edgar", not sym.endswith(".ST"))),
            "grupp": meta.get("grupp", "karna"),
        }
    if grupper:
        ut = {s: m for s, m in ut.items() if m["grupp"] in grupper}
    return ut


# Branscher där de vanliga måtten INTE fungerar rakt av, och som därför
# hanteras separat i matt.py (banker har inte "rörelsekapital", fastighets-
# bolag har negativt kassaflöde efter capex per konstruktion, osv).
SARSKILDA = {
    "Bank": "Balansräkningen ÄR affären. EV, nettoskuld och capex saknar mening.",
    "Finans": "Delvis balansräkningsdriven — tolka skuldsättning försiktigt.",
    "Fastighet": "Värdeförändringar dominerar resultatet; skuld är verktyget, inte risken i sig.",
    "Investmentbolag": "Substansvärdet styr, inte resultaträkningen.",
}
