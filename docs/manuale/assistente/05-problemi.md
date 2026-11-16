# 5. Se non funziona

## L'assistente non vede Impaginatore

1. Controlla il file di configurazione (vedi [Collegare](03-collegare.md)). Un errore comune è una virgola mancante o
   in più: il file deve essere JSON valido.
2. Controlla il percorso del comando. Deve essere completo, da `/` (macOS, Linux) o da `C:\` (Windows).
3. Prova il comando nel Terminale con il percorso completo e `mcp --help`, per esempio
   `/Users/nome/Impaginatore/.venv/bin/impaginatore mcp --help`. Deve rispondere con l'aiuto.
4. Chiudi del tutto l'assistente e riaprilo.

Claude Desktop scrive cosa succede nei suoi registri:

| Sistema | Cartella | File |
|---|---|---|
| macOS | `~/Library/Logs/Claude` | `mcp.log` e `mcp-server-impaginatore.log` |
| Windows | `%APPDATA%\Claude\logs` | gli stessi |

In Claude Code: `claude mcp list` nel Terminale, oppure `/mcp` dentro Claude Code.

## «Il server MCP ha bisogno dell'SDK ufficiale «mcp»…»

Manca il componente per l'assistente. Da una copia del codice: `uv sync --extra mcp`.

## «Il collegamento con l'assistente AI (MCP) non fa parte della licenza Essenziale…»

La licenza Essenziale non comprende l'assistente. Serve Pro o Studio.

## «Impaginatore è in sola lettura…»

La prova gratuita è finita. Inserisci la chiave di licenza: vedi [Prova gratuita e licenza](../11-prova-licenza.md).

## Una richiesta finisce con «(limite della licenza)»

Quella funzione non è nella tua licenza. Per esempio la bozza non c'è con Essenziale.

## L'assistente dice che le immagini sono spente

È così di serie. Leggi [Cosa vede l'assistente](02-cosa-vede.md) prima di accenderle.

## «L'album è stato modificato nell'editor dopo la tua ultima lettura…»

Hai cambiato l'album nell'editor mentre l'assistente lavorava. Non è un errore: l'assistente rilegge l'album e
riprova. Se non lo fa, chiediglielo.

## «Impaginatore non risponde: forse è stato chiuso.»

Il programma è stato chiuso. Chiedi all'assistente di riaprire l'album.

## «Troppe richieste in poco tempo…»

L'assistente ha fatto più di 120 richieste in un minuto. Aspetta qualche secondo.

## Non vedo il programma, ma l'assistente ci lavora

L'assistente ha avviato Impaginatore senza finestra. Apri Impaginatore: si collega a quello già acceso. Oppure chiedi
all'assistente «Mostrami l'album»: si apre nel browser.

## Dove sono i file esportati dall'assistente?

Nella cartella dell'album, in `Esportazioni/JPG` o `Esportazioni/PDF`, in una cartella che comincia con «Assistente»
e la data.
