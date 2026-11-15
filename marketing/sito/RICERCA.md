# Ricerca per la pagina di vendita (T-502)

Documento interno: non si pubblica (`sito.py pubblica` non lo copia). Qui i concorrenti si nominano; sulla pagina no.

## Metodo e limiti

- Pagine consultate il **15/11/2026** con uno strumento che restituisce il testo della pagina riassunto da un modello. **Le pagine non sono state viste renderizzate**: cosa sta «sopra la piega» è ricavato dall'ordine del testo, il tipo di immagine è dedotto. Le frasi tra virgolette sono citazioni rese dallo strumento.
- Prezzi e condizioni dei concorrenti cambiano spesso. Per le cifre del confronto sul sito valgono `docs/mercato/prezzi.md` §1 e §1.1 e `docs/mercato/competitor.md`, non questa tabella.
- Non letti o senza dati: Pixelmator Pro (rimanda ad apple.com), Sketch, Photo Mechanic (errore di certificato), prezzi di SmartAlbums, AlbumTeller, Pic-Time, AlbumStomp, AI Album Studio (pagine caricate via JavaScript), home di CleanShot e Capture One, prezzi di Things. Nielsen Norman Group: nessuna pagina verificata.

## Gruppo A: programmi desktop a licenza una tantum

| Sito | Sopra la piega | Prezzi e fasce | Fiducia |
|---|---|---|---|
| Nova, https://nova.app | Titolo breve, un solo pulsante «Download Nova 14.1»; sotto: «Free, 30-day trial • 75.8 MB .zip • Requires macOS 15.6+». Schermata vera | Nessun prezzo in pagina. «If you like it, buy it, and keep it forever.» Prova 30 giorni senza carta | Link «Verify integrity» accanto al download |
| Sublime Text, https://www.sublimetext.com, https://www.sublimehq.com/store/text | «Text Editing, Done Right», 4 pulsanti di download | «once off purchase… 3 years of updates», poi upgrade | Numero di build, sede dichiarata |
| TablePlus, https://tableplus.com/pricing | Un download primario, nessun prezzo | Tre fasce perpetue, «Bonus 1 year of updates», nessuna evidenziata, rimborso 7 giorni | «Trusted by 1M+ developers», loghi |
| Fork, https://fork.dev/buy | Due download, prezzo 59,99 $ | «One-time purchase», «up to 3 machines» | Nessuna recensione |
| Audio Hijack, https://rogueamoeba.com/audiohijack | «Free Download» e «Purchase» | «This download serves as both the free trial and the full version» | Premi, politica di rimborso |
| Acorn, https://flyingmeat.com/acorn | Prova di 14 giorni e acquisto | «no subscriptions», «you buy a thing, you get a thing» | Premi |
| Typora, https://typora.io | Prezzo sopra la piega (14,99 $), prova 15 giorni | Una fascia | Testimonianze |
| CleanShot X, https://cleanshot.com/pricing | (solo prezzi) | «Pay once, use forever», un anno di aggiornamenti, rimborso 30 giorni | — |
| Things 3, https://culturedcode.com/things | Video di presentazione | Prezzi per piattaforma | Apple Design Award, stampa |
| iA Writer, https://ia.net/writer | Tre download, schermate vere | Prova 7 giorni | «over two million writers», premi |
| Kaleidoscope, https://kaleidoscope.app | «Download Free Trial» ripetuto | Solo abbonamento | Testimonianze |
| DxO PhotoLab, https://www.dxo.com/dxo-photolab | «Buy now» e «Try for free», etichetta «Perpetual license» | Fasce non in pagina | Trustpilot |
| ON1 Photo RAW, https://www.on1.com/products/photo-raw | «No subscription required», promozione con prezzo barrato | Perpetua «Own version 2027 outright. Never expires.», rimborso 30 giorni | «No cloud lock-in. No data mining. Complete privacy.» |
| Capture One, https://www.captureone.com/en/pricing | (solo prezzi) | Perpetua accanto agli abbonamenti, con il limite detto chiaro | — |

## Gruppo B: programmi per album di matrimonio

| Sito | Sopra la piega | Prezzi e fasce | Fiducia |
|---|---|---|---|
| DigiAlbum, https://digialbum.it | «Il software per impaginare album di matrimonio», primario «Scarica la prova gratuita», riga «Senza carta di credito · 14 giorni · impagini quanti album vuoi», conto alla rovescia | Licenze annuali, prezzi IVA inclusa | Fatto in Italia, volti riconosciuti in locale; tabella di confronto che nomina i concorrenti |
| SmartAlbums, https://www.smartalbums.com | «Design Beautiful Albums in 30 Minutes or Less», due pulsanti, entrambi per la prova | Abbonamento, prova 14 giorni senza carta | 1,5 milioni di album, 130.000 fotografi |
| Fundy Designer, https://www.fundydesigner.com | «Lock In Your Price» come primario | Abbonamento, prezzi barrati, «Prices go up every few weeks» | Testimonianze |
| AlbumTeller, https://albumteller.com | «Album design. Redesigned.», «Download Free» | Non letti | Trustpilot |
| Pic-Time, https://www.pic-time.com/album-designer | «Make Albums Part of Every Gallery» | Legato ai piani del servizio online | Rete di laboratori |
| AlbumStomp, https://stompsoftware.com | Mockup su portatile | Non letti | — |
| AI Album Studio, https://www.aialbumstudio.com | «Try it for FREE», editor nel browser | Non letti | Ditta italiana nel piè di pagina |

## Fonti sulle buone pratiche

