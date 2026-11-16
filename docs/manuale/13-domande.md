# 13. Domande frequenti e se qualcosa non va

## Domande frequenti

**Dove sono i miei album?**
Gli album creati dalla cartella delle foto stanno accanto alle foto, nella cartella `Impaginatore`. Gli altri stanno
nella cartella scritta in fondo alla schermata Album: «I nuovi album vengono salvati in: …». Per aprire la cartella di
un album: «⋯» sulla riga › «Mostra nel Finder» (Windows: «Mostra in Esplora risorse»).

**Il programma modifica le mie foto?**
No. Correzioni, ritagli e bianco e nero stanno nell'album. Finiscono solo nei file che esporti.

**Le mie foto vanno su internet?**
No. Impaginatore non carica le foto in rete. Fa eccezione solo l'assistente AI, e solo se lo permetti tu: vedi
[Cosa vede l'assistente](assistente/02-cosa-vede.md).

**Serve internet?**
No. Anche la chiave di licenza si controlla senza internet.

**Il primo avvio di un album è lento.**
All'apertura il programma prepara le miniature e cerca i volti nelle foto. Lo fa mentre lavori: puoi cominciare
subito. Le volte dopo è più veloce.

**Una foto ha i ppi in rosso.**
La foto è troppo ingrandita per la sua cornice: in stampa si vedrà sgranata. Rimpicciolisci la cornice o usa
un'altra foto. Sotto 150 ppi il controllo la segna tra le cose che bloccano la stampa.

**Alcune foto non sono state importate.**
Il programma salta le foto con un nome di file già presente nell'album e i formati che non apre (RAW, GIF, BMP,
PSD; HEIC senza il componente apposito). Vedi [Le foto](03-foto.md).

**Su un altro computer i testi hanno un altro carattere.**
Quel computer non ha il carattere usato. Installa i caratteri elencati in `font_usati.txt`, nella copia del progetto.

**Posso aprire lo stesso album in due finestre?**
Meglio di no. Se succede, una finestra si aggiorna e leggi «L'album è cambiato in un'altra finestra: ti mostro com'è
adesso. Rifai l'ultima modifica.»

**Posso usare il programma su Linux?**
Sì, ma senza PSD: Photoshop non c'è per Linux.

## Se qualcosa non va

**Nell'elenco degli album lo stato è «Non si apre».**
Il programma non riesce a leggere l'album. Se la cartella è su un disco esterno, collegalo. Se hai spostato la
cartella, aprila di nuovo con «⋯» › «Apri album esistente…». Non cancellare la cartella: scrivi all'assistenza.

**«L'album non si è aperto. Riprova; se succede ancora, guarda il file editor.log nella cartella degli album.»**
Chiudi il programma e riaprilo. Se succede ancora, manda all'assistenza il file `editor.log`. Lo trovi nella
cartella scritta in fondo alla schermata Album.

**In alto leggi «Non salvato: riprova».**
Cliccalo. Se non basta, il disco può essere pieno, scollegato o protetto. Non chiudere il programma finché non leggi
«Salvato».

**«⚠ N foto mancanti».**
Le foto sono state spostate o rinominate, o il disco è scollegato. Vedi [Foto da ricollegare](10-progetti-e-foto.md).

**L'esportazione non parte.**
Leggi il messaggio nella finestra «Esporta». I casi più comuni sono in [Esportare](08-esportare.md#se-qualcosa-non-va).

**I PSD non si creano.**
Serve Photoshop installato su questo computer (macOS o Windows). Il motivo è nella finestra «Esporta». Durante la prova gratuita e con la licenza Essenziale i PSD non ci sono.

**Nel browser leggi «Questa scheda non è collegata al programma.»**
Apri Impaginatore dal suo collegamento, non da un indirizzo salvato. L'indirizzo vale una volta sola.

**Non riesco a modificare niente.**
Guarda in alto: se leggi «Sola lettura», la prova è finita. Vedi [Prova gratuita e licenza](11-prova-licenza.md).

## Scrivere all'assistenza

Scrivi a {{EMAIL_SUPPORTO}}. *(indirizzo da inserire)*

Scrivi:

- cosa stavi facendo e cosa hai letto sullo schermo (una schermata aiuta);
- la versione del programma: è in alto nella schermata Album;
- il tuo sistema: macOS, Windows o Linux.

Se ti chiedono il registro del programma, è il file `impaginatore.log` in questa cartella:

| Sistema | Cartella |
|---|---|
| macOS | `~/Library/Application Support/Impaginatore/registro` |
| Windows | `%APPDATA%\Impaginatore\registro` |
| Linux | `~/.local/share/impaginatore/registro` |

Il registro contiene nomi di cartelle e di file, non le foto. Non mandare le foto dei tuoi clienti se non te le
chiedono.
