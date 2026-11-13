"""SSIF: Isolation Forest semisupervisado, variante (a) (decisión D5).

Variante implementada (``if_entrenado_en_normales``): el mismo Isolation Forest,
pero entrenado solo con las unidades etiquetadas como normales dentro de la parte
de entrenamiento temporal. Así el bosque aprende únicamente el comportamiento
normal y los ataques quedan más aislados.

Trabajo futuro (opción b, ``ssif_literatura``): un SSIF publicado que usa las
etiquetas al construir los árboles. Si se hace, irá como un detector nuevo en el
registro, sin reemplazar este.

Como necesita etiquetas, no aplica a datasets sin Ground Truth (Loghub): el runner
debe omitir esos runs.
"""

import numpy as np

from anonlogs.detection.isolation_forest import IsolationForestDetector


class SSIFDetector(IsolationForestDetector):
    """Isolation Forest entrenado solo con las unidades normales; score y predict se heredan."""

    uses_labels = True

    def fit(self, X, y=None):
        """Entrena con las filas donde ``y == 0``.

        Raises:
            ValueError: si no se pasan etiquetas o si no hay ninguna unidad normal.
        """
        if y is None:
            raise ValueError("SSIF necesita etiquetas de entrenamiento (y); no aplica a datasets sin Ground Truth.")
        normal = np.asarray(y) == 0
        if not normal.any():
            raise ValueError("sin unidades normales en entrenamiento")
        # iloc filtra por posición: no depende de que el índice del DataFrame coincida con y.
        X_normal = X.iloc[normal] if hasattr(X, "iloc") else X[normal]
        self.model_ = self._new_model().fit(X_normal)
        self.n_train_normal_ = int(normal.sum())
        return self
