# Chiavi di licenza firmate in proprio: il formato

Questo file è il contratto tra `chiavi.py` (nella stessa cartella), che emette le chiavi, e il programma, che le verifica in `src/impaginatore/licenze/`. Il percorso è quello predefinito: niente piattaforme esterne né server; la chiave si verifica dentro il programma, senza rete. Come funziona dal lato del programma: `docs/architettura/LICENZE.md`.

Stato delle prove:
- `chiavi.py autotest` supera i vettori 1 e 2 della RFC 8032, i formati 1 e 2 e la manomissione;
- il programma ha la sua copia di Ed25519 (`src/impaginatore/ed25519.py`): `tests/test_ed25519.py` la prova con i vettori 1, 2 e 3 della RFC 8032 e controlla che firmi gli stessi byte di `chiavi.py`;
- `tests/test_chiavi_negozio.py` emette chiavi e revoche con `chiavi.py` e le fa verificare al programma;
- 30 firme casuali sono risultate identiche a quelle della libreria `cryptography` (44.0.2);
- **integrato nel programma** (T-202). Manca la chiave pubblica di produzione: nel codice c'è un segnaposto, e un test impedisce di rilasciare una versione finale con il segnaposto (`LICENZE.md`, «Prima del rilascio»).

## 1. Come è fatta la chiave

Testo: `IMP1-` seguito dal base32 (RFC 4648, senza `=`) di `payload || firma`, a gruppi di 5 caratteri separati da `-`. Esempio, di 199 caratteri:

```
IMP1-AEDQE-AQCAA-AAAAB-KAGRB-QU3UO-VSGS3-ZAIZX-XI33H-OJQWM-2LDN4-QMHAD-MMZQ5-...
```

| Byte | Campo | Valori |
|---|---|---|
| 0 | formato | `1` licenza senza scadenza; `2` licenza a scadenza |
| 1 | id della chiave di firma | 1-255. Serve alla rotazione: il programma conosce più chiavi pubbliche |
| 2 | fascia | 1 essenziale, 2 pro, 3 studio, 4 laboratorio |
| 3 | versione maggiore | `2` |
| 4 | computer (attivazioni) | da `tier.json`: 1, 2 o 5 |
| 5 | flag | bit 0 omaggio, bit 1 beta; gli altri bit a zero |
| 6-9 | seriale | uint32 big-endian, progressivo nel registro |
| 10-11 | data di emissione | giorni dal 01/01/2026, uint16 big-endian |
| 12 | n | lunghezza dell'intestatario, 0-48 |
| 13…13+n | intestatario | UTF-8, ad esempio «Studio Rossi» |
| solo formato 2: i 2 byte dopo l'intestatario | scadenza | ultimo giorno valido, compreso: giorni dal 01/01/2026, uint16 big-endian |
| ultimi 64 | firma | Ed25519 di `b"IMPAGINATORE-LICENZA-v1\x00" + payload` |

Il formato 2 serve alle licenze a tempo: la «licenza di sito» annuale dei laboratori (modello C di `docs/mercato/tier.json`), o una proroga della prova data dal supporto. Si emette con `chiavi.py emetti … --scadenza AAAA-MM-GG`. Un programma che conosce solo il formato 1 rifiuta le chiavi del formato 2 (lunghezza e byte 0): non le scambia mai per licenze perpetue.

**Chiavi della beta privata.** Sono chiavi del formato 2, fascia Studio, con i bit omaggio e beta accesi (`flag` = 3) e prezzo `beta` nel registro. Si emettono tutte insieme, una per tester:

    python3 chiavi.py emetti-beta --intestatari tester.txt --quante 10 --scadenza 2027-01-31

`tester.txt` ha un intestatario per riga (righe vuote e `#` si saltano; ripetuti o troppo lunghi fermano tutto). `--quante` è un controllo: deve coincidere con le righe. Il registro si scrive una volta sola, dopo che tutte le chiavi sono firmate; chiavi e link `impaginatore://attiva?chiave=…` vanno in un CSV (`seriale,intestatario,scadenza,chiave,link`) con permessi 600, creato nuovo (un file che c'è già non si sovrascrive) e mai dentro il repository; il nome predefinito è `<cartella del negozio>/beta-<data>-seriali-<primo>-<ultimo>.csv`. Nel programma la licenza si presenta come «Beta privata · scade il 31/01/2027» (`licenze.stato()`: `beta`, `etichetta_beta`, `riga_beta`); dopo la scadenza il programma passa in sola lettura come alla fine della prova e dice «La beta privata è finita il …». Solo con questa licenza il programma chiede se condividere le statistiche d'uso (`docs/architettura/STATISTICHE.md`).

Il prefisso `IMP1-` distingue queste chiavi da quelle Polar (`IMP-` seguito da un UUID: `polar/API-LICENZE.md`). Il programma oggi accetta solo `IMP1-`.

## 2. Cosa fa il programma

1. **Normalizza** il testo: maiuscole, via spazi, a capo e trattini; accetta anche il link `impaginatore://attiva?chiave=…` incollato per intero (`licenze/chiave.py`, `da_testo`). Il link non apre ancora il programma da solo: va registrato dall'installatore (T-302).
2. **Verifica** la firma con le chiavi pubbliche compilate nel programma (`licenze/chiave.py`, `CHIAVI_PUBBLICHE`), in pochi millisecondi, con la sola libreria standard.
3. **Sblocca** le `funzioni` della fascia (`tier.json`) e mostra «Licenza Pro attiva, intestata a «Studio Rossi», per 2 computer».
4. **Salva** il testo della chiave nella cartella dei dati dell'utente (`<dati>/licenza/chiave.txt`, leggibile solo dall'utente), così sopravvive alla reinstallazione.
5. Se la `versione_maggiore` è diversa da quella del programma, non sblocca niente e scrive «Questa chiave è per Impaginatore N»: con una chiave più vecchia indica l'aggiornamento della licenza, con una più nuova chiede di aggiornare il programma. Vale la prova gratuita, se non è finita.

