"""Parseo de logs de autenticación SSH a una tabla de eventos con ``event_id``.

Acepta el formato RFC 3339 del laboratorio y el tradicional ``Mmm dd hh:mm:ss``
de Loghub. Los segmentos de una captura se concatenan en una *línea de tiempo
virtual* (``timestamp``), conservando el tiempo real (``timestamp_real``), para
que ventanas y partición temporal traten los segmentos como una sola corrida.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# Columnas de la tabla de eventos que comparten todas las etapas siguientes.
# ``timestamp`` es la línea virtual; ``timestamp_real`` es el reloj de pared, que
# es contra el que se alinea el Ground Truth (sus marcas son reales).
EVENT_COLUMNS = ["event_id", "timestamp", "timestamp_real", "segment", "host",
                 "process", "pid", "event_type", "user", "src_ip", "src_port", "message"]

# Separación virtual entre segmentos: evita que el último evento de uno y el
# primero del siguiente caigan en la misma ventana de tiempo.
_SEGMENT_GAP = timedelta(seconds=1)

# Cabecera de syslog. El proceso puede traer pid entre corchetes (sshd[1234]) y
# un guion: OpenSSH >= 9.8 registra la autenticación como ``sshd-session``.
_RE_RFC3339 = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\S+)\s+(?P<host>\S+)\s+"
    r"(?P<proc>[\w-]+)(?:\[(?P<pid>\d+)\])?:\s+(?P<msg>.*)$")
_RE_TRADITIONAL = re.compile(
    r"^(?P<ts>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+"
    r"(?P<proc>[\w-]+)(?:\[(?P<pid>\d+)\])?:\s+(?P<msg>.*)$")

# Extrae usuario/IP/puerto del texto del mensaje de sshd. ``invalid user`` es
# opcional para cubrir tanto cuentas reales como inexistentes.
_RE_CREDS = re.compile(
    r"(?:invalid user |user )?(?P<user>\S+) from (?P<ip>\d+\.\d+\.\d+\.\d+)"
    r"(?: port (?P<port>\d+))?")


def _classify(msg: str) -> str:
    """Devuelve el ``event_type`` según el texto del mensaje de sshd."""
    if "Failed password for invalid user" in msg or msg.startswith("Invalid user"):
        return "invalid_user"
    if msg.startswith("Failed password"):
        return "failed_password"
    if msg.startswith("Accepted password") or msg.startswith("Accepted publickey"):
        return "accepted"
    return "other"


def _parse_ts(raw: str, year: int | None) -> datetime | None:
    """Parsea la marca de tiempo en cualquiera de los dos formatos, en UTC.

    El formato tradicional no trae año; se usa ``year`` (o el actual) y se asume
    UTC, coherente con el ``SyslogFacility``/``TZ=UTC`` de la víctima.
    """
    try:
        if "T" in raw:
            dt = datetime.fromisoformat(raw)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        y = year or datetime.now(timezone.utc).year
        dt = datetime.strptime(f"{y} {raw}", "%Y %b %d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_auth_log(path: str | Path, dataset: str, year: int | None = None,
                   segment: int = 0) -> pd.DataFrame:
    """Convierte un ``auth.log`` (lab o Loghub) en la tabla de eventos de un segmento.

    ``event_id`` es ``<dataset>:seg<segment>:<nº de línea>``: único y estable, y
    las etiquetas se asocian por él (no por IP/usuario, que la anonimización altera).
    En esta etapa ``timestamp`` es aún el tiempo real; la línea virtual se arma al
    concatenar segmentos con :func:`build_virtual_timeline`.
    """
    rows = []
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8", errors="replace").splitlines()):
        m = _RE_RFC3339.match(line) or _RE_TRADITIONAL.match(line)
        if not m:
            continue
        ts = _parse_ts(m["ts"], year)
        if ts is None:
            continue
        msg = m["msg"]
        etype = _classify(msg)
        user = ip = port = None
        if etype in ("failed_password", "invalid_user", "accepted"):
            cm = _RE_CREDS.search(msg)
            if cm:
                user, ip, port = cm["user"], cm["ip"], cm["port"]
        rows.append({
            "event_id": f"{dataset}:seg{segment}:{lineno}",
            "timestamp": ts, "timestamp_real": ts, "segment": segment,
            "host": m["host"], "process": m["proc"],
            "pid": int(m["pid"]) if m["pid"] else None,
            "event_type": etype, "user": user, "src_ip": ip,
            "src_port": int(port) if port else None, "message": msg,
        })
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)


def build_virtual_timeline(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatena segmentos ordenados en una sola línea de tiempo virtual.

    Cada segmento arranca justo después de donde terminó el anterior (más un
    hueco fijo), preservando las distancias internas. Así las features por ventana
    y la partición temporal tratan los segmentos como una corrida continua, sin
    inventar actividad en los huecos reales entre capturas.
    """
    frames = [f for f in sorted(frames, key=lambda d: int(d["segment"].iloc[0])) if not f.empty]
    if not frames:
        return pd.DataFrame(columns=EVENT_COLUMNS)
    cursor = frames[0]["timestamp_real"].min()
    out = []
    for f in frames:
        f = f.copy()
        seg_start = f["timestamp_real"].min()
        f["timestamp"] = cursor + (f["timestamp_real"] - seg_start)
        out.append(f)
        cursor = f["timestamp"].max() + _SEGMENT_GAP
    events = pd.concat(out, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    return events


def load_ground_truth(path: str | Path) -> pd.DataFrame:
    """Lee el CSV de Ground Truth del laboratorio (el que escribe ``anomalia.c``).

    Columnas: ``scenario, segment, burst_id, attacker, src_ip, user, ts_start, ts_end``.
    Es independiente de los logs: se registra al lanzar cada intento.
    """
    gt = pd.read_csv(path)
    for col in ("ts_start", "ts_end"):
        gt[col] = pd.to_datetime(gt[col], utc=True)
    return gt


def link_ground_truth(events: pd.DataFrame, ground_truth: pd.DataFrame,
                      slack_before: float = 1.0, slack_after: float = 2.0) -> pd.DataFrame:
    """Etiqueta cada evento como ataque (1) o normal (0) y devuelve ``event_id, is_attack, fuente``.

    Un evento es ataque si su ``src_ip`` coincide con el de una fila de GT y su
    ``timestamp_real`` cae en ``[ts_start - slack_before, ts_end + slack_after]``.
    Luego la marca se propaga a todas las líneas de la misma conexión sshd (mismo
    ``host``+``pid``), para cubrir el par ``Invalid user``/``Failed password`` y el
    cierre de conexión, que no siempre traen IP. Se hace **una sola vez sobre los
    logs originales**; desde ahí la etiqueta viaja por ``event_id``.
    """
    labels = pd.DataFrame({"event_id": events["event_id"], "is_attack": 0})
    labels["fuente"] = "auto"
    if ground_truth.empty:
        return labels

    is_attack = pd.Series(False, index=events.index)
    # Comparación vectorizada por IP: para cada IP atacante, marca los eventos de
    # esa IP cuya hora cae en alguna de sus ventanas de intento.
    tr = events["timestamp_real"]
    for ip, g in ground_truth.groupby("src_ip"):
        same_ip = events["src_ip"] == ip
        if not same_ip.any():
            continue
        starts = g["ts_start"] - pd.Timedelta(seconds=slack_before)
        ends = g["ts_end"] + pd.Timedelta(seconds=slack_after)
        in_window = pd.Series(False, index=events.index)
        for s, e in zip(starts, ends):
            in_window |= same_ip & (tr >= s) & (tr <= e)
        is_attack |= in_window

    # Propagación por conexión: misma (host, pid) que un evento ya marcado.
    attacked_conns = set(
        map(tuple, events.loc[is_attack & events["pid"].notna(), ["host", "pid"]].values))
    if attacked_conns:
        conn = list(zip(events["host"], events["pid"]))
        is_attack |= pd.Series([c in attacked_conns for c in conn], index=events.index)

    labels["is_attack"] = is_attack.astype(int).values
    return labels


def apply_revisions(labels: pd.DataFrame, revisions: pd.DataFrame) -> pd.DataFrame:
    """Aplica las correcciones humanas del GT encima de las etiquetas automáticas.

    ``revisions`` trae ``event_id, is_attack`` (y opcionalmente ``motivo, revisor,
    fecha``). Cada fila sobrescribe la etiqueta de su evento y marca ``fuente =
    revision``, para poder auditar cuántas etiquetas tocó una persona.
    """
    if revisions is None or revisions.empty:
        return labels
    out = labels.set_index("event_id")
    rev = revisions.set_index("event_id")
    common = out.index.intersection(rev.index)
    out.loc[common, "is_attack"] = rev.loc[common, "is_attack"].astype(int)
    out.loc[common, "fuente"] = "revision"
    return out.reset_index()


def find_dudosos(events: pd.DataFrame, labels: pd.DataFrame,
                 ground_truth: pd.DataFrame) -> pd.DataFrame:
    """Lista los eventos que una persona debería revisar en el Ground Truth.

    Son los casos donde la etiqueta automática puede equivocarse:
    fallos desde IPs de atacantes fuera de una ráfaga, logins **aceptados** desde
    IPs de atacantes, y fallos desde IPs legítimas (típicamente errores de tipeo).
    El revisor decide cada uno en ``<dataset>_revisiones.csv``.
    """
    attacker_ips = set(ground_truth["src_ip"]) if not ground_truth.empty else set()
    lab = labels.set_index("event_id")["is_attack"]
    ev = events.set_index("event_id")

    razones = []
    for eid, row in ev.iterrows():
        is_atk = int(lab.get(eid, 0))
        ip, etype = row["src_ip"], row["event_type"]
        motivo = None
        if ip in attacker_ips and etype == "accepted":
            motivo = "login aceptado desde IP de atacante"
        elif ip in attacker_ips and is_atk == 0 and etype in ("failed_password", "invalid_user"):
            motivo = "fallo de IP atacante fuera de ráfaga"
        elif ip not in attacker_ips and etype == "failed_password":
            motivo = "fallo desde IP legítima (posible error de tipeo)"
        if motivo:
            razones.append({"event_id": eid, "timestamp_real": row["timestamp_real"],
                            "src_ip": ip, "user": row["user"], "event_type": etype,
                            "is_attack_auto": is_atk, "motivo": motivo})
    return pd.DataFrame(razones, columns=["event_id", "timestamp_real", "src_ip",
                                          "user", "event_type", "is_attack_auto", "motivo"])
