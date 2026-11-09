"""Detector baseline por reglas de umbral (determinista, sin semilla)."""

import numpy as np

from anonlogs.detection.base import Detector


class ThresholdDetector(Detector):
    """Marca una unidad como anómala si alguna feature activa supera su umbral.

    Los umbrales vienen de ``experiment.yaml → detectors.umbral`` (criterio experto
    del equipo). El score continuo es el máximo de ``feature / umbral``, para poder
    calcular ROC-AUC y PR-AUC igual que en los demás detectores.
    """

    def fit(self, X, y=None):
        """No aprende: los umbrales son fijos. Valida que exista uno por feature."""
        faltan = [c for c in X.columns if c not in self.params]
        if faltan:
            raise ValueError(f"Faltan umbrales en detectors.umbral para: {faltan}")
        # Vector de umbrales alineado con las columnas de X (orden del rule_set).
        self.thresholds_ = np.array([self.params[c] for c in X.columns], dtype=float)
        self.columns_ = list(X.columns)
        return self

    def score(self, X) -> np.ndarray:
        """Máximo de ``feature / umbral`` por fila (más alto = más anómalo)."""
        ratios = X[self.columns_].to_numpy(dtype=float) / self.thresholds_
        return ratios.max(axis=1)

    def predict(self, X) -> np.ndarray:
        """1 si el score es ≥ 1 (alguna feature alcanzó o pasó su umbral)."""
        return (self.score(X) >= 1.0).astype(int)