Non serve la rete. **Il numero di computer non viene contato**: senza un server non si può. Il limite vale per contratto (EULA) ed è reso visibile dall'intestatario mostrato nel programma. È coerente con il prezzo d'impulso: costa meno comprare una seconda licenza che aggirarla.

Decisione del titolare (15/11/2026): in `tier.json` `politica_aggiornamenti.attivazione_online_una_tantum_per_computer` vale `false`. Non ci sono attivazioni online e nessun server di attivazione: il numero di computer è un limite contrattuale.

## 3. Che cosa garantisce la firma, e che cosa no

- Chi non ha la chiave privata non può fabbricare o modificare una licenza: cambiare la fascia, la versione o la scadenza rompe la firma (provato in `autotest` e in `tests/test_licenze.py`).
- Chi copia una chiave valida la può usare su altri computer, ma vi compare il nome dell'intestatario.
- Chi modifica il programma (patch del controllo) aggira qualsiasi verifica locale. Nessuno schema solo locale lo impedisce; con questi prezzi non vale la pena inseguirlo (`LICENZE.md`, «Che cosa non protegge»).

## 4. Revoche (rimborsi): arrivano con gli aggiornamenti

Decisione del titolare (T-202): il programma **non scarica niente** per la licenza. L'elenco delle chiavi revocate viaggia dentro il programma, come il resto del codice.

- `chiavi.py revoca --seriale N --motivo rimborso` aggiorna il registro e firma `revoche.json`, con dominio `IMPAGINATORE-REVOCHE-v1\0` e JSON canonico (chiavi ordinate, senza spazi) senza il campo `firma`.
- Prima di ogni rilascio: `chiavi.py revoche --uscita src/impaginatore/licenze/revoche.json` nella copia del rilascio. Il file entra nel pacchetto; con l'aggiornamento successivo il programma mette in sola lettura le licenze elencate.
- File assente, illeggibile o con una firma che non torna: nessun effetto (il programma lo scrive nel registro e va avanti).
- Effetto: la revoca vale solo su chi aggiorna il programma. Chi non aggiorna più tiene la chiave. Si accetta: il rimborso è un caso raro e il prezzo è basso.
- `chiavi.py togli-revoca --seriale N --motivo storno-a-favore` (oppure `errore`) rimette la licenza attiva nel registro e rifirma l'elenco: la stessa chiave torna valida con il rilascio successivo. Se il cliente non può aspettare il rilascio, si emette una chiave nuova (TERMINI-VENDITA, B.7).

Dopo un **upgrade di fascia** si emette una chiave nuova e la vecchia si revoca con `--motivo upgrade`.

## 5. Chiave privata e registro

- Vivono **fuori dal repository**: in `~/.impaginatore-negozio`, oppure in `--dir`, oppure nella cartella indicata da `IMPAGINATORE_NEGOZIO_DIR`. Lo script rifiuta una cartella interna al repository.
- I permessi sono 600 sui file e 700 sulla cartella.
- **Copia offline obbligatoria** della chiave privata (chiavetta cifrata o stampa). Se la si perde, i programmi distribuiti non accettano le nuove licenze finché un aggiornamento non porta una nuova chiave pubblica.
- `genera-coppia` stampa la riga da mettere in `src/impaginatore/licenze/chiave.py`: `CHIAVI_PUBBLICHE = {1: Pubblica("…")}`.
- **Se la chiave privata viene rubata**:
  1. `genera-coppia --nuova` crea una chiave con un nuovo id, che si aggiunge a `CHIAVI_PUBBLICHE`;
  2. nella chiave vecchia si scrive la data del furto: `Pubblica("…", emesse_fino="AAAA-MM-GG")`. Con l'aggiornamento successivo il programma rifiuta le chiavi firmate con il vecchio id ed emesse dopo quella data (il campo data è firmato);
  3. si riemettono le chiavi ai clienti, gratis.
- `registro.csv` contiene per ogni licenza seriale, data, fascia, prezzo (`listino`, `lancio`, `upgrade`, `rottamazione`, `convenzione`, `omaggio`, `beta`), riferimento della fattura, intestatario, impronta, stato, note e, in coda, la scadenza (vuota per le licenze senza scadenza; i registri scritti prima si leggono uguale).
- Il registro è un dato contabile del titolare. Contiene dati personali (l'intestatario), quindi va nel backup e non si condivide. L'elenco delle revoche contiene solo seriali.
- `stato-lancio` conta le licenze `lancio` ancora attive rispetto alle 300 di `tier.json`. Una licenza rimborsata libera il posto.
