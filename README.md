# Spazio · Gestione eventi

Prima versione locale, senza dipendenze esterne. Richiede Python 3.12 o successivo e un browser moderno.

## Windows: cartella PrimoCodex

Scarica o clona questo progetto in `Desktop\PrimoCodex`. Se hai già collegato la cartella al repository, scarica prima le modifiche pubblicate con `git pull`. Il codice creato nel cloud deve essere trasferito o pubblicato nel repository prima di poterlo scaricare sul PC: non si sincronizza automaticamente.

Installa Python da https://www.python.org/downloads/windows/ (includi il launcher `py`). Fai doppio clic su `Avvia.bat`, mantieni aperto il terminale e usa il browser all’indirizzo indicato dal programma. Se il browser si apre prima del server, aggiorna la pagina. In alternativa, da PowerShell nella cartella:

```powershell
py -3 app.py
```

Chiudi con Ctrl+C. Nessun account o credenziale richiesto per le funzioni locali. Per altri sistemi: `python3 app.py`.

## Funzioni operative

- Archivio SQLite persistente, inserimento e modifica delle richieste; tabella, schede, ricerca e dashboard.
- Referente, date e ore, 230/400 m², partecipanti, preventivo, note, servizi e indirizzi dei fornitori.
- Calendario locale con intervalli occupati estesi di 12 ore prima e 12 dopo. Sono ore trascorse, non necessariamente una mattina o un pomeriggio lavorativo. Tutti gli orari vanno inseriti come orari locali Europe/Rome.
- Qualsiasi evento confermato blocca l’intero spazio, anche se richiede 230 m²: impostazione prudenziale finché non sono definite le regole di condivisione dello spazio.
- Firma e pagamento registrati manualmente sono entrambi obbligatori per confermare. Il server impedisce conferme concorrenti sovrapposte con una transazione atomica. Il primo che **viene registrato come confermato** ottiene la data; questa versione non verifica pagamenti o firme esterni.
- Email tramite programma di posta: referente, disponibilità/concorrenza, introduzione cliente-fornitore. L’utente deve verificare destinatari e inviare. Per avvisare più lead, aprire la rispettiva scheda e preparare la risposta per ciascuno; nessun avviso automatico.
- Modello contrattuale fornito dall’utente per ogni scheda, esportazione di una bozza TXT con segnaposto. Nessun modello legale presunto e nessuna firma elettronica.
- Backup JSON esportabile. Per ripristino completo copia `eventi.sqlite3` a server spento nella stessa cartella; il JSON è consultabile ma non è importabile nell’interfaccia.

## Collegamenti ancora da realizzare

Typeform (webhook HTTPS con verifica firma e mappatura), invio email automatico con registro e ritentativi e sincronizzazione con Google Calendar. Il calendario Google da usare e il relativo accesso restano da configurare. La disponibilità mostrata considera i lead locali e le occupazioni importate, ma non verifica gli aggiornamenti del calendario esistente. Il modello contrattuale deve essere fornito e revisionato prima dell’uso. Per scelta operativa non sono previste integrazioni di firma elettronica o pagamento: la firma ricevuta e il pagamento gestito separatamente vengono registrati manualmente. La prima conferma completa registrata nel gestionale assegna la data.

Il server ascolta solo su loopback: non esporlo su Internet. Questa versione è per un singolo operatore locale e non include autenticazione o accessi multiutente. Non mettere il database con dati personali nel repository. Esegui backup protetti.

## Verifica

```powershell
py -3 -m unittest discover -s tests -v
```

I test usano un archivio temporaneo e verificano persistenza, conflitti, buffer, firma/pagamento e gestione delle modifiche.

## Importare Eventi Spazio Murat

Apri **Collegamenti**, carica l’esportazione `.xlsx` del Google Sheet e consulta l’anteprima. Il foglio `Events` deve avere in A–E: `Titolo`, `Data Inizio`, `Data Fine`, `Luogo`, `Descrizione`. Il lettore non esegue formule: usa soltanto i valori salvati nell’esportazione. Nessuna dipendenza Excel aggiuntiva.

Seleziona le righe che devono bloccare lo spazio: non sono selezionate automaticamente perché il foglio non specifica lo stato delle prenotazioni e contiene anche appuntamenti. La fine è trattata come **esclusiva** (inizio incluso, fine esclusa): verifica questa convenzione nel file prima di confermare. Per ciascuna voce puoi mantenere le 12 ore prima/dopo oppure disattivarle, ad esempio quando il periodo importato rappresenta già l’occupazione complessiva. Non vengono dedotti orari dai titoli o dalle descrizioni.

Le occupazioni esterne restano separate dai lead, compaiono nel calendario e sono considerate sia negli avvisi di disponibilità sia nel blocco della conferma sul server. Il file ricevuto contiene 20 voci leggibili con date a mezzanotte: queste non rappresentano necessariamente gli orari reali dell’evento. Le righe non vengono convertite in clienti né considerate firmate o pagate.

Reimportare titolo, inizio e fine identici aggiorna la voce senza duplicarla. Se cambia uno di questi tre campi, rimuovi il vecchio blocco dalla sezione Collegamenti prima di importare quello aggiornato. Le cancellazioni sul foglio non vengono propagate. Nessuna sincronizzazione automatica con Google Sheets o Google Calendar. L’importazione non cancella lead e non rimuove conferme già registrate: eventuali conflitti nuovi sono segnalati nella disponibilità.

Aggiornamento Windows: chiudi il server e sostituisci i file dell’app con quelli dello ZIP aggiornato; conserva `eventi.sqlite3`. Riavvia con `Avvia.bat`. La nuova tabella delle occupazioni viene creata automaticamente. Non condividere il database o il foglio con dati personali nel repository.
