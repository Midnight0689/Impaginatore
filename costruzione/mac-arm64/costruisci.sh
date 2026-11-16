#!/usr/bin/env bash
# Costruisce e prova il pacchetto di Impaginatore per: Mac con chip Apple (M1 e successivi), macOS 13 o successivo. Va lanciato su un Mac con chip Apple.
# Uso e risultato: costruzione/LEGGIMI.md  (opzioni: --aiuto)
CHIAVE=mac-arm64
SISTEMA=Darwin
MACCHINA=arm64
ARCHITETTURA=arm64
MACOS_MINIMO=13.0
PIATTAFORMA_UV=aarch64-apple-darwin
source "$(dirname "${BASH_SOURCE[0]}")/../comune.sh"
costruisci "$@"
