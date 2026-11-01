"""Métricas de detección de cada run, calculadas solo sobre la parte de prueba."""

import numpy as np


def detection_metrics(y_true: np.ndarray | None, y_pred: np.ndarray,
                      scores: np.ndarray) -> dict:
    """Calcula las métricas de detección de un run.

    Args:
        y_true: etiquetas reales; ``None`` si el dataset no tiene Ground Truth.
        y_pred: predicción binaria del detector.
        scores: score continuo (más alto = más anómalo).

    Returns:
        ``precision, recall, f1, fpr, tp, fp, tn, fn, roc_auc, pr_auc``.
        Sin etiquetas, todas valen ``NaN`` y se agrega ``labels_available: False``,
        para que el reporte no las confunda con ceros.
    """
    raise NotImplementedError
