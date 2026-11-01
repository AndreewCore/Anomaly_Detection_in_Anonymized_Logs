# scripts/ — Pipeline reproducible por línea de comandos

- Se ejecutan **en orden numérico** desde la raíz del repo con el venv activo: `python scripts/01_parse_logs.py ...`.
- Cada script solo orquesta: la lógica vive en `src/anonlogs/`. Aquí no se copia código del paquete.
- `05_build_tables.py` reconstruye todas las tablas solo a partir de `results/runs/`.
- Aquí no van notebooks, datos ni resultados.
