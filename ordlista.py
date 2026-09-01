"""
ordlista.py — varje ord i appen förklarat för någon som aldrig sett det förut.

Regeln för varje förklaring här: den ska gå att förstå utan att man kan ett
enda finansord sedan tidigare, och den ska säga vad talet betyder FÖR DIG, inte
bara vad det är matematiskt. Ett mått man inte förstår är ett mått man litar
blint på, och det är farligare än att inte ha måttet alls.

`STEG` är arbetsgången. `ORD` är uppslagsverket. Båda serveras till Hjälp-fliken.
"""

STEG = [
    {
        "nr": 1,
        "rubrik": "Kör en skanning",
        "text": "Tryck på <b>Kör ny skanning</b> uppe till höger i Jakt-fliken, eller "
                "dubbelklicka SKANNA.bat. Appen hämtar då bokslut, kurser och "
                "årsredovisningar för alla 217 bolag. Första gången tar det 15–30 "
                "minuter, sedan under en minut eftersom allt sparas på din dator.",
        "tips": "Du behöver inte göra det oftare än ungefär en gång i månaden. "
                "Bokslut kommer fyra gånger om året.",
    },
    {
        "nr": 2,
        "rubrik": "Sålla bort det mesta",
        "text": "Sätt <b>Minsta täckning</b> till 100 % och <b>Varningar</b> till "
                "\"bara utan varning\". Nu ser du bara bolag där hela modellen kunde "
                "räknas och där ingenting ser direkt fel ut. Av 216 bolag blir det "
                "kanske 40. Välj också <b>Grupp</b> — halvledare och AI-bolag jämförs "
                "bara med varandra, eftersom de alltid värderas högre än ett mejeri.",
        "tips": "Det här är appens viktigaste funktion. Den är bättre på att säga "
                "NEJ än JA.",
    },
    {
        "nr": 3,
        "rubrik": "Titta på pelarna, inte på poängen",
        "text": "Varje bolag får betyg i sex pelare. Det du letar efter är ett bolag "
                "som är högt på <b>Kvalitet</b> OCH högt på <b>Värdering</b> samtidigt "
                "— alltså ett bra bolag som är billigt. Det är ovanligt, och när det "
                "händer finns det nästan alltid en anledning. Att hitta den anledningen "
                "är ditt jobb, inte appens.",
        "tips": "Poängen längst till vänster är bara pelarna hopvägda. Den har testats "
                "och klarade inte testet — se Validering-fliken. Läs pelarna i stället.",
    },
    {
        "nr": 4,
        "rubrik": "Öppna bolaget och läs i rätt ordning",
        "text": "Klicka på raden. Läs sedan: först <b>Det som talar emot</b>, sedan "
                "<b>Det som talar för</b>, sedan <b>Rapporten</b> längst ned. Att läsa "
                "invändningarna först är inte pedantiskt — det är det enda sättet att "
                "inte bli förälskad i ett bolag innan man förstått det.",
        "tips": "I Rapporten: har bolaget skrivit om sitt riskavsnitt? Under 0,90 "
                "betyder att något hänt. De nya riskstyckena är bolagets egna ord om "
                "vad som förändrats.",
    },
    {
        "nr": 5,
        "rubrik": "Skriv av \"Vad som skulle göra caset fel\"",
        "text": "Längst ned i varje bolag finns en lista med konkreta villkor som "
                "skulle motbevisa caset. Klistra in den i ett anteckningsblock "
                "tillsammans med bolagets namn och dagens datum. Vid varje "
                "kvartalsrapport går du igenom listan.",
        "tips": "Ett case man inte kan motbevisa är inte ett case, det är en "
                "förhoppning. Den här listan är skillnaden mellan att investera och "
                "att hoppas.",
    },
    {
        "nr": 6,
        "rubrik": "Kolla när rapporten kommer",
        "text": "Kolumnen <b>Rapport</b> visar hur många dagar det är kvar till nästa "
                "rapport, och under den hur mycket aktien BRUKAR röra sig den dagen. "
                "Ericsson rör sig typiskt ±7,8 %, AstraZeneca ±2,6 %. Det talet säger "
                "hur mycket du riskerar om du sitter kvar över rapporten.",
        "tips": "Riktningen går INTE att förutsäga — appen har testat det på 5085 "
                "rapporter och träffade 50,8 %, alltså slantsingling. Storleken är "
                "däremot ett faktum.",
    },
    {
        "nr": 7,
        "rubrik": "Läs Validering-fliken innan du agerar",
        "text": "Där står vad appens rangordning faktiskt klarade när den testades mot "
                "verkligheten, år för år, med enbart information som fanns då. Svaret "
                "är att den inte klarade sig. Det är inte ett fel i appen — det är "
                "det ärligaste den kan ge dig.",
        "tips": "Om någon säljer dig ett verktyg som INTE visar sitt eget testresultat, "
                "är det för att testet inte gick bra.",
    },
]


