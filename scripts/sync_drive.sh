#!/usr/bin/env bash
# Sincroniza datos pesados con la carpeta compartida de Google Drive vía rclone.
# No borra nada en el destino (usa `rclone copy`): varios integrantes suben sin
# pisarse, porque las subcarpetas de capturas y de runs llevan nombre único.
#
# Configura una sola vez el remoto y pon su nombre y carpeta en .env:
#   rclone config                       # crea un remoto de Drive (p. ej. "drive")
#   DRIVE_REMOTE=drive                  # en .env
#   DRIVE_FOLDER=AnonLogs               # carpeta del grupo en ese Drive
#
# Uso:
#   scripts/sync_drive.sh push|pull [capturas|datos|resultados|all] [--dry-run]
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
    echo "uso: scripts/sync_drive.sh push|pull [capturas|datos|resultados|all] [--dry-run]"; exit 1
fi
DRY=""; [ "$FLAG" = "--dry-run" ] && DRY="--dry-run"

REMOTE="${DRIVE_REMOTE}:${DRIVE_FOLDER}"

# Pares "ruta_local  ruta_remota". Las features no se suben: se regeneran.
map_for() {
    case "$1" in
        capturas)   echo "lab/output                capturas" ;;
        datos)      echo "data/raw                  datasets/raw
                          data/ground_truth         datasets/ground_truth
                          data/interim              datasets/interim
                          data/processed            datasets/processed" ;;
        resultados) echo "results/runs              results/runs
                          results/sessions          results/sessions
                          results/tables            results/tables
                          results/figures           results/figures" ;;
        *) return 1 ;;
    esac
}

sync_group() {
    local grp="$1" local_path remote_path
    map_for "$grp" | while read -r local_path remote_path; do
        [ -z "$local_path" ] && continue
        if [ "$DIR_CMD" = "push" ]; then
            echo ">> push $local_path -> $REMOTE/$remote_path"
            [ -e "$local_path" ] && rclone copy "$local_path" "$REMOTE/$remote_path" --progress $DRY || true
        else
            echo ">> pull $REMOTE/$remote_path -> $local_path"
            rclone copy "$REMOTE/$remote_path" "$local_path" --progress $DRY || true
        fi
    done
}

if [ "$WHAT" = "all" ]; then
    for g in capturas datos resultados; do sync_group "$g"; done
else
    sync_group "$WHAT"
fi
