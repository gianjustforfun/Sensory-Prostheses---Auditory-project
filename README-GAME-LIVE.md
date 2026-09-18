# Collegare gli audio al gioco

Questo è un aggiornamento per il progetto esistente nel branch `game`.
Contiene tutti i 30 WAV elaborati (5 frasi × 6 livelli), i cinque originali
adattati per il confronto e il codice che li collega all'interfaccia.
Non è un secondo progetto da avviare separatamente.

## Installazione

1. Apri il tuo progetto in PyCharm e controlla il branch con `git branch --show-current`.
   Installa questi file nella copia di lavoro del branch `game`.
2. Se il gioco è in esecuzione, ferma il server con **Ctrl+C** nel terminale.
3. Estrai lo ZIP e copia i file nelle posizioni indicate qui sotto.
   Unisci il contenuto delle cartelle: non sostituire l'intera cartella `game`,
   perché contiene anche gli altri file del progetto.

| Nel pacchetto | Destinazione nel progetto |
|---|---|
| `game/web/app.js` | Sostituisci `game/web/app.js` |
| `game/web/index.html` | Sostituisci `game/web/index.html` |
| `game/web/audio_check.html` | Sostituisci `game/web/audio_check.html` |
| `game/assets/processed/` | Copia i 35 WAV e i 5 JSON in `game/assets/processed/` |
| `game/README-GAME.md` | Documentazione aggiornata dentro `game/` |
| `README-GAME-LIVE.md` | Radice del progetto, accanto a `run_game.py` |

Restano necessari i tuoi file già presenti `run_game.py`, `game/web/model.js`,
`game/web/style.css` e `game/web/coin.svg`. Il modello deve contenere le cinque
frasi nello stesso ordine riportato nella documentazione del gioco.
Palette, monetina, coriandoli e crediti sono quelli dell'interfaccia esistente.

Dalla radice del progetto esegui:

```bash
python run_game.py
```

Apri **http://127.0.0.1:8765/web/** nel browser. Se vedi ancora la vecchia
pagina, fai un aggiornamento forzato con **Cmd+Shift+R**.
Non aprire `index.html` direttamente: il controllo dei file audio usa il server locale.

Non devi installare nuovi pacchetti per giocare e non devi rigenerare gli audio:
sono già inclusi. Python avvia il server usando la libreria standard;
il browser esegue l'interfaccia e riproduce i WAV.

## Cosa verificare sul Mac

- Premi **Play**, inserisci il nome e ascolta la prima frase.
- Invia una risposta sbagliata: il livello deve passare da Legend a Champion.
- Indovina: devono comparire coriandoli, moneta e punti corretti.
- Su un'altra frase, arriva oltre Rookie: **Listen to original** deve riprodurre
  la voce originale di quella frase e non assegnare punti.
- Concludi le cinque frasi: verifica totale e classifica; torna alla home per
  controllare che il risultato sia ancora visibile.

Puoi aprire **Compare the audio levels** dalla home per riascoltare le
versioni delle cinque frasi. La pagina di confronto non registra punteggi.
Le risposte già conosciute rendono più facile il gioco: per una prima prova
di comprensibilità coinvolgi qualcuno che non abbia già ascoltato le frasi.

## Salvataggio e riproducibilità

I risultati sono salvati nel browser su questo computer, per lo stesso
indirizzo e porta. Usa sempre `127.0.0.1:8765`: `localhost:8765` è uno spazio
di salvataggio diverso. La classifica non è condivisa tra computer.
I vecchi risultati della demo restano separati e non vengono cancellati.

La generazione è quella di `prepare_game_audio.py`, già consegnato nel
pacchetto precedente. Per rigenerare in futuro: `python prepare_game_audio.py`
nell'ambiente Python del progetto con le parti 1, 2 e 3 integrate.
L'interfaccia usa solo i WAV pronti; non calcola gli impulsi durante una partita.
Se cambiate parametri o frasi, rigenerate gli audio e cambiate anche `SCORE_KEY`
e `audioVersion` in `app.js` per tenere separate le classifiche.

## Verifiche effettuate su questo aggiornamento

- Sette test di integrazione dell'interfaccia e delle regole passati con DOM
  simulato e riproduzione audio simulata: controllo dei 35 file, annullamento
  del caricamento, sei livelli e originale, limiti di ascolto, errori di
  riproduzione, eventi tardivi e salvataggio unico del totale.
- Letti e controllati tutti i 35 WAV: mono, 22050 Hz, PCM16, durata coerente
  per frase, valori finiti, versioni distinte, picco entro 0.95004 dopo la
  quantizzazione. RMS corrispondente tra le sette versioni di ogni frase.
- Generazione di tutti i livelli completata con i controlli sugli impulsi CIS.

Questi sono controlli automatici del codice e dei segnali. La riproduzione
reale nel tuo browser e l'aspetto sul tuo schermo vanno confermati con la
partita di prova sopra. Nessun commit, merge o push è stato eseguito da questo pacchetto.
