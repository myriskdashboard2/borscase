# Analysrummet – Börscase 2.0

Öppna http://127.0.0.1:8810/analys när appen kör. Länken finns även överst i den gamla översikten.

## Arbetsgång

1. Välj bolag. Förändringar visar de senaste två tillgängliga årsboksluten, med absoluta förändringar och källmetadata. Ändrade mått sedan den föregående sparade analysen visas separat.
2. Kontrollera rapportdatum, kursdatum, saknade uppgifter och eventuella skillnader mellan SEC och Yahoo. En källkonflikt betyder att uppgifter skiljer mer än 5 procent, inte att någon källa säkert har fel. SEC prioriteras vid samma period och valuta.
3. Läs rapporternas riskstycken och identifierade ledningsuttalanden. Uttalanden hittas med svenska/engelska textregler. De är kandidater, inte AI-verifierade prognoser eller löften. Exakta textutdrag, position i extraherad text och rapportkälla sparas.
4. Spara en investeringstes eller ett mätbart ledningsmål. Välj mått, operator och gräns. Andelar anges som 0,15 för 15 procent; belopp i rapportvalutans hela enheter. Ett ledningsmål kräver källa och exakt bokslutsperiodens slutdatum. För mål stöds intäkter, rörelseresultat, fritt kassaflöde, skuld, kassa och rörelsemarginal. Andra mått stöds i löpande tesbevakning. Saknad målperiod ger väntestatus, inte ett underkänt mål.
5. Öppna värderingen. Fyll i eller kontrollera omsättning, marginal, tillväxt, kassakonvertering efter skatt och återinvestering, kapitalkostnad, terminaltillväxt, nettoskuld, aktier och börsvärde. Alla belopp måste vara i samma rapportvaluta. Förifyllda marknads- och bokslutsvärden kan avse olika datum. Kassakonverteringen är ett eget antagande; den hämtas inte från redovisat kassaflöde.
6. Beräkna tre scenarier, känslighet för marginal/kapitalkostnad och vilken årlig tillväxt dagens börsvärde skulle kräva. DCF-modellen är inte anpassad för banker. Negativt beräknat eget kapital visas som sådant. Per aktie uttrycks i rapportvalutan, inte automatiskt i noteringsvalutan.
7. Hämta och journalför en ny analys när du vill följa upp bolaget. En full skanning sparar också analyser och kör utfallsuppföljningen. Villkor utvärderas mot den senaste sparade analysen när vyn öppnas. Journalfliken visar bevakningar för alla bolag.

## Journal och lärande

SQLite-filen `analysjournal.sqlite3` innehåller oföränderliga observationer, användarvillkor, utfall och modellversioner. Samma bolag och skanningstid sparas bara en gång. Gamla skanningar arkiveras som `legacy` och används aldrig som nya prognoser. Öppna gamla analyser med **Visa** i journalen.

Utfallsuppföljningen mäter 30, 90 och 365 dagar när perioden har gått ut. Inträde sker tidigast nästa kalenderdags handelsstängning efter observationen. Båda prisändpunkterna hämtas från samma justerade serie för att undvika blandade split-/utdelningsbaser. Handel måste finnas nära måldatum; äldre kurser accepteras inte som ett nytt utfall. SPY respektive XACT-OMXS30.ST är jämförelser för amerikanska och svenska aktier. Schablonkostnaden är 0,5 procent tur och retur. Detta är lokal valuta, inte portföljavkastning i SEK eller faktiska mäklarkostnader. Saknade kurser och avnoterade bolag kan fortfarande skapa urvalsbias.

Modellen använder sex fasta variabler: ROIC, rörelsemarginal, FCF/EV, nettoskuld/EBITDA, soliditet och 12–1-månadersmomentum. Den är en ridge-regression som tränar mot nettoöveravkastning efter 90 dagar. Saknade variabler utesluts; inga värden hittas på. Högst en observation per bolag och startmånad används för träningen.

Minst 120 kompletta observationer från 12 startmånader behövs. Därefter tränas modellen med rullande testmånader; varje träningsutfall måste ha avslutats före testperiodens början. Skalning lärs endast på träningsdelen. Minst tre testperioder krävs. Modellens fel jämförs mot prognosen noll nettoöveravkastning. Ett ungefärligt intervall för skillnaden beräknas genom omsampling av testmånader; det eliminerar inte all tids- eller bolagskorrelation.

Modellen kör alltid i **skuggläge**. Nya prognoser sparas tillsammans med den modellversion som gjorde dem och påverkar inga råd. Historiska rullande tester är inte samma sak som verklig framåtriktad prövning. Det finns ingen färdig tränad modell vid installation och ingen garanti att en framtida modell förbättrar avkastningen. Modellen tränar från uppmätta utfall, inte från klick eller självskapade träningsexempel. Inga externa AI-tjänster eller nya API-nycklar används.

