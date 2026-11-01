"""Parseo de logs de autenticación SSH a una tabla de eventos con ``event_id``."""

from pathlib import Path

import pandas as pd

# Columnas de la tabla de eventos que comparten todas las etapas siguientes.
EVENT_COLUMNS = ["event_id", "timestamp", "host", "process", "pid",
                 "event_type", "user", "src_ip", "src_port", "message"]


def parse_auth_log(path: str | Path, dataset: str, year: int | None = None) -> pd.DataFrame:
    """Convierte un ``auth.log`` (lab o Loghub) en la tabla de eventos.

    Acepta el formato RFC 3339 del laboratorio y el formato tradicional
    ``Mmm dd hh:mm:ss`` de Loghub, que no trae año (por eso ``year``).

    Args:
        path: archivo de log crudo.
        dataset: nombre del dataset; forma parte del ``event_id``.
        year: año a asumir cuando el formato no lo incluye.

    Returns:
        DataFrame con ``EVENT_COLUMNS``. ``event_id`` es único y estable
        (``<dataset>:<nº de línea>``), porque las etiquetas se asocian por él
        y no por IP/usuario, que la anonimización altera.
        ``event_type`` ∈ {failed_password, invalid_user, accepted, other}.
    """
    raise NotImplementedError


def load_ground_truth(path: str | Path) -> pd.DataFrame:
    """Lee el CSV de Ground Truth del laboratorio.

    Returns:
        DataFrame con ``scenario, start_ts, end_ts, src_ip, target_users``.
        Es independiente de los logs: se registra al lanzar cada ataque.
    """
    raise NotImplementedError


def link_ground_truth(events: pd.DataFrame, ground_truth: pd.DataFrame) -> pd.DataFrame:
    """Etiqueta cada evento como ataque o normal y devuelve ``event_id, is_attack``.

    Se hace **una sola vez sobre los logs originales**, antes de anonimizar; desde
    ese momento la etiqueta viaja por ``event_id`` a todas las versiones.
    """
    raise NotImplementedError
