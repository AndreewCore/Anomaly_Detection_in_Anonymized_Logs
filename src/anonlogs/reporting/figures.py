"""Figuras para el artículo. Cada figura se exporta en PDF (Overleaf) y PNG (vista rápida)."""

from pathlib import Path

import pandas as pd


def save_figure(fig, out_dir: Path, name: str) -> None:
    """Guarda ``fig`` como ``<name>.pdf`` y ``<name>.png`` en ``out_dir``."""
    raise NotImplementedError


def boxplots_by_treatment(runs: pd.DataFrame, metric: str, out_dir: Path) -> None:
    """Boxplot de ``metric`` por tratamiento y detector, mostrando la varianza entre semillas."""
    raise NotImplementedError


def roc_pr_curves(runs_dir: Path, run_ids: list[str], out_dir: Path) -> None:
    """Curvas ROC y PR de runs representativos, leídas de su ``scores.csv``."""
    raise NotImplementedError


def heatmap_treatment_rules(aggregated: pd.DataFrame, metric: str, out_dir: Path) -> None:
    """Heatmap tratamiento × conjunto de reglas con la media de ``metric``."""
    raise NotImplementedError
