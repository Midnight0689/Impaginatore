# Guida all’invio delle email

Questa cartella contiene i modelli delle email di Impaginatore e gli strumenti per prepararli. La guida spiega come metterli online, con quale servizio, con quali permessi e in che ordine.

Fonti dei contenuti: listino `docs/mercato/tier.json` (versione 2026-11-15d), `marketing/negozio/FLUSSO-ACQUISTO.md`, `marketing/lancio/PIANO-90-GIORNI.md`, `docs/legale/PRIVACY.md`, `brand/STYLEBOOK.md`. Se cambiano quelle, si cambiano queste.

Legenda: **[V]** verificato su fonte pubblica il 15/11/2026; **[NV]** da verificare prima di usarlo; **[L]** da far vedere al legale.

---

## 1. Cosa c’è e come si usa

| Percorso | Contenuto |
|---|---|
| `sorgenti/*.mjml` | Sorgenti MJML. `_base/` ha le parti comuni: testa (colori, caratteri, modalità scura, telefono), testata con logo, piè di pagina di servizio e di campagna, in italiano e in inglese |
| `html/*.html` | HTML compilato: CSS in linea, tabelle, 600 px, modalità scura, testo alternativo, preheader. Segnaposto neutri `{{nome}}` |
| `testo/*.txt` | Versione solo testo, da allegare sempre all’HTML (invio multipart) |
| `html/<servizio>/`, `testo/<servizio>/` | Le stesse email nella sintassi di SendGrid, Mailchimp, Brevo e Resend |
| `immagini/` | Logo, simbolo, icone, spunta, caratteri per le email, segnaposto delle schermate |
| `anteprime/*.png` | Ogni email a 600 e 375 px, chiara e scura, resa con Chrome |
| `strumenti/` | `compila.py`, `converti.py`, `anteprime.py`, `genera_immagini.py`, `costanti.json`, `invii/*.json` |
| `OGGETTI.md` | Tre varianti di oggetto e preheader per email |
| `SEGNAPOSTO.md` | Tutti i segnaposto e come si chiamano in ogni servizio |

Le email:

| Modello | Tipo | Quando parte |
|---|---|---|
| `lancio` (+ `.en`) | campagna | 21/02/2027 accesso anticipato alla lista, 23/02/2027 apertura |
| `benvenuto-chiave` (+ `.en`) | servizio | quando la chiave è emessa, con fattura e chiave `.txt` in allegato |
| `prova-giorno-1`, `prova-giorno-7`, `prova-scadenza` | campagna automatica | giorni 1, 7 e 27 della prova, solo a chi l’ha chiesto |
| `rosetta` | campagna | S5 (29/03-4/04/2027), dopo la revisione legale |
| `laboratori-primo-contatto`, `laboratori-seguito` | da persona a persona | G1 e G5 del piano, a mano, uno alla volta |
| `aggiornamento` (+ `.en`) | campagna ai clienti | a ogni versione |
| `rimborso-conferma` | servizio | quando il bonifico di rimborso è partito |
| `attivazione-problema` | servizio | risposta dell’assistenza |
| `assistenza-ore` | servizio | quando un pacchetto di ore è pagato |

Il flusso di lavoro, dalla cartella `marketing/email/`:

```bash
# 1. Compilare (MJML non sta nel repository: lo scarica npx nella sua cache)
python3 strumenti/compila.py            # sorgenti → html, poi controlli: peso, alt, link, parole vietate

# 2. Anteprime (servono Chrome e Pillow)
uv run --with pillow python strumenti/anteprime.py [nome …]

# 3. Varianti per i servizi
python3 strumenti/converti.py --dati strumenti/invii/lancio-apertura.json --servizi brevo

# 4. Email finite, senza segnaposto (invio a mano o via API)
python3 strumenti/converti.py --rendi dati.json --modelli rimborso-conferma --uscita /percorso
```

Per rigenerare immagini e caratteri, dalla radice del repository:
`uv run --with cairosvg --with pillow --with fonttools --with brotli python marketing/email/strumenti/genera_immagini.py`.

