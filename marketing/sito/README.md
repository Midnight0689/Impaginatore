# Sito di vendita di Impaginatore (T-502)

Pagine statiche scritte a mano: HTML, un foglio di stile, un piccolo script. Nessun framework, nessuna dipendenza da installare, nessuna risorsa da altri siti (caratteri compresi), nessun cookie, nessun tracciamento. Si aprono anche con un doppio clic su `index.html` e funzionano su qualsiasi hosting statico.

**Stato: modello pronto, non pubblicabile così com'è.** Dominio, indirizzi email, titolare, testi legali, tre schermate e diverse funzioni promesse non esistono ancora: l'elenco è sotto, in «Prima di pubblicare».

## Cosa c'è

| Percorso | Cosa |
|---|---|
| `index.html` | Pagina principale in italiano |
| `en/index.html` | La stessa pagina in inglese (`hreflang` reciproci) |
| `prezzi.html` | Fasce, tabella delle funzioni, aggiornamenti, come si compra, domande sui prezzi |
| `installa.html`, `en/installa.html` | Comando di una riga spiegato pezzo per pezzo, installatore classico, verifica dell'impronta |
| `grazie.html` | Conferma dopo la lista d'attesa (`?per=lista`) o la richiesta d'acquisto (`?per=acquisto`); senza JavaScript mostra entrambi i blocchi |
| `legale.html` | Privacy, condizioni, licenza, assistenza, terze parti, crediti delle foto, titolare: **riassunti segnaposto** |
| `404.html` | Pagina d'errore, con percorsi dalla radice del sito |
| `config.json` | **Unico punto di configurazione** (vedi sotto) |
| `css/sito.css` | Stile del sito; colori, caratteri e spazi solo dai token |
| `css/token.css`, `css/font.css`, `font/`, `img/marca/`, `favicon.*` | Copie dalla marca fatte da `sito.py marca`: non si modificano qui |
| `js/sito.js` | Copia dei comandi, blocchi di `grazie.html`, rete di sicurezza del prezzo di lancio, chiusura del menu |
| `img/schermate/` | WebP delle schermate in più larghezze, ricavati da `img/originali/` (esclusa da git) |
| `img/og/` | Immagini Open Graph 1200 × 630, rese da `strumenti/modelli/og.html` |
| `sitemap.xml`, `robots.txt` | Generati da `sito.py configura` |
| `strumenti/` | `sito.py` (tutti i passi), `schermate.py` (schermate dell'editor), `cromo.py` (Chrome senza schermo, solo libreria standard) |
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
| `data-cfg="email.contatti"` | Il testo diventa il valore di `config.json`; ci sono anche `data_lancio`, `data_fine_lancio` (scritte per esteso), `comando_mac`, `comando_windows`, `requisiti` |
| `data-link="acquisto.pro"` | `href` diventa il link configurato; se è vuoto, un `mailto:` già compilato (acquisto con i dati per la fattura, ore di assistenza, laboratori, lista d'attesa) |
| `data-url="prezzi.html"` | `href` o `content` diventa l'indirizzo assoluto (canonical, `hreflang`, Open Graph) |
| `data-se="in_vendita"`, `data-se-non="in_vendita"` | Mostra o nasconde l'elemento (`hidden`). Interruttori: `in_vendita`, `mcp_disponibile`, `riprova_sociale`, più `lancio` (vero fino a `data_fine_lancio`) e `modulo_lista` (vero se c'è l'indirizzo del modulo) |
| `data-fonte="mercato"` | Cifre di terzi (il confronto con gli abbonamenti): escluse dal controllo dei prezzi, da riverificare a mano |
| `<script data-ld="software">`, `data-ld="faq"` | Dati strutturati `SoftwareApplication` (offerte dai prezzi di oggi, `PreOrder` o `InStock`) e `FAQPage` (dalle domande visibili della pagina) |

Gli interruttori:

- `in_vendita` (oggi `false`): in prevendita i pulsanti dicono «Avvisami al lancio» e portano alla lista d'attesa; quando è vero diventano «Scarica la prova gratuita» e «Acquista …», e compaiono i pulsanti di download.
- `mcp_disponibile` (oggi `false`): la sezione «Se usi Claude, può preparare la bozza con te», la riga nella card Pro e nella tabella delle fasce. Come l'interruttore omonimo delle email (`marketing/email/strumenti/costanti.json`).
- `riprova_sociale` (oggi `false`): la sezione delle testimonianze. Si accende solo con testimonianze vere e consenso scritto.

La lista d'attesa: con `modulo_lista_attesa` vuoto, al posto del modulo c'è un pulsante `mailto:` con il messaggio già scritto (destinatario `email.lista_attesa`). Con un indirizzo, compare il modulo (`email`, `consenso`, `lingua`, in POST); il servizio che lo riceve deve rimandare a `grazie.html?per=lista`. Non c'è un ripiego che finga un'iscrizione andata a buon fine.

Il prezzo di lancio ha due sicurezze: `configura` sceglie lancio o listino in base alla data di oggi, e `js/sito.js` sostituisce comunque il prezzo con il listino (attributo `data-listino`) e nasconde le frasi sul lancio se la data scritta in `<html data-fine-lancio>` è passata. Il controllo `--pubblicazione` segnala una data già scaduta.

## Che cosa controlla `sito.py controlla`

Pagine allineate a `config.json` e `tier.json`; un solo `h1` e titoli senza salti; `id` unici; titolo, descrizione, viewport, canonical, `hreflang` fra le pagine gemelle; collegamenti interni e ancore; nessuna richiesta verso altri siti (HTML, CSS, JS); immagini con `alt`, `width`/`height` coerenti con il file e `loading="lazy"` sotto la piega; SVG decorativi nascosti; campi con etichetta; link con testo; parole vietate dallo stylebook (§5) e punti esclamativi ed emoji, in italiano e in inglese; marchi dei concorrenti (da `docs/mercato/competitor.json` più un elenco fisso); ogni cifra in euro legata a `tier.json` o marcata come prezzo di mercato; niente testo barrato; peso di ogni pagina. Con `--pubblicazione` rifiuta anche: segnaposto `{{…}}` e testi «SEGNAPOSTO», dominio ed email `.example`, schermate segnaposto visibili, data di lancio passata.

`sito.py istantanee` apre ogni pagina in Chrome alle quattro larghezze nei due temi e segnala scorrimento orizzontale, richieste esterne, errori JavaScript e immagini che non si caricano.

## Pubblicare

1. Compila `config.json`: `dominio`, `percorso_base`, email, `titolare`, `partita_iva`, `sede`, `requisiti`, `data_lancio`, `data_fine_lancio`; il modulo della lista d'attesa se c'è.
2. Il giorno del lancio: `in_vendita: true`, link di download, link alle impronte, eventuali link d'acquisto (vuoti = `mailto:` all'indirizzo `email.vendite`).
3. Se il sito non sta nella radice del dominio, cambia `percorso_base` e i percorsi che iniziano con `/` in `404.html`.
4. `python3 strumenti/sito.py tutto --pubblicazione` deve finire con 0 errori.
5. `python3 strumenti/sito.py pubblica /percorso/vuoto` e carica il contenuto di quella cartella sull'hosting, con HTTPS. Configura l'hosting perché serva `404.html` per le pagine mancanti.
6. Intestazioni consigliate: `Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; form-action 'self' <indirizzo del modulo>`, `Referrer-Policy: strict-origin-when-cross-origin`, cache lunga per `font/` e `img/`.
7. `installa.sh` e `installa.ps1` vanno pubblicati nella radice accanto alle pagine (li prepara il team prodotto, T-302): finché mancano, il controllo li segnala come avviso.

## Segnaposto

| Dove | Cosa manca |
|---|---|
| `config.json` | Dominio e email (`.example`), `titolare`, `partita_iva`, `sede`, requisiti minimi di memoria e disco, link di download e impronte, modulo della lista d'attesa |
| `legale.html` | Tutti i testi completi: oggi ci sono riassunti marcati «SEGNAPOSTO» con il documento di origine in `docs/legale/` |
| `index.html`, `en/index.html` | Sezione delle testimonianze (nascosta, `riprova_sociale`) |
| `img/schermate/psd-livelli-*` | Segnaposto 1600 × 1000: uno spread aperto in Photoshop con le foto su livelli separati |
| `img/schermate/preset-laboratorio-*` | Segnaposto 1600 × 1000: scelta di laboratorio, formato e copertina (dopo T-208) |
| `img/schermate/bozza-claude-*` | Segnaposto 1600 × 1000, in una sezione oggi nascosta (dopo T-203) |
| Confronto dei costi | Le larghezze delle barre (`style="width:…"`) sono scritte a mano su 99 € e 870 €: se cambiano listino o prezzi di mercato, vanno ricalcolate |
| `en/index.html` | La domanda «Is the app in English?» promette l'interfaccia inglese prima del lancio (T-206): da confermare |

## Schermate

Le schermate attuali sono **provvisorie**: mostrano l'editor 1.5.2, con i colori e la disposizione di oggi (scuro, pulsanti blu e gialli). Dopo il ridisegno dell'interfaccia (T-205) vanno rifatte tutte, anche per il rischio di somiglianza segnalato in LEG-004. I nomi dei file sono stabili: si sostituiscono gli originali e si rilancia `sito.py immagini`, le pagine non cambiano.

| Nome stabile | Misura dell'originale | Stato | Contenuto | Usata in |
|---|---|---|---|---|
| `editor-album` | 2880 × 1800 | provvisoria | Editor intero, album dimostrativo (62 foto, 25 spread), spread 22 in vista; finestra 1440 × 900 a densità 2 | copertina IT/EN, Open Graph |
| `controllo-stacchi` | 2200 × 692 | provvisoria | Finestra «Controllo spaziature» con «Correggi tutto l'album» | funzione «Spazi e tono» |
| `editor-spread` | 1720 × 1312 | provvisoria | Tela con righelli e barra degli strumenti, spread 7 | funzione «Rifinisci» |
| `spread-01` … `spread-06` | 1980 × 990 | provvisorie | Spread 10, 22, 7, 18, 24 e 8 della bozza resi dal motore d'esportazione | `spread-01` e `spread-04` nella funzione «Bozza» |
| `psd-livelli` | 1600 × 1000 | segnaposto | Spread in Photoshop con i livelli | funzione «PSD» |
| `preset-laboratorio` | 1600 × 1000 | segnaposto | Creazione dell'album con laboratorio, formato e copertina | funzione «Formati del laboratorio» |
| `bozza-claude` | 1600 × 1000 | segnaposto | Claude prepara la bozza nell'editor | sezione Claude (nascosta) |

Rigenerare le schermate dell'editor (lavora su una copia delle foto in una cartella temporanea fuori dal repository, con una casa finta: non tocca né `marketing/demo` né i progetti dell'utente; nessuna rete):

