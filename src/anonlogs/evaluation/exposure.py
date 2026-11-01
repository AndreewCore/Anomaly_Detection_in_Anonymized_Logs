"""Exposición residual: cuánto de la identidad original sobrevive a la anonimización."""

import pandas as pd


def residual_exposure(original: pd.DataFrame, anonymized: pd.DataFrame) -> dict:
    """Porcentaje de usuarios e IPs originales que siguen apareciendo literalmente.

    Busca cada valor original distinto en las columnas **y** en ``message`` de la
    versión anonimizada (emparejando por ``event_id``).

    Returns:
        ``exposure_users_pct, exposure_ips_pct`` (0–100).
    """
    raise NotImplementedError