- web.dev, «Largest Contentful Paint (LCP)», https://web.dev/articles/lcp (aggiornato il 4/9/2025): l'elemento più grande visibile deve comparire entro 2,5 s al 75° percentile.
- web.dev, «Optimize Cumulative Layout Shift», https://web.dev/articles/optimize-cls (aggiornato il 7/2/2025): riservare lo spazio con `width` e `height`; CLS 0,1 o meno.
- W3C, WCAG 2.2, https://www.w3.org/TR/WCAG22/ (Raccomandazione del 12/12/2024): fra i criteri AA nuovi, 2.5.8 dimensione minima dei bersagli e 2.4.11 focus non coperto.
- Baymard Institute, «Product Page UX 2026», https://baymard.com/blog/current-state-ecommerce-product-page-ux (aggiornato il 18/3/2026): il 67% dei siti non mostra il costo totale vicino al pulsante d'acquisto. È e-commerce: va trasferito con cautela.
- Smashing Magazine, «Designing Effective Pricing Plans UX», https://smashingmagazine.com/2022/07/designing-better-pricing-page (data non verificata): le tabelle di confronto si leggono riga per riga, vanno tenute corte; sul telefono servono schede o scorrimento.

## Schemi ricorrenti

1. Titolo breve, sottotitolo che dice cosa fa e per chi, **un solo pulsante primario**.
2. Il prezzo raramente sta sopra la piega; chi lo mette ha una fascia sola.
3. Nel settore album il pulsante primario è sempre **la prova**, di 14 giorni e senza carta. La nostra è di 30.
4. Una riga sotto il pulsante con durata della prova, carta, requisiti.
5. Schermate vere per i prodotti curati; il settore album mostra spread finiti.
6. Sotto la piega, una sezione per funzione con una schermata ritagliata.
7. «Una volta» spiegato con un limite chiaro sugli aggiornamenti; nessuno dice «per sempre» senza dire cosa comprende.
8. Una fascia centrale evidenziata è rara: è un modo per distinguersi.
9. Prezzi barrati e conti alla rovescia sono comuni; i prodotti migliori del gruppo A non li usano.
10. Rimborso dichiarato: 30 giorni nei casi migliori.
11. Fiducia con numeri, premi e testimonianze con nome. I segnali sull'installazione sono rari: solo Nova verifica l'integrità; nessuno parla di installatori non firmati.
12. La privacy come argomento: ON1 e DigiAlbum.

## Scelte che ne derivano

| Schema | Scelta sul sito | Dove |
|---|---|---|
| 1, 3 | Un pulsante verde per schermata: «Avvisami al lancio» in prevendita, «Scarica la prova gratuita» quando `in_vendita` è vero. Il secondo pulsante è neutro | `index.html`, copertina e chiusura |
| 2 | Il prezzo non è il titolo, ma un badge «Pro 79 € · una volta» compare sopra la piega: il prezzo basso è un argomento (prezzi.md, «prezzo d'impulso») | copertina |
| 4 | Riga sotto il pulsante: data di vendita, prezzo di lancio con la data di fine e il listino, IVA esclusa, prova di 30 giorni senza carta | copertina |
| 5, 6 | Schermata vera dell'editor con l'album dimostrativo; una sezione per funzione con la sua immagine | `#funzioni` |
| 7 | «Paghi una volta» sempre con il limite: aggiornamenti della versione comprati, versione maggiore facoltativa a metà prezzo, non prima di 18 mesi | prezzi, domande |
| 8 | Tre fasce con Pro al centro evidenziato («Consigliato», unico pulsante verde) | `#prezzi` |
| 9 | **Niente prezzi barrati né conti alla rovescia**: «79 € fino al 23 aprile 2027, poi 99 €». Il controllo rifiuta `<s>`, `<del>` e `line-through` | ovunque |
| 10 | Rimborso di 30 giorni scritto accanto ai prezzi e nelle domande | prezzi, domande |
| 11 | Niente numeri di clienti né testimonianze finché non sono vere (sezione nascosta, interruttore `riprova_sociale`). Al loro posto: la storia vera del progetto e una pagina che spiega il comando d'installazione pezzo per pezzo e come verificare le impronte | `#storia`, `installa.html` |
| 12 | «Le foto restano sul tuo computer» come scheda a sé e nella tabella di confronto | `#funzioni`, `#confronto` |
| confronto | Il confronto con nomi e tabella di DigiAlbum è efficace ma ci espone (pubblicità comparativa). Confronto **per categorie**, con una riga «Dove siamo indietro» | `#confronto` |
| Smashing | Tabella delle fasce corta e raggruppata; sul telefono scorre di lato con un avviso | `prezzi.html` |
| web.dev | Immagine della copertina con `fetchpriority="high"` e `srcset`; tutte le immagini con `width`/`height`; caratteri locali precaricati | tutte le pagine |
| WCAG 2.2 | Pulsanti alti almeno 36 px (il criterio 2.5.8 ne chiede 24), quelli principali 44 e 52; testata appiccicosa con `scroll-padding-top` perché il fuoco non finisca sotto | `css/sito.css` |

## Alternative scartate

- **Prezzo come titolo** («79 € una volta»): forte, ma il titolo deve dire cosa fa il programma; il prezzo sta nel badge e nella riga sotto.
- **Tabella con i nomi dei concorrenti** come DigiAlbum: vietata dal compito e rischiosa senza revisione legale.
- **Conto alla rovescia del lancio**: urgenza artificiale, contraria al tono della marca.
- **Modulo d'iscrizione con un servizio esterno** (Mailchimp e simili): richiesta di rete e cookie di terzi. Il modulo resta spento finché `modulo_lista_attesa` è vuoto; al suo posto un `mailto:` già compilato.
- **Video di presentazione**: non c'è ancora un'interfaccia definitiva da filmare (T-205).
