#!/usr/bin/env bash
# Captura un segmento de un escenario de principio a fin y deja la salida en una
# carpeta con nombre descriptivo (fecha, segmento, usuario, nº de eventos, duración).
#
# Uso:
#   lab/capture.sh <escenario> <segmento> [--minutes N]
#   lab/capture.sh concentrado 1
#   lab/capture.sh concentrado 1 --minutes 5      # captura corta de prueba
#
# Los segmentos de un mismo escenario se pueden correr en días distintos; el
# parser (scripts/01) los concatena como una sola línea de tiempo.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$LAB_DIR"

SCENARIO="${1:-}"
SEGMENT="${2:-}"
MINUTES_OVERRIDE=""
if [ "${3:-}" = "--minutes" ]; then MINUTES_OVERRIDE="${4:-}"; fi

ENV_FILE="scenarios/${SCENARIO}.env"
if [ -z "$SCENARIO" ] || [ -z "$SEGMENT" ] || [ ! -f "$ENV_FILE" ]; then
    echo "uso: lab/capture.sh <escenario> <segmento> [--minutes N]"
    echo "escenarios: $(ls scenarios/*.env 2>/dev/null | xargs -n1 basename | sed 's/.env//' | tr '\n' ' ')"
    exit 1
fi

# shellcheck disable=SC1090
set -a; . "./$ENV_FILE"; set +a
[ -n "$MINUTES_OVERRIDE" ] && SEGMENT_MINUTES="$MINUTES_OVERRIDE"
export SCENARIO SEGMENT SEGMENT_MINUTES

COMPOSE="docker compose -f docker-compose.yml --env-file $ENV_FILE"
ACTUAL="output/_actual"

echo ">> escenario=$SCENARIO segmento=$SEGMENT duracion=${SEGMENT_MINUTES}min perfil=$PROFILE"

# Empezamos de cero: _actual solo contiene la captura en curso.
rm -rf "$ACTUAL"
mkdir -p "$ACTUAL/victim" "$ACTUAL/gt" "$ACTUAL/legit"

START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_EPOCH="$(date +%s)"

# --abort-on-container-exit no sirve: la víctima nunca termina. Levantamos en
# segundo plano y esperamos a que mueran atacantes y tráfico legítimo.
$COMPOSE --profile "$PROFILE" up --build -d

echo ">> capturando... (Ctrl-C para abortar; la salida parcial se conserva)"
# Esperamos a que terminen los generadores de carga (no la víctima ni rsyslog).
while true; do
    running=$($COMPOSE ps --status running --format '{{.Service}}' 2>/dev/null \
             | grep -E '^(attacker_|legit_)' || true)
    [ -z "$running" ] && break
    sleep 5
done

END_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DUR_S=$(( $(date +%s) - START_EPOCH ))

$COMPOSE --profile "$PROFILE" down >/dev/null 2>&1 || true

# Nombre descriptivo. N eventos = líneas sshd del auth.log capturado.
AUTH="$ACTUAL/victim/auth.log"
N_EVENTS=$(grep -c 'sshd' "$AUTH" 2>/dev/null || echo 0)
DUR_MIN=$(( DUR_S / 60 ))
USER_TAG="${USER:-anon}"
STAMP="$(date -u +%Y-%m-%d_%H%M)"
DEST="output/${SCENARIO}/${STAMP}__seg${SEGMENT}__${USER_TAG}__${N_EVENTS}eventos__${DUR_MIN}min"

mkdir -p "$DEST"
cp -r "$ACTUAL/victim" "$ACTUAL/gt" "$ACTUAL/legit" "$DEST/" 2>/dev/null || true

cat > "$DEST/manifest.json" <<JSON
{
  "scenario": "$SCENARIO",
  "segment": $SEGMENT,
  "seed_base": ${SEED_BASE:-0},
  "seed": $(( ${SEED_BASE:-0} + SEGMENT )),
  "segment_minutes": $SEGMENT_MINUTES,
  "commit": "$(git -C "$LAB_DIR/.." rev-parse --short HEAD 2>/dev/null || echo unknown)",
  "started_utc": "$START_ISO",
  "ended_utc": "$END_ISO",
  "duration_seconds": $DUR_S,
  "user": "$USER_TAG",
  "n_sshd_events": $N_EVENTS
}
JSON

echo ">> listo: $DEST  ($N_EVENTS eventos sshd, ${DUR_MIN} min)"
echo ">> súbelo a Drive con:  scripts/sync_drive.sh push capturas"
