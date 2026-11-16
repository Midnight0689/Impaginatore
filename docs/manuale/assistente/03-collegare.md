# 3. Collegare Claude Desktop o Claude Code

## Prima di cominciare

Ti serve:

1. Impaginatore con il componente per l'assistente. Non c'è ancora un installatore (vedi
   [Installare](../00-installazione.md)). Da una copia del codice il componente si installa con:

   ```
   uv sync --extra mcp
   ```

   Il comando per l'assistente è `impaginatore mcp`. Senza il componente, il comando lo dice ed esce.
2. Una licenza Pro o Studio, o la prova gratuita.
3. Claude Desktop o Claude Code, con il tuo account.

### Il percorso completo del comando

Claude Desktop non sempre trova i comandi che trovi nel Terminale. Scrivi il percorso completo di `impaginatore`.

- macOS e Linux: nel Terminale scrivi `which impaginatore`. Se usi una copia del codice, il comando è in
  `<cartella del codice>/.venv/bin/impaginatore`.
- Windows: nel Prompt dei comandi scrivi `where impaginatore`. Da una copia del codice:
  `<cartella del codice>\.venv\Scripts\impaginatore.exe`.

## Claude Desktop

1. Apri Claude Desktop.
2. Apri le impostazioni dal menu del programma (non quelle nella finestra della chat): «Settings…» › «Developer» ›
   «Edit Config». I nomi cambiano da una versione all'altra e possono essere in italiano.
3. Si apre la cartella con il file `claude_desktop_config.json`:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux (Claude Desktop per Linux è in prova): `~/.config/Claude/claude_desktop_config.json`
4. Apri il file con un editor di testo e scrivi (al posto del percorso d'esempio, il tuo):

   ```json
   {
     "mcpServers": {
       "impaginatore": {
         "command": "/Users/nome/Impaginatore/.venv/bin/impaginatore",
         "args": ["mcp"]
       }
     }
   }
   ```

   Se nel file c'è già un blocco `"mcpServers"`, aggiungi solo la parte `"impaginatore": { … }` dentro quel blocco,
   separata dalle altre da una virgola.
5. Salva il file.
6. Chiudi del tutto Claude Desktop (non solo la finestra) e riaprilo.
7. Nella chat, dal pulsante «+» sotto il riquadro di scrittura, apri i connettori: deve comparire «impaginatore».
8. Prova: scrivi «Che album ho in Impaginatore?».

Claude ti chiede il permesso prima di usare un comando di Impaginatore.

### Con la copia del codice e uv

Se preferisci lanciare il programma con uv:

```json
{
  "mcpServers": {
    "impaginatore": {
      "command": "uv",
      "args": ["--directory", "/percorso/di/Impaginatore", "run", "--extra", "mcp", "impaginatore", "mcp"]
    }
  }
}
```

Anche qui, se `uv` non si trova, scrivi il suo percorso completo (`which uv`).

## Claude Code

Nel Terminale:

```
claude mcp add --scope user impaginatore -- impaginatore mcp
```

- `--scope user` rende Impaginatore disponibile in tutte le cartelle in cui usi Claude Code. Senza, vale solo nella
  cartella in cui hai dato il comando.
- Se `impaginatore` non si trova, scrivi il percorso completo al posto del secondo `impaginatore`.

Da una copia del codice, con uv:

```
claude mcp add --scope user impaginatore -- uv --directory /percorso/di/Impaginatore run --extra mcp impaginatore mcp
```

Per controllare:

- nel Terminale, `claude mcp list` mostra i collegamenti e se funzionano;
- dentro Claude Code, `/mcp` mostra lo stato e ricollega.

Claude Code ti chiede il permesso prima di usare un comando di Impaginatore. Puoi dirgli di non chiederlo più per un
comando: le modifiche dell'album si annullano comunque.

Per togliere il collegamento: `claude mcp remove impaginatore`.

## Le immagini con l'opzione

Il modo semplice per accendere le immagini è l'interruttore nella schermata Album (vedi
[Cosa vede l'assistente](02-cosa-vede.md)). Chi preferisce la configurazione aggiunge l'opzione:

```json
"args": ["mcp", "--consenti-immagini"]
```

oppure, con Claude Code, `-- impaginatore mcp --consenti-immagini`. Poi riavvia l'assistente. Con l'opzione le immagini
restano accese anche se l'interruttore è spento.
