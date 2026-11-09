#!/bin/sh
# Lanza el ataque de fuerza bruta SSH de un atacante y escribe su Ground Truth.
# Toda la configuración llega por variables de entorno desde el escenario
# (ver lab/docker-compose.yml y lab/scenarios/<escenario>.env).
set -eu

sleep "${START_DELAY:-8}"

DURATION_S=$(( ${SEGMENT_MINUTES:-30} * 60 ))
# Semilla reproducible por segmento: dos capturas del mismo segmento coinciden.
SEED=$(( ${SEED_BASE:-0} + ${SEGMENT:-1} ))
GT_FILE="/gt/${SCENARIO:-escenario}_seg${SEGMENT:-1}.csv"

# El encabezado lo escribe el primer atacante que llega; el resto solo agrega.
# flock evita que dos atacantes escriban el encabezado a la vez.
if command -v flock >/dev/null 2>&1; then
    ( flock 9
      [ -s "$GT_FILE" ] || echo "scenario,segment,burst_id,attacker,src_ip,user,ts_start,ts_end" > "$GT_FILE"
    ) 9>/gt/.header.lock
else
    [ -s "$GT_FILE" ] || echo "scenario,segment,burst_id,attacker,src_ip,user,ts_start,ts_end" > "$GT_FILE"
fi

echo "[$ATTACKER_NAME] ssh -> $TARGET_HOST | usuarios=$ATTACK_USERS n=$ATTACK_N rafagas=${BURSTS_PER_SEGMENT:-2} dur=${DURATION_S}s"

exec anomalia ssh "${TARGET_HOST:-victim}" \
    -u "$ATTACK_USERS" \
    -n "$ATTACK_N" \
    -p "${PAUSE_MS:-800}" \
    -d "$DURATION_S" \
    -b "${BURSTS_PER_SEGMENT:-2}" \
    -s "$SEED" \
    -g "$GT_FILE" \
    -I "$SRC_IP" \
    -a "$ATTACKER_NAME" \
    -S "${SCENARIO:-escenario}" \
    -k "${SEGMENT:-1}"
