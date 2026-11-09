"""Pruebas de los dos detectores por umbral: fijo y calibrado."""

import numpy as np
import pandas as pd

from anonlogs.detection import make_detector
from anonlogs.detection.threshold import ThresholdDetector
from anonlogs.detection.threshold_calibrated import CalibratedThresholdDetector


def _X():
    return pd.DataFrame({"fallos_por_ip": [2, 5, 20], "fallos_por_ventana": [5, 10, 60]})


def test_umbral_fijo_predice_por_regla():
    """Con umbral 10, la fila con 20 fallos supera el umbral y es anómala."""
    params = {"fallos_por_ip": 10, "fallos_por_ventana": 30}
    det = ThresholdDetector(params).fit(_X())
    assert list(det.predict(_X())) == [0, 0, 1]
    # El score es monótono con la anomalía.
    s = det.score(_X())
    assert s[2] > s[1] > s[0]


def test_umbral_fijo_exige_umbral_por_feature():
    """Si falta el umbral de una feature, fit avisa."""
    det = ThresholdDetector({"fallos_por_ip": 10})
    try:
        det.fit(_X())
        assert False, "debió fallar por falta de umbral de fallos_por_ventana"
    except ValueError:
        pass


def test_umbral_calibrado_usa_percentil_de_normales():
    """El umbral sale del percentil de las filas normales de entrenamiento."""
    X = pd.DataFrame({"fallos_por_ip": [1, 1, 2, 2, 50]})
    y = np.array([0, 0, 0, 0, 1])  # la última es ataque, no entra al percentil
    det = CalibratedThresholdDetector({"percentile": 99}).fit(X, y)
    # El umbral queda cerca de 2 (máx de los normales), no de 50.
    assert det.thresholds_[0] < 5
    assert det.predict(X)[-1] == 1  # 50 supera el umbral


def test_calibrado_necesita_etiquetas():
    """umbral_calibrado sin etiquetas falla (es semisupervisado)."""
    det = make_detector("umbral_calibrado", {"percentile": 99}, seed=None)
    assert det.uses_labels is True
    try:
        det.fit(_X())
        assert False
    except ValueError:
        pass