```
.venv/bin/python marketing/sito/strumenti/schermate.py --lavoro /tmp/impaginatore-schermate --eroe 21 --dettaglio 6 --spread 9,21,6,17,23,7
```

`--solo-bozza` costruisce l'album e rende tutti gli spread in piccolo, per sceglierli. La bozza è costruita dallo script con i modelli che l'editor propone per ogni gruppo di foto (in ordine di scatto, panoramiche da sole): **approssima** l'impaginazione automatica promessa per Pro, che nell'editor non esiste ancora come comando.

Foto: Pexels, 55 di Andrea Prochilo e 7 di altri autori (`marketing/demo/README.md`). Negli spread e nelle schermate ci sono volti riconoscibili, anche se piccoli (spread 22, spiaggia, ballo): prima di usarli in pubblicità serve la conferma scritta dell'autore, oppure vanno sostituiti con spread di dettagli e di spalle.

## Prima di pubblicare: promesse da verificare

Ogni frase del sito qui sotto descrive una cosa che oggi **non esiste o non è provata**. Va verificata sul prodotto vero, oppure tolta.

- [ ] **Bozza di tutto l'album** (Pro): oggi l'editor suggerisce modelli spread per spread; il comando che impagina l'album intero non c'è.
- [ ] **Formati dei laboratori** già pronti, con abbondanza, piega e copertina (T-208): non esistono.
- [ ] **Licenza, chiave, prova di 30 giorni con filigrana e sola lettura alla scadenza, fasce** (T-202): non esistono.
- [ ] **macOS, Windows e Linux**: oggi il programma gira su macOS; Windows e Linux non sono provati. PSD solo con Photoshop (non su Linux).
- [ ] **Comando d'installazione e installatori** `.dmg`, `.exe`, AppImage, `.deb` (T-302), verifica SHA-256 e firma del manifesto, collegamenti `impaginatore://`: non esistono. Le etichette di macOS («Apri comunque») e di SmartScreen vanno controllate sulle versioni in uso.
- [ ] **Funziona senza internet** e **nessun server di attivazione**: coerente con `tier.json`, da provare a programma finito.
- [ ] **Tono uniforme su tutto l'album**, **avviso di ritaglio**, **versioni salvate**, **testi con stili**, **progetto da portare su un altro computer**: presenti nell'editor 1.5.2 in qualche forma; da riprovare dopo il ridisegno.
- [ ] **Manuale e guide video gratuiti** (fascia dell'assistenza): non esistono ancora (T-40x).
- [ ] **Interfaccia in inglese** prima del lancio (T-206).
- [ ] **Edizione Laboratorio**: catalogo, marchio del laboratorio, regole di prestampa sono progetto, non prodotto.
- [ ] **Storia** («impagina album da più di dieci anni con un programma comprato nel 2012»): da `docs/prodotto/REQUISITI-VOCALI.md` e dallo stylebook; da far rileggere al titolare.
- [ ] **Prezzi di mercato** (150–290 € l'anno, 450–870 € in tre anni, cambio BCE del 13/11/2026) e righe della tabella di confronto per categorie: da riverificare alla data di pubblicazione.
- [ ] **Pagamento con bonifico e chiave entro 2 ore lavorative**: percorso di `marketing/negozio/FLUSSO-ACQUISTO.md` §1; se si passa a una piattaforma (§5) cambiano testi e link.

## Punti legali aperti

Da far decidere a chi segue l'aspetto legale (vedi anche `docs/legale/DA-DECIDERE.md`):

- **Pubblicità comparativa**: il confronto è per categorie e senza marchi, ma le cifre dei concorrenti devono essere verificabili e datate. La pagina dice che le fonti sono disponibili su richiesta; valutare se pubblicarle.
- **Prezzi IVA esclusa in grande**: il pubblico sono professionisti, ma la pagina è visibile ai consumatori. Il totale con IVA è sempre accanto; valutare se basta (art. 49 Codice del consumo).
- **Recesso** per i contenuti digitali e la funzione di recesso richiesta per i contratti online: su un sito statico senza carrello va chiarito come si esercita.
- **Accessibilità** (European Accessibility Act): il sito è costruito per WCAG 2.2 AA, ma non è stato verificato con un lettore di schermo né da un revisore.
- **Testi legali in contraddizione** con le decisioni di `tier.json`: `docs/legale/TERMINI-VENDITA.md` §4.3 e `PRIVACY.md` (righe C e I) parlano di un server di attivazione e di cookie statistici con consenso; il sito dice «nessun server di attivazione» e «nessun cookie».
- **Liberatorie dei volti** nelle foto dimostrative (sopra, «Schermate»).
- **IVA per chi compra dall'estero**: la pagina inglese dice che si paga l'IVA del proprio paese o nessuna con partita IVA europea valida; vale se l'IVA viene gestita così (OSS o piattaforma).

## Cose note da sistemare

- `cromo.py` non funziona su Windows (pipe ereditate): istantanee e immagini Open Graph si fanno da Linux, macOS o WSL.
- Le barre del confronto dei costi non seguono i prezzi in automatico.
- L'immagine Open Graph non ha la versione scura (le reti sociali non la usano).
- `anteprime/` pesa circa 21 MB (64 JPEG, ognuno sotto 700 KB): si può tenere fuori da git e rigenerare con `sito.py istantanee`.
