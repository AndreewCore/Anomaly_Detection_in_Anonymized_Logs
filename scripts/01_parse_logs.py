"""Etapa 1: parsea los logs crudos a data/interim/<dataset>/ y une el Ground Truth por event_id.

Uso:
    python scripts/01_parse_logs.py --datasets lab_concentrado loghub_openssh
"""

import argparse


def main() -> None:
    """Lee los argumentos y ejecuta la etapa."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="configs/experiment.yaml")
    parser.add_argument("--datasets", nargs="+", help="por defecto, todos los de experiment.yaml")
    parser.parse_args()
    raise NotImplementedError


if __name__ == "__main__":
    main()
