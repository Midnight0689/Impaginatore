# Chiavi di licenza firmate in proprio: il formato

Questo file è il contratto per chi scrive il gestore licenze dell'app. Le chiavi si emettono con `chiavi.py`, nella stessa cartella. Il percorso è quello predefinito: niente piattaforme esterne né server; la chiave si verifica dentro l'app, anche senza rete.

Stato delle prove:
- `chiavi.py autotest` supera i vettori 1 e 2 della RFC 8032 e il giro completo del formato;
- 30 firme casuali sono risultate identiche a quelle della libreria `cryptography` (44.0.2);
- emissione, verifica, revoca e conteggio del lancio sono stati provati in una cartella di prova;
- **non è ancora integrato nell'app**.

## 1. Come è fatta la chiave

Testo: `IMP1-` seguito dal base32 (RFC 4648, senza `=`) di `payload || firma`, a gruppi di 5 caratteri separati da `-`. Esempio, di 199 caratteri:

```
IMP1-AEDQE-AQCAA-AAAAB-KAGRB-QU3UO-VSGS3-ZAIZX-XI33H-OJQWM-2LDN4-QMHAD-MMZQ5-...
```

| Byte | Campo | Valori |
|---|---|---|
| 0 | formato | `1` |
| 1 | id della chiave di firma | 1-255. Serve alla rotazione: l'app conosce più chiavi pubbliche |
| 2 | fascia | 1 essenziale, 2 pro, 3 studio, 4 laboratorio |
| 3 | versione maggiore | `2` |
| 4 | computer (attivazioni) | da `tier.json`: 1, 2 o 5 |
| 5 | flag | bit 0 omaggio, bit 1 beta |
| 6-9 | seriale | uint32 big-endian, progressivo nel registro |
| 10-11 | data di emissione | giorni dal 01/01/2026, uint16 big-endian |
| 12 | n | lunghezza dell'intestatario, 0-48 |
| 13…13+n | intestatario | UTF-8, ad esempio «Studio Rossi» |
| ultimi 64 | firma | Ed25519 di `b"IMPAGINATORE-LICENZA-v1\x00" + payload` |

Il prefisso `IMP1-` distingue queste chiavi da quelle Polar (`IMP-` seguito da un UUID: `polar/API-LICENZE.md`). L'app può accettare entrambi i formati.

## 2. Cosa fa l'app

1. **Normalizzare** il testo: maiuscole, via spazi, a capo e trattini. Accettare anche il link `impaginatore://attiva?chiave=…`. La funzione `da_testo` lo fa già.
2. **Verificare** con `decodifica(testo, CHIAVI_PUBBLICHE)`, cioè la verifica Ed25519 sulle chiavi pubbliche compilate nell'app. Le funzioni `ed25519_verifica`, `da_testo` e `decodifica` di `chiavi.py` si copiano così come sono: libreria standard, verifica in circa 0,1 s. In alternativa si usa `cryptography` o PyNaCl: il formato non cambia.
3. **Sbloccare** le `funzioni` della fascia (`tier.json`) e mostrare «Licenza Pro per 2 computer, intestata a Studio Rossi».
4. **Salvare** il testo della chiave nella cartella dati dell'utente, così sopravvive alla reinstallazione.
5. Se `versione_maggiore` è diversa dalla versione dell'app, scrivere «Questa chiave è per Impaginatore N» e indicare il prezzo dell'upgrade.

Non serve la rete. **Il numero di computer non viene contato**: senza un server non si può. Il limite vale per contratto (EULA) ed è reso visibile dall'intestatario mostrato nell'app. È coerente con il prezzo d'impulso: costa meno comprare una seconda licenza che aggirarla. Se un giorno si vorrà contarli, si attiva l'attivazione online con Polar (`polar/API-LICENZE.md`) o con il proxy nostro.

Decisione del titolare (15/11/2026): in `tier.json` `politica_aggiornamenti.attivazione_online_una_tantum_per_computer` vale `false`. Non ci sono attivazioni online: il numero di computer è un limite contrattuale.

## 3. Che cosa garantisce la firma, e che cosa no

- Chi non ha la chiave privata non può fabbricare o modificare una licenza: cambiare la fascia rompe la firma (provato in `autotest`).
- Chi copia una chiave valida la può usare su altri computer, ma vi compare il nome dell'intestatario.
- Chi modifica l'app (patch del controllo) aggira qualsiasi verifica locale. Nessuno schema solo locale lo impedisce; con questi prezzi non vale la pena inseguirlo.

## 4. Revoche (rimborsi), facoltative e mai bloccanti

- `chiavi.py revoca --seriale N --motivo rimborso` aggiorna il registro e firma `revoche.json`, con dominio `IMPAGINATORE-REVOCHE-v1\0` e JSON canonico senza il campo `firma`.
- Il file si pubblica a un indirizzo fisso, per esempio `https://<dominio>/licenze/revoche.json`.
- L'app lo scarica al massimo una volta alla settimana, quando c'è rete, e **solo se la firma è valida** mette in sola lettura le licenze elencate.
- Errori di rete o file assente: nessun effetto.
- Senza sito la revoca resta solo nel registro: si accetta, il rimborso è un caso raro.

Dopo un **upgrade di fascia** si emette una chiave nuova e la vecchia si revoca con `--motivo upgrade`.

## 5. Chiave privata e registro

- Vivono **fuori dal repository**: in `~/.impaginatore-negozio`, oppure in `--dir`, oppure nella cartella indicata da `IMPAGINATORE_NEGOZIO_DIR`. Lo script rifiuta una cartella interna al repository.
- I permessi sono 600 sui file e 700 sulla cartella.
- **Copia offline obbligatoria** della chiave privata (chiavetta cifrata o stampa). Se la si perde, le app distribuite non accettano le nuove licenze finché un aggiornamento non porta una nuova chiave pubblica.
- **Se la chiave privata viene rubata**:
  1. `genera-coppia --nuova` crea una chiave con un nuovo id;
  2. l'aggiornamento successivo dell'app rifiuta le chiavi con il vecchio id emesse dopo la data del furto (il campo data è firmato);
  3. si riemettono le chiavi ai clienti, gratis.
- `registro.csv` contiene per ogni licenza seriale, data, fascia, prezzo (`listino`, `lancio`, `upgrade`, `rottamazione`, `convenzione`, `omaggio`, `beta`), riferimento della fattura, intestatario, impronta e stato.
- Il registro è un dato contabile del titolare. Contiene dati personali (l'intestatario), quindi va nel backup e non si condivide.
- `stato-lancio` conta le licenze `lancio` ancora attive rispetto alle 300 di `tier.json`. Una licenza rimborsata libera il posto.
