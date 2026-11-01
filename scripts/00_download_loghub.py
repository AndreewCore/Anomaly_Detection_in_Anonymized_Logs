"""Etapa 0: descarga el dataset OpenSSH de Loghub a ``data/raw/loghub/``.

Uso:
    python scripts/00_download_loghub.py
"""

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEST = REPO_ROOT / "data" / "raw" / "loghub"

# TODO: confirmar la URL oficial del log OpenSSH de Loghub (repositorio logpai/loghub
#       en GitHub y/o su registro en Zenodo) y si se usa la muestra de 2k líneas o el
#       log completo. No se deja una URL sin verificar.
LOGHUB_OPENSSH_URL: str | None = None


def main() -> None:
    """Descarga el archivo a ``DEST``; si ya existe, no hace nada."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", type=Path, default=DEST)
    parser.parse_args()
    if LOGHUB_OPENSSH_URL is None:
        raise SystemExit("Falta definir LOGHUB_OPENSSH_URL (ver TODO en este script).")
    raise NotImplementedError


if __name__ == "__main__":
    main()
