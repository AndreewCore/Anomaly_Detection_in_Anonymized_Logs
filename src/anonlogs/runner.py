"""Ejecución de un run y escritura de sus artefactos en ``results/runs/<run_id>/``."""

import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from anonlogs.detection import make_detector, REGISTRY
from anonlogs.evaluation.metrics import detection_metrics
from anonlogs.labeling import label_units
from anonlogs.matrix import RunSpec
from anonlogs.splitting import NoAttacksInTestError, temporal_split


def provenance() -> dict:
    """Hash del commit, si hay cambios sin commitear, y versiones de Python/librerías."""
    def git(*args):
        try:
            return subprocess.check_output(["git", *args], text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:
            return "unknown"
    import numpy, pandas, sklearn, scipy
    return {
        "commit": git("rev-parse", "--short", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "python": platform.python_version(),
        "numpy": numpy.__version__, "pandas": pandas.__version__,
        "scikit-learn": sklearn.__version__, "scipy": scipy.__version__,
    }


def is_complete(run_dir: Path) -> bool:
    """Un run está completo si existe ``metrics.json``: es lo último que se escribe."""
    return (run_dir / "metrics.json").is_file()


def _features_path(experiment: dict, spec: RunSpec, repo_root: Path) -> Path:
    """Ruta del CSV de features de este run (lo escribe la etapa 3)."""
    return (repo_root / experiment["paths"]["features"] / spec.dataset /
            f"{spec.tratamiento}-{spec.campo}" / spec.unit / f"w{spec.window_seconds}" /
            "features.csv")


def _write_metrics(run_dir: Path, metrics: dict) -> None:
    """Escribe metrics.json de forma atómica (temporal + rename), lo último del run."""
    tmp = run_dir / "metrics.json.tmp"
    tmp.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    os.replace(tmp, run_dir / "metrics.json")


def execute_run(spec: RunSpec, experiment: dict, runs_dir: Path,
                labeling_cfg: dict | None = None, repo_root: Path | None = None) -> Path:
    """Ejecuta un run completo y escribe sus artefactos.

    Orden: ``config.yaml`` → ``run.log`` → ``scores.csv`` → ``metrics.json``
    (atómico). Un run con detector que usa etiquetas sobre un dataset sin Ground
    Truth, o sin etiquetas disponibles, se marca ``status = omitido`` y queda
    completo, para que la reanudación no lo reintente sin fin.
    """
    from anonlogs.config import REPO_ROOT
    repo_root = repo_root or REPO_ROOT
    labeling_cfg = labeling_cfg or {"rule": "any"}
    run_dir = runs_dir / spec.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    config = {"spec": asdict(spec), "run_id": spec.run_id, "seed": spec.seed,
              "labeling": labeling_cfg, "provenance": provenance()}
    (run_dir / "config.yaml").write_text(json.dumps(config, indent=2), encoding="utf-8")
    log = run_dir / "run.log"

    uses_labels = REGISTRY[spec.detector].uses_labels

    features = pd.read_csv(_features_path(experiment, spec, repo_root))
    labels_path = repo_root / experiment["paths"]["interim"] / spec.dataset / "labels.csv"
    tiene_gt = labels_path.is_file()

    # Un detector semisupervisado sin Ground Truth no puede correr: se omite.
    if uses_labels and not tiene_gt:
        log.write_text("omitido: detector con etiquetas sobre dataset sin Ground Truth\n")
        _write_metrics(run_dir, {"status": "omitido", "motivo": "sin_ground_truth",
                                 "labels_available": False})
        return run_dir

    y_true = None
    if tiene_gt:
        event_labels = pd.read_csv(labels_path)
        y_true = label_units(features, event_labels, labeling_cfg["rule"],
                             labeling_cfg.get("min_fraction"))

    split_cfg = experiment["split"]
    try:
        train_idx, test_idx = temporal_split(
            features, y_true, split_cfg["train_fraction"],
            split_cfg.get("min_attack_units_in_test", 1))
    except NoAttacksInTestError as e:
        log.write_text(f"omitido: {e}\n")
        _write_metrics(run_dir, {"status": "sin_ataques_en_prueba", "motivo": str(e),
                                 "labels_available": True})
        return run_dir

    X = features[list(spec.features)]
    X_train, X_test = X.loc[train_idx], X.loc[test_idx]

    det = make_detector(spec.detector, experiment["detectors"][spec.detector], spec.seed)
    if uses_labels:
        det.fit(X_train, y_true.loc[train_idx])
    else:
        det.fit(X_train)
    scores = det.score(X_test)
    preds = det.predict(X_test)

    y_test = y_true.loc[test_idx].to_numpy() if y_true is not None else None
    metrics = detection_metrics(y_test, preds, scores)
    metrics["status"] = "ok"
    metrics["n_train"], metrics["n_test"] = int(len(X_train)), int(len(X_test))

    # La exposición residual se calculó en la etapa 2; se adjunta al run.
    exp_path = (repo_root / experiment["paths"]["processed"] / spec.dataset /
                spec.tratamiento / spec.campo / "exposure.json")
    if exp_path.is_file():
        metrics["exposure"] = json.loads(exp_path.read_text())

    scores_df = pd.DataFrame({
        "unit_id": features.loc[test_idx, "unit_id"].to_numpy(),
        "score": scores, "pred": preds,
        "label": y_test if y_test is not None else [None] * len(test_idx),
    })
    scores_df.to_csv(run_dir / "scores.csv", index=False)
    log.write_text(f"ok: {len(X_train)} train / {len(X_test)} test\n")
    _write_metrics(run_dir, metrics)
    return run_dir
