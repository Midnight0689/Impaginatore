# Sito di vendita di Impaginatore (T-502)

Pagine statiche scritte a mano: HTML, un foglio di stile, un piccolo script. Nessun framework, nessuna dipendenza da installare, nessuna risorsa da altri siti (caratteri compresi), nessun cookie, nessun tracciamento. Si aprono anche con un doppio clic su `index.html` e funzionano su qualsiasi hosting statico.

**Stato: modello pronto, non pubblicabile così com'è.** Dominio, indirizzi email, titolare, testi legali, installatori e pagina d'installazione non esistono ancora: l'elenco è sotto, in «Prima di pubblicare». Dal riallineamento T-501 le pagine descrivono solo quello che la versione 2.0 fa oggi; quello che manca è tolto o detto «in arrivo», senza date.

## Cosa c'è

| Percorso | Cosa |
|---|---|
| `index.html` | Pagina principale in italiano |
| `en/index.html` | La stessa pagina in inglese (`hreflang` reciproci) |
| `prezzi.html` | Fasce, tabella delle funzioni, aggiornamenti, come si compra, domande sui prezzi |
| `installa.html`, `en/installa.html` | Per ora solo «gli installatori sono in arrivo»: fuori dai menu e dalla mappa del sito finché non esistono (T-301, T-302). Il testo di prima (comando di una riga, installatore classico, impronte) è nella storia di git |
| `grazie.html` | Conferma dopo la lista d'attesa (`?per=lista`) o la richiesta d'acquisto (`?per=acquisto`); senza JavaScript mostra entrambi i blocchi |
| `legale.html` | Privacy, condizioni, licenza, assistenza, terze parti, foto delle schermate, titolare: **riassunti segnaposto** |
| `404.html` | Pagina d'errore, con percorsi dalla radice del sito |
| `config.json` | **Unico punto di configurazione** (vedi sotto) |
| `css/sito.css` | Stile del sito; colori, caratteri e spazi solo dai token |
| `css/token.css`, `css/font.css`, `font/`, `img/marca/`, `favicon.*` | Copie dalla marca fatte da `sito.py marca`: non si modificano qui |
| `js/sito.js` | Copia dei comandi, blocchi di `grazie.html`, rete di sicurezza del prezzo di lancio, chiusura del menu |
| `img/schermate/` | WebP delle schermate in più larghezze, ricavati da `img/originali/` (esclusa da git) |
| `img/og/` | Immagini Open Graph 1200 × 630, rese da `strumenti/modelli/og.html` |
| `sitemap.xml`, `robots.txt` | Generati da `sito.py configura` |
| `strumenti/` | `sito.py` (tutti i passi), `schermate.py` (schermate della 2.0, in italiano e in inglese), `cromo.py` (Chrome senza schermo, solo libreria standard) |
| `anteprime/` | Istantanee di ogni pagina a 360, 768, 1280 e 1920 px, tema chiaro e scuro |
| `RICERCA.md` | Ricerca sulle pagine di vendita e scelte che ne derivano |

## Comandi

Dalla cartella `marketing/sito`:

```
python3 strumenti/sito.py marca         # token, caratteri, logo, icone da brand/
python3 strumenti/sito.py immagini      # WebP delle schermate, immagini Open Graph, icona Apple (Pillow e Chrome)
python3 strumenti/sito.py configura     # applica config.json e docs/mercato/tier.json alle pagine
python3 strumenti/sito.py controlla     # controlli; con --pubblicazione rifiuta anche i segnaposto
python3 strumenti/sito.py istantanee    # anteprime/ (Chrome e Pillow)
python3 strumenti/sito.py pubblica /percorso/vuoto   # copia solo i file da mettere sul server
python3 strumenti/sito.py tutto         # marca, immagini, configura, controlla
```

Servono Python 3.10 o successivo, Chrome o Chromium (per immagini e istantanee) e Pillow (per immagini e istantanee: `uv run --with pillow python3 strumenti/sito.py immagini`, oppure il Python di `.venv` del progetto). `marca`, `configura` e `controlla` usano solo la libreria standard. `cromo.py` parla con Chrome su una pipe, senza aprire porte; funziona su Linux e macOS.

