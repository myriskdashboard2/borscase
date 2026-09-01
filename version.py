"""
version.py — en enda plats som säger vilken version du kör.

Finns för att det annars är omöjligt att veta. Appen kopieras till USB, packas
i zip, delas vidare och startas från olika mappar — och två fönster kan visa
olika versioner samtidigt om webbläsaren cachat den gamla sidan.

Versionen visas i sidhuvudet tillsammans med när skanningen gjordes, så att
båda frågorna besvaras på en gång: rätt PROGRAM och färsk DATA.
"""

VERSION = "1.12"
DATUM = "2026-08-24"

NYHETER = [
    ("1.12", "2026-08-24",
     "Stödlänkar till Buy Me a Coffee och PayPal — appen är och förblir gratis. "
     "Presentation på /presentation, gjord för att spelas in."),
    ("1.11", "2026-08-20",
     "Startfönstret visar version, adress och datadatum i stället för Flasks "
     "röda produktionsvarning, som gällde en situation appen aldrig är i."),
    ("1.10", "2026-08-19",
     "Versionsnummer och datafärskhet i sidhuvudet. Jakt-fliken talar om när "
     "filtren döljer bolag — Fabege syntes i Insyn men saknades i Jakt utan "
     "förklaring, eftersom täckningsfiltret tog bort den tyst."),
    ("1.9", "2026-08-19",
     "Insynshandel från Finansinspektionen och SEC Form 4. Signalen testades på "
     "1342 observationer och FÖLL (p = 0,75) — domen står i appen."),
    ("1.8", "2026-08-17",
     "Fliken Idag med besked i tre högar, råd per bolag, positionsstorlek i "
     "kronor och läget mot bolagets egen värderingshistorik."),
    ("1.7", "2026-08-14",
     "Fliken Omskrivet: alla bolag rangordnade efter hur mycket rapporttexten "
     "ändrats. Tolkning i klartext under varje bolag."),
    ("1.6", "2026-08-14",
     "Bankerna fick egna nyckeltal (K/I-tal, räntenetto, kapitalstyrka) och "
     "jämförs bara med varandra. Rapportdatum räknas om vid visning."),
    ("1.5", "2026-08-13",
     "Hjälp-flik med arbetsgång i sju steg och ordlista över 55 begrepp. "
     "Resultattavla över alla genomförda test."),
    ("1.4", "2026-08-13",
     "Hela SOXX-korgen plus AI-bolag. Universumet delat i grupper, percentiler "
     "räknas inom gruppen."),
    ("1.3", "2026-08-13",
     "Svenska rapporter läses via MFN. Rapportkalender med historisk "
     "reaktionsstatistik."),
    ("1.0", "2026-08-13",
     "Första versionen: 145 bolag, fem pelare, rapportläsning från SEC, "
     "ärlig validering med nollkontroll."),
]


def kort() -> str:
    return f"v{VERSION} ({DATUM})"
