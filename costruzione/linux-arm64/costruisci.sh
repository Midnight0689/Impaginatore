#!/usr/bin/env bash
# Costruisce e prova il pacchetto di Impaginatore per: Linux arm64 (Ubuntu 24.04 e derivate). Va lanciato su Ubuntu 24.04 arm64.
# Uso e risultato: costruzione/LEGGIMI.md  (opzioni: --aiuto)
CHIAVE=linux-arm64
SISTEMA=Linux
MACCHINA=aarch64
ARCHITETTURA=arm64

source "$(dirname "${BASH_SOURCE[0]}")/../comune.sh"
costruisci "$@"
