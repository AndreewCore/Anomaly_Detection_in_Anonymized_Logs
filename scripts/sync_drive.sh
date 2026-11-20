#!/usr/bin/env bash
# Sincroniza datos pesados con la carpeta compartida de Google Drive vía rclone.
# No borra nada en el destino (usa `rclone copy`).
#
# Layout en Drive: la FECHA es la carpeta principal. Cada push crea una carpeta de
# ejecución <AAAA-MM-DD_HH-MM> (la hora del push) y mete dentro los grupos:
#
#   AnonLogs/
#     2026-11-20_00-31/            <- una ejecución (una sincronización)
#       capturas/                  (lab/output: victim/ gt/ legit/)
#       datos/                     (raw/ ground_truth/ interim/ processed/)
#       resultados/                (runs/ sessions/ tables/ figures/)
#
# Así cada ejecución queda autocontenida: datos sin procesar + ground truth +
# tablas comparativas, sin mezclarse entre corridas. Para fijar el nombre de la
# carpeta en vez de usar la hora, exporta EXEC (p. ej. EXEC=2026-11-20_prueba1).
#
# Configura una sola vez el remoto y pon su nombre y carpeta en .env:
#   rclone config                       # crea un remoto de Drive (p. ej. "drive")
#   DRIVE_REMOTE=drive                  # en .env
#   DRIVE_FOLDER=AnonLogs               # carpeta del grupo en ese Drive
#
# Uso:
#   scripts/sync_drive.sh push|pull [capturas|datos|resultados|all] [--dry-run]
#   EXEC=2026-11-20_00-31 scripts/sync_drive.sh pull   # elegir una ejecución al bajar
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Carga DRIVE_REMOTE/DRIVE_FOLDER desde .env sin volcar el resto del entorno.
if [ -f .env ]; then
    DRIVE_REMOTE="$(grep -E '^DRIVE_REMOTE=' .env | cut -d= -f2- || true)"
    DRIVE_FOLDER="$(grep -E '^DRIVE_FOLDER=' .env | cut -d= -f2- || true)"
fi
: "${DRIVE_REMOTE:=}" ; : "${DRIVE_FOLDER:=}" ; : "${EXEC:=}"

DIR_CMD="${1:-}"; WHAT="${2:-all}"; FLAG="${3:-}"
if [ -z "$DRIVE_REMOTE" ] || [ -z "$DRIVE_FOLDER" ]; then
    echo "Falta DRIVE_REMOTE o DRIVE_FOLDER en .env (ver cabecera de este script)."; exit 1
fi
if [ "$DIR_CMD" != "push" ] && [ "$DIR_CMD" != "pull" ]; then
    echo "uso: scripts/sync_drive.sh push|pull [capturas|datos|resultados|all] [--dry-run]"; exit 1
fi
DRY=""; [ "$FLAG" = "--dry-run" ] && DRY="--dry-run"

REMOTE="${DRIVE_REMOTE}:${DRIVE_FOLDER}"

# Pares "ruta_local  subruta_remota" dentro de la carpeta de ejecución. Las features
# no se suben: se regeneran desde los datos.
map_for() {
    case "$1" in
        capturas)   echo "lab/output                capturas" ;;
        datos)      echo "data/raw                  datos/raw
                          data/ground_truth         datos/ground_truth
                          data/interim              datos/interim
                          data/processed            datos/processed" ;;
        resultados) echo "results/runs              resultados/runs
                          results/sessions          resultados/sessions
                          results/tables            resultados/tables
                          results/figures           resultados/figures" ;;
        *) return 1 ;;
    esac
}

# Sincroniza un grupo bajo la carpeta de ejecución ($EXEC). En capturas se excluye
# _actual (la captura en curso, sin nombre definitivo).
sync_group() {
    local grp="$1" local_path remote_sub
    map_for "$grp" | while read -r local_path remote_sub; do
        [ -z "$local_path" ] && continue
        local -a excl=()
        [ "$grp" = "capturas" ] && excl=(--exclude "_actual/**")
        local remote_path="$REMOTE/$EXEC/$remote_sub"
        if [ "$DIR_CMD" = "push" ]; then
            echo ">> push $local_path -> $EXEC/$remote_sub"
            [ -e "$local_path" ] && rclone copy "$local_path" "$remote_path" \
                ${excl[@]+"${excl[@]}"} --progress $DRY || true
        else
            echo ">> pull $EXEC/$remote_sub -> $local_path"
            rclone copy "$remote_path" "$local_path" --progress $DRY || true
        fi
    done
}

# Resuelve la carpeta de ejecución: al subir, la hora del push (o $EXEC si se fijó);
# al bajar, la última ejecución en Drive (o $EXEC si se indicó).
if [ "$DIR_CMD" = "push" ]; then
    [ -z "$EXEC" ] && EXEC="$(date -u +%Y-%m-%d_%H-%M)"
    echo ">> ejecución (carpeta en Drive): $EXEC"
else
    if [ -z "$EXEC" ]; then
        EXEC="$(rclone lsf "$REMOTE" --dirs-only 2>/dev/null \
                | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}_' | sort | tail -1 | sed 's#/$##')"
    fi
    [ -z "$EXEC" ] && { echo "No hay ejecuciones <fecha> en $REMOTE. Usa EXEC=<carpeta> para elegir una."; exit 1; }
    echo ">> pull desde ejecución: $EXEC"
fi

if [ "$WHAT" = "all" ]; then
    for g in capturas datos resultados; do sync_group "$g"; done
else
    sync_group "$WHAT"
fi
