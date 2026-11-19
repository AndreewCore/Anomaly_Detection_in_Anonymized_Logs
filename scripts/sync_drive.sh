#!/usr/bin/env bash
# Sincroniza datos pesados con la carpeta compartida de Google Drive vía rclone.
# No borra nada en el destino (usa `rclone copy`): varios integrantes suben sin
# pisarse, porque las subcarpetas de capturas y de runs llevan nombre único.
#
# Las pruebas (capturas del lab y sesiones de runs) se dividen en Drive por fecha:
# cada una cuelga de una carpeta <HH:MM-DD-MM-AAAA> derivada de su propia marca de
# tiempo. El pull aplana esas carpetas de vuelta al layout local plano.
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

# Pares "ruta_local  ruta_remota" para los grupos SIN dividir por fecha (datasets y
# los agregados de resultados). Las features no se suben: se regeneran.
map_for() {
    case "$1" in
        datos)      echo "data/raw                  datasets/raw
                          data/ground_truth         datasets/ground_truth
                          data/interim              datasets/interim
                          data/processed            datasets/processed" ;;
        resultados) echo "results/runs              results/runs
                          results/tables            results/tables
                          results/figures           results/figures" ;;
        *) return 1 ;;
    esac
}

# Etiqueta de carpeta por fecha (HH:MM-DD-MM-AAAA) a partir del nombre de una
# carpeta de prueba, que empieza por AAAA-MM-DD_HHMM (lo fijan capture.sh y
# 04_run_matrix.py). Si el nombre no trae esa marca, cae en "sin_fecha".
date_label() {
    local n; n="$(basename "$1")"
    if [[ "$n" =~ ^([0-9]{4})-([0-9]{2})-([0-9]{2})_([0-9]{2})([0-9]{2}) ]]; then
        echo "${BASH_REMATCH[4]}:${BASH_REMATCH[5]}-${BASH_REMATCH[3]}-${BASH_REMATCH[2]}-${BASH_REMATCH[1]}"
    else
        echo "sin_fecha"
    fi
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

# Grupos divididos por fecha: cada prueba (captura o sesión de runs) se sube a
# <remoto>/<HH:MM-DD-MM-AAAA>/<ruta relativa de la prueba>, para que en Drive queden
# agrupadas por el momento en que se corrieron. `depth` es la profundidad de la
# carpeta de prueba bajo la base local (capturas: <escenario>/<prueba> = 2;
# sesiones: <prueba> = 1). El pull aplana: copia el contenido de cada carpeta de
# fecha de vuelta a la base local, reconstruyendo el layout plano original.
sync_dated() {
    local local_base="$1" remote_base="$2" depth="$3" d rel label labels
    if [ "$DIR_CMD" = "push" ]; then
        [ -d "$local_base" ] || return 0
        find "$local_base" -mindepth "$depth" -maxdepth "$depth" -type d \
             -not -path '*/_actual/*' -not -name _actual | while read -r d; do
            rel="${d#"$local_base"/}"
            label="$(date_label "$d")"
            echo ">> push $d -> $REMOTE/$remote_base/$label/$rel"
            rclone copy "$d" "$REMOTE/$remote_base/$label/$rel" --progress $DRY || true
        done
    else
        labels="$(rclone lsf "$REMOTE/$remote_base" --dirs-only 2>/dev/null || true)"
        for label in $labels; do
            echo ">> pull $REMOTE/$remote_base/${label%/} -> $local_base"
            rclone copy "$REMOTE/$remote_base/${label%/}" "$local_base" --progress $DRY || true
        done
    fi
}

sync_all_resultados() {
    sync_dated "results/sessions" "results/sessions" 1   # sesiones de runs, por fecha
    sync_group resultados                                # runs/tables/figures (plano)
}

sync_what() {
    case "$1" in
        capturas)   sync_dated "lab/output" "capturas" 2 ;;  # <escenario>/<prueba>, por fecha
        datos)      sync_group datos ;;
        resultados) sync_all_resultados ;;
        *) echo "grupo desconocido: $1"; return 1 ;;
    esac
}

if [ "$WHAT" = "all" ]; then
    for g in capturas datos resultados; do sync_what "$g"; done
else
    sync_what "$WHAT"
fi
