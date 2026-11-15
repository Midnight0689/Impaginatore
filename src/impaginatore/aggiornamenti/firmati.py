"""Contratto degli aggiornamenti a pacchetti firmati (per le installazioni senza git: fase successiva, non ancora attivo).

Oggi un'installazione da checkout si aggiorna con git (git.Git): chi controlla il repository distribuisce codice che gira
sui computer degli utenti senza altra verifica (SEC-007). Le installazioni da pacchetto useranno invece questo schema:

1. manifesto  GET <fonte>/manifesto.json  ->  {"versione": "2.1.0", "data": "...", "novita": [...],
              "pacchetti": {"<sistema>": {"url": "...", "sha256": "<64 cifre esadecimali>", "dimensione": n}}}
              e accanto manifesto.json.sig: firma Ed25519 (64 byte, base64) dei byte esatti di manifesto.json.
2. verifica   la firma si controlla con la CHIAVE PUBBLICA Ed25519 incorporata nel programma (CHIAVI_FIDATE; la chiave
              privata resta solo sulla macchina che firma i rilasci, mai nel repository). Senza firma valida, con una
              versione non più nuova di quella in uso (niente ritorni indietro imposti da fuori) o con campi mancanti
              il manifesto si scarta e lo stato dice perché.
3. scarica    il pacchetto va in una cartella temporanea dell'utente; si controllano dimensione e sha256 del manifesto
              (firmato): un pacchetto diverso da quello firmato non si installa.
4. installa   solo su richiesta dell'utente dalla pagina (gettone della sessione), mai da solo; poi riavvia().

Le funzioni si implementano quando ci sarà il canale dei rilasci (serve una libreria Ed25519, es. «cryptography», da
aggiungere alle dipendenze). Fino ad allora questa classe dichiara il contratto e non fa niente: predefiniti() non la sceglie.
"""
from . import Aggiornamenti, NonDisponibili

CHIAVI_FIDATE = ()         # chiavi pubbliche Ed25519 (32 byte, base64) dei rilasci: vuote finché il canale non esiste


class PacchettiFirmati(Aggiornamenti):
    """aggiornamenti da pacchetti con manifesto firmato Ed25519 (vedi il docstring del modulo). Non ancora attivo"""

    MOTIVO = "Aggiornamenti a pacchetti firmati: non ancora attivi in questa versione"

    def __init__(self, fonte="", riavvia=None):
        self.fonte, self.riavvia = fonte, riavvia or (lambda: None)

    def stato(self): return NonDisponibili(self.MOTIVO).stato()

    def controlla(self): return self.stato()

    def versioni(self, k=20): return []

    def manifesto(self):
        """manifesto della fonte, solo se firmato da una chiave fidata: dict (passi 1-2)"""
        raise NotImplementedError(self.MOTIVO)

    def verifica(self, dati, firma, chiavi=CHIAVI_FIDATE):
        """True se firma (Ed25519) dei byte dati è valida per una delle chiavi (passo 2)"""
        raise NotImplementedError(self.MOTIVO)

    def scarica(self, manifesto):
        """percorso del pacchetto scaricato e controllato (dimensione, sha256) (passo 3)"""
        raise NotImplementedError(self.MOTIVO)

    def aggiorna(self): raise ValueError(self.MOTIVO)

    def ripristina(self, codice): raise ValueError(self.MOTIVO)

    def ciclo(self, fermo, ogni=10 * 60): return
