"""Construcción de features por ventana de tiempo, según la unidad de análisis (D1).

Cada regla se define de forma distinta según la unidad (ver la tabla en
``docs/diseno_experimento.md`` §3). Las features se calculan sobre las entidades
tal como quedaron tras anonimizar: si el tratamiento fusiona IPs (supresión, /24),
las features lo reflejan, y eso es justo lo que se mide.
"""

import numpy as np
import pandas as pd

# Reglas disponibles. Agregar una regla = una función nueva + su nombre aquí.
RULES = ("fallos_por_ip", "fallos_por_usuario", "usuarios_unicos_por_ip", "fallos_por_ventana")

# Tipos de evento que cuentan como intento fallido.
_FAIL_TYPES = {"failed_password", "invalid_user"}


def assign_windows(events: pd.DataFrame, window_seconds: int) -> pd.DataFrame:
    """Agrega ``window_id`` y ``window_start`` (ventanas fijas sin solapamiento).

    Usa la línea de tiempo virtual (``timestamp``), así los segmentos de una
    captura caen en una sola rejilla de ventanas continua.
    """
    out = events.copy()
    ts = pd.to_datetime(out["timestamp"], utc=True)
    t0 = ts.min()
    out["window_id"] = ((ts - t0).dt.total_seconds() // window_seconds).astype(int)
    out["window_start"] = t0 + pd.to_timedelta(out["window_id"] * window_seconds, unit="s")
    return out


def _per_window_tables(ev: pd.DataFrame) -> dict:
    """Precalcula, por ventana, los conteos de fallos por IP, por usuario y totales."""
    fails = ev[ev["event_type"].isin(_FAIL_TYPES)]
    fipc = fails.groupby(["window_id", "src_ip"]).size()                       # fallos por (ventana, ip)
    fupc = fails.groupby(["window_id", "user"]).size()                         # fallos por (ventana, usuario)
    uuip = fails.groupby(["window_id", "src_ip"])["user"].nunique()           # usuarios únicos por (ventana, ip)
    total = fails.groupby("window_id").size()                                  # fallos por ventana
    # Qué usuarios tocó cada ip y qué ips tocaron a cada usuario (para los máximos cruzados).
    users_de_ip = fails.groupby(["window_id", "src_ip"])["user"].apply(set)
    ips_de_user = fails.groupby(["window_id", "user"])["src_ip"].apply(set)
    return {"fipc": fipc, "fupc": fupc, "uuip": uuip, "total": total,
            "users_de_ip": users_de_ip, "ips_de_user": ips_de_user}


def _max_or_zero(values) -> int:
    """Máximo de un iterable, o 0 si está vacío (ventana sin fallos de esa entidad)."""
    values = list(values)
    return int(max(values)) if values else 0


def build_features(events: pd.DataFrame, features: list[str], window_seconds: int,
                   unit: str) -> pd.DataFrame:
    """Calcula las features pedidas para cada unidad de análisis.

    Returns:
        Una fila por unidad con ``unit_id``, ``window_start``, ``event_ids`` (los
        ``event_id`` que contiene, para etiquetar) y una columna por feature.
    """
    ev = assign_windows(events, window_seconds)
    t = _per_window_tables(ev)

    # Entidad que define la fila según la unidad; para ip/usuario se descartan los
    # eventos sin esa entidad (no se pueden atribuir a una fila).
    if unit == "ventana":
        groups = ev.groupby("window_id")
        keys = [(w,) for w in groups.groups]
    elif unit == "ventana_ip":
        sub = ev[ev["src_ip"].notna()]
        groups = sub.groupby(["window_id", "src_ip"])
        keys = list(groups.groups)
    elif unit == "ventana_usuario":
        sub = ev[ev["user"].notna()]
        groups = sub.groupby(["window_id", "user"])
        keys = list(groups.groups)
    else:
        raise ValueError(f"Unidad desconocida: {unit!r}")

    rows = []
    for key in keys:
        g = groups.get_group(key if len(key) > 1 else key[0])
        w = g["window_id"].iloc[0]
        total_w = int(t["total"].get(w, 0))

        if unit == "ventana":
            ips = t["fipc"].loc[w] if w in t["fipc"].index.get_level_values(0) else pd.Series(dtype=int)
            usrs = t["fupc"].loc[w] if w in t["fupc"].index.get_level_values(0) else pd.Series(dtype=int)
            uus = t["uuip"].loc[w] if w in t["uuip"].index.get_level_values(0) else pd.Series(dtype=int)
            row = {"fallos_por_ip": _max_or_zero(ips), "fallos_por_usuario": _max_or_zero(usrs),
                   "usuarios_unicos_por_ip": _max_or_zero(uus), "fallos_por_ventana": total_w}
            unit_id = f"{w}"
        elif unit == "ventana_ip":
            ip = key[1]
            users_tocados = t["users_de_ip"].get((w, ip), set())
            row = {
                "fallos_por_ip": int(t["fipc"].get((w, ip), 0)),
                "fallos_por_usuario": _max_or_zero(t["fupc"].get((w, u), 0) for u in users_tocados),
                "usuarios_unicos_por_ip": int(t["uuip"].get((w, ip), 0)),
                "fallos_por_ventana": total_w,
            }
            unit_id = f"{w}|ip={ip}"
        else:  # ventana_usuario
            user = key[1]
            ips_tocadas = t["ips_de_user"].get((w, user), set())
            row = {
                "fallos_por_ip": _max_or_zero(t["fipc"].get((w, ip), 0) for ip in ips_tocadas),
                "fallos_por_usuario": int(t["fupc"].get((w, user), 0)),
                "usuarios_unicos_por_ip": _max_or_zero(t["uuip"].get((w, ip), 0) for ip in ips_tocadas),
                "fallos_por_ventana": total_w,
            }
            unit_id = f"{w}|user={user}"

        row = {k: row[k] for k in features}  # solo las features del rule_set
        row["unit_id"] = unit_id
        row["window_start"] = g["window_start"].iloc[0]
        row["event_ids"] = ";".join(g["event_id"].tolist())
        rows.append(row)

    cols = ["unit_id", "window_start", "event_ids"] + list(features)
    return pd.DataFrame(rows, columns=cols).sort_values("window_start").reset_index(drop=True)
