"""Pruebas estadísticas entre tratamientos."""

import pandas as pd


def wilcoxon_between_treatments(runs: pd.DataFrame, metric: str, alpha: float = 0.05) -> pd.DataFrame:
    """Wilcoxon pareado por semilla entre cada par de tratamientos, con corrección de Holm.

    Para cada (dataset, rule_set, ventana, detector) compara los pares de
    (tratamiento, campo) emparejando runs por semilla. Con muchos pares, sin
    corrección algunas diferencias saldrían "significativas" por azar; por eso
    se ajustan los p-valores con Holm dentro de cada familia de comparaciones.

    El detector ``umbral`` no tiene semilla (un único valor por combinación), así
    que no entra aquí: se compara aparte con ``compare_threshold_baseline``.

    Returns:
        ``... , tratamiento_a, tratamiento_b, n_pairs, statistic, p_value,
        p_holm, significant``.
    """
    raise NotImplementedError


def compare_threshold_baseline(runs: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Comparación descriptiva del detector ``umbral`` entre tratamientos.

    Al ser determinista no hay varianza entre semillas: se reporta el valor de
    cada tratamiento y su diferencia contra ``original``, sin prueba de hipótesis.
    """
    raise NotImplementedError
