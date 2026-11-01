"""SSIF: variante semisupervisada de Isolation Forest (pendiente de elegir).

TODO (decisión D5, ``experiment.yaml → detectors.ssif.variant``):

(a) ``if_entrenado_en_normales``: Isolation Forest entrenado solo con las unidades
    etiquetadas como normales en el Ground Truth, dentro de la parte de
    entrenamiento temporal. Simple y reproducible; usa las etiquetas solo para filtrar.
(b) ``ssif_literatura``: implementar un SSIF publicado que usa etiquetas en la
    construcción de los árboles. Más fiel al término, pero hay que elegir y citar
    el paper (en Mendeley) y validar la implementación.

En ambos casos ``uses_labels = True``: el runner solo le entrega etiquetas de
entrenamiento, y en datasets sin Ground Truth (Loghub) no se ejecuta.
"""

from anonlogs.detection.base import Detector


class SSIFDetector(Detector):
    """Stub con la interfaz común; la variante se elige en la configuración."""

    uses_labels = True

    def fit(self, X, y=None):
        """Entrena con la variante configurada; exige ``y``."""
        raise NotImplementedError

    def score(self, X):
        """Score continuo de anomalía (más alto = más anómalo)."""
        raise NotImplementedError

    def predict(self, X):
        """Predicción binaria 1/0."""
        raise NotImplementedError