### 1.1 Prima del primo invio

1. **Riempi `strumenti/costanti.json`**: sito, indirizzi, partita IVA, firma, link fissi, comandi d’installazione copiati dalla pagina «Installa». Finché una costante è vuota, le campagne convertite contengono segni `[[nome]]` e lo script scrive «NON PRONTA».
2. **Lascia vuoto `mcp_disponibile`** finché il server MCP non è rilasciato: il piano dice che fino ad allora la bozza con Claude non si pubblicizza, e lo script toglie quei blocchi. Le anteprime li mostrano accesi, per far vedere come saranno.
3. **Metti online `immagini/`** in una cartella pubblica HTTPS con la versione nel percorso, per esempio `https://<dominio>/email/v1/`, e scrivi quell’indirizzo in `base_immagini`. Una volta inviata un’email, non si sovrascrivono le immagini: un cambio va in `v2/`. I file in `font/` vanno serviti con `Content-Type: font/woff2` e l’intestazione `Access-Control-Allow-Origin: *`, altrimenti alcuni client web non li caricano e usano i caratteri di ripiego, che sono già previsti. Peso totale: circa 540 KB.
4. **Sostituisci le schermate segnaposto** (§7).
5. **Pagina-ponte per l’attivazione** (§6.3).

---

## 2. Quale servizio

### 2.1 Raccomandazione

| Uso | Servizio | Perché |
|---|---|---|
| **Email di servizio** (chiave, rimborso, ore, assistenza) | **Resend**, chiamato da `chiavi.py` o a mano, con l’HTML finito di `--rendi` | Il piano gratuito basta per tutto il lancio: 3.000 email al mese, 100 al giorno [V]. Un invio è una sola chiamata HTTPS con HTML, testo e allegati (fattura e chiave). Non serve un modello sul servizio: le condizioni si risolvono in locale. Il tracciamento di aperture e clic non è attivo se non lo accendi, e per l’email della chiave deve restare spento (§6.3) |
| **Campagne** (lista d’attesa, lancio, prova, Rosetta, aggiornamenti) | **Brevo** | Azienda e server nell’Unione europea [NV: confermare nel DPA]. Moduli di iscrizione con doppia conferma e registro del consenso già pronti. Gratis fino a 300 email al giorno [V]; Starter 7 € al mese (6,33 € con pagamento annuale) per 5.000 email al mese [V]; le automazioni con più passi e il test A/B sono nel piano Standard, 15 € al mese (13,50 €) [V, da ricontrollare se la sequenza di 3 email della prova gira già nel piano gratuito] |
| **Laboratori** | **La tua casella di posta**, una email alla volta | Sono lettere da persona a persona: un servizio di campagne le farebbe sembrare un invio di massa, che è proprio ciò che la regola del piano esclude |

**Alternativa con un solo fornitore europeo.** Brevo fa anche le transazionali via API (`{{ params.x }}`), con le stesse 300 email al giorno del piano gratuito condivise con le campagne. Va bene se preferisci un solo contratto e tutti i dati nell’UE; il prezzo è una seconda configurazione DNS in meno e un limite giornaliero condiviso, da tenere d’occhio nei giorni del lancio.

**Nelle prime settimane** le email di servizio possono partire anche dalla tua casella: `--rendi` produce l’HTML finito, e in Thunderbird si incolla con *Inserisci › HTML*. Funziona finché gli ordini sono pochi; la soglia per passare all’API è la stessa del piano: oltre 5 ordini al giorno.

**La lista d’attesa prima del lancio.** Il piano (S-13) la raccoglie per email, senza servizi esterni, con registro CSV. Quando la si importa in Brevo, il CSV deve avere per ogni persona data, fonte e testo del consenso: Brevo chiede di dichiarare che i contatti hanno dato il consenso, e in caso di controllo la prova è quel registro.

### 2.2 Perché non gli altri

