"""Métricas de detección de cada run, calculadas solo sobre la parte de prueba."""

import numpy as np
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             precision_recall_fscore_support, roc_auc_score)


def detection_metrics(y_true: np.ndarray | None, y_pred: np.ndarray,
                      scores: np.ndarray) -> dict:
    """Calcula las métricas de detección de un run.

    Args:
        y_true: etiquetas reales; ``None`` si el dataset no tiene Ground Truth.
        y_pred: predicción binaria del detector.
        scores: score continuo (más alto = más anómalo).

    Returns:
        ``precision, recall, f1, fpr, tp, fp, tn, fn, roc_auc, pr_auc``.
        Sin etiquetas, las de detección valen ``NaN`` y se marca
        ``labels_available: False``, para no confundirlas con ceros.
    """
    if y_true is None:
        return {k: float("nan") for k in
                ("precision", "recall", "f1", "fpr", "roc_auc", "pr_auc")} | {
                "tp": 0, "fp": 0, "tn": 0, "fn": 0, "labels_available": False}

    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0)
    # labels=[0,1] fuerza la matriz 2x2 aunque falte una clase en la predicción.
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    # Las AUC necesitan ambas clases presentes en y_true; si no, quedan NaN.
    both = len(np.unique(y_true)) == 2
    roc = float(roc_auc_score(y_true, scores)) if both else float("nan")
    pr = float(average_precision_score(y_true, scores)) if both else float("nan")

    return {"precision": float(p), "recall": float(r), "f1": float(f1), "fpr": float(fpr),
            "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
            "roc_auc": roc, "pr_auc": pr, "labels_available": True}
