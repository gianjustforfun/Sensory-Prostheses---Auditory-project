# Multiplayer: istruzioni rapide

Questi file aggiungono la modalità di gruppo al progetto esistente.
Il presentatore riproduce gli audio; ogni partecipante risponde dal proprio
telefono. Punteggi, avanzamento e classifica sono gestiti dal server.

## 1. Dove mettere i file

Parti dalla versione del progetto che contiene il gioco e i suoi audio,
normalmente il branch `game`. Puoi lavorare su un branch dedicato come
`feature/multiplayer`, creato da quella versione. Se lo hai già creato, usalo.

Estrai lo ZIP in una cartella separata e copia il contenuto nella cartella
principale della tua repository: **la stessa in cui trovi `run_game.py`**.
Alla fine `run_multiplayer.py`, `render.yaml` e `requirements_multiplayer.txt`
devono trovarsi accanto a `run_game.py`.

Per `game` e `tests`, unisci i contenuti alle cartelle esistenti. **Non sostituire
le cartelle intere**: contengono il gioco e gli audio già preparati. Nel pacchetto
ci sono solo file aggiuntivi. Se hai già un `render.yaml`, confrontalo con questo
prima di sostituirlo.

Il server usa i 35 WAV già presenti in `game/assets/processed/`:
cinque frasi per sei livelli e cinque audio originali. Lo ZIP non li duplica.

## 2. Provalo sul tuo computer

Nel terminale della cartella principale, con il tuo ambiente Python attivo:

```bash
python -m pip install -r requirements_multiplayer.txt
python run_multiplayer.py
```

Apri <http://127.0.0.1:8000> nel browser e scegli **Host a game**.
Crea una stanza e apri il link di partecipazione in una nuova scheda per provare
il giocatore. Puoi usare un'altra finestra privata per un secondo giocatore.

In PyCharm il file da avviare è `run_multiplayer.py` nella cartella principale.
Il vecchio `run_game.py` continua ad avviare il gioco individuale.

Per usare i telefoni in locale, avvia invece:

```bash
python run_multiplayer.py --host 0.0.0.0
```

Collega computer e telefoni alla stessa rete e apri la pagina host tramite
l'indirizzo IP locale del computer. Per esempio,
`http://192.168.1.20:8000/host`, sostituendo l'IP con quello corretto.
Il QR deve contenere quell'indirizzo, non `127.0.0.1`.
La rete universitaria potrebbe impedire queste connessioni: dopo la
pubblicazione puoi usare direttamente il link HTTPS di Render.

## 3. Configura Render

Esegui commit e push dei nuovi file sul branch scelto, includendo i 35 WAV se
non sono già presenti su quel branch. Nel servizio Render collegato a GitHub:

| Campo | Valore |
| --- | --- |
| Tipo | Web Service |
| Branch | Quello che contiene questi file, per esempio `feature/multiplayer` |
| Runtime | Python 3 |
| Root Directory | Vuoto |
| Build Command | `pip install -r requirements_multiplayer.txt` |
| Start Command | `uvicorn multiplayer.server:app --host 0.0.0.0 --port $PORT --workers 1` |
| Instance Type | Free |
| Health Check Path | `/healthz` |
| Environment variable | `PYTHON_VERSION` = `3.12.10` |

Salva e avvia il deploy. Quando il servizio risulta **Live**, apri il link HTTPS
assegnato da Render e crea una stanza. Il QR viene generato automaticamente
per quella stanza e si può scansionare dal telefono.

`render.yaml` serve anche per creare un servizio tramite Render Blueprint.
Se hai già creato un normale Web Service dal modulo, compila i campi della
tabella: caricare il file YAML non aggiorna automaticamente quel servizio.

## 4. Come si svolge una partita

1. I giocatori entrano nella lobby con un nickname univoco.
2. L'host avvia il gioco e riproduce l'audio dalle casse del computer.
3. Alla fine dell'audio si apre la risposta sui telefoni.
4. Chi indovina riceve i punti, vede monetina e coriandoli, poi aspetta la frase
   successiva. Chi sbaglia aspetta il livello successivo.
5. L'host passa ai canali 1, 2, 4, 8, 16, 32. I punti sono 100, 90, 80, 70, 60, 50.
6. Dopo Rookie l'host rivela la frase e può riprodurre l'originale. Può rivelare
   prima se tutti hanno indovinato. Una frase non indovinata vale zero.
7. Dopo cinque frasi compare la classifica. **Download scores** salva un CSV.

Ogni livello concede una risposta non vuota e al massimo due ascolti condivisi.
La verifica ignora maiuscole, punteggiatura e spazi superflui, ma richiede le
parole corrette nello stesso ordine. Il punteggio dipende dai canali, non dalla
velocità con cui si scrive.

Le stanze e i punteggi restano in memoria: un riavvio o un nuovo deploy li
cancella. Scarica il CSV a fine partita. Usa un solo worker e una sola istanza,
come nel comando fornito. Render Free può sospendere il servizio quando è
inattivo: aprilo prima della presentazione e prova l'accesso da un telefono.

Le istruzioni tecniche complete e la gestione degli errori sono in
`README-MULTIPLAYER.md`. Le verifiche eseguite sono in
`VALIDATION-MULTIPLAYER.md`.
