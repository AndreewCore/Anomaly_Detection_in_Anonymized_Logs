"""Registro de detectores: nombre en la matriz → clase.

Para agregar un detector: crea su módulo implementando ``Detector`` y añade una
línea a ``REGISTRY``. El resto del pipeline no cambia.
"""

from anonlogs.detection.base import Detector
from anonlogs.detection.isolation_forest import IsolationForestDetector
from anonlogs.detection.ssif import SSIFDetector
from anonlogs.detection.threshold import ThresholdDetector
from anonlogs.detection.threshold_calibrated import CalibratedThresholdDetector

REGISTRY: dict[str, type[Detector]] = {
    "isolation_forest": IsolationForestDetector,
    "ssif": SSIFDetector,
    "umbral": ThresholdDetector,
    "umbral_calibrado": CalibratedThresholdDetector,
}


def make_detector(name: str, params: dict, seed: int | None) -> Detector:
    """Instancia el detector ``name`` con sus hiperparámetros y la semilla del run."""
    try:
        cls = REGISTRY[name]
    except KeyError:
        raise ValueError(f"Detector desconocido: {name!r}. Disponibles: {sorted(REGISTRY)}") from None
    return cls(params, seed)
