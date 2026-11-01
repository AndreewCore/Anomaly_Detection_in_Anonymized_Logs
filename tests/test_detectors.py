"""Pruebas de los detectores Isolation Forest y SSIF con datos sintéticos."""

import numpy as np
import pandas as pd
import pytest

from anonlogs.detection import make_detector
from anonlogs.detection.isolation_forest import IsolationForestDetector
from anonlogs.detection.ssif import SSIFDetector

PARAMS = {"n_estimators": 100, "max_samples": "auto", "contamination": "auto"}


def _data(seed: int = 0) -> tuple[pd.DataFrame, np.ndarray]:
    """200 filas normales alrededor de 0 y 10 outliers lejanos (etiqueta 1)."""
    rng = np.random.default_rng(seed)
    normal = rng.normal(0, 1, size=(200, 3))
    outliers = rng.normal(8, 1, size=(10, 3))
    X = pd.DataFrame(np.vstack([normal, outliers]), columns=["a", "b", "c"])
    y = np.array([0] * 200 + [1] * 10)
    return X, y


@pytest.mark.parametrize("name", ["isolation_forest", "ssif"])
def test_outliers_score_higher(name):
    """Los outliers reciben un score mayor que las filas normales (convención común)."""
    X, y = _data()
    det = make_detector(name, PARAMS, seed=0).fit(X, y)
    s = det.score(X)
    assert s[y == 1].mean() > s[y == 0].mean()


@pytest.mark.parametrize("name", ["isolation_forest", "ssif"])
def test_predict_is_binary(name):
    """predict devuelve solo 0 y 1."""
    X, y = _data()
    pred = make_detector(name, PARAMS, seed=0).fit(X, y).predict(X)
    assert set(np.unique(pred)) <= {0, 1}


def test_same_seed_same_scores():
    """Misma semilla → mismos scores (reproducibilidad de cada run)."""
    X, _ = _data()
    a = IsolationForestDetector(PARAMS, seed=7).fit(X).score(X)
    b = IsolationForestDetector(PARAMS, seed=7).fit(X).score(X)
    np.testing.assert_array_equal(a, b)


def test_ssif_requires_labels():
    """SSIF sin etiquetas falla con un mensaje claro."""
    X, _ = _data()
    with pytest.raises(ValueError):
        SSIFDetector(PARAMS, seed=0).fit(X)


def test_ssif_requires_some_normal_units():
    """Si todo el entrenamiento es ataque, SSIF no puede aprender lo normal."""
    X, _ = _data()
    with pytest.raises(ValueError):
        SSIFDetector(PARAMS, seed=0).fit(X, np.ones(len(X), dtype=int))


def test_ssif_trains_only_on_normals():
    """SSIF entrena con las 200 filas normales, aunque el índice del DataFrame no empiece en 0."""
    X, y = _data()
    X.index = X.index + 1000
    det = SSIFDetector(PARAMS, seed=0).fit(X, y)
    assert det.n_train_normal_ == 200
    assert det.model_.n_features_in_ == 3


def test_uses_labels_flags():
    """El runner decide si pasar etiquetas según uses_labels."""
    assert IsolationForestDetector.uses_labels is False
    assert SSIFDetector.uses_labels is True