- **SendGrid.** Dal 28/05/2025 non ha più un piano gratuito [V]; il primo piano costa circa 19,95 $ al mese [NV: dato di terze parti]. Azienda e server negli Stati Uniti. È ottimo per volumi alti; qui non serve.
- **Mailchimp.** Il piano gratuito ha 250 contatti, 500 invii al mese e 250 al giorno, senza automazioni [V]. I modelli in HTML proprio («code your own») richiedono il piano Standard, secondo la pagina di aiuto [V]; i prezzi in euro dei piani a pagamento non erano univoci sulla pagina [NV]. Con una lista che il piano vuole a 300 iscritti prima del lancio, si paga subito.
- **Resend per le campagne.** I broadcast sono gratuiti fino a 1.000 contatti [V], ma i modelli non hanno condizioni (`{{#if}}`), che qui servono per accesso anticipato, prezzi di lancio e blocco Claude. Si possono rendere in locale per ogni invio, ma con Brevo non serve.

### 2.3 Regole dei grandi provider (valgono per tutti i servizi)

Gmail e Yahoo dal 2024, Microsoft dal 5/05/2025 [V]:
- SPF e DKIM su ogni invio, DMARC almeno `p=none`, dominio del mittente allineato;
- reclami per spam sotto lo 0,3% (meglio sotto lo 0,1%);
- disiscrizione con un clic (intestazione `List-Unsubscribe` con `List-Unsubscribe-Post`, RFC 8058) e richieste rispettate entro 2 giorni. L’obbligo scatta oltre 5.000 email al giorno, ma Brevo, SendGrid e Mailchimp aggiungono l’intestazione alle campagne in ogni caso: lasciala attiva.

---

## 3. Dominio: SPF, DKIM, DMARC

Una sola configurazione, fatta bene, prima del primo invio. I valori esatti li mostra il pannello di ogni servizio: si copiano da lì, non da questa guida.

**Indirizzi consigliati**
- `licenze@<dominio>` per le email di servizio (Resend), con risposta a `{{email_supporto}}`;
- `notizie@<dominio>` per le campagne (Brevo), con risposta a te: chi risponde a «la leggo io» deve trovarti davvero.
- Mai un indirizzo `noreply`: tutte le email invitano a rispondere.

**Record DNS**