Per vedere il sito: apri `index.html` nel browser, oppure `python3 -m http.server -d marketing/sito 8000` e vai su `http://127.0.0.1:8000/`.

## Come funziona la configurazione

`config.json` contiene tutto ciò che cambia da un'installazione all'altra: dominio, percorso base, indirizzi email, indirizzo del modulo della lista d'attesa, link d'acquisto e di download, requisiti di sistema, date di lancio, dati del titolare e tre interruttori. **I prezzi non stanno qui**: vengono solo da `docs/mercato/tier.json`.

Dopo ogni modifica a `config.json` o a `tier.json` si esegue `sito.py configura`, che riscrive soltanto i testi e gli attributi marcati:

| Marcatura | Effetto |
|---|---|
| `data-prezzo="pro.oggi"` | Il testo diventa il prezzo da `tier.json` («79 €», «€79» in inglese). `.oggi` è il prezzo di lancio fino a `data_fine_lancio`, poi il listino; `.listino`, `.oggi_ivato`, `ore.ore_5`, `upgrade.pro`, `passaggio.essenziale_pro` e altri: vedi `valori()` in `sito.py` |
| `data-valore="computer.pro"` | Il testo diventa un numero da `tier.json` (computer, giorni di prova, giorni di rimborso, mesi tra versioni maggiori…) |
| `data-cfg="email.contatti"` | Il testo diventa il valore di `config.json`; ci sono anche `data_lancio`, `data_fine_lancio` (scritte per esteso), `requisiti` (le FAQ «Su quali sistemi funziona?»); `comando_mac` e `comando_windows` restano in `config.json` per la pagina d'installazione futura |
| `data-link="acquisto.pro"` | `href` diventa il link configurato; se è vuoto, un `mailto:` già compilato (acquisto con i dati per la fattura, ore di assistenza, laboratori, lista d'attesa) |
| `data-url="prezzi.html"` | `href` o `content` diventa l'indirizzo assoluto (canonical, `hreflang`, Open Graph) |
| `data-se="in_vendita"`, `data-se-non="in_vendita"` | Mostra o nasconde l'elemento (`hidden`). Interruttori: `in_vendita`, `mcp_disponibile`, `riprova_sociale`, più `lancio` (vero fino a `data_fine_lancio`) e `modulo_lista` (vero se c'è l'indirizzo del modulo) |
| `data-fonte="mercato"` | Cifre di terzi (il confronto con gli abbonamenti): escluse dal controllo dei prezzi, da riverificare a mano |
| `<script data-ld="software">`, `data-ld="faq"` | Dati strutturati `SoftwareApplication` (offerte dai prezzi di oggi, `PreOrder` o `InStock`) e `FAQPage` (dalle domande visibili della pagina) |

Gli interruttori:

- `in_vendita` (oggi `false`): in prevendita i pulsanti dicono «Avvisami al lancio» e portano alla lista d'attesa; quando è vero diventano «Scarica la prova gratuita» e «Acquista …» e portano a `installa.html`. **Non accenderlo finché `installa.html` dice solo «in arrivo»**.
- `mcp_disponibile` (oggi `true`, da T-501: l'assistente esiste dalla T-203): la sezione «Se usi Claude, può lavorare sull'album con te», la riga nella card Pro e nella tabella delle fasce. La sezione dice che cosa riceve l'assistente e che le immagini sono spente di serie, come `docs/manuale/assistente/02-cosa-vede.md`. L'interruttore omonimo delle email (`marketing/email/strumenti/costanti.json`) è ancora spento: il componente si installa solo da una copia del codice.
- `riprova_sociale` (oggi `false`): la sezione delle testimonianze. Si accende solo con testimonianze vere e consenso scritto.

La lista d'attesa: con `modulo_lista_attesa` vuoto, al posto del modulo c'è un pulsante `mailto:` con il messaggio già scritto (destinatario `email.lista_attesa`). Con un indirizzo, compare il modulo (`email`, `consenso`, `lingua`, in POST); il servizio che lo riceve deve rimandare a `grazie.html?per=lista`. Non c'è un ripiego che finga un'iscrizione andata a buon fine.

Il prezzo di lancio ha due sicurezze: `configura` sceglie lancio o listino in base alla data di oggi, e `js/sito.js` sostituisce comunque il prezzo con il listino (attributo `data-listino`) e nasconde le frasi sul lancio se la data scritta in `<html data-fine-lancio>` è passata. Il controllo `--pubblicazione` segnala una data già scaduta.

## Che cosa controlla `sito.py controlla`

Pagine allineate a `config.json` e `tier.json`; un solo `h1` e titoli senza salti; `id` unici; titolo, descrizione, viewport, canonical, `hreflang` fra le pagine gemelle; collegamenti interni e ancore; nessuna richiesta verso altri siti (HTML, CSS, JS); immagini con `alt`, `width`/`height` coerenti con il file e `loading="lazy"` sotto la piega; SVG decorativi nascosti; campi con etichetta; link con testo; parole vietate dallo stylebook (§5) e punti esclamativi ed emoji, in italiano e in inglese; marchi dei concorrenti (da `docs/mercato/competitor.json` più un elenco fisso); ogni cifra in euro legata a `tier.json` o marcata come prezzo di mercato; niente testo barrato; peso di ogni pagina. Con `--pubblicazione` rifiuta anche: segnaposto `{{…}}` e testi «SEGNAPOSTO», dominio ed email `.example`, schermate segnaposto visibili, data di lancio passata.

`sito.py istantanee` apre ogni pagina in Chrome alle quattro larghezze nei due temi e segnala scorrimento orizzontale, richieste esterne, errori JavaScript e immagini che non si caricano.

## Pubblicare

1. Compila `config.json`: `dominio`, `percorso_base`, email, `titolare`, `partita_iva`, `sede`, `requisiti`, `data_lancio`, `data_fine_lancio`; il modulo della lista d'attesa se c'è.
2. Il giorno del lancio: riscrivi `installa.html` e `en/installa.html` con i file veri e rimettile in `NELLA_MAPPA` (`sito.py`), nei menu e nei piedi; poi `in_vendita: true`, link di download, link alle impronte, eventuali link d'acquisto (vuoti = `mailto:` all'indirizzo `email.vendite`).
3. Se il sito non sta nella radice del dominio, cambia `percorso_base` e i percorsi che iniziano con `/` in `404.html`.
4. `python3 strumenti/sito.py tutto --pubblicazione` deve finire con 0 errori.
5. `python3 strumenti/sito.py pubblica /percorso/vuoto` e carica il contenuto di quella cartella sull'hosting, con HTTPS. Configura l'hosting perché serva `404.html` per le pagine mancanti.
6. Intestazioni consigliate: `Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; form-action 'self' <indirizzo del modulo>`, `Referrer-Policy: strict-origin-when-cross-origin`, cache lunga per `font/` e `img/`.
7. Se la pagina d'installazione tornerà al comando di una riga, `installa.sh` e `installa.ps1` vanno pubblicati nella radice accanto alle pagine (T-302).

## Segnaposto

| Dove | Cosa manca |
|---|---|
| `config.json` | Dominio e email (`.example`), `titolare`, `partita_iva`, `sede`, requisiti minimi di memoria e disco, link di download e impronte, modulo della lista d'attesa |
| `legale.html` | Tutti i testi completi: oggi ci sono riassunti marcati «SEGNAPOSTO» con il documento di origine in `docs/legale/` |
| `index.html`, `en/index.html` | Sezione delle testimonianze (nascosta, `riprova_sociale`) |
| `installa.html`, `en/installa.html` | Tutta la pagina: oggi dice «in arrivo» (T-301, T-302) |
| Confronto dei costi | Le larghezze delle barre (`style="width:…"`) sono scritte a mano su 99 € e 870 €: se cambiano listino o prezzi di mercato, vanno ricalcolate |

## Schermate

Le schermate vengono dalla versione 2.0 (T-205, T-206), in italiano e in inglese: le pagine inglesi usano i file `-en`. Le foto sono **sintetiche**, le stesse forme di `strumenti/schermate_ux.py` (cielo, terreno, sagoma; con EXIF di data e ora), ingrandite tre volte: nessuna persona vera, niente `marketing/demo`. L'album è uno solo, «Matrimonio Rossi Bianchi» («Wedding Smith Jones»): 36 foto, prodotto «Orizzontale 30 × 22,5» del catalogo dei formati comuni, 12 spread fatti da «Prepara la bozza» applicata così com'è. Finestra 1280 × 800 a densità 2, tema chiaro, licenza Pro di prova con una chiave generata per la sessione.

| Nome stabile | Misura pubblicata | Contenuto | Usata in |
|---|---|---|---|
| `editor-album`, `-en` | 2400 × 1500 | L'editor intero nella vista Impagina, spread 05–06 | copertina IT/EN, Open Graph |
| `bozza`, `-en` | 1960 × 1284 | La finestra «Prepara la bozza» con la proposta di 12 spread, prima di applicarla | funzione «Prepara la bozza» |
| `disposizione`, `-en` | 2288 × 1128 | Tela e pannello delle disposizioni dopo un D sullo spread 03–04, con l'avviso «Disposizione 2 di 20» | funzione «Un'altra disposizione» |
| `controlla`, `-en` | 1460 × 1050 | Pannello «Controlla l'album» accanto allo spread, dopo due ritocchi fatti apposta (una foto schiarita di 0,9 EV, una spostata di 8 pixel della pagina) | funzione «Controlla, poi Sistema» |
| `esporta-psd`, `-en` | 1120 × 914 | Finestra «Esporta» sulla linguetta «PSD a livelli» | funzione «PSD» (non c'è una schermata di Photoshop) |
| `nuovo-album`, `-en` | 960 × 1014 | Finestra «Nuovo album» con un prodotto del catalogo dei formati comuni | funzione «Formati e cataloghi» |
| `assistente`, `-en` | 960 × 904 | Finestra «Assistente AI» della schermata degli album, immagini spente | sezione Claude |

Rifarle (Chrome; nessuna rete; casa finta in una cartella temporanea, i dati dell'utente non si toccano):

```
.venv/bin/python marketing/sito/strumenti/schermate.py              # tutte le scene, italiano e inglese
.venv/bin/python marketing/sito/strumenti/schermate.py --lingua en controlla
cd marketing/sito && ../../.venv/bin/python strumenti/sito.py immagini
```

Gli originali vanno in `img/originali/` (esclusa da git) con `schermate.json`; `sito.py immagini` ritaglia (`riquadro`) e ricava i WebP. Le schermate a finestra intera della schermata degli album mostrano in basso il nome dell'autore del programma: le scene del sito sono ritagliate in modo da non includerlo.

Nella schermata inglese «Nuovo album» il catalogo dei formati comuni ha ancora le etichette in italiano («Orizzontale 30 × 22,5», «Nessun laboratorio: formati comuni»): lo dice anche il testo alternativo.

## Prima di pubblicare: promesse da verificare

Il sito descrive la 2.0 com'è oggi (verificato su codice, manuale e schermate il 16/11/2026, T-501). Restano cose che dipendono da lavoro non ancora fatto o da decisioni del titolare:

- [ ] **Installatori** per macOS, Windows e Linux (T-301, T-302): non esistono. `installa.html` dice «in arrivo»; i pulsanti di download compaiono solo con `in_vendita`.
- [ ] **macOS e Windows**: i test automatici girano sui tre sistemi, ma il programma non è mai stato provato su computer Mac e Windows veri; requisiti minimi di memoria e disco non definiti (`config.json`, `requisiti`). Il sito non dice «testato su».
- [ ] **Aggiornamenti della versione inclusi** (card «Paghi una volta», FAQ, prezzi): è un impegno commerciale; oggi chi compra non ha un modo per ricevere gli aggiornamenti (niente aggiornamenti automatici, niente installatori).
- [ ] **Le foto restano sul tuo computer**: vero per il programma; l'eccezione dell'assistente AI con le immagini accese è scritta accanto (card, FAQ, sezione Claude, `legale.html`). La regola di `AGENTS.md` («nessuna funzione può caricarle in rete») e il consenso alle immagini dell'assistente vanno messi d'accordo dal titolare (`docs/legale/DA-DECIDERE.md` §1.15).
- [ ] **Edizione Laboratorio**: il catalogo importabile esiste; nessun laboratorio vero ha un catalogo, il marchio del laboratorio nel programma è «in arrivo», la copertina è solo descritta nel riepilogo della consegna.
- [ ] **Storia** («impagina album da più di dieci anni con un programma comprato nel 2012»): da `docs/prodotto/REQUISITI-VOCALI.md` e dallo stylebook; da far rileggere al titolare.
- [ ] **Prezzi di mercato** (150–290 € l'anno, 450–870 € in tre anni, cambio BCE del 13/11/2026) e righe della tabella di confronto per categorie: da riverificare alla data di pubblicazione.
- [ ] **Pagamento con bonifico e chiave entro 2 ore lavorative**: percorso di `marketing/negozio/FLUSSO-ACQUISTO.md` §1; se si passa a una piattaforma (§5) cambiano testi e link. `FLUSSO-ACQUISTO.md` parla ancora di link `impaginatore://` e di chiave letta dagli appunti, che il programma non ha.
- [ ] **Manuale**: il sito lo promette gratis; oggi è in `docs/manuale/`, non pubblicato.

## Punti legali aperti

Da far decidere a chi segue l'aspetto legale (vedi anche `docs/legale/DA-DECIDERE.md`):

- **Pubblicità comparativa**: il confronto è per categorie e senza marchi, ma le cifre dei concorrenti devono essere verificabili e datate. La pagina dice che le fonti sono disponibili su richiesta; valutare se pubblicarle.
- **Prezzi IVA esclusa in grande**: il pubblico sono professionisti, ma la pagina è visibile ai consumatori. Il totale con IVA è sempre accanto; valutare se basta (art. 49 Codice del consumo).
- **Recesso** per i contenuti digitali e la funzione di recesso richiesta per i contratti online: su un sito statico senza carrello va chiarito come si esercita.
- **Accessibilità** (European Accessibility Act): il sito è costruito per WCAG 2.2 AA, ma non è stato verificato con un lettore di schermo né da un revisore.
- **Testi legali in contraddizione** con le decisioni di `tier.json`: `docs/legale/TERMINI-VENDITA.md` §4.3 e `PRIVACY.md` (righe C e I) parlano di un server di attivazione e di cookie statistici con consenso; il sito dice «nessun server di attivazione» e «nessun cookie».
- **Assistente AI**: che cosa riceve il fornitore dell'assistente (testi e nomi di tutti gli album elencati, immagini solo col consenso) è scritto nel riassunto di `legale.html`; ruoli, base giuridica e trasferimenti fuori dall'UE sono aperti in `docs/legale/DA-DECIDERE.md` §1.15.
- **IVA per chi compra dall'estero**: la pagina inglese dice che si paga l'IVA del proprio paese o nessuna con partita IVA europea valida; vale se l'IVA viene gestita così (OSS o piattaforma).

## Cose note da sistemare

- `cromo.py` non funziona su Windows (pipe ereditate): istantanee e immagini Open Graph si fanno da Linux, macOS o WSL.
- Le barre del confronto dei costi non seguono i prezzi in automatico.
- L'immagine Open Graph non ha la versione scura (le reti sociali non la usano).
- `anteprime/` è fuori da git (`.gitignore`): si rigenera con `sito.py istantanee`, anche solo a 390 e 1280 px (`--larghezze 390,1280`).
