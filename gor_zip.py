"""
gor_zip.py — paketerar appen för någon annan att köra.

Vad som INTE följer med, och varför:

  cache/            Hundratals megabyte nedladdad data som ändå regenereras.
                    Mottagaren hämtar sin egen — det är dessutom rätt ur
                    licenssynpunkt: varje installation hämtar från källan
                    själv, ingenting distribueras vidare.
  __pycache__/      Kompilerad Python, bunden till just min version.
  app.pid           Ett processnummer på MIN dator.

Vad som FÖLJER med utöver koden:

  rapportmodell.json        Domen över riktningsgissningen (50,8 % träffsäkerhet).
                            Utan den visar appen ingen sannolikhet alls — och
                            det är med flit. En sannolikhet utan känd
                            träffsäkerhet är en spådom.
  validering_resultat.json  Domen över poängmodellen. Samma skäl.
  skanning_resultat.json    Senaste skanningen, så att appen har något att
                            visa direkt vid första start.
"""

from __future__ import annotations

import os
import zipfile
from datetime import date

HAR = os.path.dirname(os.path.abspath(__file__))
UTESLUT_MAPPAR = {"cache", "__pycache__", ".git", ".idea", ".vscode"}
UTESLUT_FILER = {"app.pid", "gor_zip.py", "skann_logg.txt"}
UTESLUT_ANDELSER = {".pyc", ".pyo", ".log", ".tmp"}


def _renad_installning(sokvag: str) -> str:
    """Inställningsfilen utan personliga uppgifter."""
    import json
    try:
        with open(sokvag, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d["sec_kontakt"] = ""
    return json.dumps(d, ensure_ascii=False, indent=2)


def bygg(malfil: str | None = None) -> str:
    # Versionsnumret i filnamnet, så att man ser vilken zip som är vilken utan
    # att packa upp den. Datumet ensamt räckte inte — flera versioner byggdes
    # samma dag.
    try:
        import version as ver
        etikett = f"v{ver.VERSION}-{ver.DATUM}"
    except Exception:
        etikett = date.today().isoformat()
    malfil = malfil or os.path.join(os.path.dirname(HAR), f"borscase-{etikett}.zip")
    med, hoppade = [], []
    with zipfile.ZipFile(malfil, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rot, mappar, filer in os.walk(HAR):
            mappar[:] = [m for m in mappar if m not in UTESLUT_MAPPAR]
            for f in filer:
                if f in UTESLUT_FILER or os.path.splitext(f)[1] in UTESLUT_ANDELSER:
                    hoppade.append(f)
                    continue
                full = os.path.join(rot, f)
                rel = os.path.relpath(full, HAR)
                if f == "installningar.json":
                    # Personliga uppgifter följer inte med i ett paket som ska
                    # vidare till någon annan. sec_kontakt är den adress som
                    # skickas till SEC vid varje hämtning — mottagaren ska fylla
                    # i sin egen, inte skicka avsändarens.
                    z.writestr(os.path.join("borscase", rel), _renad_installning(full))
                    med.append((rel + " (rensad)", 0))
                    continue
                z.write(full, os.path.join("borscase", rel))
                med.append((rel, os.path.getsize(full)))
    return malfil, med, hoppade


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    saknas = [f for f in ("rapportmodell.json", "validering_resultat.json",
                          "skanning_resultat.json")
              if not os.path.exists(os.path.join(HAR, f))]

    fil, med, _ = bygg()
    med.sort(key=lambda x: -x[1])
    print(f"\n  Paket klart: {fil}")
    print(f"  {len(med)} filer, {os.path.getsize(fil) / 1e6:.1f} MB\n")
    print("  Största filerna:")
    for namn, storlek in med[:8]:
        print(f"    {namn:34s} {storlek / 1e6:7.2f} MB")

    if saknas:
        print("\n  VARNING — de här saknas i paketet:")
        for f in saknas:
            print(f"    {f}")
        print("  Utan rapportmodell.json visar appen ingen riktningssannolikhet,")
        print("  och utan validering_resultat.json är Validering-fliken tom.")
        print("  Kör 'python rapportkalender.py' och 'python validering.py' först.")
    print()
