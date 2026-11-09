"""Etiquetado de unidades de análisis a partir de las etiquetas por evento (D2)."""

import pandas as pd


def label_units(units: pd.DataFrame, event_labels: pd.DataFrame, rule: str,
                min_fraction: float | None = None) -> pd.Series:
    """Devuelve la etiqueta real (1 = ataque) de cada unidad.

    Usa solo ``event_id → is_attack`` (nunca IP/usuario), así que la etiqueta es la
    misma en todas las versiones anonimizadas.

    Args:
        units: unidades con la columna ``event_ids`` (``event_id`` separados por ``;``).
        event_labels: tabla con ``event_id`` e ``is_attack``.
        rule: ``any`` (basta un evento de ataque) o ``fraction`` (fracción ≥ ``min_fraction``).
        min_fraction: umbral cuando ``rule == "fraction"``.

    Returns:
        Serie de 0/1 alineada con el índice de ``units``.
    """
    is_attack = event_labels.set_index("event_id")["is_attack"].to_dict()

    def label_one(event_ids: str) -> int:
        ids = [e for e in str(event_ids).split(";") if e]
        if not ids:
            return 0
        flags = [int(is_attack.get(e, 0)) for e in ids]
        if rule == "any":
            return int(any(flags))
        if rule == "fraction":
            if min_fraction is None:
                raise ValueError("La regla 'fraction' requiere min_fraction.")
            return int((sum(flags) / len(flags)) >= min_fraction)
        raise ValueError(f"Regla de etiquetado desconocida: {rule!r}")

    return units["event_ids"].map(label_one).astype(int)