def _o(term, grupp, kort, lang, tolka=None, fallgrop=None, kalla=None):
    return {"term": term, "grupp": grupp, "kort": kort, "lang": lang,
            "tolka": tolka or [], "fallgrop": fallgrop, "kalla": kalla}


ORD = [
    # ---------------------------------------------------------- appens egna --
    _o("Poäng", "Appens egna begrepp",
       "Alla pelare hopvägda till ett tal mellan 0 och 100.",
       "Varje mått jämförs med de andra bolagen och får en placering. Placeringarna "
       "vägs ihop till pelare, och pelarna till en poäng. 50 är mitten.",
       [("Över 65", "hör till de bättre i sin grupp"),
        ("Under 30", "något är genomgående svagt")],
       "Poängen har testats mot verkligheten och klarade inte testet. Läs den som en "
       "sammanfattning av bolagets siffror, inte som en gissning om framtiden."),

    _o("Percentil", "Appens egna begrepp",
       "Hur bolaget ligger till jämfört med de andra, på en skala 0–100.",
       "Percentil 90 betyder att bolaget är bättre än 90 % av de andra bolagen på just "
       "det måttet. Anledningen till att appen använder placeringar i stället för fasta "
       "gränser är att fasta gränser åldras: \"P/E under 15 är billigt\" var sant 1995 "
       "och är det inte idag.",
       [("Över 75", "topp fjärdedel"), ("Runt 50", "mitten"), ("Under 25", "botten fjärdedel")]),

    _o("Täckning", "Appens egna begrepp",
       "Hur stor del av modellen som faktiskt gick att räkna för bolaget.",
       "Alla mått fungerar inte i alla branscher. En bank har ingen bruttovinst, ett "
       "investmentbolags vinst är bara börsens rörelse bokförd som resultat. Appen "
       "stänger då av de måtten i stället för att räkna fel — och täckningen sjunker.",
       [("100 %", "hela modellen kunde räknas, poängen är jämförbar"),
        ("40 %", "mindre än halva modellen — läs poängen med stor försiktighet"),
        ("Under 35 %", "ingen poäng sätts alls")],
       "En hög poäng med låg täckning är inte samma sak som en hög poäng. Den bygger på "
       "färre saker."),

    _o("Pelare", "Appens egna begrepp",
       "De sex grupperna av mått: Kvalitet, Värdering, Finansiell styrka, Tillväxt, "
       "Marknad och Rapportsignaler.",
       "Varje pelare svarar på en egen fråga. Kvalitet: tjänar bolaget riktiga pengar "
       "på det kapital det binder? Värdering: vad betalar du för de pengarna? "
       "Finansiell styrka: överlever bolaget tre dåliga år? Tillväxt: blir det större? "
       "Marknad: vad tycker andra just nu? Rapportsignaler: vad står det i texten?"),

    _o("Profil", "Appens egna begrepp",
       "Vilka pelare som väger tyngst.",
       "<b>Sammansatt</b> väger allt ungefär lika. <b>Kvalitet</b> lyfter fram bra bolag "
       "även om de är dyra. <b>Värde</b> lyfter fram billiga bolag även om de är trista. "
       "Byter du profil viktas listan om direkt utan att data hämtas på nytt."),

    _o("Grupp", "Appens egna begrepp",
       "Universumet är delat i \"Kärna\" och \"Halvledare & AI\".",
       "Placeringarna räknas inom gruppen. Ett halvledarbolag jämfört med Axfood får "
       "alltid usel värderingsplacering — inte för att det är dyrt för att vara "
       "halvledarbolag, utan för att cykliska tillväxtbolag alltid värderas högre än "
       "dagligvaror. Blandar man dem mäter man bransch i stället för bolag."),

    # ------------------------------------------------------------- kvalitet --
    _o("ROIC (avkastning på investerat kapital)", "Kvalitet",
       "Hur mycket bolaget tjänar per krona det binder i verksamheten.",
       "Räknas som rörelsevinsten efter skatt delat med det kapital verksamheten "
       "kräver (eget kapital plus lån minus kassa). Är ROIC 20 % kan bolaget "
       "återinvestera varje intjänad krona till 20 % — det är hela ränta-på-ränta-"
       "maskinen. Det är förmodligen det enskilt bästa kvalitetsmåttet som finns.",
       [("Över 20 %", "starkt"), ("10–20 %", "normalt bra"),
        ("Under 8 %", "tillväxt förstör värde i stället för att skapa det")],
       "Bolag som köpt tillbaka mycket egna aktier får en pytteliten nämnare och därmed "
       "ROIC på 100 %+. Det är rätt räknat men överdrivet — titta på femårssnittet."),

    _o("Bruttolönsamhet", "Kvalitet",
       "Bruttovinsten delad med bolagets alla tillgångar.",
       "Bruttovinst = försäljning minus vad varorna kostade att tillverka. Måttet ligger "
       "högst upp i resultaträkningen och är därför minst påverkat av bokföringsval "
       "längre ner. Novy-Marx visade 2013 att det förutsäger avkastning bättre än "
       "nettovinsten gör.",
       [("Över 0,33", "starkt"), ("Under 0,15", "svagt")],
       kalla="Novy-Marx (2013), The Other Side of Value"),

    _o("Rörelsemarginal", "Kvalitet",
       "Hur många öre av varje intjänad krona som blir kvar efter alla kostnader utom "
       "räntor och skatt.",
       "20 % rörelsemarginal betyder att bolaget behåller 20 öre per omsatt krona. Hög "
       "marginal betyder oftast att bolaget har något andra inte har — ett varumärke, "
       "ett patent, en position.",
       [("Över 20 %", "starkt"), ("Under 5 %", "tunt — en dålig period äter upp allt")]),

    _o("Bruttomarginal", "Kvalitet",
       "Andelen av försäljningen som är kvar efter tillverkningskostnaden.",
       "Mjukvarubolag ligger på 70–90 % eftersom en extra kopia inte kostar något. "
       "Livsmedelshandel ligger på 20–25 %. Talet säger mest när man jämför ett bolag "
       "med sig självt över tid: en fallande bruttomarginal betyder att någon annan "
       "börjat konkurrera med pris."),

    _o("Kassaflöde delat med vinst", "Kvalitet",
       "Om den redovisade vinsten faktiskt kom in på kontot.",
       "Vinst är en åsikt, kassaflöde är ett faktum. Vinsten kan påverkas av när man "
       "bokför saker; pengarna på banken kan den inte. Ligger kvoten uthålligt under 1 "
       "finns vinsten på papperet men inte i kassan.",
       [("Över 1,0", "bra — kassaflödet överstiger vinsten"),
        ("Under 0,8 flera år i rad", "varningstecken")]),

    _o("Fritt kassaflöde", "Kvalitet",
       "Pengarna som blir över efter att bolaget betalat för att hålla igång och "
       "utveckla verksamheten.",
       "Kassaflöde från rörelsen minus investeringar. Det är de pengar som faktiskt kan "
       "gå till utdelning, återköp, amortering eller förvärv. Ett bolag med hög vinst "
       "men inget fritt kassaflöde tjänar pengar som omedelbart måste stoppas tillbaka "
       "i maskinerna."),

    # ------------------------------------------------------------ värdering --
    _o("P/E-tal", "Värdering",
       "Priset delat med vinsten. Hur många årsvinster du betalar.",
       "P/E 15 betyder att du betalar 15 gånger fjolårets vinst — grovt sett 15 år på "
       "att få tillbaka pengarna om vinsten står still. Lågt P/E är billigt, men "
       "billigt är sällan billigt utan orsak.",
       [("Under 12", "lågt"), ("15–25", "normalt"), ("Över 30", "marknaden förväntar sig tillväxt")],
       "Går bolaget med förlust blir P/E negativt, och då betyder talet ingenting alls. "
       "Appen visar då inget P/E i stället för att låtsas att förlusten är billig."),

    _o("EV (företagsvärde)", "Värdering",
       "Vad hela verksamheten kostar, inte bara aktierna.",
       "Börsvärdet plus skulderna minus kassan. Tänk på det som priset för att köpa "
       "hela bolaget: du får betala för aktierna OCH ta över lånen, men kassan följer "
       "med på köpet. Två bolag kan ha samma börsvärde men helt olika företagsvärde om "
       "det ena är skuldsatt."),

    _o("EBIT / EV", "Värdering",
       "Rörelsevinsten i förhållande till vad hela bolaget kostar.",
       "Ett slags ränta: hur mycket verksamheten producerar per krona du betalar för "
       "den. Måttet är rättvisare än P/E vid jämförelser mellan bolag, eftersom det "
       "bortser från hur bolaget är finansierat och hur mycket skatt det råkar betala.",
       [("Över 10 %", "billigt"), ("Under 4 %", "dyrt")],
       kalla="Greenblatt (2005), The Little Book That Still Beats the Market"),

    _o("EV/EBITDA", "Värdering",
       "Företagsvärdet delat med rörelsevinsten före avskrivningar.",
       "Ungefär ett P/E-tal för hela verksamheten. Används flitigt av köpare av hela "
       "bolag. EBITDA = vinst före räntor, skatt och avskrivningar.",
       [("Under 8", "lågt"), ("8–14", "normalt"), ("Över 20", "högt")],
       "EBITDA bortser från avskrivningar — men maskiner slits på riktigt. För "
       "kapitaltunga bolag smickrar måttet."),

    _o("P/B (pris mot bokfört värde)", "Värdering",
       "Priset delat med det egna kapitalet i böckerna.",
       "P/B 1,0 betyder att du betalar exakt vad tillgångarna är bokförda till. För "
       "banker, fastighetsbolag och investmentbolag är det ett av få mått som faktiskt "
       "betyder något. För ett mjukvarubolag betyder det nästan ingenting, eftersom "
       "värdet ligger i kod och kunder som aldrig bokförs."),

    _o("Direktavkastning", "Värdering",
       "Utdelningen delad med aktiekursen.",
       "4 % direktavkastning betyder att du får tillbaka 4 % av köpeskillingen per år i "
       "kontanter, om utdelningen består.",
       fallgrop="En mycket hög direktavkastning är oftare en varning än en gåva — den "
                "uppstår när kursen fallit för att marknaden tror utdelningen ska "
                "sänkas."),

    # ---------------------------------------------------- finansiell styrka --
    _o("Soliditet", "Finansiell styrka",
       "Hur stor del av bolagets tillgångar som är betalda med egna pengar i stället "
       "för lån.",
       "Soliditet 40 % betyder att 40 öre av varje krona i tillgångar är bolagets eget "
       "kapital och 60 öre är lånat. Ju högre, desto mer tål bolaget att det går dåligt "
       "ett tag utan att banken börjar ställa krav.",
       [("Över 40 %", "starkt"), ("20–40 %", "normalt"), ("Under 20 %", "känsligt")],
       "Banker har alltid låg soliditet, ofta 5–8 %. Det är hela affärsmodellen — de "
       "lånar in för att låna ut — inte en svaghet. Appen stänger därför av måttet "
       "för banker."),

    _o("Nettoskuld / EBITDA", "Finansiell styrka",
       "Hur många års rörelsevinst det skulle ta att betala av skulderna.",
       "Nettoskuld = lån minus kassa. Är kvoten 2,0 tar det två år av full vinst att bli "
       "skuldfri. Det är det mått banker och kreditvärderare tittar på först.",
       [("Under 1", "mycket lågt"), ("1–2,5", "normalt"),
        ("Över 3,5", "ansträngt — bolaget har lite marginal om det går dåligt"),
        ("Negativt", "bolaget har mer pengar i kassan än det har lån")],
       "Skuldsättning är det som gör en dålig period till en existentiell period. Ett "
       "obelånat bolag kan ha fel i tre år; ett hårt belånat kan inte ha fel i ett."),

    _o("Räntetäckningsgrad", "Finansiell styrka",
       "Hur många gånger rörelsevinsten täcker räntekostnaden.",
       "Är den 8 kan vinsten falla med nästan 90 % innan bolaget inte längre klarar sina "
       "räntor. Under 2 är det obehagligt nära kanten.",
       [("Över 8", "tryggt"), ("3–8", "normalt"), ("Under 2", "farligt")]),

    _o("Kassalikviditet", "Finansiell styrka",
       "Om bolaget har tillräckligt med pengar och kortfristiga tillgångar för att "
       "betala det som förfaller inom ett år.",
       "Omsättningstillgångar delat med kortfristiga skulder. Under 1,0 betyder att "
       "bolaget måste låna, sälja något eller få in pengar snabbt för att klara nästa "
       "år — vilket ofta går bra, men inte alltid."),

    _o("Piotroski F-score", "Finansiell styrka",
       "Nio ja/nej-frågor om bolaget blir bättre eller sämre. Poäng 0–9.",
       "Frågorna handlar om lönsamhet (går bolaget med vinst? kommer pengarna in?), "
       "finansiering (minskar skulderna? ges nya aktier ut?) och effektivitet (stiger "
       "marginalen? säljer man mer per tillgång?). Poängen mäter RIKTNING, inte nivå — "
       "alltså om det underliggande förbättras.",
       [("8–9", "starkt"), ("4–7", "mitten"), ("0–3", "svagt")],
       "Modellen är framtagen för vanliga bolag och utesluter uttryckligen banker och "
       "finansbolag. Appen visar den därför inte för dem.",
       kalla="Piotroski (2000)"),

    _o("Altman Z'' (konkursmått)", "Finansiell styrka",
       "Ett enda tal som skattar hur nära ekonomisk kollaps ett bolag är.",
       "Formeln väger ihop fyra saker: hur mycket rörelsekapital bolaget har i "
       "förhållande till sina tillgångar, hur mycket vinst det samlat på sig genom åren, "
       "hur mycket det tjänar på sina tillgångar nu, och hur stort det egna kapitalet är "
       "mot skulderna. Edward Altman tog fram den 1968 genom att jämföra bolag som gick "
       "i konkurs med bolag som överlevde. Dubbelapostrofen betyder att det är den "
       "variant som fungerar även för bolag som inte tillverkar saker.",
       [("Över 2,6", "säker zon"), ("1,1–2,6", "grå zon"),
        ("Under 1,1", "nödzon — statistiskt förhöjd konkursrisk")],
       "Måttet säger inget om aktiekursen. Men bolag i nödzonen tenderar att lösa sina "
       "problem genom att ge ut nya aktier — och det är du som blir utspädd.",
       kalla="Altman (1968, 1995)"),

    _o("Ohlson O-score", "Finansiell styrka",
       "Ett andra konkursmått som ger en sannolikhet i stället för ett betyg.",
       "Kompletterar Altman genom att särskilt väga in om bolaget gått med förlust två "
       "år i rad och om skulderna överstiger tillgångarna.",
       kalla="Ohlson (1980)"),

    # -------------------------------------------------------------- tillväxt --
    _o("Tillväxt (CAGR)", "Tillväxt",
       "Genomsnittlig årlig ökning, utjämnad över flera år.",
       "CAGR står för genomsnittlig årlig tillväxttakt. Har omsättningen gått från 100 "
       "till 133 på tre år är CAGR 10 % per år. Poängen med att räkna så är att ett "
       "enskilt bra eller dåligt år inte får styra bilden."),

    _o("Marginaltrend", "Tillväxt",
       "Om marginalen stiger eller faller över åren.",
       "Ett bolag som växer med fallande marginal köper sin tillväxt. Ett som växer med "
       "stigande marginal blir starkare medan det växer — det är den betydligt bättre "
       "sorten."),

    _o("Rule of 40", "Tillväxt",
       "Tumregel för mjukvarubolag: tillväxt i procent plus marginal i procent bör vara "
       "minst 40.",
       "30 % tillväxt och 10 % marginal ger 40 — godkänt. Tanken är att ett ungt bolag "
       "får välja mellan att växa fort eller tjäna pengar, men inte att göra ingetdera. "
       "Appen visar måttet bara för bolag med mycket hög bruttomarginal, eftersom det "
       "inte betyder något för verkstadsindustri."),

    # --------------------------------------------------------------- marknad --
    _o("Momentum 12–1", "Marknad",
       "Kursutvecklingen det senaste året, men utan den senaste månaden.",
       "Aktier som gått bra ett år har historiskt fortsatt gå något bättre än snittet en "
       "tid till. Den senaste månaden räknas bort eftersom den tvärtom brukar vända — "
       "det är två olika effekter som annars tar ut varandra.",
       kalla="Jegadeesh & Titman (1993)"),

    _o("Volatilitet", "Marknad",
       "Hur mycket kursen svänger, uttryckt som procent per år.",
       "Volatilitet 30 % betyder ungefär att aktien under ett normalår rör sig ±30 % "
       "runt sin bana. Det är inte samma sak som risk för att förlora pengar — det är "
       "risk för att det svänger. Men det avgör hur mycket du står ut med att äga."),

    _o("Största fall (max drawdown)", "Marknad",
       "Den värsta resan från topp till botten som aktien gjort.",
       "Står det −71 % betyder det att den som köpte på toppen såg sju tiondelar av "
       "pengarna försvinna innan det vände. Det är den siffra du ska fråga dig själv om "
       "du hade suttit kvar genom.",
       fallgrop="Nästan alla bra bolag har en riktigt otäck siffra här. Det är själva "
                "priset för avkastningen."),

    _o("Beta", "Marknad",
       "Hur mycket aktien brukar röra sig när hela börsen rör sig.",
       "Beta 1,3 betyder att aktien historiskt rört sig 30 % mer än marknaden åt båda "
       "hållen. Beta 0,7 betyder lugnare än marknaden."),

    # -------------------------------------------------------------- varningar --
    _o("Periodiseringar (accruals)", "Varningar",
       "Skillnaden mellan redovisad vinst och pengar som verkligen kom in.",
       "En stor del av vinsten kan bestå av bokföringsposter — fakturerat men inte "
       "betalt, varulager som räknas som värde, kostnader som skjutits framåt. Sloan "
       "visade 1996 att bolag med höga periodiseringar systematiskt gick sämre året "
       "efter.",
       [("Under 0", "bra — kassan växer snabbare än vinsten"),
        ("Över 0,10", "flagga")],
       kalla="Sloan (1996)"),

    _o("Beneish M-score", "Varningar",
       "Ett mått som letar efter mönster typiska för bolag som skönmålat sin bokföring.",
       "Åtta index vägs ihop: växer kundfordringarna fortare än försäljningen? Faller "
       "bruttomarginalen? Skjuts kostnader framåt? Modellen flaggade Enron ett år före "
       "kollapsen.",
       [("Över −1,78", "liknar statistiskt ett bolag som manipulerat")],
       "Det är INTE en anklagelse. Snabbväxande bolag som gör förvärv triggar modellen "
       "helt oskyldigt — Nvidia gör det. Läs det som \"gå och läs noterna\", inget mer.",
       kalla="Beneish (1999)"),

    _o("Tillgångstillväxt", "Varningar",
       "Hur snabbt balansräkningen växer.",
       "Bolag som blåser upp sina tillgångar snabbt — genom förvärv eller stora "
       "investeringar — har historiskt gett sämre avkastning de följande åren. "
       "Förklaringen är enkel: man expanderar som mest när optimismen är som störst, "
       "och det är sällan rätt tidpunkt.",
       [("Över 30 % på ett år", "flagga")],
       kalla="Cooper, Gulen & Schill (2008)"),

    _o("Utspädning", "Varningar",
       "Att antalet aktier ökar, så att din andel av bolaget krymper.",
       "Äger du 1 % av ett bolag som ger ut 10 % nya aktier äger du plötsligt 0,91 %, "
       "utan att någon frågat dig. Nya aktier ges ut för att betala förvärv, för att "
       "belöna personal med optioner, eller för att bolaget behöver pengar.",
       fallgrop="Det är den tystaste formen av förlust — kursen kan stå still medan din "
                "andel krymper år efter år."),

    _o("Going concern", "Varningar",
       "Engelska för \"fortsatt drift\". När revisorn skriver att det finns "
       "\"substantial doubt\" om detta ifrågasätter hen om bolaget överlever tolv "
       "månader till.",
       "Det är revisorns starkaste formulering och den står aldrig av misstag. Appen "
       "drar av 25 poäng när den hittas — mer än någon annan varning.",
       fallgrop="Frasen förekommer också som ren rutintext i redovisningsprinciperna. "
                "Appen kräver därför orden \"substantial doubt\" i närheten."),

    _o("Material weakness", "Varningar",
       "Väsentlig brist i den interna kontrollen.",
       "Bolaget säger själv att dess system för att få siffrorna rätt inte fungerar. "
       "Det betyder att alla andra tal i rapporten är mindre pålitliga.",
       fallgrop="Varenda årsredovisning innehåller meningen \"ingen väsentlig brist "
                "identifierades\" och varenda revisionsberättelse innehåller \"bedömer "
                "risken för att en väsentlig brist finns\". Appen har därför ett filter "
                "som kastar träffar med nekande formulering runt sig."),

    _o("Kontrollbalansräkning", "Varningar",
       "Ett svenskt begrepp, och ett av de allvarligaste som finns.",
       "Den måste upprättas när bolagets egna kapital gått under halva aktiekapitalet. "
       "Därefter har styrelsen åtta månader på sig att återställa kapitalet, annars ska "
       "bolaget likvideras. Står ordet i en rapport är det inte en detalj."),

    # --------------------------------------------------------- rapportläsning --
    _o("Språkförändring (Lazy Prices)", "Rapportläsning",
       "Hur mycket bolaget skrivit om sin rapporttext jämfört med förra året.",
       "Bolag skriver rapporter genom att kopiera fjolårets text och ändra det som "
       "behöver ändras. Tre forskare mätte 2020 hur mycket texten ändrats och fann att "
       "de bolag som ändrade MEST gav sämst avkastning året efter — särskilt när "
       "ändringen låg i riskavsnittet. Talet 1,000 betyder ordagrant samma text.",
       [("Över 0,97", "nästan oförändrad"), ("0,92–0,97", "normalt omskriven"),
        ("Under 0,90", "bolaget har aktivt skrivit om sin riskbild"),
        ("Under 0,30", "texterna är inte jämförbara — olika språk eller trasig PDF")],
       kalla="Cohen, Malloy & Nguyen (2020), Journal of Finance"),

    _o("Tonläge", "Rapportläsning",
       "Andelen negativa, osäkra och juridiska ord i rapporten.",
       "Vanliga ordlistor för att mäta tonläge är gjorda för romaner och tror att ord "
       "som \"skuld\", \"skatt\" och \"kostnad\" är negativa. Loughran och McDonald "
       "byggde 2011 listor särskilt för finansiella texter, och det är de som används "
       "här.",
       fallgrop="Jämför ALLTID ett bolag med sig självt över tid. Att ett bolag har "
                "fler negativa ord än ett annat kan lika gärna bero på bransch eller "
                "jurister.",
       kalla="Loughran & McDonald (2011)"),

    _o("Nya riskstycken", "Rapportläsning",
       "De stycken i riskavsnittet som inte fanns i fjolårets rapport.",
       "Det här är ofta det mest informativa i hela årsredovisningen: bolagets egen, "
       "juridiskt granskade beskrivning av vad som förändrats sedan sist. Ingen skriver "
       "in en ny risk för nöjes skull."),

    _o("10-K", "Rapportläsning",
       "Den amerikanska årsredovisningen.",
       "Ett 100–200 sidor långt dokument som varje börsnoterat amerikanskt bolag måste "
       "lämna till myndigheten SEC. Den innehåller ett lagstadgat riskavsnitt (Item 1A) "
       "där bolaget måste räkna upp allt som kan gå fel. Utländska bolag noterade i USA "
       "lämnar i stället en 20-F."),

    _o("MFN", "Rapportläsning",
       "Den tjänst som distribuerar svenska börsbolags pressmeddelanden.",
       "Sverige har ingen motsvarighet till SEC:s öppna databas, men rapporterna måste "
       "offentliggöras via en godkänd distributör. Appen hämtar delårsrapporterna som "
       "PDF därifrån och jämför alltid mot samma kvartal föregående år — aldrig mot "
       "förra kvartalet, eftersom Q2 alltid skrivs annorlunda än Q4."),

    # ------------------------------------------------------------- validering --
    _o("Point-in-time", "Validering och statistik",
       "Att bara använda information som faktiskt var offentlig den dag man låtsas "
       "fatta beslutet.",
       "Amerikanska bolags siffror finns hos SEC tillsammans med datumet då de "
       "publicerades. Ett bokslut för 2019 som lämnades in i februari 2020 fanns alltså "
       "inte i världen i juni 2019. Utan den kontrollen \"vet\" testet framtiden."),

    _o("Look-ahead bias", "Validering och statistik",
       "Felet att råka använda information som inte fanns då.",
       "Det är det vanligaste sättet att lura sig själv med marknadsdata, och det får i "
       "princip vilken strategi som helst att se lysande ut."),

    _o("Överlevnadsbias", "Validering och statistik",
       "Att bara mäta på de bolag som finns kvar idag.",
       "Bolagen som gick under finns inte med i listan, eftersom de inte längre finns. "
       "Alla historiska resultat blir därför för snälla. Appens validering lider av "
       "detta och säger det rakt ut."),

    _o("Nollkontroll", "Validering och statistik",
       "Att köra exakt samma test på slumpmässiga siffror och se vad slumpen producerar.",
       "Om modellens resultat ryms inom vad ren tur ger, har modellen inte visat "
       "någonting — hur fin tabellen än ser ut. Det är det testet som fällde både den "
       "här appens poäng och den tidigare trendappen."),

    _o("p-värde", "Validering och statistik",
       "Sannolikheten att man fått ett minst så bra resultat av ren tur.",
       "p = 0,03 betyder att slumpen skulle ge ett så här bra utfall i tre fall av "
       "hundra. Vanlig gräns är 0,05. Appens poängmodell landade på p = 0,89 — alltså "
       "sämre än slumpen i nio fall av tio.",
       [("Under 0,05", "resultatet är svårt att förklara med tur"),
        ("Över 0,10", "resultatet ryms i turen")]),

    _o("Spearman (rangkorrelation)", "Validering och statistik",
       "Om ordningen i en lista har något att göra med ordningen i en annan.",
       "+1 betyder perfekt samma ordning, 0 betyder inget samband, −1 betyder exakt "
       "omvänd ordning. Appen mäter om ordningen på poängen hade något att göra med "
       "ordningen på den efterföljande avkastningen. Svaret blev −0,03, alltså inget."),

    _o("Femtedel (kvintil)", "Validering och statistik",
       "Listan delad i fem lika stora högar.",
       "Toppfemtedelen är de 20 % med högst poäng. Att jämföra toppen med botten är "
       "standardsättet att pröva om en rangordning betyder något. I appens test gick "
       "bottenfemtedelen bättre än toppen, vilket är ett tydligt underkännande."),

    # -------------------------------------------------------------- praktiskt --
    _o("Courtage", "Praktiskt",
       "Avgiften du betalar din bank varje gång du köper eller säljer.",
       "Den kan vara en procentsats med ett minimibelopp. Har du en klass med 69 kr i "
       "minimum blir en affär på 5 000 kr dyr: 1,4 % bara i avgift, och lika mycket "
       "igen när du säljer."),

    _o("Spread", "Praktiskt",
       "Skillnaden mellan vad någon vill sälja för och vad någon vill betala.",
       "Du köper alltid till det högre priset och säljer till det lägre. I stora bolag "
       "är skillnaden några tiondels promille; i små bolag kan den vara flera procent, "
       "vilket är en dold kostnad varje gång du handlar."),

    _o("ISK", "Praktiskt",
       "Investeringssparkonto — en kontoform där du inte betalar skatt på vinster.",
       "I stället betalar du en liten årlig schablonskatt på hela värdet, oavsett om du "
       "gått plus eller minus. Att sälja kostar därför ingenting skattemässigt, till "
       "skillnad från en vanlig depå där varje realiserad vinst beskattas med 30 %. "
       "Detta är en beskrivning av hur kontoformerna fungerar, inte skatterådgivning."),

    _o("Utdelning", "Praktiskt",
       "Pengar bolaget betalar ut till sina ägare, oftast en gång om året.",
       "Utdelningen kommer ur vinsten. Ett bolag som delar ut mer än det tjänar gör det "
       "med lånade pengar eller kassan, och det håller inte i längden."),
]


def grupper() -> list[str]:
    sedda = []
    for o in ORD:
        if o["grupp"] not in sedda:
            sedda.append(o["grupp"])
    return sedda
