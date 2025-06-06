# fakspy
Et Python-basert verktøy designet for å bearbeide data som kan importeres 
eller eksporteres fra **FAKS** (Felles aksjonsstøttesystem). 

## Funksjoner

### sartopo2faks.py 
Konverterer geojson eksportert fra SARTopo til FAKS geojson import filer.

### Nettgrensesnitt for transformasjon 
Enkel prosessering og transformasjon av GeoJSON-filer 
via et brukervennlig nettgrensesnitt. Last opp GeoJSON-filen din, og 
systemet vil behandle, klassifisere og generere nedlastbare resultater.

## Forutsetninger
Dette prosjektet er bygget med Python 3.13.3 eller senere. Sørg for å ha 
følgende installert på systemet ditt:
- Python 3.13.3
- `pip` (Python-pakkebehandler)

Du kan bekrefte installasjonen av Python ved å kjøre:
```bash
python3 --version
```
Sørg for at det viser Python 3.13.3.

## Installasjon
### Steg 1: Klon repoet
Klon repoet ved å bruke følgende kommando:
```bash
git clone git@github.com:kengu/fakspy.git
```

### Steg 2: Opprett et virtuelt miljø (valgfritt, men anbefalt)
Opprett et virtuelt miljø for å isolere prosjektavhengighetene:
```bash
python3 -m venv venv
```
Aktiver det virtuelle miljøet:
- På macOS/Linux:
  ```bash
  source venv/bin/activate
  ```
- På Windows:
  ```bash
  venv\Scripts\activate
  ```

### Steg 3: Installer avhengigheter
Installer nødvendige Python-pakker med `pip`:
```bash
pip install -r requirements.txt
```
Hvis `requirements.txt` ikke finnes, kan du manuelt installere `numpy`-pakken:
```bash
pip install numpy
```

### Steg 4: Bekreft installasjon
Kjør følgende Python-kommando for å bekrefte at avhengigheter er korrekt installert:
```bash
python3 -c "import numpy; print('Numpy-versjon:', numpy.__version__)"
```
Du bør se versjonen av `numpy` skrevet ut i konsollen.

## Bruk

### Kommandolinje
Når oppsettet er fullført, kan du kjøre skriptene i prosjektet med:
```bash
python3 <script_name>.py
```
Erstatt `<script_name>` med navnet på Python-skriptet du vil kjøre.

Konvertering av SARTopo export til FAKS geojson import filer:
```bash
python3 sartopo2faks.py sartopo.geojson geojson/
```
der `sartopo.geojson` er eksportert fra SARTopo og `geojson/` er folderen som 
FAKS importfiler skrives til.

### Transformere GeoJSON-filer via nettgrensesnitt
Start webserver lokalt med  
```bash
python3 main.py
```
og åpne siden http://127.0.0.1:5000 i en nettleser

## Notater
- Hvis flere avhengigheter legges til, oppdater `requirements.txt`-filen med:
  ```bash
  pip freeze > requirements.txt
  ```
- [Aktiver alltid det virtuelle miljøet](https://python.land/virtual-environments/virtualenv#Python_venv_activation) etter utsjekk av kode før du jobber med prosjektet.

## Feilsøking
Hvis du møter problemer under installasjon eller kjøring, sjekk:
- At du bruker Python 3.13.3.
- At riktig versjon av `numpy` er installert.
- At alle kommandoer kjøres i prosjektmappen.

Opprett gjerne en [sak](https://github.com/kengu/fakspy/issues/new/choose) hvis du trenger mer hjelp.