| Record | Nome | Valore (esempio) | Note |
|---|---|---|---|
| SPF | `@` | `v=spf1 include:<quello del tuo provider di posta> include:<quello di Brevo, se richiesto> ~all` | **Uno solo** per nome; al massimo 10 ricerche DNS in tutto. Resend usa un sottodominio proprio per il mittente tecnico (in genere `send.<dominio>`), con il suo SPF e un record MX: aggiungili come li mostra il pannello [NV] |
| DKIM Resend | `resend._domainkey` | chiave pubblica (TXT) | dal pannello di Resend, *Domains* [NV: nome esatto] |
| DKIM Brevo | come indicato da Brevo | due CNAME o un TXT | dal pannello, *Mittenti, domini e IP dedicati › Domini* [NV] |
| Verifica Brevo | `@` | `brevo-code:…` | solo se richiesto |
| DMARC | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@<dominio>; adkim=r; aspf=r` | Partenza in osservazione. Dopo 2-4 settimane di rapporti puliti, `p=quarantine`; poi, se tutto è allineato, `p=reject` |

**Verifica.** Manda una prova a un indirizzo Gmail, apri *Mostra originale* e controlla `SPF: PASS`, `DKIM: PASS`, `DMARC: PASS`. Per SendGrid e Mailchimp il principio è lo stesso: SendGrid chiede tre CNAME (`em…`, `s1._domainkey`, `s2._domainkey`) in *Settings › Sender Authentication* [V]; Mailchimp due CNAME in *Domains* [NV].

---

## 4. Caricare le email: passo per passo

Prima di ogni caricamento:

```bash
python3 strumenti/compila.py
python3 strumenti/converti.py --dati strumenti/invii/<invio>.json --servizi <servizio>
```

Le varianti pronte sono in `html/<servizio>/` e `testo/<servizio>/`. Se lo script scrive «NON PRONTA», mancano costanti o dati d’invio.

### 4.1 SendGrid (Dynamic Templates)

1. *Email API › Dynamic Templates › Create a Dynamic Template*, nome uguale al file (`benvenuto-chiave`).
2. *Add Version › Blank Template › Code Editor*. Incolla `html/sendgrid/<nome>.html`.
3. In *Settings* della versione: oggetto e preheader da `OGGETTI.md`. L’oggetto accetta gli stessi segnaposto (`{{fascia}}`).
4. *Plain Text*: togli la spunta della generazione automatica e incolla `testo/sendgrid/<nome>.txt`.
5. *Test Data*: incolla un JSON con i valori (gli esempi sono nella colonna «Cosa contiene» di `SEGNAPOSTO.md`). Controlla l’anteprima chiara e scura.
6. Per le campagne: crea un gruppo di disiscrizione (*Suppressions › Unsubscribe Groups*) e indicane l’`asm.group_id` nell’invio, altrimenti `{{{unsubscribe}}}` resta vuoto.
7. Per `benvenuto-chiave` e `attivazione-problema`: *Settings › Tracking*, **disattiva il tracciamento dei clic** per questi invii (`tracking_settings.click_tracking.enable: false` nella chiamata).
8. Invio con `template_id` e `dynamic_template_data`; gli allegati (fattura, chiave `.txt`) vanno nella stessa chiamata.

### 4.2 Mailchimp (solo campagne)

1. *Audience › Settings › Audience fields and \*|MERGE|\* tags*: crea i campi del destinatario con i nomi esatti della colonna Mailchimp di `SEGNAPOSTO.md` (per le campagne servono solo `FNAME` ed `EMAIL`, che esistono già). Le costanti e i dati d’invio sono già scritti da `converti.py`.
2. *Content › Email templates › Create template › Code your own › Paste in code*: incolla `html/mailchimp/<nome>.html`. Serve il piano Standard [V].
3. *Campaigns › Create › Regular email*: destinatari, mittente `notizie@<dominio>`, oggetto da `OGGETTI.md`. Lascia vuoto il campo *Preview text*: il preheader è già nell’HTML, e due preheader si sommano.
4. *Content › Plain-text*: incolla `testo/mailchimp/<nome>.txt`.
5. *Preview and test › Send a test email* a Gmail, Outlook e Apple Mail (§8).
6. Le immagini restano su `{{base_immagini}}`: non servono lo ZIP né il Content Studio.

### 4.3 Brevo (raccomandato per le campagne)

1. *Contatti › Impostazioni › Attributi*: se usi altri attributi oltre a `FIRSTNAME` ed `EMAIL`, creali in maiuscolo come nella colonna Brevo.
2. *Campagne › Modelli › Nuovo modello › Incolla il tuo codice*: `html/brevo/<nome>.html`.
3. *Campagne › Crea una campagna email*: mittente, oggetto e testo di anteprima (lascialo vuoto: il preheader è nell’HTML), lista, modello. Incolla la versione testo `testo/brevo/<nome>.txt` se il pannello la chiede.
4. *Invia un test* e controlla (§8). Poi programma l’invio.
5. **Sequenza della prova** (*Automazioni*): ingresso = iscrizione al modulo «consigli per la prova» con doppia conferma; email 1 subito, attesa 6 giorni, email 2, attesa fino a 3 giorni prima della scadenza, email 3. Servono due attributi: la scadenza come **data**, per l’attesa, e `DATA_SCADENZA_PROVA` come **testo** già scritto («15 dicembre 2026»), per l’email. Chi raccoglie l’iscrizione (app o pagina della prova) deve scriverli entrambi [NV: da decidere con il team prodotto].
6. **Moduli con doppia conferma**: *Contatti › Moduli › Crea un modulo d’iscrizione*, opzione «doppia conferma», con il testo del consenso del §5.1 e il link all’informativa.
7. Dopo il lancio (24/04/2027 o alle 300 licenze) riconverti `prova-scadenza` con `strumenti/invii/dopo-il-lancio.json` e sostituisci il modello: la sequenza mostrerà il listino.

### 4.4 Resend (raccomandato per le email di servizio)

1. *Domains › Add domain*: aggiungi i record DNS che mostra (§3) e attendi la verifica.
2. *API Keys*: crea una chiave con il solo permesso di invio, conservala fuori dal repository.
3. Per ogni invio: `--rendi` con i dati del cliente, poi una chiamata `POST https://api.resend.com/emails` con `from`, `to`, `reply_to`, `subject`, `html` (il file reso), `text` (il `.txt` reso) e `attachments` (fattura PDF, chiave `.txt`). Questa chiamata è il punto in cui `chiavi.py` può spedire da solo dopo `emetti` [da realizzare: oggi non lo fa].
4. Lascia spento il tracciamento di aperture e clic sul dominio.
5. I modelli salvati in Resend (`html/resend/`) sono un’alternativa, ma non hanno condizioni: il saluto con il nome e l’ora inclusa di Studio si perdono. Con `--rendi` non si perde niente.

