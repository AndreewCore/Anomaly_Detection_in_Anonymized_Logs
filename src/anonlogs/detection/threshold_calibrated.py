"""Umbral calibrado: el umbral de cada feature sale de los normales de entrenamiento."""

import numpy as np

from anonlogs.detection.threshold import ThresholdDetector


class CalibratedThresholdDetector(ThresholdDetector):
    """Umbral por regla, pero derivado de los datos en vez de fijado a mano.

    En ``fit`` toma el percentil (``detectors.umbral_calibrado.percentile``, p99 por
    defecto) de cada feature sobre las unidades **normales** de entrenamiento. Así el
    criterio no es arbitrario; el resto (score y predict) se hereda de ``umbral``.
    Como necesita etiquetas, no aplica a datasets sin Ground Truth.
    """

    uses_labels = True

    def fit(self, X, y=None):
        """Calibra un umbral por feature con el percentil de las filas normales."""
        if y is None:
            raise ValueError("umbral_calibrado necesita etiquetas de entrenamiento (y).")
        y = np.asarray(y)
        normal = X.iloc[y == 0] if hasattr(X, "iloc") else X[y == 0]
        if len(normal) == 0:
            raise ValueError("sin unidades normales en entrenamiento")
        pct = self.params.get("percentile", 99)
        # Umbral mínimo de 1: evita dividir por 0 cuando una feature es siempre 0 en normales.
        self.thresholds_ = np.maximum(1.0, np.percentile(normal.to_numpy(dtype=float), pct, axis=0))
        self.columns_ = list(X.columns)
        return self
