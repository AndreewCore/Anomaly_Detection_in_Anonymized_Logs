"""Etapa 0 (lab): copia las capturas de lab/output/ a data/raw/lab/ y consolida el GT.

Para cada segmento de un escenario toma la captura más reciente (el nombre empieza
por fecha, así que la última ordena al final) y la deja en
``data/raw/lab/<escenario>/seg<k>/auth.log``. Junta los Ground Truth por segmento
en ``data/ground_truth/lab_<escenario>.csv``.

Uso:
    python scripts/00_ingest_lab.py --scenario concentrado
"""

import argparse
import re
import shutil
from pathlib import Path

import pandas as pd

from anonlogs.config import REPO_ROOT, load_yaml

_SEG_RE = re.compile(r"__seg(\d+)__")


def _latest_por_segmento(scenario_dir: Path) -> dict[int, Path]:
    """Devuelve, por número de segmento, la carpeta de captura más reciente."""
    latest: dict[int, Path] = {}
    for d in sorted(scenario_dir.iterdir()):
        if not d.is_dir():
            continue
        m = _SEG_RE.search(d.name)
        if m:
            latest[int(m.group(1))] = d  # el orden alfabético deja la última al final
    return latest


def main() -> None:
    """Copia las capturas del escenario y consolida su Ground Truth."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--scenario", required=True, help="concentrado | multi_cuenta | distribuido | spraying")
    args = parser.parse_args()

    exp = load_yaml(args.config)
    scenario_dir = REPO_ROOT / "lab" / "output" / args.scenario
    if not scenario_dir.is_dir():
        raise SystemExit(f"No hay capturas en {scenario_dir}. Corre lab/capture.sh primero.")

    capturas = _latest_por_segmento(scenario_dir)
    if not capturas:
        raise SystemExit(f"No se encontraron carpetas __seg<k>__ en {scenario_dir}.")

    raw_dir = REPO_ROOT / exp["paths"]["raw"] / "lab" / args.scenario
    gt_frames = []
    for seg, folder in sorted(capturas.items()):
        auth = folder / "victim" / "auth.log"
        if not auth.is_file():
            print(f"  aviso: el segmento {seg} no tiene victim/auth.log, se omite")
            continue
        dest = raw_dir / f"seg{seg}"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(auth, dest / "auth.log")
        for gt in (folder / "gt").glob("*.csv"):
            gt_frames.append(pd.read_csv(gt))
        print(f"  segmento {seg}: {folder.name} -> {dest}")

    expected = max(capturas)
    faltan = [k for k in range(1, expected + 1) if k not in capturas]
    if faltan:
        print(f"  aviso: faltan segmentos {faltan} (puedes capturarlos otro día)")

    if gt_frames:
        gt_all = pd.concat(gt_frames, ignore_index=True).drop_duplicates()
        gt_path = REPO_ROOT / exp["paths"]["ground_truth"] / f"lab_{args.scenario}.csv"
        gt_path.parent.mkdir(parents=True, exist_ok=True)
        gt_all.to_csv(gt_path, index=False)
        print(f"Ground Truth consolidado: {gt_path} ({len(gt_all)} filas)")


if __name__ == "__main__":
    main()