---

## 5. Consenso e regole italiane

Questa sezione riassume le regole da rispettare; non sostituisce il parere del legale, che il piano di lancio ha già messo a budget [L].

### 5.1 Chi può ricevere cosa

| Email | Base | Cosa serve |
|---|---|---|
| Servizio (chiave, rimborso, ore, assistenza) | esecuzione del contratto | Niente consenso. Solo contenuto di servizio: niente offerte dentro |
| Lancio, Rosetta | consenso | Iscrizione con **doppia conferma**: modulo + email con link di conferma. Registro con data, ora, fonte, testo del consenso. Il Garante tratta la doppia conferma come prova del consenso (provv. 4/6/2025 n. 330) [NV: estremi da far confermare] |
| Prova, giorni 1-7-scadenza | consenso | La prova non chiede l’email. Le tre email partono solo a chi, scaricandola, ha chiesto i consigli con una casella **non preselezionata** e ha confermato |
| Aggiornamento, ai clienti | art. 130, comma 4, Codice privacy («soft spam») | Solo per prodotti analoghi a quello comprato; informativa al momento dell’acquisto; possibilità di opporsi in ogni email, che c’è [L] |
| Laboratori | **da chiarire** | Vedi §5.3 |

Testo del consenso per la lista d’attesa (proposta): «Voglio ricevere per email l’avviso del lancio di Impaginatore e le sue novità, al massimo due volte al mese. Posso disiscrivermi con un clic da ogni email. [Informativa privacy]».

### 5.2 Cosa c’è già nei modelli

- Identità del mittente, indirizzo e partita IVA in ogni piè di pagina, e natura commerciale riconoscibile (D.Lgs. 70/2003, art. 9).
- Una riga «Ricevi questa email perché…» in ogni email.
- Disiscrizione con un clic e pagina delle preferenze in ogni campagna.
- Prezzi di lancio senza prezzo barrato: «79 € fino al {{data}}, poi 99 €». Il prezzo «prima» di uno sconto deve essere il più basso dei 30 giorni precedenti (art. 17-bis Codice del consumo); una lettura prudente esclude il barrato su un prodotto mai venduto [L].
- Assistente AI: sempre «abbonamento a parte» e «riceve i dati dell’album, non le foto, salvo consenso», come in `PRIVACY.md` §6.
- Nessun «unico», «il primo», nessun concorrente definito superato: `compila.py` lo controlla.

### 5.3 Laboratori: approccio prudente

Il Garante ha sostenuto che serve il consenso per le email promozionali anche verso le persone giuridiche (caso Preventivi Italia, 2015) e che un indirizzo trovato in pubblico non si può usare per promozione senza consenso (provv. 17/4/2026 n. 285) [NV: estremi da far confermare]. Non risulta una pronuncia specifica sugli indirizzi generici come `info@`. Per questo:

