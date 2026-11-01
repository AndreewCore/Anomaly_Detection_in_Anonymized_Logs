"""Carga de la configuración del experimento (YAML) y de los secretos (.env)."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: str | Path) -> dict:
    """Lee un archivo YAML y lo devuelve como diccionario.

    Las rutas relativas se resuelven contra la raíz del repo, para que los
    scripts funcionen igual sin importar desde qué carpeta se ejecuten.
    """
    path = Path(path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_salt() -> bytes:
    """Devuelve el salt secreto de seudonimización (``ANON_SALT`` en ``.env``).

    Raises:
        RuntimeError: si falta o sigue con el valor de ejemplo; seudonimizar con
            un salt conocido equivale a no anonimizar.
    """
    load_dotenv(REPO_ROOT / ".env")
    salt = os.getenv("ANON_SALT", "")
    if not salt or salt.startswith("reemplazar"):
        raise RuntimeError("Define ANON_SALT en .env (pídelo por el canal privado del grupo).")
    return salt.encode("utf-8")