Uppföljningen körs vid full skanning och via knappen **Följ upp utfall och utvärdera modell**. Appen schemalägger inte Windows-jobb och arbetar inte när den är stängd.

## Rättad databehandling

- XBRL-perioder håller isär startdatum, slutdatum och enhet. Ett kvartal kan inte längre tränga undan ett helår med samma slutdatum.
- Historiska bokslut byggs fältvis ur senast publicerade observation vid testdatumet. Omräkningar sparas; härledda värden beräknas först efter datumfiltret.
- Fulla årsflöden måste ha startdatum och omfatta 300–400 dagar.
- Skanning och validering använder samma gruppindelning och bankspecifika pelare.
- Yahoo Close utan auto_adjust är fortfarande splitjusterad; senare splitfaktorer återställs för historiska börsvärden i en ny separat cache.
- Saknad växelkurs ger fel i stället för en påhittad kurs 1,0.
- Saknade rapporter/jämförelser ger ofullständigt underlag i stället för ett positivt besked.
- Cache och skanningsfil skrivs via temporär fil och atomiskt filbyte.
- Lokala API-skrivningar accepterar JSON och blockerar främmande Origin/Host. Journalen undantas från Git och zip-paketering.

Äldre historiska valideringar sparades i `backups/version1-validering/`. Nya huvudmodellens resultat finns i `validering_resultat.json`. Överlevnadsbias, dagens universum, approximation av aktieantal mellan rapporter, ADR-förhållanden, upprepade modellförsök och begränsat antal oberoende år kvarstår. Valideringen omfattar USA, inte svenska aktier. Huvudmodellens 13-årstest är explorativt och ska inte behandlas som bevis för en placeringsstrategi.

## Verifiering och drift

`python -B -m unittest test_intel -v` kör 19 tester utan nätverk eller ändringar i den riktiga journalen. Testerna täcker periodkollisioner, publiceringstid/omräkningar, splits, valutafel, saknade rapporter, journalens beständighet, målperioder, DCF-facit, utfallskurser, modellens tidsgränser, API-validering och lokalt åtkomstskydd. Syntetiska data används endast i tester med separat temporär databas.

`node --check analys.js` kontrollerar JavaScript-syntax. De direktberoenden som användes finns i `requirements-tested.txt`; ordinarie installationsfil finns kvar.

En full skanning kördes 2026-09-08: 216 bedömda bolag av 217, 215 med rapport. AUTO.ST saknade bokslut. Huvudvalideringen kördes om: 1 509 observationer, 13 år, cirka −2,84 procentenheter per år mot universumets genomsnitt. Resultatet visar inte någon förbättrad placeringsförmåga.

Säkerhetskopiera journalen med SQLite backup-API medan appen kör, eller kopiera databasfilen när appen är stängd. Ta inte bara huvudfilen under en pågående skrivning, eftersom SQLite kan använda en WAL-fil.


## Nyckeltal i version 2.1 (2026-09-14)

Fliken Nyckeltal samlar 26 belopp och kvoter för kassaflöde, försäljning, marginaler, skuld, värdering och utdelning. Varje kort visar definition, formel, period och källhänvisning. Föregående helår visas när det finns underlag. Stora belopp anges i miljoner (mn) eller miljarder (md) i rapportvalutan. Marginalförändringar anges i procentenheter; tillväxtprocent beräknas bara från ett positivt jämförelsevärde.

Välj senaste helåret eller TTM (fyra sammanhängande kvartal). Om TTM saknas ersätts den inte med helår. TTM-EPS visas inte eftersom ett periodvägt årsaktieantal saknas. Värderingsmåtten använder analysens börsvärde och den valda resultatperioden, inte analytikerprognoser. EV definieras här förenklat som börsvärde plus nettoskuld. Fritt kassaflöde beräknas som operativt kassaflöde minus Capex. Utdelning avser kontant utbetald utdelning under perioden, inte framtida föreslagen utdelning.

Äldre journalposter kan sakna fält som nu sparas, exempelvis EBITDA och utdelning. Hämta och journalför en ny analys för att komplettera. Saknade uppgifter förblir markerade som saknade. Nya analyser för Apple och Atlas Copco har verifierats: 23 respektive 26 tillgängliga helårsmått. För banker undertrycks kvoter som inte är lämpliga.

Siffrorna hämtas från appens bolags- och marknadskällor, inte DI TV. Organisk tillväxt, orderingång/orderbok, konsensus, prognos-P/E och justerad EBITA kräver ytterligare underlag och anges som ej tillgängliga.

Verifiering: `python -B -m unittest test_nyckeltal test_intel -q` (24 tester) och `node --check analys.js`. Fliken och periodbyte har även kontrollerats i webbläsaren.
