"""Prueba de ``execute_run`` de punta a punta con un dataset sintético en disco."""

import json

import numpy as np
import pandas as pd

from anonlogs.matrix import RunSpec
from anonlogs.runner import execute_run, is_complete

PATHS = {"features": "data/features", "interim": "data/interim",
         "processed": "data/processed", "runs": "results/runs"}
EXPERIMENT = {
    "paths": PATHS,
    "split": {"train_fraction": 0.6, "min_attack_units_in_test": 1},
    "detectors": {
        "isolation_forest": {"n_estimators": 50, "max_samples": "auto", "contamination": "auto"},
        "umbral": {"fallos_por_ip": 10, "fallos_por_ventana": 30},
    },
}


def _montar_dataset(root, dataset="lab_x", unit="ventana_ip", window=300,
                    trat="original", campo="ninguno", con_gt=True):
    """Crea features.csv y labels.csv sintéticos: normales al inicio, ataques al final."""
    base = pd.Timestamp("2026-11-09T14:00:00Z")
    filas, labels = [], []
    for i in range(10):
        es_ataque = i >= 6  # los ataques caen en la parte de prueba (temporal)
        fallos = 40 if es_ataque else 1
        eid = f"{dataset}:seg0:{i}"
        filas.append({"unit_id": f"{i}|ip=A", "window_start": base + pd.Timedelta(minutes=i),
                      "event_ids": eid, "fallos_por_ip": fallos, "fallos_por_ventana": fallos})
        labels.append({"event_id": eid, "is_attack": int(es_ataque)})

    fdir = root / PATHS["features"] / dataset / f"{trat}-{campo}" / unit / f"w{window}"
    fdir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_csv(fdir / "features.csv", index=False)

    if con_gt:
        idir = root / PATHS["interim"] / dataset
        idir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(labels).to_csv(idir / "labels.csv", index=False)


def _spec(detector, dataset="lab_x"):
    return RunSpec(dataset, "original", "ninguno", "todas",
                   ("fallos_por_ip", "fallos_por_ventana"), "ventana_ip", "any",
                   300, detector, seed=0 if detector != "umbral" else None)


def test_run_umbral_detecta_ataques(tmp_path):
    """Un run con umbral produce metrics.json completo y detecta los ataques finales."""
    _montar_dataset(tmp_path)
    runs_dir = tmp_path / "results" / "runs"
    run_dir = execute_run(_spec("umbral"), EXPERIMENT, runs_dir,
                          {"rule": "any"}, repo_root=tmp_path)
    assert is_complete(run_dir)
    m = json.loads((run_dir / "metrics.json").read_text())
    assert m["status"] == "ok" and m["recall"] == 1.0
    assert (run_dir / "scores.csv").is_file() and (run_dir / "config.yaml").is_file()


def test_run_isolation_forest_marca_filas(tmp_path):
    """Isolation Forest corre sin etiquetas y escribe scores por fila de prueba."""
    _montar_dataset(tmp_path)
    runs_dir = tmp_path / "results" / "runs"
    run_dir = execute_run(_spec("isolation_forest"), EXPERIMENT, runs_dir,
                          {"rule": "any"}, repo_root=tmp_path)
    scores = pd.read_csv(run_dir / "scores.csv")
    assert len(scores) == 4 and set(scores["pred"].unique()) <= {0, 1}


def test_run_ssif_sin_gt_se_omite(tmp_path):
    """SSIF sobre un dataset sin Ground Truth se marca omitido, no falla."""
    _montar_dataset(tmp_path, dataset="loghub", con_gt=False)
    runs_dir = tmp_path / "results" / "runs"
    run_dir = execute_run(_spec("ssif", dataset="loghub"), EXPERIMENT, runs_dir,
                          {"rule": "any"}, repo_root=tmp_path)
    m = json.loads((run_dir / "metrics.json").read_text())
    assert m["status"] == "omitido" and is_complete(run_dir)
