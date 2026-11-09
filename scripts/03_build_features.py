"""Etapa 3: calcula features por ventana para cada (dataset, tratamiento, campo, unidad, ventana).

Guarda todas las reglas en un solo archivo por combinación; el runner selecciona
luego las del ``rule_set`` de cada run. La unidad de análisis es la decisión D1,
que se prueba como eje de la matriz.

Uso:
    python scripts/03_build_features.py --matrix configs/matrix_smoke.yaml
"""

import argparse
import itertools

import pandas as pd

from anonlogs.config import REPO_ROOT, load_yaml
from anonlogs.features import RULES, build_features


def main() -> None:
    """Construye las features de todas las combinaciones de la matriz."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--matrix", required=True)
    args = parser.parse_args()

    exp = load_yaml(args.config)
    matrix = load_yaml(args.matrix)
    pairs = [(t["tratamiento"], t["campo"]) for t in matrix["treatments"]]
    units = matrix.get("units", ["ventana"])
    windows = matrix["window_seconds"]

    for dataset, (trat, campo), unit, window in itertools.product(
            matrix["datasets"], pairs, units, windows):
        proc = REPO_ROOT / exp["paths"]["processed"] / dataset / trat / campo / "events.csv"
        if not proc.is_file():
            print(f"{dataset}/{trat}/{campo}: falta {proc} (corre la etapa 2). Se omite.")
            continue
        events = pd.read_csv(proc)
        feats = build_features(events, list(RULES), window, unit)
        out_dir = (REPO_ROOT / exp["paths"]["features"] / dataset /
                   f"{trat}-{campo}" / unit / f"w{window}")
        out_dir.mkdir(parents=True, exist_ok=True)
        feats.to_csv(out_dir / "features.csv", index=False)
        print(f"{dataset}/{trat}/{campo}/{unit}/w{window}: {len(feats)} unidades")


if __name__ == "__main__":
    main()
