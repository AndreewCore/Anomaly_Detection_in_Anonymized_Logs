"""Etapa 0: descarga el dataset OpenSSH de Loghub a ``data/raw/loghub/``.

Uso:
    python scripts/00_download_loghub.py
    python scripts/00_download_loghub.py --force   # vuelve a descargar
"""

import argparse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEST = REPO_ROOT / "data" / "raw" / "loghub"

# Muestra de 2k líneas del repositorio logpai/loghub. Se usa la URL "raw": la de
# github.com/.../blob/... devuelve la página HTML, no el log.
# TODO: decidir si además se usa el log completo (publicado en Zenodo por Loghub).
LOGHUB_OPENSSH_URL = "https://raw.githubusercontent.com/logpai/loghub/master/OpenSSH/OpenSSH_2k.log"


def download(url: str, dest_dir: Path, force: bool = False) -> Path:
    """Descarga ``url`` en ``dest_dir`` y devuelve la ruta del archivo.

    Si el archivo ya existe y no se pide ``force``, no descarga nada. Se escribe en
    un ``.part`` y se renombra al final, para que una descarga cortada no quede
    como un archivo válido a medias.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / url.rsplit("/", 1)[-1]
    if target.exists() and not force:
        print(f"Ya existe, no se descarga: {target}")
        return target

    tmp = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(url, timeout=60) as resp:
        content_type = resp.headers.get("Content-Type", "")
        if "html" in content_type:
            raise SystemExit(f"La URL devolvió HTML, no un log ({content_type}). ¿Es una URL /blob/ en vez de raw?")
        tmp.write_bytes(resp.read())
    tmp.replace(target)
    lines = sum(1 for _ in target.open(encoding="utf-8", errors="replace"))
    print(f"Descargado: {target} ({target.stat().st_size:,} bytes, {lines:,} líneas)")
    return target


def main() -> None:
    """Lee los argumentos y descarga el log OpenSSH de Loghub."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", type=Path, default=DEST)
    parser.add_argument("--force", action="store_true", help="descarga aunque el archivo ya exista")
    args = parser.parse_args()
    download(LOGHUB_OPENSSH_URL, args.dest, args.force)


if __name__ == "__main__":
    main()
