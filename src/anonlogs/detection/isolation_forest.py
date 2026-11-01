"""Isolation Forest de scikit-learn (método principal, no supervisado)."""

from anonlogs.detection.base import Detector


class IsolationForestDetector(Detector):
    """Envuelve ``sklearn.ensemble.IsolationForest``.

    Hiperparámetros (``experiment.yaml``): ``n_estimators``, ``max_samples``,
    ``contamination``. La semilla del run va a ``random_state``. El score es
    ``-score_samples`` para respetar "más alto = más anómalo".
    """

    def fit(self, X, y=None):
        """Entrena sin etiquetas; ``y`` se ignora."""
        raise NotImplementedError

    def score(self, X):
        """Devuelve ``-score_samples(X)``."""
        raise NotImplementedError

    def predict(self, X):
        """Convierte la salida de sklearn (-1/1) a 1/0."""
        raise NotImplementedError
