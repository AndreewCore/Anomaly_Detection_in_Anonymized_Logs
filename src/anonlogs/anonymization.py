"""Tratamientos de anonimización sobre usuario e IP, en columnas y en el texto libre."""

import pandas as pd


def suppress(value: str, token: str) -> str:
    """Reemplaza el valor por un token fijo; todas las entidades quedan indistinguibles."""
    raise NotImplementedError


def pseudonymize(value: str, salt: bytes, digest_chars: int) -> str:
    """Seudónimo HMAC-SHA256(salt, valor), truncado a ``digest_chars`` hex.

    Es consistente dentro del dataset (mismo valor → mismo seudónimo) y no es
    reversible sin el salt.
    """
    raise NotImplementedError


def generalize_ip(ip: str, prefix: int) -> str:
    """Generaliza una IPv4 a su red (p. ej. ``/24`` → ``192.168.1.0/24``).

    Las IPv6 y los valores que no son IP se dejan sin cambios y se registran en el log.
    """
    raise NotImplementedError


def apply_treatment(events: pd.DataFrame, tratamiento: str, campo: str, params: dict,
                    salt: bytes | None = None) -> pd.DataFrame:
    """Aplica un par (tratamiento, campo) a la tabla de eventos.

    Transforma las columnas ``user``/``src_ip`` **y** las apariciones literales en
    ``message``; si el texto libre no se trata, la exposición residual sería alta
    aunque las columnas estén anonimizadas.

    Args:
        events: tabla de eventos de ``parsing.parse_auth_log``.
        tratamiento: original | suprimida | seudonimizada | ip_generalizada.
        campo: ninguno | usuario | ip | ambos (ver ``matrix.VALID_TREATMENTS``).
        params: sección ``anonymization`` de ``experiment.yaml``.
        salt: obligatorio para ``seudonimizada``.

    Returns:
        Copia de ``events`` con los mismos ``event_id`` y orden.
    """
    raise NotImplementedError
