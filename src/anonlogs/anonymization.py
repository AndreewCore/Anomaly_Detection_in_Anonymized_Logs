"""Tratamientos de anonimización sobre usuario e IP, en columnas y en el texto libre.

Los tres métodos del estudio: supresión (borra), seudonimización (HMAC con sal) y
generalización de IP a /24. Cada tratamiento transforma las columnas ``user``/
``src_ip`` **y** las apariciones literales en ``message``: si el texto libre no se
trata, la exposición residual sería alta aunque las columnas estén anonimizadas.
"""

import hashlib
import hmac
import ipaddress
import re

import pandas as pd

# Campos que toca cada valor de ``campo``. ip_generalizada solo aplica a ip (D3).
_FIELDS = {"ninguno": (), "usuario": ("user",), "ip": ("src_ip",),
           "ambos": ("user", "src_ip")}


def suppress(value: str, token: str) -> str:
    """Reemplaza el valor por un token fijo; todas las entidades quedan indistinguibles."""
    return token


def pseudonymize(value: str, salt: bytes, digest_chars: int, prefix: str = "") -> str:
    """Seudónimo HMAC-SHA256(salt, valor), truncado a ``digest_chars`` hex.

    Consistente dentro del dataset (mismo valor → mismo seudónimo) e irreversible
    sin la sal. El prefijo (``u_``/``ip_``) ayuda a leer el log anonimizado.
    """
    digest = hmac.new(salt, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{prefix}{digest[:digest_chars]}"


def generalize_ip(ip: str, prefix: int) -> str:
    """Generaliza una IPv4 a su red (``172.28.1.101`` → ``172.28.1.0/24``).

    Las IPv6 y los valores que no son IPv4 se devuelven sin cambios (el llamador
    los registra); generalizarlos no está definido para este estudio.
    """
    try:
        net = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
    except ValueError:
        return ip
    if net.version != 4:
        return ip
    return str(net)


def _build_mapping(values: pd.Series, tratamiento: str, params: dict,
                   salt: bytes | None, prefix: str) -> dict:
    """Construye el diccionario valor_original → valor_anonimizado para un campo."""
    mapping = {}
    for v in values.dropna().unique():
        v = str(v)
        if tratamiento == "suprimida":
            mapping[v] = suppress(v, params["suppression_token"])
        elif tratamiento == "seudonimizada":
            if salt is None:
                raise ValueError("La seudonimización requiere la sal (ANON_SALT).")
            mapping[v] = pseudonymize(v, salt, params["hmac_digest_chars"], prefix)
        elif tratamiento == "ip_generalizada":
            mapping[v] = generalize_ip(v, params["ipv4_prefix"])
        else:
            mapping[v] = v
    return mapping


def _apply_to_message(message: pd.Series, mappings: dict[str, dict]) -> pd.Series:
    """Reemplaza en el texto libre cada valor original por su versión anonimizada.

    Une todos los mapeos (usuarios e IPs) y los reemplaza de más largo a más corto,
    con límites de token, para que ``admin`` no rompa dentro de ``administrator`` ni
    ``172.28.1.1`` dentro de ``172.28.1.10``.
    """
    combined = {}
    for m in mappings.values():
        combined.update(m)
    if not combined:
        return message
    # El orden por longitud evita que un valor corto corte a uno largo que lo contiene.
    keys = sorted(combined, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w.])(" + "|".join(re.escape(k) for k in keys) + r")(?![\w.])")
    return message.map(lambda s: pattern.sub(lambda mt: combined[mt.group(0)], s) if isinstance(s, str) else s)


def apply_treatment(events: pd.DataFrame, tratamiento: str, campo: str, params: dict,
                    salt: bytes | None = None) -> pd.DataFrame:
    """Aplica un par (tratamiento, campo) a la tabla de eventos.

    Args:
        events: tabla de ``parsing`` (debe traer ``user``, ``src_ip``, ``message``).
        tratamiento: original | suprimida | seudonimizada | ip_generalizada.
        campo: ninguno | usuario | ip | ambos (ver ``matrix.VALID_TREATMENTS``).
        params: sección ``anonymization`` de ``experiment.yaml``.
        salt: obligatoria para ``seudonimizada``.

    Returns:
        Copia de ``events`` con los mismos ``event_id`` y orden; solo cambian las
        columnas tratadas y sus apariciones en ``message``.
    """
    out = events.copy()
    if tratamiento == "original" or campo == "ninguno":
        return out

    fields = _FIELDS[campo]
    # ip_generalizada declara el campo "ip" aunque el par venga como "ambos"/"ip".
    if tratamiento == "ip_generalizada":
        fields = ("src_ip",)

    mappings: dict[str, dict] = {}
    for field in fields:
        prefix = "u_" if field == "user" else "ip_"
        mapping = _build_mapping(out[field], tratamiento, params, salt, prefix)
        mappings[field] = mapping
        out[field] = out[field].map(lambda v: mapping.get(str(v), v) if pd.notna(v) else v)

    out["message"] = _apply_to_message(out["message"], mappings)
    return out