1. **Primo contatto non per email**: telefonata al numero aziendale, oppure di persona a una fiera. Si chiede se si può mandare una presentazione e a quale indirizzo. Poi si manda `laboratori-primo-contatto` con `se_accordo_telefonico = 1`.
2. Se si sceglie comunque l’email aziendale pubblicata, **solo dopo il parere del legale**, che il piano prevede prima di scrivere ai laboratori.
3. In ogni caso: un indirizzo aziendale, nessun nome di persona raccolto senza che lo dia lei; una email, un seguito, poi la chiamata (massimo 3 tentativi); la riga «rispondete “no” e non vi scriverò più» e il rispetto immediato; un registro dei contatti con data, canale e risposta; informativa al primo contatto (art. 14 GDPR: da dove viene l’indirizzo, link all’informativa), che il modello già contiene.

### 5.4 Testi da far vedere al legale prima dell’invio [L]

- `lancio`: il confronto con gli abbonamenti («intorno ai 20 € al mese», nota con 250-290 $ l’anno e cambio BCE) senza marchi. Le fonti con i nomi stanno nella pagina prezzi (pubblicità comparativa, D.Lgs. 145/2007).
- `rosetta`: tutto il testo, l’offerta (prezzi, scadenza, prova richiesta) e l’impegno a cancellare lo screenshot dopo l’emissione della chiave.
- I testi del consenso (§5.1) e la clausola sul «soft spam» nelle condizioni di vendita.

---

## 6. Note tecniche

### 6.1 Compatibilità

- Larghezza 600 px, una colonna; sotto i 480 px margini di 20 px, titoli più piccoli e card in colonna.
- **Modalità scura**: colori propri per Apple Mail, Mail di iOS, Outlook per Mac e Thunderbird (`prefers-color-scheme`); regole `[data-ogsc]` per Outlook.com. Gmail sul telefono inverte da solo i colori e non legge la media query: logo e icone sono PNG con fondo pieno, leggibili anche invertiti; la spunta verde è unica e si legge su entrambi i fondi.
- **Outlook per Windows** usa Segoe UI, Georgia e Consolas al posto dei caratteri della marca; pulsanti e card restano tabelle.
- **Caratteri**: Newsreader, Instrument Sans e IBM Plex Mono ospitati in `immagini/font/`, mai da Google Fonts. Newsreader e Instrument Sans sono ritagliati sui caratteri latini; IBM Plex Mono è quello originale, perché la licenza OFL vieta di distribuire versioni modificate con lo stesso nome.
- **Peso**: tutte sotto i 66 KB (le misura `compila.py`). Gmail taglia i messaggi oltre circa 102 KB; i link tracciati dei servizi aggiungono peso, per questo il limite interno è 80 KB.

### 6.2 Versione solo testo

Sempre allegata. Ha gli stessi segnaposto e le stesse condizioni dell’HTML; `converti.py` la traduce insieme.

### 6.3 Il link «Attiva in Impaginatore»

`FLUSSO-ACQUISTO.md` prevede un link diretto `impaginatore://attiva?chiave=…`. Nei modelli il link è `{{link_attivazione}}`, per due motivi:
- **Gmail e altri client web tolgono o bloccano i link con schemi diversi da `https` e `mailto`** [NV: da provare su Gmail web, Gmail app, Outlook.com prima del lancio]. Il pulsante resterebbe morto proprio dove si legge più posta.
- **Il tracciamento dei clic** dei servizi riscrive i link passando dai loro server: la chiave finirebbe nei loro registri.

Proposta: `{{link_attivazione}}` = `https://<dominio>/attiva#<CHIAVE>`. La pagina legge la chiave dal frammento dopo `#`, che il browser **non invia** al server, apre `impaginatore://attiva?chiave=…` e, se non succede nulla, mostra la chiave da copiare con le istruzioni del menu *Licenza › Attiva*. Se la prova dimostra che lo schema diretto passa ovunque, basta mettere quello nel valore: il modello non cambia. In ogni caso il tracciamento dei clic resta spento per `benvenuto-chiave` e `attivazione-problema`.

### 6.4 Allegati

