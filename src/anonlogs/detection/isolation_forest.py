"""Isolation Forest de scikit-learn (método principal, no supervisado)."""

import numpy as np
from sklearn.ensemble import IsolationForest

from anonlogs.detection.base import Detector


class IsolationForestDetector(Detector):
    """Envuelve ``sklearn.ensemble.IsolationForest``.

    Hiperparámetros (``experiment.yaml → detectors.isolation_forest``):
    ``n_estimators``, ``max_samples`` y ``contamination``. La semilla del run va a
    ``random_state``, para que cada run sea reproducible.
    """

    def _new_model(self) -> IsolationForest:
        """Crea un IsolationForest sin entrenar con los hiperparámetros del run."""
        return IsolationForest(
            n_estimators=self.params.get("n_estimators", 100),
            max_samples=self.params.get("max_samples", "auto"),
            contamination=self.params.get("contamination", "auto"),
            random_state=self.seed,
        )

    def fit(self, X, y=None):
        """Entrena sin etiquetas; ``y`` se ignora."""
        self.model_ = self._new_model().fit(X)
        return self

    def score(self, X) -> np.ndarray:
        """Score de anomalía: más alto = más anómalo.

        sklearn devuelve lo contrario (``score_samples`` más bajo = más anómalo);
        se invierte el signo para que todos los detectores sigan la misma convención.
        """
        return -self.model_.score_samples(X)

    def predict(self, X) -> np.ndarray:
        """1 si sklearn marca la fila como anómala (-1), 0 si es normal."""
        return (self.model_.predict(X) == -1).astype(int)
