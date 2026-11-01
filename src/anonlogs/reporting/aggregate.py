"""Consolidación de runs crudos en tablas. Solo lee ``results/runs/``; nunca recalcula."""

from pathlib import Path

import pandas as pd


def consolidate_runs(runs_dir: Path) -> pd.DataFrame:
    """Una fila por run completo: columnas de ``config.yaml`` + ``metrics.json``.

    Los runs sin ``metrics.json`` (interrumpidos) se omiten y se reportan en el log.
    """
    raise NotImplementedError


def aggregate_over_seeds(runs: pd.DataFrame) -> pd.DataFrame:
    """Agrega por combinación sin semilla: media, desviación estándar, mínimo y máximo de cada métrica.

    Incluye ``n_seeds`` para detectar combinaciones incompletas.
    """
    raise NotImplementedError
