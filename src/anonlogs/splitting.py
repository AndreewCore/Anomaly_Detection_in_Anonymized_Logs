"""Partición entrenamiento/prueba separada por tiempo (evita fuga de información)."""

import pandas as pd


class NoAttacksInTestError(ValueError):
    """La parte de prueba no tiene ataques: recall y F1 quedarían indefinidos."""


def temporal_split(units: pd.DataFrame, labels: pd.Series | None, train_fraction: float,
                   min_attack_units_in_test: int = 1) -> tuple[pd.Index, pd.Index]:
    """Divide las unidades por un corte temporal: todo lo anterior entrena, lo posterior se evalúa.

    Args:
        units: unidades con ``window_start``.
        labels: etiquetas reales; ``None`` en datasets sin Ground Truth (Loghub),
            donde no se verifica el mínimo de ataques.
        train_fraction: fracción del rango temporal usada para entrenar.
        min_attack_units_in_test: mínimo de unidades de ataque exigido en prueba.

    Returns:
        Índices de entrenamiento y de prueba.

    Raises:
        NoAttacksInTestError: si la prueba tiene menos ataques que el mínimo; el
            mensaje indica dataset, corte y dónde quedaron los ataques (decisión D4).
    """
    raise NotImplementedError
