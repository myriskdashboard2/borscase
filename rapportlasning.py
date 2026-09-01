"""
rapportlasning.py — att faktiskt läsa rapporterna, inte bara siffrorna.

Det här är den del som skiljer verktyget från en vanlig screener. Siffrorna i en
årsredovisning är sammanfattningen; texten är där bolaget måste beskriva vad som
kan gå fel, och där förändringar syns först.

Fyra analyser görs, och alla fyra har en publicerad grund:

1. SPRÅKFÖRÄNDRING ("Lazy Prices", Cohen, Malloy & Nguyen, Journal of Finance
   2020). Bolag skriver om sina rapporter genom att kopiera förra årets text och
   ändra det som behövs. Deras fynd: de bolag som ändrade MEST i sin text gav
   sämst avkastning det följande året — och effekten satt främst i risk-
   avsnittet. Vi mäter likheten mellan i år och i fjol med cosinuslikhet på
   ordfrekvenser. Låg likhet = något har hänt som bolaget kände sig tvunget att
   skriva om.

2. TONLÄGE (Loughran & McDonald, Journal of Finance 2011). Vanliga
   sentimentlexikon är gjorda för romaner och tror att "liability", "tax" och
   "cost" är negativa ord. LM byggde listor specifikt för finansiella texter.
   Här används en delmängd av deras kategorier: negativa, osäkerhets-, tvist-
   och begränsningsord. Delmängd, inte hela listan — måttet ska läsas som en
   trend över tid för samma bolag, inte som ett absolut tal mellan bolag.

3. RÖDA FLAGGOR. Ordagranna formuleringar som betyder något exakt i en
   amerikansk rapport: "going concern", "material weakness in internal control",
   "restatement", "covenant violation". De står aldrig där av misstag.
   Mönstren kräver att något FAKTISKT hänt, inte att det nämns som möjlighet.
   Utan det kravet flaggas varje bolag för goodwillnedskrivning, eftersom alla
   beskriver sin nedskrivningsPRÖVNING i redovisningsprinciperna — och en flagga
   som tänds för alla är värdelös.

4. NYA RISKER. Vilka stycken i riskavsnittet som inte fanns i förra årets
   rapport. Ett nytt riskstycke är bolagets egen juridiska bekännelse om att
   något förändrats.

Fungerar direkt för amerikanska bolag (SEC EDGAR). För svenska bolag finns
ingen motsvarande öppen databas — där kan du peka ut en rapport själv
(URL eller PDF) och få exakt samma analys via `analysera_rapporttext`.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import datakallor as dk

# --------------------------------------------------------------- lexikon --
# Delmängder av Loughran-McDonalds kategorier. Räcker för trendmätning.

LM_NEGATIVA = set("""
abandon abandoned abandoning abandonment adverse adversely adversity against
aggravate alleged allegation allegations annulled anomalies anomaly antitrust
argue argued arguing arrears attrition backlog bad bail bailout bankrupt
bankruptcy barred breach breached breaches break broke burden burdened burdens
cancel canceled cancellation cancellations cease ceased challenge challenged
challenges claim claims closed closing closure closures collapse collision
collusion complain complaint complaints complicate complicated concede conceded
concern concerns condemn confess confession conflict conflicts confront
confusion contempt contend contention contract contraction controversial
controversy convict convicted conviction correction corrections corrosion
costly counterfeit crime criminal crisis critical criticism criticize
critique cumbersome curtail curtailed curtailment cut cutback damage damaged
damages danger dangerous deadlock deadweight decline declined declines
declining deconsolidation default defaulted defaults defect defective defects
defend defendant deficiencies deficiency deficient deficit deficits delay
delayed delays delinquency delinquent demolish demote denial denied denies deny
deplete depleted depletion depress depressed deprive derogatory destroy
destroyed destruction deter deteriorate deteriorated deteriorating
deterioration detriment detrimental devalue devaluation deviate deviation
difficult difficulties difficulty diminish diminished diminishing disadvantage
disadvantaged disagree disagreement disallow disallowed disappear disappointed
disappointing disappointment disaster disastrous disclaim disclaimed
disclosed discontinue discontinued discourage discrepancies discrepancy
dishonest dismiss dismissal dismissed disparage dispute disputed disputes
disqualified disrupt disrupted disruption disruptions dissent dissolution
distort distortion distress distressed disturb divert diverted downgrade
downgraded downsize downtime downturn drought duress dysfunctional egregious
embargo embarrass embezzle encroach endanger enjoin erode eroded erosion
erroneous error errors escalate escalating evade evasion exacerbate exaggerate
excessive exculpatory exploit exposed exposure expropriate fail failed failing
failure failures fallout false falsified fault faulty fear fictitious fined
fines flaw flawed forbear forced forcing foreclose foreclosure forfeit
forfeited fraud fraudulent frivolous frustrate frustration fugitive grievance
guilty halt halted hamper hardship harm harmed harmful hazard hazardous
hinder hindered hostile hurdle hurt idle illegal illegality illiquid illiquidity
impair impaired impairment impairments impede impediment imperfection improper
imprudent inability inaccessible inaccuracies inaccuracy inaccurate inadequacy
inadequate inadvisable incapable incapacity incidence incompatible incompetent
incomplete inconsistencies inconsistency inconsistent incorrect incorrectly
indefeasibly indict indicted indictment ineffective inefficiencies inefficiency
inefficient ineligible inequitable inevitable inexperienced inferior inflicted
infraction infringe infringed infringement inhibit injunction injure injured
injuries injury inordinate inquiry insecure insolvency insolvent instability
insufficiency insufficient interfere interference interruption interruptions
intimidation invalid invalidate investigate investigated investigation
investigations involuntarily involuntary irreconcilable irrecoverable
irregular irregularities irregularity irreparable jeopardize lack lacked
lacking lag lagging lapse late latency lawsuit lawsuits layoff layoffs
lien liens limitation limitations linger liquidate liquidation litigate
litigation lose loses losing loss losses lost malfunction malpractice
manipulate manipulation misappropriation misclassification misconduct
misdemeanor mishandled misinform misinterpretation misjudgment mislabel
mislead misleading mismanage mismatch misplaced misrepresent misrepresentation
misstate misstated misstatement misstatements mistake mistaken misunderstanding
misuse monopolize moratorium negative negatively neglect negligence negligent
nonattainment noncompliance noncompliant nonpayment nonperformance nonperforming
nonproducing nonrecoverable nonrenewal notdefensible nuisance objection
obsolescence obsolete obstacle offense omission omitted onerous opposition
outage outdated overage overbuilt overcapacity overcharge overdue overestimate
overload overpaid overproduction overrun overshadow overstate overstated
overstatement overtly panic penalize penalties penalty peril persist petition
plaintiff plea plead pledged poor poorly postpone postponed postponement
precipitated preclude predatory prejudice prevent prevented probe problem
problematic problems prolonged prone prosecute prosecution protest protested
protracted provoke punish punitive question questionable questioned quit
recall recalled recession reconsider recourse redact redress reduction refusal
refuse refused reject rejected rejection relinquish reluctance remediate
remediation renegotiate renounce repossess repudiate rescind resign resignation
resigned restate restated restatement restatements restrain restraint restrict
restricted restriction restrictions restructure restructuring retaliate
revoke revoked ridicule riskier riskiest risky sacrifice sanction sanctioned
scandal scrutinize scrutiny seize seizure serious setback setbacks sever
severe severely severity shortage shortages shortfall shrinkage shut shutdown
slander slippage slow slowdown slowed slower sluggish solvency spam
stagnant stagnate standstill stolen stoppage stopped stress strain
subpoena substandard sue sued suffer suffered suffering summons surrender
susceptible suspect suspend suspended suspension suspicion suspicious
taint tainted tampering terminate terminated termination testify threat
threaten threatened threats tolerate tortuous tragedy trouble troubled
unable unacceptable unaccounted unannounced unanticipated unapproved
unattractive unauthorized unavailability unavailable unavoidable unaware
uncollectable uncollected uncollectible uncompetitive uncompleted
unconscionable uncontrollable uncontrolled uncorrected uncover uncovered
undelivered undercapitalized undercut underestimate underfunded underinsured
undermine underpaid underperform underperformance underperformed
underproduction underreporting understate understated undesirable undetected
undisclosed undocumented undue unecomonical unemployed unethical unexcused
unexpected unexpectedly unfair unfavorable unfavorably unfeasible unfit
unforeseeable unforeseen unfortunate unfounded unfriendly unfulfilled
uninsured unjust unjustified unknowing unlawful unlicensed unliquidated
unmarketable unmerchantable unnecessary unneeded unobtainable unoccupied
unpaid unperformed unplanned unpopular unpredictable unprofitable
unqualified unrealistic unreasonable unrecoverable unreimbursed unreliable
unremedied unresolved unsafe unsalable unsatisfactory unsatisfied unsavory
unscheduled unsold unsound unstable unsubstantiated unsuccessful unsuitable
unsuited unsupported unsure unsuspecting unsustainable untenable untimely
untrusted untruth unusable unwanted unwarranted unwelcome unwilling
unworthy usurious usurp vandalism violate violated violates violating
violation violations violator volatile volatility vulnerability vulnerable
warn warned warning warnings waste wasted weak weaken weakened weakening
weakness weaknesses willfully worse worsen worsened worsening worst writedown
writedowns writeoff writeoffs wrong wrongdoing wrongful wrongly
""".split())

LM_OSAKERHET = set("""
almost ambiguity ambiguous anticipate anticipated anticipates anticipating
apparent apparently appear appeared appearing appears approximate approximated
approximately approximates arbitrary assume assumed assumes assuming assumption
assumptions believe believed believes believing cautious cautiously clarify
conceivable conditional confuses contingencies contingency contingent could
depend depended depending depends destabilizing deviate differ differed
differing doubt doubtful exposure fluctuate fluctuated fluctuates fluctuating
fluctuation fluctuations hidden hinges imprecise imprecision improbable
incompleteness indefinite indefinitely indeterminable indeterminate
inexact inexactness instabilities instability intangible likelihood may maybe
might nearly nonassessable occasionally ordinarily pending perhaps possible
possibly precaution precautionary predict predictability predicted predicting
prediction predictions predicts preliminarily preliminary presumably presume
probabilistic probability probable probably random randomly reassess
reassessed reassessing recalculate reconsider reexamine reexamining
revise revised risk risked riskier riskiest risks risky rough roughly
seems seldom something sometime sometimes somewhat speculate speculated
speculates speculating speculation speculations speculative sudden suddenly
suggest suggested suggesting suggests susceptibility tending tentative
tentatively turbulence uncertain uncertainly uncertainties uncertainty unclear
unconfirmed undecided undefined undesignated undetectable undetermined
undocumented unequal unexpected unexpectedly unforecasted unforseen
unguaranteed unhedged unidentifiable unidentified unknown unknowns unobservable
unplanned unpredictability unpredictable unpredictably unproved unproven
unquantifiable unquantified unreconciled unseasonable unsettled unspecified
untested unusual unusually unwritten vagaries vague vaguely vagueness
variability variable variables variably variance variances variant variation
variations varied varies vary varying volatile volatility
""".split())

LM_TVIST = set("""
absolve absolved accuse accused acquit acquittal adjudicate adjudication
allegation allegations allege alleged allegedly alleges appeal appealed
appellate arbitrate arbitration attorney attorneys claimant complainant
contractual counterclaim court courts damages defendant defendants deposition
docket enforceability enforceable felony indemnification indemnify indemnity
indict indicted indictment injunction injunctions judicial juries jurisdiction
jurisdictional jury lawsuit lawsuits legislate legislation liable litigant
litigate litigated litigation ordinance plaintiff plaintiffs plea pleading
prosecute prosecution regulate regulated regulation regulations regulatory
settlement statutory subpoena sue sued sues suing summons testimony tort
tribunal verdict
""".split())

LM_BEGRANSNING = set("""
bound bounded commit commitment commitments committed compel compelled compels
comply compulsion confine confined constrain constrained constraining
constraint constraints depend dependance dependence dependencies dependency
dependent depending directive encumber encumbered encumbrance encumbrances
entail escrow forbid forbidden imposed imposes imposing imposition indenture
limit limitation limitations limited limiting limits mandate mandated
mandates mandating mandatory obligate obligated obligation obligations
obligatory oblige obliged precludes prevent prevented preventing prevents
prohibit prohibited prohibiting prohibition prohibitions prohibitive
prohibits require required requirement requirements requires requiring
restrain restricted restricting restriction restrictions restrictive
restricts stipulate stipulated stipulates stipulation stipulations
""".split())

LM_POSITIVA = set("""
able abundance achieve achieved achievement achievements achieves achieving
advancement advances advancing advantage advantaged advantageous advantages
attain attained attaining attains attractive beautiful beneficial benefit
benefited benefiting benefits best better boom boost boosted breakthrough
brilliant charitable collaborate collaborated collaborating collaboration
collaborative compliment complimentary conclusive conducive confident
constructive courteous creative delight delighted delightful dependability
dependable desirable desired despite destined diligent distinction
distinctive easier easily effective efficiencies efficiency efficient
empower enable enabled enables enabling encouraged encouraging enhance
enhanced enhancement enhancements enhances enhancing enjoy enjoyable enjoyed
enjoying enthusiasm enthusiastic excellence excellent exceptional excited
exciting exclusive exclusively exemplary fantastic favorable favorably
favored favoring friendly gain gained gaining gains good great greater
greatest happiness happy highest honor honorable ideal impress impressive
improve improved improvement improvements improves improving incredible
influential informative ingenuity innovate innovation innovations innovative
insightful inspiration integrity leader leadership leading lucrative
meritorious opportunities opportunity optimistic outperform outperformed
outperforming outstanding perfect pleasant pleased pleasure plentiful
popular positive positively preeminent premier prestige prestigious proactive
proficiency proficient profitability profitable progress prospered
prosperous rebound rebounded receptive record regain resolve revolutionize
reward rewarded rewarding satisfaction satisfactorily satisfactory satisfied
smooth solves stability stabilization stabilize stabilized stable strength
strengthen strengthened strengthening strengths strong stronger strongest
succeed succeeded succeeding succeeds success successes successful
successfully superior surpass surpassed surpassing transparency tremendous
unmatched unparalleled unsurpassed upturn valuable versatile vibrant win
winner winning worthy
""".split())

# ---------------------------------------------------------------------------
# Svenska ordlistor. Kortare än de engelska — det finns ingen svensk
# motsvarighet till Loughran-McDonald att luta sig mot, så listorna är byggda
# på samma princip: ord som betyder något negativt SPECIFIKT i en finansiell
# text. Läs alltid de svenska talen som en trend för samma bolag över tid,
# aldrig som en jämförelse mellan två bolag.
# ---------------------------------------------------------------------------

SV_NEGATIVA = set("""
avbrott avbryta avbröt avmattning avskedade avskrivning avslag avslutade
avvattning avveckling avvecklade avvikelse avvikelser besvär bortfall brist
brister bristande brott dröjsmål dålig dåligt efterfrågeminskning eftersläpning
fallande fel felaktig felaktiga fördröjning fördröjningar förlora förlorade
förlust förluster försämrad försämrades försämring försening förseningar
förvärrad haveri hinder hot inbromsning inställd inställda konflikt konkurs
kostnadsökning kris krympande kränkning lagerjustering minskad minskade
minskning missnöje motgång motgångar negativ negativa negativt nedgång
nedjustering nedläggning nedskrivning nedskrivningar nedstängning obestånd
olycka omstrukturering osäker osäkert oro oroande oväntad oväntade press
pressad pressade problem problematisk rättegång rättsprocess sanktion
sanktioner skada skadad skadestånd stopp stoppad störning störningar svag
svaga svagare svaghet svårigheter svårt sviktande tapp tappade tillbakagång
tvist tvister underskott undermålig uppsägning uppsägningar utebliven
utmaning utmaningar varsel viten vite väsentlig ökad_risk överkapacitet
avmattat bristfällig fallit förlustbringande försvagad försvagning
inbromsat instabil instabilitet kostnadsinflation lönsamhetsproblem
marginalpress obalans olönsam prispress rekonstruktion turbulens
underprestera volatil volatilitet återkallelse överskuldsatt
""".split())

SV_OSAKERHET = set("""
antagande antaganden approximativ bedöma bedömer bedömning bedömningar
beroende cirka eventuell eventuella eventuellt förutsatt förväntad förväntade
förväntar förväntas indikation kan komma kanske möjlig möjliga möjligen
osäker osäkerhet osäkerheter osäkerhetsfaktorer oviss ovisshet prognos
prognoser preliminär preliminärt riskerar sannolikhet sannolikt skulle
svårbedömd svårbedömt tros troligen troligt ungefär uppskattning
uppskattningar variation variationer varierande volatil ökad_osäkerhet
avvakta avvaktande beror svårt_att_bedöma osäkra bedömas antas
""".split())

SV_POSITIVA = set("""
attraktiv bra effektiv effektivisering framgång framgångsrik framgångsrikt
fördel fördelaktig förbättrad förbättrades förbättring förstärkning god goda
gott hög högre högsta konkurrenskraftig lönsam lönsamhet lyckad lyckades
möjlighet möjligheter nöjd positiv positiva positivt rekord rekordhög
rekordnivå stabil stabilitet stark starka starkare starkt stigande stärkt
tillväxt uppgång utmärkt vinst växande ökad ökade ökning återhämtning
effektivt gynnsam gynnsamt momentum rekordresultat robust solid
""".split())

SV_TVIST = set("""
domstol dom domar förlikning grupptalan käranden kärande process rättegång
rättsprocess sanktionsavgift skadestånd stämning stämningsansökan svarande
talan tingsrätt tvist tvister vite viten överklagan överklagande åtal
konkurrensverket finansinspektionen tillsynsmyndighet föreläggande
""".split())

# Svenska formuleringar som betyder något exakt. "Kontrollbalansräkning" är den
# allvarligaste av dem alla och saknar engelsk motsvarighet: den upprättas när
# det egna kapitalet understiger halva aktiekapitalet, och därefter har
# styrelsen åtta månader på sig innan bolaget ska likvideras.
SV_RODA_FLAGGOR = [
    (r"kontrollbalansr[äa]kning", 5,
     "Kontrollbalansräkning: det egna kapitalet har gått under halva "
     "aktiekapitalet. Åtta månader till likvidation om det inte återställs.",
     r"\b(?:inte|ej|inget|behöver inte|utan)\b"),
    (r"v[äa]sentlig os[äa]kerhetsfaktor[^.]{0,80}fortsatt drift"
     r"|betydande tvivel[^.]{0,60}fortsatt drift", 5,
     "Väsentlig osäkerhet om fortsatt drift — revisorns fackuttryck för att "
     "bolagets överlevnad är ifrågasatt.", None),
    (r"anm[äa]rkning i revisionsber[äa]ttelsen|revisionsber[äa]ttelse med anm[äa]rkning"
     r"|villkorat uttalande|uttalande med reservation", 4,
     "Revisorn har lämnat en anmärkning eller reservation.", None),
    (r"v[äa]sentlig brist i den interna kontrollen", 4,
     "Väsentlig brist i den interna kontrollen.",
     r"\b(?:inga|ingen|inte|ej)\b"),
    (r"r[äa]ttelse av fel|omr[äa]kning av j[äa]mf[öo]relsetal|justerade j[äa]mf[öo]relsetal", 3,
     "Tidigare siffror har rättats eller räknats om.", None),
    (r"brott mot (?:l[åa]nevillkor|villkor i l[åa]neavtal|covenant)"
     r"|villkoren i l[åa]neavtalen (?:har )?(?:brutits|inte uppfyll)", 4,
     "Lånevillkor brutna.", None),
    (r"f[öo]retr[äa]desemission|nyemission|riktad emission", 3,
     "Emission: nya aktier ges ut och din andel av bolaget krymper.",
     r"\b(?:inte|ej|ingen|planerar inte)\b"),
    (r"omv[äa]nd split|sammanl[äa]ggning av aktier", 3,
     "Omvänd split eller sammanläggning: kursen har fallit långt.", None),
    (r"f[öo]retagsrekonstruktion|ans[öo]kan om konkurs|obest[åa]nd", 5,
     "Rekonstruktion eller konkursrisk.", r"\b(?:inte|ej|ingen)\b"),
    (r"avnotering|handelsstopp|observationslist", 4,
     "Avnotering, handelsstopp eller observationslista.", r"\b(?:inte|ej|ingen)\b"),
    (r"nedskrivning av goodwill|goodwillnedskrivning", 3,
     "Goodwillnedskrivning: ett förvärv blev inte vad man hoppades.",
     r"\b(?:ingen|inga|inte|ej|prövning|prövas|test)\b"),
    (r"varsel om uppsägning|varslat|varslar", 2,
     "Varsel om uppsägningar.", None),
    (r"vd (?:har )?(?:l[äa]mnar|l[äa]mnat|avg[åa]r|avgick)"
     r"|verkst[äa]llande direkt[öo]r (?:l[äa]mnar|avg[åa]r)"
     r"|finanschef(?:en)? (?:l[äa]mnar|avg[åa]r)", 3,
     "Vd eller finanschef lämnar bolaget.", None),
    (r"byte av revisor|revisorn (?:har )?avg[åa]tt", 4,
     "Bolaget har bytt revisor — kolla varför.", None),
    (r"cyberangrepp|cyberattack|dataintr[åa]ng|it-incident", 2,
     "Cyberincident eller dataintrång.", r"\b(?:inte|ej|ingen|risk f[öo]r)\b"),
    (r"[åa]terkallelse av produkt|produkt[åa]terkallelse", 2,
     "Produktåterkallelse.", None),
]


# Formuleringar som betyder något exakt. Vikten är hur illa det är, 1-5.
#
# Fjärde fältet är ett NEGATIONSMÖNSTER: hittas det i närheten av träffen kastas
# träffen. Utan det blir "material weakness" den mest värdelösa flaggan i hela
# appen, eftersom varenda 10-K innehåller meningen "management concluded that
# our internal control was effective and no material weakness was identified".
# En flagga som tänds för alla säger ingenting om någon.
RODA_FLAGGOR = [
    (r"substantial doubt about (?:the|our) ability to continue as a going concern",
     5, "Går-vidare-tvivel: revisorn ifrågasätter om bolaget överlever tolv månader."),
    (r"(?:substantial|significant) doubt[^.]{0,60}going concern", 4,
     "Uttryckt tvivel om fortlevnaden. Termen 'substantial doubt' är revisorns "
     "fackuttryck, inte en tillfällighet."),
    (r"(?:identified|concluded|disclosed|reported|determined)[^.]{0,90}"
     r"material weakness(?:es)?",
     4, "Väsentlig brist i intern kontroll som bolaget säger sig ha HITTAT "
        "(inte bara nämnt som möjlighet). Siffrorna går inte att lita på fullt ut.",
     r"(?:no|not|any|without|were effective|was effective|is effective|"
     r"absence of|did not identify)"),
    (r"significant deficienc(?:y|ies) in internal control",
     3, "Betydande brist i intern kontroll."),
    (r"(?:we|the company) (?:have |has )?restated[^.]{0,60}financial statements"
     r"|restatement of (?:our|the company's) previously issued[^.]{0,40}financial statements",
     4, "Omräkning av tidigare bokslut: det som stod förut var fel.",
     r"(?:no|not|any|would|could|may)"),
    (r"violat(?:ed|ion) of (?:certain |the )?(?:financial |debt )?covenants?",
     4, "Lånevillkor brutna: bankerna sitter vid bordet."),
    (r"waiver (?:of|from) (?:our |the )?(?:lenders?|banks?)",
     3, "Bolaget har fått dispens från långivare."),
    (r"(?:SEC|Securities and Exchange Commission) (?:subpoena|investigation|inquiry|enforcement)",
     4, "Myndighetsutredning pågår."),
    (r"(?:purported |putative )?class action (?:lawsuits?|complaints?|litigation)"
     r"(?:[^.]{0,60})?(?:filed|pending|brought)", 2,
     "Grupptalan som är inlämnad eller pågår."),
    (r"(?:recorded|recognized|incurred)[^.]{0,80}impairment (?:charge|loss)"
     r"|impairment (?:charge|loss) of \$?\d", 2,
     "Nedskrivning bokförd: ett tidigare köp var för dyrt."),
    (r"(?:recorded|recognized|incurred)[^.]{0,60}goodwill impairment"
     r"|goodwill impairment (?:charge|loss) of", 3,
     "Goodwillnedskrivning: förvärv som inte blev vad man hoppades.",
     r"(?:no|not|any|would|could|may)"),
    (r"we (?:may|will) (?:need|be required) to raise additional (?:capital|funds)",
     3, "Bolaget flaggar för att det kan behöva nytt kapital — utspädning."),
    (r"reverse (?:stock )?split", 3, "Omvänd split: kursen har fallit långt."),
    (r"(?:notice|notification|letter)[^.]{0,60}delisting"
     r"|deficiency letter from (?:the )?(?:nasdaq|nyse)", 4,
     "Bolaget har fått besked om möjlig avnotering."),
    (r"resignation of (?:our )?(?:chief|principal) (?:executive|financial) officer",
     3, "Vd eller finanschef har avgått."),
    (r"dismissed (?:our )?independent registered public accounting firm",
     4, "Bolaget bytte revisor — kolla varför."),
    (r"(?:experienced|suffered|identified|detected|was subject to)[^.]{0,90}"
     r"cyber(?:security)?[- ](?:incident|breach|attack)", 2,
     "Cyberincident som bolaget säger sig ha drabbats av (inte bara nämnt som risk).",
     r"(?:no material|not had|have not|did not|no such)"),
    (r"recall of (?:our|certain) products", 2, "Produktåterkallelse."),
    (r"substantial(?:ly)? (?:all|dependent) (?:of our revenue|on) (?:a|one) (?:single |major )?customer",
     3, "Kundkoncentration: en kund kan välta intäkterna."),
]

ORD = re.compile(r"[a-zåäöéü][a-zåäöéü'-]{1,}")
STOPPORD = set("""
the of and to in a for on that as with by is are was were be been being at
from or an it its this these those which we our us their his her they them
have has had not no but if then than so such may will would could should can
shall other any all each more most some there here when where who whom what
also into during under over between among per within upon about
""".split())


SV_STOPPORD = set("""
och att det som en av på för med den de till i är var har hade blir blev
inte men eller vid från om under över mellan efter samt kan ska skall dess
vi vår våra sin sina deras denna dessa detta ett per där när vilket vilka
""".split())


def orda(text: str, sprak: str = "en") -> list[str]:
    stopp = SV_STOPPORD if sprak == "sv" else STOPPORD
    return [o for o in ORD.findall((text or "").lower()) if o not in stopp]


def cosinuslikhet(a: Counter, b: Counter) -> float:
    """Standardmåttet i Lazy Prices-litteraturen. 1,0 = identisk text."""
    if not a or not b:
        return 0.0
    gemensam = set(a) & set(b)
    prick = sum(a[o] * b[o] for o in gemensam)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return 0.0 if na == 0 or nb == 0 else prick / (na * nb)


def jaccard(a: Counter, b: Counter) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


# ------------------------------------------------------------ avsnitten --

AVSNITT = {
    "riskfaktorer": ([r"item\s*1a\.?\s*[-–—:]?\s*risk\s*factors",
                      r"\brisk\s*factors\b"],
                     r"item\s*1b\.?\s*[-–—:]?\s*unresolved|item\s*2\.?\s*[-–—:]?\s*propert"
                     r"|unresolved\s+staff\s+comments|other\s+key\s+information"
                     r"|item\s*3\.?\s*[-–—:]?\s*legal\s+proceedings"
                     r"|item\s*5\.?\s*[-–—:]?\s*market\s+for\s+registrant"
                     r"|consolidated\s+statements?\s+of\s+(?:operations|income)"
                     r"|report\s+of\s+independent\s+registered\s+public\s+accounting"
                     r"|notes\s+to\s+(?:the\s+)?consolidated\s+financial\s+statements"
                     r"|information\s+about\s+(?:our\s+)?executive\s+officers"
                     r"|executive\s+officers\s+of\s+the\s+registrant"
                     r"|item\s*4\.?\s*[-–—:]?\s*mine\s+safety"),
    "vd_analys": ([r"item\s*7\.?\s*[-–—:]?\s*management\W{0,4}s?\W{0,4}discussion",
                   r"management\W{0,4}s?\W{0,4}discussion\s*and\s*analysis"],
                  r"item\s*7a\.?\s*[-–—:]?\s*quantitative|item\s*8\.?\s*[-–—:]?\s*financial\s*statements"
                  r"|quantitative\s+and\s+qualitative\s+disclosures\s+about\s+market\s+risk"
                  r"|report\s+of\s+independent\s+registered\s+public\s+accounting\s+firm"),
    "verksamhet": ([r"item\s*1\.?\s*[-–—:]?\s*business"],
                   r"item\s*1a\.?\s*[-–—:]?\s*risk\s*factors"),
}


# Hur ett riktigt riskavsnitt ser ut. Utan den här kontrollen glider urklippet
# vidare in i noterna för bolag vars rapport saknar tydlig slutrubrik, och då
# mäts språkförändringen på leasingtabeller i stället för på risktext. Entegris
# hamnade överst i "mest omskriven" av precis det skälet: 0,25 % riskord och
# 5 % siffertäthet, mot 0,70 % och 0,3 % i ett korrekt urklipp från Apple.
KRAV = {
    "riskfaktorer": {"minsta_riskandel": 0.004, "hogsta_siffertathet": 0.030},
    "vd_analys": {"minsta_riskandel": 0.0, "hogsta_siffertathet": 0.12},
    "verksamhet": {"minsta_riskandel": 0.0, "hogsta_siffertathet": 0.08},
}


def ser_rimligt_ut(text: str, namn: str) -> bool:
    """Sant om urklippet faktiskt liknar det avsnitt vi bad om."""
    krav = KRAV.get(namn)
    if not krav or not text:
        return bool(text)
    ord_ = orda(text)
    if len(ord_) < 300:
        return False
    riskandel = sum(1 for o in ord_ if o.startswith("risk")) / len(ord_)
    siffertathet = sum(c.isdigit() for c in text) / max(len(text), 1)
    return (riskandel >= krav["minsta_riskandel"]
            and siffertathet <= krav["hogsta_siffertathet"])


def hitta_avsnitt(text: str, namn: str, minlangd: int = 6000) -> str:
    """
    Klipper ut ett avsnitt ur en 10-K.

    Två saker gör det svårare än det låter. Rubriken förekommer alltid minst två
    gånger — en gång i innehållsförteckningen och en gång på riktigt — så vi tar
    den längsta biten, inte den första. Och en del bolag (Intel t.ex.) har bara
    korsreferenser under "Item 7" och lägger själva texten under egna rubriker,
    därför finns en andra sökning utan "Item"-prefix.
    """
    if namn not in AVSNITT:
        return ""
    startmonster, slut_m = AVSNITT[namn]
    lag = text.lower()
    slutpunkter = [m.start() for m in re.finditer(slut_m, lag)]
    for monster in startmonster:
        basta = ""
        for m in re.finditer(monster, lag):
            s = m.start()
            efter = [p for p in slutpunkter if p > s + 2000]
            bit = text[s:(efter[0] if efter else len(text))]
            if len(bit) > len(basta):
                basta = bit
        if len(basta) > minlangd and ser_rimligt_ut(basta, namn):
            return basta
    # Inget urklipp klarade kontrollen. Att returnera tomt är rätt svar: appen
    # faller då tillbaka på hela rapporten och SÄGER att avsnittet inte hittades,
    # i stället för att mäta på fel text och låtsas att siffran betyder något.
    return ""


def stycken(text: str, minlangd: int = 200) -> list[str]:
    rader = re.split(r"\n\s*\n|(?<=\.)\s{2,}", text)
    return [r.strip() for r in rader if len(r.strip()) >= minlangd]


# ------------------------------------------------------------- analysen --

LEXIKON = {
    "en": (LM_NEGATIVA, LM_POSITIVA, LM_OSAKERHET, LM_TVIST, LM_BEGRANSNING),
    "sv": (SV_NEGATIVA, SV_POSITIVA, SV_OSAKERHET, SV_TVIST, set()),
}

# Ord som bara förekommer i den ena texttypen. Räcker gott för att skilja en
# svensk delårsrapport från en engelsk.
_SV_MARKORER = ("och", "för", "med", "att", "koncernen", "kvartalet", "resultatet")
_EN_MARKORER = ("the", "and", "for", "with", "that", "company", "quarter")


def gissa_sprak(text: str) -> str:
    lag = (text or "")[:20000].lower()
    sv = sum(lag.count(" " + o + " ") for o in _SV_MARKORER)
    en = sum(lag.count(" " + o + " ") for o in _EN_MARKORER)
    return "sv" if sv > en else "en"


def tonlage(text: str, sprak: str = "auto") -> dict:
    """
    Andel ord ur varje kategori. `sprak` styr vilket lexikon som används;
    "auto" gissar. Den svenska listan är kortare än den engelska, så svenska
    och engelska tal går INTE att jämföra med varandra — bara med sig själva
    över tid. Därför skickas språket med i svaret.
    """
    if sprak == "auto":
        sprak = gissa_sprak(text)
    negativa, positiva, osakerhet, tvist, begransning = LEXIKON.get(sprak, LEXIKON["en"])

    ord_ = orda(text, sprak)
    n = len(ord_)
    if n < 200:
        return {}
    c = Counter(ord_)

    def andel(lex):
        return sum(v for o, v in c.items() if o in lex) / n * 100 if lex else 0.0

    neg, pos = andel(negativa), andel(positiva)
    return {
        "sprak": sprak,
        "antal_ord": n,
        "negativa_pct": neg,
        "positiva_pct": pos,
        "osakerhet_pct": andel(osakerhet),
        "tvist_pct": andel(tvist),
        "begransning_pct": andel(begransning),
        "nettoton": pos - neg,
    }


def roda_flaggor(text: str, sprak: str = "auto") -> list[dict]:
    """
    Flaggor på engelska ELLER svenska. Svenska rapporter körs mot båda
    listorna — många svenska bolag blandar in engelska termer, och en engelsk
    rapport från ett svenskt bolag kan innehålla "kontrollbalansräkning" i en
    parentes.
    """
    if sprak == "auto":
        sprak = gissa_sprak(text)
    listor = RODA_FLAGGOR + SV_RODA_FLAGGOR if sprak == "sv" else RODA_FLAGGOR
    lag = " ".join((text or "").lower().split())
    ut = []
    for post in listor:
        monster, vikt, forklaring = post[0], post[1], post[2]
        negation = post[3] if len(post) > 3 else None
        traffar = []
        for t in re.finditer(monster, lag):
            if negation:
                fonster = lag[max(0, t.start() - 110):t.end() + 70]
                if re.search(negation, fonster):
                    continue           # bolaget säger tvärtom — inte en flagga
            traffar.append(t)
        if not traffar:
            continue
        t = traffar[0]
        start = max(0, t.start() - 220)
        ut.append({
            "flagga": forklaring,
            "vikt": vikt,
            "antal": len(traffar),
            "citat": "..." + lag[start:t.end() + 220].strip() + "...",
        })
    return sorted(ut, key=lambda x: -x["vikt"])


def sprakforandring(text_nu: str, text_forra: str) -> dict | None:
    """Lazy Prices-måttet: hur mycket har bolaget skrivit om?"""
    if not text_nu or not text_forra:
        return None
    sprak = gissa_sprak(text_nu)
    a, b = Counter(orda(text_nu, sprak)), Counter(orda(text_forra, sprak))
    if len(a) < 100 or len(b) < 100:
        return None
    cos = cosinuslikhet(a, b)
    return {
        "cosinuslikhet": cos,
        "jaccard": jaccard(a, b),
        "langd_nu": sum(a.values()),
        "langd_forra": sum(b.values()),
        "langdforandring": (sum(a.values()) / sum(b.values()) - 1) if sum(b.values()) else None,
        # Under 0,30 är det inte en omskrivning. Två versioner av samma rapport
        # delar alltid mer ordförråd än så — så låga tal betyder att texterna
        # inte är jämförbara alls (olika språk, eller en PDF som inte gick att
        # textextrahera). Då ska måttet säga just det, inte larma.
        "tolkning": ("nästan oförändrad" if cos > 0.97 else
                     "normalt omskriven" if cos > 0.92 else
                     "påtagligt omskriven" if cos > 0.85 else
                     "kraftigt omskriven" if cos > 0.30 else
                     "EJ JÄMFÖRBARA — troligen olika språk eller trasig PDF"),
        "jamforbar": cos > 0.30,
    }


# Stycken som ALDRIG är nya risker, hur olika fjolåret de än ser ut.
#
# Ledningsbiografier byts ut varje år ("Ms. Maxson, 48, has been our Chief
# Financial Officer since April 2026") och hamnade överst i listan över nya
# riskstycken för Oracle. Sifferrader ur noterna är samma problem. Båda är
# förändringar i texten — men inte den sortens förändring måttet handlar om.
BIOGRAFI = re.compile(
    r"\b(?:mr|ms|mrs|dr)\.\s+[a-z]+,?\s*\d{2},?\s+(?:has|was|served|joined)"
    r"|,\s*\d{2},\s+has\s+been\s+(?:our|the)"
    r"|(?:served|has\s+served)\s+as\s+(?:our|the)\s+(?:senior\s+)?vice\s+president",
    re.I)


def ar_brus(stycke: str) -> bool:
    """Sant för stycken som inte är risktext: biografier och sifferrader."""
    if BIOGRAFI.search(stycke):
        return True
    siffror = sum(c.isdigit() for c in stycke) / max(len(stycke), 1)
    return siffror > 0.18


def nya_stycken(text_nu: str, text_forra: str, max_antal: int = 8) -> list[str]:
    """Vilka riskstycken är nya i år? Grundat på ordöverlapp mot fjolårets stycken."""
    if not text_nu or not text_forra:
        return []
    sprak = gissa_sprak(text_nu)
    gamla = [Counter(orda(s, sprak)) for s in stycken(text_forra)]
    ut = []
    for s in stycken(text_nu):
        c = Counter(orda(s, sprak))
        if sum(c.values()) < 40:
            continue
        if re.match(r"\s*item\s*1a", s.lower()):     # rubriken är inte en ny risk
            continue
        if ar_brus(s):
            continue
        basta = max((cosinuslikhet(c, g) for g in gamla), default=0.0)
        if basta < 0.55:
            ut.append({"likhet_mot_fjolaret": basta, "text": s[:900]})
    ut.sort(key=lambda x: x["likhet_mot_fjolaret"])
    return ut[:max_antal]


# ------------------------------------------------------ EDGAR-kopplingen --

def hamta_rapporter(symbol: str, form: str = "10-K", antal: int = 3) -> list[dict]:
    cik = dk.sec_cik(symbol) or dk.sec_cik(symbol.replace("-", "."))
    if not cik:
        return []
    sub = dk.sec_inlamningar(cik)
    if not sub:
        return []
    tratt = [f for f in sub["inlamningar"] if f["form"] == form and f.get("dokument")]
    ut = []
    for f in tratt[:antal]:
        try:
            text = dk.sec_dokumenttext(cik, f["accession"], f["dokument"])
        except Exception:
            continue
        if len(text) < 5000:
            continue
        ut.append({**f, "cik": cik, "text": text,
                   "url": dk.sec_dokument_url(cik, f["accession"], f["dokument"])})
    return ut


# ---------------------------------------------------------------- tolkning --

def tolkning(r: dict, median_marknad: float | None = None) -> list[dict]:
    """
    Vad siffrorna faktiskt SÄGER, i meningar.

    Ett tal utan referenspunkt är inte information. "Cosinuslikhet 0,604" säger
    ingenting för den som inte vet att medianbolaget ligger på 0,990. Och
    "5,8 % negativa ord" säger ingenting alls mellan bolag — Apple ligger på
    5,6 % och Oracle på 0,7 %, utan att Apple för den skull är i kris. Det enda
    som betyder något är bolaget mot SIG SJÄLVT över tid.

    Varje mening får en `vikt`: 3 = värt att titta på nu, 2 = notera, 1 = lugnt.
    """
    ut = []
    if not r or not r.get("tillganglig"):
        return ut

    fr = r.get("forandring_risk") or r.get("forandring_hela") or {}
    lik = fr.get("cosinuslikhet")
    if lik is not None:
        andel_ord = fr.get("langdforandring")
        langd = ""
        if andel_ord is not None and abs(andel_ord) > 0.10:
            langd = (f" Texten blev dessutom {abs(andel_ord) * 100:.0f} % "
                     f"{'längre' if andel_ord > 0 else 'kortare'}.")
        jamf = ""
        if median_marknad:
            jamf = (f" Medianbolaget på samma marknad ligger på "
                    f"{median_marknad:.3f}.")
        if lik >= 0.97:
            ut.append({"vikt": 1, "text":
                       f"Rapporttexten är i praktiken oförändrad ({lik:.3f}). Bolaget har "
                       f"inte behövt skriva om sin beskrivning av vad som kan gå fel."
                       + jamf + langd})
        elif lik >= 0.92:
            ut.append({"vikt": 1, "text":
                       f"Texten är normalt omarbetad ({lik:.3f}) — ungefär vad ett bolag "
                       f"ändrar ett vanligt år." + jamf + langd})
        elif lik >= 0.85:
            ut.append({"vikt": 2, "text":
                       f"Texten är påtagligt omskriven ({lik:.3f}), mer än ett vanligt år."
                       + jamf + langd + " Läs de nya styckena nedan."})
        else:
            ut.append({"vikt": 3, "text":
                       f"Texten är kraftigt omskriven ({lik:.3f})." + jamf + langd
                       + " Något har hänt som bolaget varit tvunget att beskriva på nytt. "
                         "Det säger inte VAD — men det säger var du ska läsa."})

    trend = r.get("tonlagestrend") or []
    if len(trend) >= 2:
        nu, forra = trend[-1]["negativa_pct"], trend[-2]["negativa_pct"]
        diff = nu - forra
        tidigare = " → ".join(f"{t['negativa_pct']:.1f}" for t in trend[-3:])
        if abs(diff) < 0.3:
            ut.append({"vikt": 1, "text":
                       f"Tonläget är oförändrat ({tidigare} % negativa ord). Bolaget "
                       f"beskriver sin situation ungefär som förra året."})
        elif diff > 0:
            ut.append({"vikt": 3 if diff > 1.5 else 2, "text":
                       f"Tonläget har mörknat: andelen negativa ord gick från "
                       f"{forra:.1f} % till {nu:.1f} % ({tidigare} %). Bolaget skriver "
                       f"mer om vad som kan gå fel än det gjorde i fjol."})
        else:
            ut.append({"vikt": 1, "text":
                       f"Tonläget har ljusnat: negativa ord från {forra:.1f} % till "
                       f"{nu:.1f} % ({tidigare} %)."})

    nya = len(r.get("nya_risker") or [])
    if nya:
        ut.append({"vikt": 2 if nya >= 3 else 1, "text":
                   f"{nya} riskstycke{'n' if nya != 1 else ''} finns inte i förra "
                   f"rapporten. Det är bolagets egna ord om vad som förändrats — "
                   f"ofta det mest informativa i hela dokumentet."})

    flaggor = r.get("roda_flaggor") or []
    if flaggor:
        tyngst = max(f["vikt"] for f in flaggor)
        ut.append({"vikt": 3 if tyngst >= 4 else 2, "text":
                   f"{len(flaggor)} bevakade formulering{'ar' if len(flaggor) != 1 else ''} "
                   f"hittades: {', '.join(f['flagga'].split(':')[0] for f in flaggor[:3])}. "
                   f"Läs citaten i sitt sammanhang innan du drar slutsatser."})

    ut.append({"vikt": 0, "text":
               "Kom ihåg: den här signalen är testad i appen och föll (topp minus botten "
               "−5,0 procentenheter, p = 0,757). Den säger var du ska LÄSA, inte vad du "
               "ska göra."})
    return ut


def analysera_bolag(symbol: str, form: str = "10-K", djup: int = 3) -> dict:
    """
    Full rapportanalys för ett amerikanskt bolag.
    Returnerar allt utom rapporternas rådtext (den är megabyte-stor).
    """
    rapporter = hamta_rapporter(symbol, form, djup)
    if not rapporter:
        return {"tillganglig": False,
                "skal": "Inga rapporter hittades hos SEC för symbolen."}

    nu = rapporter[0]
    forra = rapporter[1] if len(rapporter) > 1 else None

    risk_nu = hitta_avsnitt(nu["text"], "riskfaktorer")
    mda_nu = hitta_avsnitt(nu["text"], "vd_analys")
    risk_fo = hitta_avsnitt(forra["text"], "riskfaktorer") if forra else ""
    mda_fo = hitta_avsnitt(forra["text"], "vd_analys") if forra else ""

    ut = {
        "tillganglig": True,
        "form": form,
        "senaste": {"datum": nu["datum"], "period": nu.get("rapportdatum"), "url": nu["url"]},
        "foregaende": ({"datum": forra["datum"], "url": forra["url"]} if forra else None),
        "avsnitt_hittade": {"riskfaktorer": bool(risk_nu), "vd_analys": bool(mda_nu)},
        "tonlage_hela": tonlage(nu["text"], "en"),
        "tonlage_risk": tonlage(risk_nu, "en") if risk_nu else {},
        "tonlage_vd": tonlage(mda_nu, "en") if mda_nu else {},
        "roda_flaggor": roda_flaggor(nu["text"]),
        "forandring_hela": sprakforandring(nu["text"], forra["text"]) if forra else None,
        "forandring_risk": sprakforandring(risk_nu, risk_fo),
        "forandring_vd": sprakforandring(mda_nu, mda_fo),
        "nya_risker": nya_stycken(risk_nu, risk_fo),
    }

    # Tonlägestrend över alla hämtade rapporter — mer sägande än en enskild siffra.
    trend = []
    for r in rapporter:
        avsnitt = hitta_avsnitt(r["text"], "riskfaktorer") or r["text"]
        t = tonlage(avsnitt, "en")
        if t:
            trend.append({"datum": r["datum"], "negativa_pct": t["negativa_pct"],
                          "osakerhet_pct": t["osakerhet_pct"], "antal_ord": t["antal_ord"]})
    ut["tonlagestrend"] = list(reversed(trend))
    return ut


def analysera_rapporttext(text_nu: str, text_forra: str = "") -> dict:
    """
    Samma analys på text du matat in själv — för svenska årsredovisningar, som
    saknar en öppen databas. Fungerar på engelska; svenska rapporter analyseras
    bäst i sin engelska version (de flesta svenska storbolag publicerar en).
    """
    return {
        "tillganglig": True,
        "form": "egen",
        "tonlage_hela": tonlage(text_nu),
        "roda_flaggor": roda_flaggor(text_nu),
        "forandring_hela": sprakforandring(text_nu, text_forra) if text_forra else None,
        "nya_risker": nya_stycken(text_nu, text_forra) if text_forra else [],
    }


def las_pdf(sokvag: str) -> str:
    """Läser en PDF om pypdf finns installerat. Frivilligt beroende."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("PDF-läsning kräver pypdf. Kör: pip install pypdf")
    lasare = PdfReader(sokvag)
    return "\n\n".join((s.extract_text() or "") for s in lasare.pages)


def las_url(url: str) -> str:
    import urllib.request
    beg = urllib.request.Request(url, headers={"User-Agent": dk.KONTAKT})
    rad = urllib.request.urlopen(beg, timeout=60).read()
    if rad[:5] == b"%PDF-":
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(rad)
            tmp = f.name
        try:
            return las_pdf(tmp)
        finally:
            os.unlink(tmp)
    return dk.html_till_text(rad.decode("utf-8", errors="replace"))
