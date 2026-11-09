"""Exposición residual: cuánto de la identidad original sobrevive a la anonimización."""

import pandas as pd


def _literal_hits(originals: set[str], anon: pd.DataFrame, columns: list[str]) -> int:
    """Cuenta cuántos valores originales aparecen literalmente en la versión anonimizada.

    Busca en las columnas indicadas y en ``message``, como subcadena, porque un
    valor puede quedar embebido en el texto libre aunque la columna se haya tratado.
    """
    if not originals:
        return 0
    # fillna antes de convertir: un NaN en columna/mensaje rompería el join.
    blob = anon[columns + ["message"]].fillna("").astype(str)
    joined = " ".join(blob.values.ravel().tolist())
    return sum(1 for v in originals if v and v in joined)


def residual_exposure(original: pd.DataFrame, anonymized: pd.DataFrame) -> dict:
    """Porcentaje de usuarios e IPs originales que siguen apareciendo literalmente.

    Un 0 % significa que ningún identificador original quedó en la versión
    anonimizada (ni en columnas ni en texto libre); un 100 %, que todos siguen ahí
    (por ejemplo, el campo que no se trató).

    Returns:
        ``exposure_users_pct``, ``exposure_ips_pct`` (0–100) y los conteos crudos.
    """
    users = {str(u) for u in original["user"].dropna().unique()}
    ips = {str(i) for i in original["src_ip"].dropna().unique()}

    u_hits = _literal_hits(users, anonymized, ["user", "src_ip"])
    i_hits = _literal_hits(ips, anonymized, ["user", "src_ip"])

    return {
        "exposure_users_pct": round(100.0 * u_hits / len(users), 2) if users else 0.0,
        "exposure_ips_pct": round(100.0 * i_hits / len(ips), 2) if ips else 0.0,
        "n_users": len(users), "n_ips": len(ips),
        "users_expuestos": u_hits, "ips_expuestas": i_hits,
    }
