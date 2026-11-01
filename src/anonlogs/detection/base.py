"""Interfaz común de los detectores: el pipeline solo conoce estos tres métodos."""

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class Detector(ABC):
    """Detector de anomalías sobre la tabla de features.

    Convención: ``score`` más alto = más anómalo, para que ROC-AUC y PR-AUC se
    calculen igual en todos los detectores.
    """

    #: True si ``fit`` usa etiquetas; el runner entonces le pasa ``y`` solo de la
    #: parte de entrenamiento temporal.
    uses_labels: bool = False

    def __init__(self, params: dict, seed: int | None = None):
        """Guarda los hiperparámetros (de ``experiment.yaml``) y la semilla del run."""
        self.params = params
        self.seed = seed

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "Detector":
        """Ajusta el detector con la parte de entrenamiento y devuelve ``self``."""

    @abstractmethod
    def score(self, X: pd.DataFrame) -> np.ndarray:
        """Devuelve un score continuo de anomalía por fila."""

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Devuelve 1 (anómalo) o 0 (normal) por fila."""
