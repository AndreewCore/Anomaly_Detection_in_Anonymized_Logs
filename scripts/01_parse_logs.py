"""Etapa 1: parsea los logs crudos a data/interim/<dataset>/ y une el Ground Truth.

Por cada dataset: parsea los segmentos a una línea de tiempo virtual, asocia las
etiquetas por ``event_id`` (solo si hay GT), aplica las revisiones humanas si
existen, y genera ``dudosos.csv`` con los casos a revisar.

Uso:
    python scripts/01_parse_logs.py --datasets lab_concentrado loghub_openssh
"""

import argparse
from pathlib import Path

import pandas as pd

from anonlogs.config import REPO_ROOT, load_yaml
from anonlogs import parsing


def _parse_lab(raw_dir: Path, dataset: str) -> pd.DataFrame:
    """Parsea todos los ``seg*/auth.log`` de un escenario a la línea de tiempo virtual."""
    frames = []
    for seg_dir in sorted(raw_dir.glob("seg*")):
        auth = seg_dir / "auth.log"
        if auth.is_file():
            seg = int(seg_dir.name.removeprefix("seg"))
            frames.append(parsing.parse_auth_log(auth, dataset, segment=seg))
    return parsing.build_virtual_timeline(frames)


def _parse_loghub(raw_dir: Path, dataset: str) -> pd.DataFrame:
    """Parsea los .log de Loghub (formato tradicional, un único 'segmento')."""
    frames = [parsing.parse_auth_log(p, dataset, segment=0) for p in sorted(raw_dir.glob("*.log"))]
    return parsing.build_virtual_timeline(frames)


def main() -> None:
    """Parsea los datasets pedidos y escribe events/labels/dudosos en interim."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--datasets", nargs="+", help="por defecto, todos los de experiment.yaml")
    args = parser.parse_args()

    exp = load_yaml(args.config)
    datasets = args.datasets or list(exp["datasets"])
    gt_dir = REPO_ROOT / exp["paths"]["ground_truth"]

    for name in datasets:
        meta = exp["datasets"][name]
        raw_dir = REPO_ROOT / exp["paths"]["raw"] / Path(meta["path"]).relative_to("raw")
        if meta["source"] == "lab":
            events = _parse_lab(raw_dir, name)
        else:
            events = _parse_loghub(raw_dir, name)

        if events.empty:
            print(f"{name}: sin eventos en {raw_dir} (¿corriste la etapa 0?). Se omite.")
            continue

        out_dir = REPO_ROOT / exp["paths"]["interim"] / name
        out_dir.mkdir(parents=True, exist_ok=True)
        events.to_csv(out_dir / "events.csv", index=False)

        if meta.get("ground_truth"):
            gt_path = gt_dir / Path(meta["ground_truth"]).name
            if gt_path.is_file():
                gt = parsing.load_ground_truth(gt_path)
                labels = parsing.link_ground_truth(events, gt)
                rev_path = gt_dir / f"{name}_revisiones.csv"
                if rev_path.is_file():
                    labels = parsing.apply_revisions(labels, pd.read_csv(rev_path))
                    print(f"  {name}: revisiones aplicadas desde {rev_path.name}")
                labels.to_csv(out_dir / "labels.csv", index=False)
                parsing.find_dudosos(events, labels, gt).to_csv(out_dir / "dudosos.csv", index=False)
                n_atk = int(labels["is_attack"].sum())
                print(f"{name}: {len(events)} eventos, {n_atk} de ataque -> {out_dir}")
                continue

        # Sin Ground Truth (Loghub o aún sin consolidar): no se escriben etiquetas.
        print(f"{name}: {len(events)} eventos, sin etiquetas -> {out_dir}")


if __name__ == "__main__":
    main()
