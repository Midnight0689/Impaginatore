#!/usr/bin/env bash
# Costruisce e prova il pacchetto di Impaginatore per: Mac con processore Intel, macOS 14 o successivo. Va lanciato su un Mac Intel.
# Uso e risultato: costruzione/LEGGIMI.md  (opzioni: --aiuto)
CHIAVE=mac-x86_64
SISTEMA=Darwin
MACCHINA=x86_64
ARCHITETTURA=x86_64
MACOS_MINIMO=14.0
PIATTAFORMA_UV=x86_64-apple-darwin
source "$(dirname "${BASH_SOURCE[0]}")/../comune.sh"
costruisci "$@"