`benvenuto-chiave` dice «in allegato trovi la fattura e la stessa chiave in un file di testo»; `rimborso-conferma` la nota di credito; `assistenza-ore` la fattura. Se un invio parte senza allegati, quella frase è falsa: va corretta o l’allegato aggiunto.

---

## 7. Immagini e schermate

In `immagini/` ci sono solo logo e icone della marca, generati dai file di `brand/`. Le schermate dell’app sono segnaposto marcati «SEGNAPOSTO · SCHERMATA DA SOSTITUIRE», da sostituire con file dello stesso nome e delle stesse misure (doppie rispetto alla resa, per gli schermi ad alta densità):

| File | Misure del file | Resa | Email | Cosa mostrare | Testo alternativo (già nei sorgenti) |
|---|---|---|---|---|---|
| `segnaposto/lancio-spread.png` | 1040 × 650 | 520 × 325 | lancio | Uno spread nell’editor, tema chiaro, con una quota verde «5,0 mm» fra due foto | «Uno spread di un album di matrimonio in Impaginatore, con le misure di margini e piega.» |
| `segnaposto/benvenuto-primo-spread.png` | 1040 × 586 | 520 × 293 | benvenuto-chiave | L’album di esempio appena impaginato: primo spread, pannello misure, nessuna filigrana | «Il primo spread dell’album di esempio aperto in Impaginatore, con il pannello delle misure.» |
| `segnaposto/prova-bozza-claude.png` | 1040 × 650 | 520 × 325 | prova-giorno-1 (solo con `mcp_disponibile`) | La colonna degli spread con la bozza completa; uno spread rifinito a mano evidenziato | «Impaginatore con la bozza di un album preparata da Claude e il pannello degli spread.» |
| `segnaposto/aggiornamento-novita.png` | 1040 × 586 | 520 × 293 | aggiornamento | La funzione nuova, ritagliata sul punto che si racconta, una sola annotazione | «La novità principale della versione {{versione}} di Impaginatore.» (da precisare a ogni versione) |

Regole: PNG o JPG sotto i 200 KB l’uno; foto dell’album dimostrativo con licenza e liberatoria degli sposi; nessun dato vero di clienti visibile. Le versioni inglesi usano le stesse immagini: se l’interfaccia nella schermata è in italiano, va bene, ma il testo alternativo inglese è già tradotto nei sorgenti `.en`.

`icona-app.png` non è usata nelle email: serve come immagine del profilo del mittente dove il servizio lo consente.

---

## 8. Prima di ogni invio

**Contenuti**
- [ ] Prezzi uguali a `docs/mercato/tier.json` (oggi 49/99/149 €, lancio 39/79/119 €, ore 49/249/499 € senza sconto a quantità) e scritti «X € fino al …, poi Y €».
- [ ] `data_fine_lancio` vera: 23 aprile 2027, o la data in cui si arriva a 300 licenze. Dopo, si riconverte con `dopo-il-lancio.json`.
- [ ] `mcp_disponibile` vuoto finché il server MCP non è rilasciato.
- [ ] `lancio`: nota sul confronto con gli abbonamenti ricontrollata (prezzi e data; nel 2027 un concorrente ha annunciato 320 $) e vista dal legale.
- [ ] `rosetta`: **verificato che Impaginatore giri in modo nativo sui Mac con processore Apple** (eseguibile arm64 o universale, provato su un Mac Apple silicon senza Rosetta installato). Senza questa prova la frase «gira in modo nativo» va tolta. Ricontrollati il link all’annuncio Apple e le etichette del Finder («Applicazione (Intel)», «(Universal)», «(Apple Silicon)») sulla versione di macOS in uso [NV]. Offerta approvata dal titolare.
- [ ] Schermate segnaposto sostituite.
- [ ] Oggetto e preheader scelti in `OGGETTI.md`; se non è la variante A, preheader aggiornato nel sorgente.

