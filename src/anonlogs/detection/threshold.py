"""Detector baseline por reglas de umbral (determinista, sin semilla)."""

from anonlogs.detection.base import Detector


class ThresholdDetector(Detector):
    """Marca una unidad como anómala si alguna feature activa supera su umbral.

    Los umbrales vienen de ``experiment.yaml → detectors.umbral``. Como score
    continuo se usa el máximo de ``feature / umbral``, para poder calcular
    ROC-AUC y PR-AUC igual que en los demás detectores.
    """

    def fit(self, X, y=None):
        """No aprende nada: los umbrales son fijos. Solo valida que existan para cada feature."""
        raise NotImplementedError

    def score(self, X):
        """Máximo de ``feature / umbral`` por fila."""
        raise NotImplementedError

    def predict(self, X):
        """1 si el score es >= 1."""
        raise NotImplementedError
