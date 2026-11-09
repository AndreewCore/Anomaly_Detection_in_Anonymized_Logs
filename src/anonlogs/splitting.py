"""Partición entrenamiento/prueba separada por tiempo (evita fuga de información)."""

import pandas as pd


class NoAttacksInTestError(ValueError):
    """La parte de prueba no tiene ataques: recall y F1 quedarían indefinidos."""


def temporal_split(units: pd.DataFrame, labels: pd.Series | None, train_fraction: float,
                   min_attack_units_in_test: int = 1) -> tuple[pd.Index, pd.Index]:
    """Divide las unidades por un corte temporal: lo anterior entrena, lo posterior evalúa.

    El corte se toma sobre ``window_start`` (la línea de tiempo virtual), así que la
    división respeta el orden real de los eventos y no mezcla futuro con pasado.

    Args:
        units: unidades con ``window_start``.
        labels: etiquetas reales; ``None`` en datasets sin Ground Truth (Loghub),
            donde no se verifica el mínimo de ataques.
        train_fraction: fracción del rango temporal usada para entrenar.
        min_attack_units_in_test: mínimo de unidades de ataque exigido en prueba.

    Returns:
        Índices de entrenamiento y de prueba.

    Raises:
        NoAttacksInTestError: si la prueba tiene menos ataques que el mínimo.
    """
    ws = pd.to_datetime(units["window_start"], utc=True)
    t_min, t_max = ws.min(), ws.max()
    cut = t_min + (t_max - t_min) * train_fraction

    train_idx = units.index[ws <= cut]
    test_idx = units.index[ws > cut]

    if labels is not None:
        n_attack_test = int(labels.loc[test_idx].sum())
        if n_attack_test < min_attack_units_in_test:
            n_attack_train = int(labels.loc[train_idx].sum())
            raise NoAttacksInTestError(
                f"La parte de prueba tiene {n_attack_test} unidades de ataque "
                f"(mínimo {min_attack_units_in_test}). Corte={cut.isoformat()}; "
                f"ataques en entrenamiento={n_attack_train}. Reparte el ataque en más "
                f"ráfagas o ajusta train_fraction.")
    return train_idx, test_idx
