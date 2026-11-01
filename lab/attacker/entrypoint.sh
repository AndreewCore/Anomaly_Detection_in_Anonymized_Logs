#!/bin/sh
# Lanza un ataque de fuerza bruta SSH contra la víctima.
# TODO: cuando anomalia.c acepte parámetros (ver docs/pendientes.md), leer aquí el escenario
#       de lab/scenarios/ y escribir su fila en el Ground Truth.
set -eu
sleep "${START_DELAY:-10}"
exec anomalia ssh "${TARGET_HOST:-victim}"
