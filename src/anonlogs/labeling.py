"""Etiquetado de unidades de análisis a partir de las etiquetas por evento."""

import pandas as pd


def label_units(units: pd.DataFrame, event_labels: pd.DataFrame, rule: str,
                min_fraction: float | None = None) -> pd.Series:
    """Devuelve la etiqueta real (1 = ataque) de cada unidad.

    Usa solo ``event_id → is_attack`` (nunca IP/usuario), así que la etiqueta es
    la misma en todas las versiones anonimizadas.

    Args:
        units: unidades con la lista de ``event_id`` que contienen.
        event_labels: salida de ``parsing.link_ground_truth``.
        rule: ``any`` o ``fraction`` (decisión D2).
        min_fraction: umbral cuando ``rule == "fraction"``.
    """
    raise NotImplementedError
