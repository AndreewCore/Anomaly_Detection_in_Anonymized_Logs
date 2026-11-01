"""Construcción de features por ventana de tiempo.

La unidad de análisis (qué representa cada fila) está pendiente: decisión D1 en
``docs/diseno_experimento.md``. Las firmas ya reciben ``unit`` para no tener que
cambiarlas cuando se decida.
"""

import pandas as pd

# Reglas disponibles. Agregar una regla = una función nueva + su nombre aquí.
RULES = ("fallos_por_ip", "fallos_por_usuario", "usuarios_unicos_por_ip", "fallos_por_ventana")


def assign_windows(events: pd.DataFrame, window_seconds: int) -> pd.DataFrame:
    """Agrega la columna ``window_id`` (ventanas fijas sin solapamiento) a cada evento."""
    raise NotImplementedError


def build_features(events: pd.DataFrame, features: list[str], window_seconds: int,
                   unit: str) -> pd.DataFrame:
    """Calcula las features pedidas para cada unidad de análisis.

    Args:
        events: tabla de eventos (ya anonimizada).
        features: subconjunto de ``RULES`` (un ``rule_set`` de la matriz).
        window_seconds: tamaño de ventana.
        unit: ventana | ventana_ip | ventana_usuario (decisión D1).

    Returns:
        Una fila por unidad con ``unit_id``, ``window_start`` y una columna por
        feature. Las entidades se toman tal como quedaron tras anonimizar: si el
        tratamiento fusiona IPs (supresión, /24), las features lo reflejan, y eso
        es justamente lo que se mide.
    """
    raise NotImplementedError
