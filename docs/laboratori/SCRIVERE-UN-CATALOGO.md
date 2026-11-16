# Scrivere il catalogo di un laboratorio

Questa guida è per chi prepara il **catalogo** dei prodotti album di un laboratorio per Impaginatore: il laboratorio
stesso, o chi lo segue per conto del produttore. Il fotografo importa il catalogo, sceglie il prodotto quando crea
l'album e, alla fine, prepara la **consegna**: i file con il formato, l'abbondanza, la risoluzione e i nomi che il
laboratorio chiede, più un riepilogo da mandare insieme.

Lo schema completo e le regole tecniche sono in [`docs/architettura/CATALOGHI.md`](../architettura/CATALOGHI.md).

## 1. Raccogli le specifiche

Per ogni prodotto (un formato di album che il laboratorio vende) servono:

| Dato | Esempio | Note |
|---|---|---|
| Misura della **pagina** finita | 30 × 30 cm | una pagina, non lo spread aperto |
| Spread minimi e massimi | da 10 a 40 | se il laboratorio ha dei limiti |
| Abbondanza | 5 mm per lato | quanto l'immagine deve uscire dal taglio |
| Zona di sicurezza | 8 mm dal bordo | dove non mettere testi |
| Zona della piega | 10 mm per lato | dove non mettere volti e testi |
| Risoluzione | 300 ppi | dei file da mandare |
| Risoluzione minima e consigliata delle foto | 180 / 250 ppi | sotto la minima la stampa si vede sgranata |
| Profilo colore | sRGB | oggi Impaginatore consegna solo in sRGB |
| File | un JPEG per spread (o per pagina), qualità 95 | |
| Nomi dei file | `Rossi_01.jpg`, `Rossi_02.jpg`… | |
| Copertina | «Rigida in lino, da ordinare a parte» | solo descrizione |

**Non inventare niente.** Ogni numero deve venire dalle specifiche scritte del laboratorio (pagina del sito, PDF,
email). Scrivi da dove vengono nel campo `fonte`. Se un dato non è sicuro, metti `"stato": "da_confermare"`: il
fotografo lo vede ovunque e il riepilogo della consegna lo scrive in maiuscolo.

## 2. Scrivi il file

Un file di testo in UTF-8, con estensione `.json`. Esempio con un prodotto:

```json
{
  "formato_catalogo": 1,
  "id": "lab-rossi-2027",
  "nome": "Album fine art 2027",
  "laboratorio": "Laboratorio Rossi",
  "data": "2027-01-15",
  "fonte": "Specifiche tecniche del laboratorio, PDF di gennaio 2027",
  "prodotti": [
    {
      "id": "flush-30x30",
      "nome": "Flush mount 30 × 30",
      "pagina_cm": [30, 30],
      "spread_min": 10,
      "spread_max": 40,
      "abbondanza_mm": 5,
      "sicurezza_mm": 8,
      "piega_mm": 10,
      "ppi": 300,
      "ppi_minimi": 180,
      "ppi_consigliati": 250,
      "consegna": {"nome": "{album}_{n}", "qualita": 95, "file": "spread", "cifre": 2},
      "copertina": "Rigida in lino, da ordinare a parte"
    }
  ]
}
```

Regole che è facile sbagliare:

- `id` del catalogo e dei prodotti: solo lettere **minuscole**, cifre e trattini (`lab-rossi-2027`, `flush-30x30`).
  Usa un `id` nuovo per ogni laboratorio; tienilo uguale nelle edizioni successive dello stesso catalogo (chi importa la
  versione nuova sostituisce quella vecchia).
- `pagina_cm` è la **pagina**: un album 30 × 30 ha lo spread aperto di 60 × 30.
- Numeri con il punto (`22.5`), non con la virgola.
- Nomi dei file: in `consegna.nome` valgono solo `{album}`, `{prodotto}`, `{n}` (numero dello spread) e `{pagina}`
  (numero della pagina). Ci vuole `{n}`, oppure `{pagina}` se il laboratorio vuole un file per pagina
  (`"file": "pagine"`). Niente estensione (la aggiunge il programma), niente `/ \ : * ? " < > |`, al massimo 80
  caratteri. `cifre` dice quanti zeri davanti: con `2` lo spread 3 diventa `03`.
- Nessuna chiave in più: una chiave che il programma non conosce rende il catalogo non valido (meglio un errore subito
  che una regola ignorata in silenzio).
- Testi (`nome`, `laboratorio`, `descrizione`, `copertina`) su una riga; solo `note` può andare a capo.

## 3. Provalo

1. In Impaginatore: **Progetti → Nuovo album → Importa il catalogo di un laboratorio…** e scegli il file. Se qualcosa
   non va, il messaggio dice dove («lab.json, prodotto 2, abbondanza_mm: deve essere un numero da 0 a 20»).
2. Crea un album con il prodotto, metti qualche foto, premi **Controlla**: le regole del prodotto (spread, risoluzione,
   zona di sicurezza, piega) compaiono tra i problemi.
3. **Esporta → Consegna**: controlla misure in pixel, nomi dei file e riepilogo nella cartella `Esportazioni/Consegna`.
   Fai stampare una prova al laboratorio prima di distribuire il catalogo.

## 4. Firma (facoltativa)

Senza firma il catalogo funziona, ma il fotografo lo vede **«non verificato»**. Per diventare «verificato» lo firma il
produttore di Impaginatore, dopo averlo provato:

```
python3 marketing/negozio/chiavi/chiavi.py firma-catalogo lab-rossi-2027.json --uscita lab-rossi-2027-firmato.json
```

La firma copre tutto il file: **qualsiasi modifica dopo la firma rende il catalogo non valido** (il programma lo
rifiuta). Per cambiare qualcosa si prepara una nuova edizione (nuova `data`) e la si fa firmare di nuovo. Un catalogo
verificato non viene sostituito da una versione non verificata con lo stesso `id`.

## 5. Distribuiscilo

Il file si manda al fotografo come si vuole (email, sito del laboratorio). Impaginatore non scarica cataloghi da
internet e non manda niente al laboratorio: la consegna è una cartella sul computer del fotografo, che poi carica i file
con il sistema del laboratorio.

## Cosa il catalogo non fa (oggi)

- Profili colore diversi da sRGB, file TIFF o PDF di consegna.
- File della copertina (dorso, risvolti): la copertina è solo descritta nel riepilogo.
- Cambiare il formato di un album già impaginato: il fotografo crea un album nuovo con il prodotto.