**Tecnica**
- [ ] `python3 strumenti/compila.py` senza segnalazioni; `converti.py` senza «NON PRONTA».
- [ ] Prova a Gmail (web e app), Outlook (web e Windows), Apple Mail (Mac e iPhone, chiaro e scuro): immagini, caratteri, pulsanti, link, disiscrizione.
- [ ] Tutti i link aprono la pagina giusta; `{{link_attivazione}}` provato con una chiave vera.
- [ ] Tracciamento dei clic spento per chiave e assistenza; per le campagne, se acceso, controllato che non rompa i comandi d’installazione (non sono link).
- [ ] Allegati presenti dove il testo li cita.
- [ ] SPF, DKIM e DMARC in `PASS` su una prova.

**Consenso**
- [ ] Lista filtrata: solo iscritti confermati; esclusi i disiscritti e, per il lancio del 23/02, chi ha già comprato.
- [ ] Per i laboratori: parere privacy ricevuto, registro aggiornato, un invio alla volta.

---

## 9. Calendario

Date dal piano di lancio (S-14 = settimana del 16/11/2026; lancio martedì 23/02/2027). Campagne fra martedì e giovedì, alle 9; mai di sabato, quando molti fotografi sono a un matrimonio.

| Quando | Email | A chi | Note |
|---|---|---|---|
| Da S-13 (23/11/2026) | conferma dell’iscrizione | chi scrive per la lista d’attesa | Risposta con link o richiesta di conferma; nessun modello qui, è il testo del modulo |
| 14-18/12/2026 (G1) | `laboratori-primo-contatto` | 5 laboratori A, uno alla volta | Dopo la telefonata e il parere privacy (§5.3) |
| 11-15/01/2027 (G5) | `laboratori-seguito` | chi non ha detto «no» | Come risposta al primo messaggio, con l’album dimostrativo |
| S-2 (8-14/02/2027) | annuncio della data | lista d’attesa | **Manca un modello**: si può adattare `lancio` (§10) |
| Dom 21/02/2027 | `lancio` con `lancio-accesso-anticipato.json` | lista d’attesa confermata | Accesso anticipato di 48 ore. È una domenica: la data la fissa il piano; meglio le 18 che le 9 |
| Mar 23/02/2027, ore 9 | `lancio` con `lancio-apertura.json` | lista d’attesa, meno chi ha comprato | |
| Sempre | `benvenuto-chiave`, `assistenza-ore`, `rimborso-conferma`, `attivazione-problema` | il singolo cliente | Chiave entro 2 ore lavorative dal pagamento |
| Sempre, dal lancio | sequenza della prova | chi l’ha chiesta | Giorno 1, giorno 7, 3 giorni prima della scadenza |
| S5 (29/03-4/04/2027) | `rosetta` con `rosetta.json` | iscritti alle notizie | Dopo il legale e la verifica arm64 |
| S7 (12-18/04/2027) | promemoria di fine lancio | lista e prove con consenso | **Manca un modello** (§10) |
| 24/04/2027 | — | — | Riconvertire `prova-scadenza` con `dopo-il-lancio.json` |
| A ogni versione | `aggiornamento` | clienti | Con `invii/aggiornamento-modello.json` riempito |

---

## 10. Cosa resta da fare a mano

- Riempire `costanti.json`, mettere online `immagini/` e la pagina-ponte `/attiva`.
- Sostituire le 4 schermate segnaposto.
- Configurare DNS, Brevo e Resend; collegare l’invio a `chiavi.py` (oggi l’email parte a mano).
- Revisione legale dei testi marcati [L]; parere privacy prima dei laboratori.
- Verifica arm64 prima di `rosetta`; prova del link di attivazione sui client principali.
- Testi non coperti da questi modelli: risposta con i dati per il bonifico (`FLUSSO-ACQUISTO.md` §4.2, oggi testo semplice), annuncio della data (S-2), promemoria di fine lancio (S7), conferma dell’iscrizione alla lista.
- Nota per `FLUSSO-ACQUISTO.md` §4.5: l’oggetto «Le tue <ORE> ore di assistenza» con una sola ora diventa «Le tue 1 ore»; in `OGGETTI.md` ci sono varianti senza il numero.
