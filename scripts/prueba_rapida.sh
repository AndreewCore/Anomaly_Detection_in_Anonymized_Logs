#!/usr/bin/env bash
# Prueba de punta a punta: captura corta -> ingesta -> parseo con revisiones
# automáticas. Pensado para validar el flujo en pocos minutos, no para producir
# resultados del experimento.
#
# Uso:
#   scripts/prueba_rapida.sh [escenario] [segmento] [minutos] [modo_revision] [extra...]
#   scripts/prueba_rapida.sh                     # concentrado 1 10 aciertos
#   scripts/prueba_rapida.sh concentrado 1 10 cobertura --revision-frac 0.6
#   scripts/prueba_rapida.sh spraying 1 5 none   # sin revisiones automáticas
#
# El único paso lento es la captura (dura 'minutos'); ingesta y parseo son segundos.
# Requiere Docker para la captura (ver lab/README.md).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SCENARIO="${1:-concentrado}"
SEGMENT="${2:-1}"
MINUTES="${3:-10}"
REV_MODE="${4:-aciertos}"   # cobertura | aleatorio | aciertos | none
# Lo que venga después se pasa tal cual a la etapa 1 (p. ej. --revision-rate 0.9).
shift $(( $# < 4 ? $# : 4 )) || true
EXTRA=("$@")

DATASET="lab_${SCENARIO}"
# Preferimos el venv del repo si existe, para no depender de activarlo a mano.
PY="python"; [ -x ".venv/bin/python" ] && PY=".venv/bin/python"

echo "== 1/3  captura ${MINUTES} min  (${SCENARIO} seg${SEGMENT}) =="
lab/capture.sh "$SCENARIO" "$SEGMENT" --minutes "$MINUTES"

echo "== 2/3  ingesta (auth.log + GT + bitácoras legit) =="
"$PY" scripts/00_ingest_lab.py --scenario "$SCENARIO"

echo "== 3/3  parseo + revisiones =="
if [ "$REV_MODE" = "none" ] || [ -z "$REV_MODE" ]; then
    "$PY" scripts/01_parse_logs.py --datasets "$DATASET"
else
    "$PY" scripts/01_parse_logs.py --datasets "$DATASET" \
        --revision-mode "$REV_MODE" ${EXTRA[@]+"${EXTRA[@]}"}
fi

echo
echo ">> listo. Revisa:"
echo "   data/interim/${DATASET}/        (events.csv, labels.csv, dudosos.csv)"
[ "$REV_MODE" != "none" ] && echo "   data/ground_truth/${DATASET}_revisiones.csv  (revisión '${REV_MODE}')"
