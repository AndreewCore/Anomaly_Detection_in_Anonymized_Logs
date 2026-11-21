#!/usr/bin/env bash
# Sincroniza datos pesados con la carpeta compartida de Google Drive vía rclone.
# No borra nada en el destino (usa `rclone copy`): varios integrantes suben sin
# pisarse, porque cada captura cuelga de su propio nombre único.
#
# Layout en Drive, pensado para distinguir pruebas por fecha:
#
#   AnonLogs/
#     tests/                       <- una carpeta por CAPTURA (auto-fechada)
#       2026-11-19_2356__seg1__andreew__2321eventos__11min/   victim/ gt/ legit/
#       ...
#     _derivado/                   <- NO es por-test: último procesamiento + tablas
#       datos/        (raw/ ground_truth/ interim/ processed/)
#       resultados/   (runs/ sessions/ tables/ figures/)
#
# Cada captura lleva su fecha y hora (AAAA-MM-DD_HHMM) en el nombre, así que dos
# pruebas el mismo día caen en carpetas distintas de tests/ sin pisarse. Lo
# derivado (datos procesados, runs, tablas) se sobrescribe en cada corrida —
# refleja el ÚLTIMO procesamiento, no una captura concreta—, por eso va aparte.
#
# Configura una sola vez el remoto y pon su nombre y carpeta en .env:
#   rclone config                       # crea un remoto de Drive (p. ej. "drive")
#   DRIVE_REMOTE=drive                  # en .env
#   DRIVE_FOLDER=AnonLogs               # carpeta del grupo en ese Drive
#
# Uso:
#   scripts/sync_drive.sh push|pull [tests|datos|resultados|all] [--dry-run]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Carga DRIVE_REMOTE/DRIVE_FOLDER desde .env sin volcar el resto del entorno.
if [ -f .env ]; then
    DRIVE_REMOTE="$(grep -E '^DRIVE_REMOTE=' .env | cut -d= -f2- || true)"
    DRIVE_FOLDER="$(grep -E '^DRIVE_FOLDER=' .env | cut -d= -f2- || true)"
fi
: "${DRIVE_REMOTE:=}" ; : "${DRIVE_FOLDER:=}"

DIR_CMD="${1:-}"; WHAT="${2:-all}"; FLAG="${3:-}"
if [ -z "$DRIVE_REMOTE" ] || [ -z "$DRIVE_FOLDER" ]; then
    echo "Falta DRIVE_REMOTE o DRIVE_FOLDER en .env (ver cabecera de este script)."; exit 1
fi
if [ "$DIR_CMD" != "push" ] && [ "$DIR_CMD" != "pull" ]; then
    echo "uso: scripts/sync_drive.sh push|pull [tests|datos|resultados|all] [--dry-run]"; exit 1
fi
DRY=""; [ "$FLAG" = "--dry-run" ] && DRY="--dry-run"

REMOTE="${DRIVE_REMOTE}:${DRIVE_FOLDER}"

# --- tests: una carpeta por captura -----------------------------------------
# Cada captura vive en lab/output/<escenario>/<captura>/ y sube a tests/<captura>/.
# El nombre <captura> ya trae fecha+hora (AAAA-MM-DD_HHMM), así que no colisiona
# entre corridas; se excluye _actual (la captura en curso, aún sin nombre final).
# Al bajar no se puede reconstruir el escenario de origen, así que el pull deja todo
# en lab/output/_drive/ para inspección manual.
sync_tests() {
    local cap base
    if [ "$DIR_CMD" = "push" ]; then
        for cap in lab/output/*/*/ ; do
            [ -d "$cap" ] || continue
            # _actual es la captura en curso; cuelga como lab/output/_actual/{gt,legit,
            # victim}, así que se descarta cualquier ruta que la contenga, no solo el
            # nombre final.
            [[ "$cap" == */_actual/* ]] && continue
            base="$(basename "$cap")"
            echo ">> push $cap -> tests/$base/"
            rclone copy "$cap" "$REMOTE/tests/$base" --progress $DRY || true
        done
    else
        echo ">> pull tests/ -> lab/output/_drive/"
        rclone copy "$REMOTE/tests" lab/output/_drive --progress $DRY || true
    fi
}

# --- _derivado: datos procesados + resultados (NO por-test) ------------------
# Pares "ruta_local  subruta_remota" bajo _derivado/. Las features no se suben:
# se regeneran desde los datos.
map_derivado() {
    case "$1" in
        datos)      echo "data/raw           _derivado/datos/raw
                          data/ground_truth  _derivado/datos/ground_truth
                          data/interim       _derivado/datos/interim
                          data/processed     _derivado/datos/processed" ;;
        resultados) echo "results/runs       _derivado/resultados/runs
                          results/sessions   _derivado/resultados/sessions
                          results/tables     _derivado/resultados/tables
                          results/figures    _derivado/resultados/figures" ;;
        *) return 1 ;;
    esac
}

sync_derivado() {
    local grp="$1" local_path remote_sub
    map_derivado "$grp" | while read -r local_path remote_sub; do
        [ -z "$local_path" ] && continue
        if [ "$DIR_CMD" = "push" ]; then
            echo ">> push $local_path -> $remote_sub"
            [ -e "$local_path" ] && rclone copy "$local_path" "$REMOTE/$remote_sub" --progress $DRY || true
        else
            echo ">> pull $remote_sub -> $local_path"
            rclone copy "$REMOTE/$remote_sub" "$local_path" --progress $DRY || true
        fi
    done
}

case "$WHAT" in
    all)        sync_tests; sync_derivado datos; sync_derivado resultados ;;
    tests)      sync_tests ;;
    datos)      sync_derivado datos ;;
    resultados) sync_derivado resultados ;;
    *) echo "uso: scripts/sync_drive.sh push|pull [tests|datos|resultados|all] [--dry-run]"; exit 1 ;;
esac
