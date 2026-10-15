"""Skapa ett installationspaket utan privata inställningar eller hämtad bolagsdata."""
from pathlib import Path
import json
import zipfile
import version
HAR=Path(__file__).resolve().parent

def bygg(malfil=None):
    malfil=Path(malfil) if malfil else HAR.parent/f"borscase-v{version.VERSION}-{version.DATUM}.zip"
    med=[];hoppade=[]
    allowed={'.py','.html','.js','.css','.bat','.md','.txt'}
    with zipfile.ZipFile(malfil,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(HAR.iterdir()):
            if not p.is_file() or p.suffix not in allowed or p.name=='skann_logg.txt':
                hoppade.append(p.name);continue
            z.write(p,'borscase/'+p.name);med.append((p.name,p.stat().st_size))
        # Only public aggregate validation/model results are included.
        for name in ['rapportmodell.json','insynsmodell.json','validering_resultat.json','valideringstavla.json']:
            p=HAR/name
            if p.exists():z.write(p,'borscase/'+name);med.append((name,p.stat().st_size))
        z.writestr('borscase/installningar.json',json.dumps({'profil':'sammansatt','las_rapporter':True,'rapportdjup':3,'kapital_kr':100000,'grupper':['karna','halvledare_ai'],'egna_bolag':{},'sec_kontakt':''},ensure_ascii=False,indent=2))
        z.writestr('borscase/START_HAR.txt','Packa upp hela mappen. Installera Python 3.10 eller senare med Add Python to PATH. Kör INSTALLERA.bat, därefter SKANNA.bat och STARTA_APP.bat. Internet krävs. Ny installation hämtar sin egen data. Journal och personliga inställningar följer inte med. Läs LICENS.txt och ANALYSRUM.md.\n')
    return str(malfil),med,hoppade

if __name__=='__main__':
    print(bygg()[0])
