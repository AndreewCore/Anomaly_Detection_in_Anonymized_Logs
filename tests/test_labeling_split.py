"""Pruebas del etiquetado de unidades (D2) y de la partición temporal (D4)."""

import pandas as pd
import pytest

from anonlogs.labeling import label_units
from anonlogs.splitting import NoAttacksInTestError, temporal_split


def _units():
    return pd.DataFrame({
        "unit_id": ["u0", "u1", "u2"],
        "event_ids": ["e0;e1", "e2;e3;e4", "e5"],
        "window_start": pd.to_datetime(
            ["2026-11-09T14:00:00Z", "2026-11-09T14:10:00Z", "2026-11-09T14:20:00Z"]),
    })


def _labels():
    # e0 ataque; e2 ataque pero e3/e4 normales (1 de 3); e5 normal.
    return pd.DataFrame({"event_id": [f"e{i}" for i in range(6)],
                         "is_attack": [1, 0, 1, 0, 0, 0]})


def test_etiqueta_any():
    """any: basta un evento de ataque en la unidad."""
    y = label_units(_units(), _labels(), rule="any")
    assert list(y) == [1, 1, 0]


def test_etiqueta_fraction():
    """fraction 0.5: u1 tiene 1/3 de ataque, no llega al umbral."""
    y = label_units(_units(), _labels(), rule="fraction", min_fraction=0.5)
    assert list(y) == [1, 0, 0]


def test_split_temporal_respeta_orden():
    """El 60% temporal entrena; el resto evalúa (sin verificar el mínimo, labels=None)."""
    u = _units()
    train, test = temporal_split(u, None, train_fraction=0.6)
    assert list(train) == [0, 1] and list(test) == [2]


def test_split_falla_sin_ataques_en_prueba():
    """Si la prueba queda sin ataques, falla con un error claro (decisión D4)."""
    u = _units()
    y = pd.Series([1, 0, 0])  # el único ataque cae en entrenamiento
    with pytest.raises(NoAttacksInTestError):
        temporal_split(u, y, train_fraction=0.6, min_attack_units_in_test=1)
