#!/usr/bin/env bash
# Costruisce e prova il pacchetto di Impaginatore per: Linux x86_64 (Ubuntu 24.04 e derivate). Va lanciato su Ubuntu 24.04 x86_64.
# Uso e risultato: costruzione/LEGGIMI.md  (opzioni: --aiuto)
CHIAVE=linux
SISTEMA=Linux
MACCHINA=x86_64
ARCHITETTURA=x86_64

source "$(dirname "${BASH_SOURCE[0]}")/../comune.sh"
costruisci "$@"
