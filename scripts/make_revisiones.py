"""Genera ``<dataset>_revisiones.csv`` simulando la revisión humana del GT.

Reemplaza la marca a mano de los dudosos por una de tres estrategias reproducibles
(``cobertura``, ``aleatorio``, ``aciertos``; ver ``anonlogs.revision``), para estudiar
el efecto de la calidad de la revisión sin la variabilidad de cada revisor. El CSV
resultante lo aplica luego ``scripts/01_parse_logs.py``.

Uso:
    python scripts/make_revisiones.py --dataset lab_concentrado --mode cobertura --frac 0.6
    python scripts/make_revisiones.py --dataset lab_concentrado --mode aciertos --rate 0.75 --seed 7
    python scripts/make_revisiones.py --dataset lab_concentrado --mode aleatorio --seed 1
"""

import argparse
from pathlib import Path

import pandas as pd

from anonlogs import parsing, revision
from anonlogs.config import REPO_ROOT, load_yaml


def main() -> None:
    """Lee los argumentos, construye las revisiones del dataset y las escribe en el GT dir."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--mode", required=True, choices=revision.MODES)
    parser.add_argument("--frac", type=float, default=0.60, help="cobertura: fracción revisada [0-1]")
    parser.add_argument("--rate", type=float, default=0.75, help="aciertos: tasa de acierto [0-1]")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=None, help="por defecto data/ground_truth/<dataset>_revisiones.csv")
    args = parser.parse_args()

    exp = load_yaml(args.config)
    meta = exp["datasets"].get(args.dataset)
    if not meta or not meta.get("ground_truth"):
        raise SystemExit(f"{args.dataset} no tiene Ground Truth; no se pueden simular revisiones.")

    # Partimos de los eventos ya parseados por la etapa 1 (evita reparsear el log).
    events_path = REPO_ROOT / exp["paths"]["interim"] / args.dataset / "events.csv"
    if not events_path.is_file():
        raise SystemExit(
            f"Falta {events_path}. Corre antes: python scripts/01_parse_logs.py --datasets {args.dataset}")
    events = pd.read_csv(events_path)
    # Al releer el CSV las marcas de tiempo vuelven como texto; link_ground_truth las
    # compara contra Timestamps, así que hay que devolverlas a datetime UTC.
    for col in ("timestamp", "timestamp_real"):
        events[col] = pd.to_datetime(events[col], utc=True)

    gt_dir = REPO_ROOT / exp["paths"]["ground_truth"]
    gt = parsing.load_ground_truth(gt_dir / Path(meta["ground_truth"]).name)
    legit = revision.load_legit(gt_dir, args.dataset)

    rev = revision.build_revisiones(events, gt, args.mode,
                                    frac=args.frac, rate=args.rate, seed=args.seed, legit=legit)

    out = Path(args.out) if args.out else gt_dir / f"{args.dataset}_revisiones.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    rev.to_csv(out, index=False)
    print(f"{args.dataset}: {len(rev)} revisiones ('{args.mode}') -> {out}")
    print(f"Aplícalas con: python scripts/01_parse_logs.py --datasets {args.dataset}")


if __name__ == "__main__":
    main()
