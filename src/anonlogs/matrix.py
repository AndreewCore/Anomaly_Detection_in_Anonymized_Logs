"""Expansión de la matriz de experimentos y cálculo del ``run_id`` determinista."""

import hashlib
import itertools
import json
from dataclasses import asdict, dataclass

# Pares (tratamiento, campo) con sentido. ip_generalizada solo transforma IPs,
# así que con "usuario" o "ambos" sería un tratamiento distinto disfrazado (decisión D3).
VALID_TREATMENTS: frozenset[tuple[str, str]] = frozenset({
    ("original", "ninguno"),
    ("suprimida", "usuario"), ("suprimida", "ip"), ("suprimida", "ambos"),
    ("seudonimizada", "usuario"), ("seudonimizada", "ip"), ("seudonimizada", "ambos"),
    ("ip_generalizada", "ip"),
})

# Detectores deterministas: se ejecutan una sola vez por combinación (seed = None).
SEEDLESS_DETECTORS: frozenset[str] = frozenset({"umbral"})


@dataclass(frozen=True)
class RunSpec:
    """Una combinación concreta de la matriz, es decir, un run."""

    dataset: str
    tratamiento: str
    campo: str
    rule_set: str
    features: tuple[str, ...]
    window_seconds: int
    detector: str
    seed: int | None

    @property
    def run_id(self) -> str:
        """Identificador estable: ``<dataset>__<12 hex del SHA-1 de la combinación>``.

        Se serializa con claves ordenadas, así reordenar el YAML no cambia el id
        y la reanudación no repite runs ya hechos.
        """
        canonical = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]
        return f"{self.dataset}__{digest}"


def expand_matrix(matrix: dict) -> list[RunSpec]:
    """Expande un ``matrix_*.yaml`` ya cargado en la lista de runs válidos.

    Args:
        matrix: diccionario con ``datasets``, ``treatments``, ``rule_sets``,
            ``window_seconds``, ``detectors`` y ``seeds``.

    Returns:
        Runs únicos, en orden estable. Los detectores sin semilla aparecen una vez.

    Raises:
        ValueError: si algún par (tratamiento, campo) no está en ``VALID_TREATMENTS``.
    """
    pairs = [(t["tratamiento"], t["campo"]) for t in matrix["treatments"]]
    invalid = [p for p in pairs if p not in VALID_TREATMENTS]
    if invalid:
        raise ValueError(f"Pares (tratamiento, campo) no válidos: {invalid}")

    runs: dict[str, RunSpec] = {}
    for dataset, (trat, campo), (rs_name, feats), window, detector in itertools.product(
        matrix["datasets"], pairs, matrix["rule_sets"].items(),
        matrix["window_seconds"], matrix["detectors"],
    ):
        seeds = [None] if detector in SEEDLESS_DETECTORS else matrix["seeds"]
        for seed in seeds:
            spec = RunSpec(dataset, trat, campo, rs_name, tuple(feats), int(window), detector, seed)
            runs.setdefault(spec.run_id, spec)
    return list(runs.values())
